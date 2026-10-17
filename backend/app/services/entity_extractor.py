from abc import ABC, abstractmethod
import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.providers.llm.base import LLMProvider
from app.providers.llm.factory import get_llm_provider
from app.schemas.graph import (
    EntityCreate,
    ExtractedTriple,
    NodeType,
    RelationshipCreate,
    RelationshipType,
)

VALID_NODE_TYPES: Set[str] = {t.value for t in NodeType}
VALID_RELATIONSHIPS: Set[str] = {r.value for r in RelationshipType}

YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")
RANGE_YEAR_PATTERN = re.compile(
    r"\b(?:from\s+)?(19\d\d|20\d\d)\s*(?:to|-|until)\s*(19\d\d|20\d\d)\b",
    re.IGNORECASE,
)

ISOLATED_PRONOUNS: Set[str] = {
    "he", "she", "it", "they", "we", "i", "you", "his", "her", "their", "our", "my",
    "your", "him", "them", "us", "me", "its", "someone", "anyone", "everyone", "nobody", "one",
}

GENERIC_WORDS: Set[str] = {
    "company", "companies", "startup", "startups", "corporation", "firm", "firms", "business",
    "businesses", "organization", "entity", "entities", "the", "a", "an", "this", "that", "these",
    "those", "which", "who", "whom", "whose", "what", "where", "when", "how", "why", "and", "or",
    "but", "in", "on", "at", "to", "for", "with", "by", "from", "up", "about", "into", "over",
    "after", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
    "did", "can", "could", "will", "would", "shall", "should", "may", "might", "must", "technology",
    "product", "products", "services", "solutions", "industry", "market", "executive", "officer",
    "director", "employee", "founder", "investor", "billion", "million", "percent", "shares",
    "stock", "revenue", "income", "goodwill", "balance", "net", "gross", "value", "assets",
    "material", "materials", "directorship", "ip", "client", "customer", "customers", "vendor",
    "partner", "newly", "internally", "combination", "reduction", "portion", "part", "chief",
    "president", "vice", "chair", "board", "member", "senior", "experience", "operational",
    "strategic", "management", "developed technology", "technology intangible asset", "none",
}

ARTICLE_PREFIX_RE = re.compile(r"^(the|a|an|and|or|as|well|with|by|from|under|to|in|of|for)\s+", re.IGNORECASE)
TRAILING_PUNCT_RE = re.compile(r"[,\.;:\?!\"'\(\)\[\]]+$")
LEADING_PUNCT_RE = re.compile(r"^[,\.;:\?!\"'\(\)\[\]]+")

PERSON_CANDIDATE_RE = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+)\b")
NON_PERSON_TOKENS = {
    "Managing Partner", "Square Wave", "Director Since", "Chief Executive", "Senior Leadership",
    "Computer Sciences", "Dartmouth College", "National Football", "Public Company", "Financial Expert",
    "Tensilica Inc", "Daisy Systems", "PepsiCo Inc", "Quantum Corp", "Synopsys Inc", "Cadence Design",
}


def clean_and_validate_entity(name: str) -> Optional[str]:
    """
    Validates and cleans an entity name:
    - Strips leading articles/conjunctions
    - Strips surrounding punctuation
    - Rejects isolated pronouns, stop words, generic business words, and fragments
    - Ensures minimum token quality and proper capitalization
    """
    if not name or not isinstance(name, str):
        return None
    cleaned = name.strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    while True:
        new_cleaned = ARTICLE_PREFIX_RE.sub("", cleaned).strip()
        if new_cleaned == cleaned:
            break
        cleaned = new_cleaned

    cleaned = LEADING_PUNCT_RE.sub("", cleaned).strip()
    cleaned = TRAILING_PUNCT_RE.sub("", cleaned).strip()

    if len(cleaned) < 2 or len(cleaned) > 60:
        return None

    cleaned_lower = cleaned.lower()
    if cleaned_lower in ISOLATED_PRONOUNS or cleaned_lower in GENERIC_WORDS:
        return None

    if not re.search(r"[a-zA-Z]", cleaned):
        return None

    words = cleaned.split()
    first_word = words[0]
    # Entity must start with an uppercase letter or acronym
    if not (first_word[0].isupper() or (len(first_word) > 1 and first_word[1].isupper())):
        return None

    # Reject fragments starting with verbs or generic adjectives
    if first_word.lower() in {
        "scaled", "fill", "filled", "be", "record", "recorded", "represent",
        "represented", "held", "internally", "gross", "value", "net", "reduction",
    }:
        return None

    # Reject if trailing word is a preposition/conjunction
    if words[-1].lower() in {"of", "and", "or", "in", "to", "for", "with", "by", "that", "which"}:
        return None

    return cleaned


COMPANY_SUFFIX_SET = {
    "inc", "corp", "corporation", "llc", "ltd", "ventures", "systems",
    "technologies", "group", "holdings", "partners", "capital", "wave", "disk", "drive"
}

PERSON_TITLE_WORDS = {
    "financial", "expert", "general", "manager", "managing", "partner", "executive", "vice",
    "senior", "president", "independent", "director", "chief", "marketing", "public", "company",
    "engineering", "private", "family", "office", "dartmouth", "college", "oregon", "state",
    "stanford", "university", "quantum", "research", "hard", "disk", "drive", "none", "age",
    "boards", "committees", "member", "operations", "emerging", "models", "other", "current"
}


def resolve_pronoun_antecedent(
    pronoun: str, chunk_text: str, match_pos: int
) -> Optional[Tuple[str, str]]:
    """
    Resolve third-person pronouns ('he', 'she', 'his', 'her') to the unambiguous named antecedent
    in the preceding context window of the chunk.
    Returns (canonical_name, 'Person') if unambiguous, else None.
    """
    pro_lower = pronoun.strip().lower()
    if pro_lower not in {"he", "she", "his", "her"}:
        return None

    raw_preceding = chunk_text[max(0, match_pos - 450):match_pos]
    preceding = re.sub(r"\s+", " ", raw_preceding)

    honorific_matches = re.findall(r"\b(Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Z][a-z]+)\b", preceding)

    candidates = PERSON_CANDIDATE_RE.findall(preceding)
    valid: List[str] = []
    for c in candidates:
        words = c.strip().split()
        if any(w.lower() in PERSON_TITLE_WORDS or w.lower() in COMPANY_SUFFIX_SET for w in words):
            continue
        cleaned = clean_and_validate_entity(c)
        if cleaned:
            valid.append(cleaned)

    if not valid and not honorific_matches:
        return None

    # If honorific matched a last name, associate with full name ending with that last name
    if honorific_matches:
        last_name = honorific_matches[-1][1]
        for v in reversed(valid):
            if v.endswith(last_name):
                return v, "Person"
        return f"{honorific_matches[-1][0]} {last_name}", "Person"

    if valid:
        unique = list(dict.fromkeys(valid))
        return unique[-1], "Person"

    return None


class BaseEntityExtractor(ABC):
    """Abstract interface for entity and relationship extraction."""

    @abstractmethod
    async def extract(
        self,
        text: str,
        document_id: str,
        chunk_id: str,
        page_number: Optional[int] = None,
    ) -> Tuple[List[EntityCreate], List[RelationshipCreate]]:
        """Extract entities and evidence-backed relationships from chunk text."""
        pass


TRIGGER_KEYWORDS = (
    "acquire", "acquir", "found", "ceo", "chief executive", "worked", "former", "invest", "launch", "develop", "creat", "partner"
)

WORD_TOKEN = r"(?:[A-Z][a-zA-Z0-9&]+|[A-Z]\.?)"
PROPER_NAME = rf"(?:(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+)?{WORD_TOKEN}(?:\s+{WORD_TOKEN}){{0,3}}"

ACQUISITION_PATTERNS = [
    re.compile(
        rf"({PROPER_NAME})\s+(?:has\s+)?acquired\s+({PROPER_NAME})(?:\s+(?:in|for|during)\s+(\d{{4}}))?(?=[.,\n]|\s+(?:in|for|during|\Z)|$)",
    ),
    re.compile(
        rf"({PROPER_NAME})\s+(?:was\s+)?acquired\s+by\s+({PROPER_NAME})(?:\s+(?:in|for|during)\s+(\d{{4}}))?(?=[.,\n]|\s+(?:in|for|during|\Z)|$)",
    ),
]

FOUNDING_PATTERNS = [
    re.compile(
        rf"(\b(?:[Hh]e|[Ss]he)\b|{PROPER_NAME})\s+(?:co-)?founded\s+({PROPER_NAME})(?:\s+(?:in|back\s+in)\s+(\d{{4}}))?(?=[.,\n]|\s+(?:in|back|\Z)|$)",
    ),
    re.compile(
        rf"({PROPER_NAME})\s+(?:was\s+)?(?:co-)?founded\s+by\s+(?:former\s+[A-Za-z0-9&.]+\s+(?:researcher|engineer|executive|employee)\s+)?({PROPER_NAME})(?:\s+(?:in|back\s+in)\s+(\d{{4}}))?(?=[.,\n]|\s+(?:in|back|\Z)|$)",
    ),
]

CEO_PATTERNS = [
    re.compile(
        rf"({PROPER_NAME})\s+(?:served\s+as|is|was|became)\s+(?:the\s+)?(?:President\s+and\s+)?(?:Chief\s+Executive\s+Officer|CEO)\s+of\s+({PROPER_NAME})(?:\s+(?:from\s+(\d{{4}})\s+to\s+(\d{{4}})|in\s+(\d{{4}})|since\s+(\d{{4}})))?(?=[.,\n]|\s+(?:from|in|since|\Z)|$)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"({PROPER_NAME})\s+has\s+served\s+as\s+a\s+(?:Director|board\s+member)\s+of\s+({PROPER_NAME})(?:\s+since\s+(\d{{4}}))?(?=[.,\n]|\s+(?:since|\Z)|$)",
        re.IGNORECASE,
    ),
]

WORKED_AT_PATTERNS = [
    re.compile(
        rf"(\b(?:[Hh]e|[Ss]he)\b|{PROPER_NAME})\s+(?:previously\s+)?worked\s+at\s+({PROPER_NAME})(?:\s+(?:from\s+(\d{{4}})\s+to\s+(\d{{4}})|until\s+(\d{{4}})|in\s+(\d{{4}})))?(?=[.,\n]|\s+(?:from|until|in|\Z)|$)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"former\s+({PROPER_NAME})\s+(?:employee|engineer|researcher|executive|veteran)\s+({PROPER_NAME})(?=[.,\n]|$)",
        re.IGNORECASE,
    ),
]

INVESTMENT_PATTERNS = [
    re.compile(
        rf"({PROPER_NAME})\s+invested\s+in\s+({PROPER_NAME})(?:\s+(?:in\s+(\d{{4}})))?(?=[.,\n]|\s+(?:in|\Z)|$)",
    ),
]

PRODUCT_PATTERNS = [
    re.compile(
        rf"({PROPER_NAME})\s+(?:developed|launched|released|created)\s+({PROPER_NAME})(?:\s+(?:in\s+(\d{{4}})))?(?=[.,\n]|\s+(?:in|\Z)|$)",
    ),
]


class RuleBasedEntityExtractor(BaseEntityExtractor):
    """High-precision, schema-validated deterministic rule and regex extractor for financial and corporate intelligence text."""

    def __init__(self):
        self.acquisition_patterns = ACQUISITION_PATTERNS
        self.founding_patterns = FOUNDING_PATTERNS
        self.ceo_patterns = CEO_PATTERNS
        self.worked_at_patterns = WORKED_AT_PATTERNS
        self.investment_patterns = INVESTMENT_PATTERNS
        self.product_patterns = PRODUCT_PATTERNS

    async def extract(
        self,
        text: str,
        document_id: str,
        chunk_id: str,
        page_number: Optional[int] = None,
    ) -> Tuple[List[EntityCreate], List[RelationshipCreate]]:
        if not text or len(text) < 10:
            return [], []

        text_lower = text.lower()
        if not any(k in text_lower for k in TRIGGER_KEYWORDS):
            return [], []

        entities_dict: Dict[str, EntityCreate] = {}
        relationships: List[RelationshipCreate] = []

        def get_evidence_quote(start_idx: int, end_idx: int) -> str:
            # Expand to sentence boundary or up to 150 chars around match
            s_start = max(0, text.rfind(".", 0, start_idx) + 1)
            s_end = text.find(".", end_idx)
            if s_end == -1:
                s_end = min(len(text), end_idx + 40)
            else:
                s_end = min(len(text), s_end + 1)
            quote = text[s_start:s_end].strip()
            return quote if quote else text[start_idx:end_idx]

        def record_entity(name: str, ent_type: str, conf: float) -> Optional[str]:
            clean = clean_and_validate_entity(name)
            if not clean:
                return None
            val_type = ent_type if ent_type in VALID_NODE_TYPES else "Company"
            key = f"{val_type}:{clean.lower()}"
            if key not in entities_dict:
                entities_dict[key] = EntityCreate(
                    name=clean,
                    type=val_type,
                    confidence=conf,
                    source_document_id=document_id,
                    source_chunk_id=chunk_id,
                    source_page=page_number,
                )
            return clean

        # 1. Acquisitions
        for p in self.acquisition_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                match_text = match.group(0)
                if "by" in match_text.lower():
                    target_raw, acquirer_raw = groups[0], groups[1]
                else:
                    acquirer_raw, target_raw = groups[0], groups[1]

                acquirer_name = record_entity(acquirer_raw, "Company", 0.95)
                target_name = record_entity(target_raw, "Startup", 0.92)

                if acquirer_name and target_name and acquirer_name.lower() != target_name.lower():
                    year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                    quote = get_evidence_quote(match.start(), match.end())
                    relationships.append(
                        RelationshipCreate(
                            source_entity_id=acquirer_name,
                            target_entity_id=target_name,
                            relationship_type="ACQUIRED",
                            confidence=0.95,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            evidence_quote=quote,
                            valid_from=year,
                            valid_to=year,
                        )
                    )

        # 2. Founding
        for p in self.founding_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                match_text = match.group(0)
                if "by" in match_text.lower():
                    startup_raw, founder_raw = groups[0], groups[1]
                else:
                    founder_raw, startup_raw = groups[0], groups[1]

                # Pronoun antecedent resolution if founder is pronoun
                founder_conf = 0.95
                if founder_raw.strip().lower() in ISOLATED_PRONOUNS:
                    resolved = resolve_pronoun_antecedent(founder_raw, text, match.start())
                    if resolved:
                        founder_raw, _ = resolved
                        founder_conf = 0.85
                    else:
                        continue

                founder_name = record_entity(founder_raw, "Person", founder_conf)
                startup_name = record_entity(startup_raw, "Startup", 0.92)

                if founder_name and startup_name and founder_name.lower() != startup_name.lower():
                    year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                    quote = get_evidence_quote(match.start(), match.end())
                    relationships.append(
                        RelationshipCreate(
                            source_entity_id=founder_name,
                            target_entity_id=startup_name,
                            relationship_type="FOUNDED",
                            confidence=founder_conf,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            evidence_quote=quote,
                            valid_from=year,
                            valid_to=None,
                        )
                    )

        # 3. CEO Roles
        for p in self.ceo_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                person_raw, company_raw = groups[0], groups[1]
                person_name = record_entity(person_raw, "Person", 0.95)
                company_name = record_entity(company_raw, "Company", 0.95)

                if person_name and company_name and person_name.lower() != company_name.lower():
                    v_from, v_to = None, None
                    if len(groups) > 3 and groups[2] and groups[3]:
                        v_from, v_to = int(groups[2]), int(groups[3])
                    elif len(groups) > 4 and groups[4]:
                        v_from, v_to = int(groups[4]), int(groups[4])
                    elif len(groups) > 5 and groups[5]:
                        v_from = int(groups[5])
                    elif len(groups) > 2 and groups[2]:
                        v_from = int(groups[2])

                    rel_type = "BOARD_MEMBER_OF" if "director" in match.group(0).lower() or "board" in match.group(0).lower() else "CEO_OF"
                    quote = get_evidence_quote(match.start(), match.end())
                    relationships.append(
                        RelationshipCreate(
                            source_entity_id=person_name,
                            target_entity_id=company_name,
                            relationship_type=rel_type,
                            confidence=0.95,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            evidence_quote=quote,
                            valid_from=v_from,
                            valid_to=v_to,
                        )
                    )

        # 4. Worked At
        for p in self.worked_at_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                match_text = match.group(0)
                if "former" in match_text.lower():
                    company_raw, person_raw = groups[0], groups[1]
                    v_from, v_to = None, None
                else:
                    person_raw, company_raw = groups[0], groups[1]
                    v_from = int(groups[2]) if len(groups) > 2 and groups[2] else None
                    v_to = int(groups[3]) if len(groups) > 3 and groups[3] else None

                person_conf = 0.92
                if person_raw.strip().lower() in ISOLATED_PRONOUNS:
                    resolved = resolve_pronoun_antecedent(person_raw, text, match.start())
                    if resolved:
                        person_raw, _ = resolved
                        person_conf = 0.82
                    else:
                        continue

                person_name = record_entity(person_raw, "Person", person_conf)
                company_name = record_entity(company_raw, "Company", 0.92)

                if person_name and company_name and person_name.lower() != company_name.lower():
                    quote = get_evidence_quote(match.start(), match.end())
                    relationships.append(
                        RelationshipCreate(
                            source_entity_id=person_name,
                            target_entity_id=company_name,
                            relationship_type="WORKED_AT",
                            confidence=person_conf,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            evidence_quote=quote,
                            valid_from=v_from,
                            valid_to=v_to,
                        )
                    )

        # 5. Investments
        for p in self.investment_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                investor_name = record_entity(groups[0], "Investor", 0.92)
                target_name = record_entity(groups[1], "Startup", 0.92)
                if investor_name and target_name and investor_name.lower() != target_name.lower():
                    year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                    quote = get_evidence_quote(match.start(), match.end())
                    relationships.append(
                        RelationshipCreate(
                            source_entity_id=investor_name,
                            target_entity_id=target_name,
                            relationship_type="INVESTED_IN",
                            confidence=0.92,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            evidence_quote=quote,
                            valid_from=year,
                            valid_to=year,
                        )
                    )

        # 6. Products
        for p in self.product_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                comp_raw, prod_raw = groups[0], groups[1]
                comp_name = record_entity(comp_raw, "Company", 0.90)
                prod_name = record_entity(prod_raw, "Product", 0.90)
                if comp_name and prod_name and comp_name.lower() != prod_name.lower():
                    year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                    quote = get_evidence_quote(match.start(), match.end())
                    relationships.append(
                        RelationshipCreate(
                            source_entity_id=comp_name,
                            target_entity_id=prod_name,
                            relationship_type="DEVELOPED",
                            confidence=0.90,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            evidence_quote=quote,
                            valid_from=year,
                            valid_to=None,
                        )
                    )

        return list(entities_dict.values()), relationships


class LLMEntityExtractor(BaseEntityExtractor):
    """Schema-validated LLM-based entity and relationship extractor with rigorous rejection filters and fallback."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm or get_llm_provider()
        self.fallback = RuleBasedEntityExtractor()

    async def extract(
        self,
        text: str,
        document_id: str,
        chunk_id: str,
        page_number: Optional[int] = None,
    ) -> Tuple[List[EntityCreate], List[RelationshipCreate]]:
        if not text or len(text) < 10:
            return [], []

        if getattr(settings, "LLM_PROVIDER", "mock") == "mock":
            return await self.fallback.extract(text, document_id, chunk_id, page_number)

        text_lower = text.lower()
        if not any(k in text_lower for k in TRIGGER_KEYWORDS):
            return [], []

        prompt = f"""You are a Knowledge Graph Information Extraction specialist.
Analyze the following text and extract genuine entities and relationships.

ALLOWED ENTITY TYPES:
{', '.join(sorted(list(VALID_NODE_TYPES)))}

ALLOWED RELATIONSHIPS:
{', '.join(sorted(list(VALID_RELATIONSHIPS)))}

STRICT RULES:
1. NEVER create entities from pronouns ('we', 'he', 'she', 'it', 'they') or generic words ('company', 'startup', 'product', 'shares').
2. Resolve pronouns only if the antecedent person/company is explicitly and unambiguously identified in the text.
3. Every relationship MUST include an exact "evidence_quote" verbatim from the text.
4. Output STRICT JSON only with keys "entities" and "relationships".

TEXT:
\"\"\"
{text}
\"\"\"

JSON output schema:
{{
  "entities": [
    {{"name": "NVIDIA", "type": "Company", "aliases": ["NVDA"], "confidence": 0.98}}
  ],
  "relationships": [
    {{"subject_name": "Jensen Huang", "subject_type": "Person", "predicate": "FOUNDED", "object_name": "NVIDIA", "object_type": "Company", "evidence_quote": "Jensen Huang founded NVIDIA in 1993", "valid_from": 1993, "confidence": 0.95}}
  ]
}}
"""
        messages = [
            {"role": "system", "content": "You output only valid JSON with validated factual triples."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm.generate(messages, temperature=0.0)
            content = response.content.strip()
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                content = match.group(0)

            data = json.loads(content)
            extracted_entities: List[EntityCreate] = []
            extracted_rels: List[RelationshipCreate] = []

            for item in data.get("entities", []):
                raw_name = item.get("name", "")
                clean_name = clean_and_validate_entity(raw_name)
                etype = item.get("type", "Company")
                if clean_name and etype in VALID_NODE_TYPES:
                    conf = max(0.0, min(1.0, float(item.get("confidence", 0.9))))
                    extracted_entities.append(
                        EntityCreate(
                            name=clean_name,
                            type=etype,
                            aliases=[clean_and_validate_entity(a) for a in item.get("aliases", []) if clean_and_validate_entity(a)],
                            confidence=conf,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                        )
                    )

            for r in data.get("relationships", []):
                s_name = clean_and_validate_entity(r.get("subject_name") or r.get("source", ""))
                o_name = clean_and_validate_entity(r.get("object_name") or r.get("target", ""))
                pred = (r.get("predicate") or r.get("type", "")).upper()
                quote = r.get("evidence_quote", "")

                # Verify quote exists in chunk text
                if not quote or quote.lower() not in text_lower:
                    # Look for sentence containing both entities
                    if s_name and o_name:
                        for sent in text.split("."):
                            if s_name.lower() in sent.lower() and o_name.lower() in sent.lower():
                                quote = sent.strip()
                                break

                if (
                    s_name
                    and o_name
                    and s_name.lower() != o_name.lower()
                    and pred in VALID_RELATIONSHIPS
                    and quote
                ):
                    conf = max(0.0, min(1.0, float(r.get("confidence", 0.9))))
                    extracted_rels.append(
                        RelationshipCreate(
                            source_entity_id=s_name,
                            target_entity_id=o_name,
                            relationship_type=pred,
                            confidence=conf,
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            evidence_quote=quote,
                            valid_from=r.get("valid_from"),
                            valid_to=r.get("valid_to"),
                        )
                    )

            if extracted_entities or extracted_rels:
                return extracted_entities, extracted_rels

        except Exception as e:
            logger.warning(f"LLM entity extraction error ({e}), applying rule-based extractor.")

        return await self.fallback.extract(text, document_id, chunk_id, page_number)
