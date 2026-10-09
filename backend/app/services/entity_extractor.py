from abc import ABC, abstractmethod
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.core.logging import logger
from app.providers.llm.base import LLMProvider
from app.providers.llm.factory import get_llm_provider
from app.schemas.graph import (
    EntityCreate,
    NodeType,
    RelationshipCreate,
    RelationshipType,
)

VALID_NODE_TYPES = {t.value for t in NodeType}
VALID_RELATIONSHIPS = {r.value for r in RelationshipType}

YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")
RANGE_YEAR_PATTERN = re.compile(
    r"\b(?:from\s+)?(19\d\d|20\d\d)\s*(?:to|-|until)\s*(19\d\d|20\d\d)\b",
    re.IGNORECASE,
)


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
    "acquire", "acquir", "found", "ceo", "chief executive", "worked", "former", "invest", "launch", "develop", "creat"
)

ACQUISITION_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})\s+(?:has\s+)?acquired\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:in|for|during)\s+(\d{4}))?[.,\n]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})\s+(?:was\s+)?acquired\s+by\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:in|for|during)\s+(\d{4}))?[.,\n]",
        re.IGNORECASE,
    ),
]

FOUNDING_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})\s+(?:co-)?founded\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:in|back\s+in)\s+(\d{4}))?[.,\n]",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})\s+(?:was\s+)?founded\s+by\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:in|back\s+in)\s+(\d{4}))?[.,\n]",
        re.IGNORECASE,
    ),
]

CEO_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3})\s+(?:served\s+as|is|was|became)\s+(?:the\s+)?CEO\s+of\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:from\s+(\d{4})\s+to\s+(\d{4})|in\s+(\d{4})|since\s+(\d{4})))?[.,\n]",
        re.IGNORECASE,
    ),
]

WORKED_AT_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3})\s+(?:previously\s+)?worked\s+at\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:from\s+(\d{4})\s+to\s+(\d{4})|until\s+(\d{4})|in\s+(\d{4})))?[.,\n]",
        re.IGNORECASE,
    ),
    re.compile(
        r"former\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})\s+(?:employee|engineer|executive|veteran)\s+([A-Z][A-Za-z.]+(?:\s+[A-Z][A-Za-z.]+){0,3})[,\s]",
        re.IGNORECASE,
    ),
]

INVESTMENT_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})\s+invested\s+in\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:in\s+(\d{4})))?[.,\n]",
        re.IGNORECASE,
    ),
]

PRODUCT_PATTERNS = [
    re.compile(
        r"\b([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})\s+(?:developed|launched|released|created)\s+([A-Z][A-Za-z0-9&.]+(?:\s+[A-Z][A-Za-z0-9&.]+){0,4})(?:\s+(?:in\s+(\d{4})))?[.,\n]",
        re.IGNORECASE,
    ),
]

ARTICLE_PREFIX_RE = re.compile(r"^(the|a|an)\s+", re.IGNORECASE)
TRAILING_PUNCT_RE = re.compile(r"[,\.;:]$")


class RuleBasedEntityExtractor(BaseEntityExtractor):
    """High-precision deterministic rule and regex extractor for financial/market intelligence text."""

    def __init__(self):
        self.acquisition_patterns = ACQUISITION_PATTERNS
        self.founding_patterns = FOUNDING_PATTERNS
        self.ceo_patterns = CEO_PATTERNS
        self.worked_at_patterns = WORKED_AT_PATTERNS
        self.investment_patterns = INVESTMENT_PATTERNS
        self.product_patterns = PRODUCT_PATTERNS

    def _clean_entity_name(self, name: str) -> str:
        cleaned = ARTICLE_PREFIX_RE.sub("", name.strip())
        cleaned = TRAILING_PUNCT_RE.sub("", cleaned).strip()
        return cleaned

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

        def add_entity(name: str, ent_type: str) -> str:
            clean = self._clean_entity_name(name)
            key = f"{ent_type}:{clean.lower()}"
            if key not in entities_dict and len(clean) > 1:
                entities_dict[key] = EntityCreate(
                    name=clean,
                    type=ent_type if ent_type in VALID_NODE_TYPES else "Company",
                    confidence=0.92,
                    source_document_id=document_id,
                    source_chunk_id=chunk_id,
                    source_page=page_number,
                )
            return clean

        # Check acquisitions
        for p in self.acquisition_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                if "by" in match.group(0).lower():
                    target_name = add_entity(groups[0], "Startup")
                    acquirer_name = add_entity(groups[1], "Company")
                else:
                    acquirer_name = add_entity(groups[0], "Company")
                    target_name = add_entity(groups[1], "Startup")

                year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                relationships.append(
                    RelationshipCreate(
                        source_entity_id=acquirer_name,  # Temporary name placeholder before resolution
                        target_entity_id=target_name,
                        relationship_type="ACQUIRED",
                        confidence=0.95,
                        source_document_id=document_id,
                        source_chunk_id=chunk_id,
                        source_page=page_number,
                        valid_from=year,
                        valid_to=year,
                    )
                )

        # Check founding
        for p in self.founding_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                if "by" in match.group(0).lower():
                    startup_name = add_entity(groups[0], "Startup")
                    founder_name = add_entity(groups[1], "Person")
                else:
                    founder_name = add_entity(groups[0], "Person")
                    startup_name = add_entity(groups[1], "Startup")

                year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                relationships.append(
                    RelationshipCreate(
                        source_entity_id=founder_name,
                        target_entity_id=startup_name,
                        relationship_type="FOUNDED",
                        confidence=0.95,
                        source_document_id=document_id,
                        source_chunk_id=chunk_id,
                        source_page=page_number,
                        valid_from=year,
                        valid_to=None,
                    )
                )

        # Check CEO roles
        for p in self.ceo_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                person_name = add_entity(groups[0], "Person")
                company_name = add_entity(groups[1], "Company")
                v_from, v_to = None, None
                if groups[2] and groups[3]:
                    v_from, v_to = int(groups[2]), int(groups[3])
                elif groups[4]:
                    v_from, v_to = int(groups[4]), int(groups[4])
                elif groups[5]:
                    v_from = int(groups[5])

                relationships.append(
                    RelationshipCreate(
                        source_entity_id=person_name,
                        target_entity_id=company_name,
                        relationship_type="CEO_OF",
                        confidence=0.95,
                        source_document_id=document_id,
                        source_chunk_id=chunk_id,
                        source_page=page_number,
                        valid_from=v_from,
                        valid_to=v_to,
                    )
                )

        # Check worked at
        for p in self.worked_at_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                if "former" in match.group(0).lower():
                    company_name = add_entity(groups[0], "Company")
                    person_name = add_entity(groups[1], "Person")
                    v_from, v_to = None, None
                else:
                    person_name = add_entity(groups[0], "Person")
                    company_name = add_entity(groups[1], "Company")
                    v_from = int(groups[2]) if len(groups) > 2 and groups[2] else None
                    v_to = int(groups[3]) if len(groups) > 3 and groups[3] else None

                relationships.append(
                    RelationshipCreate(
                        source_entity_id=person_name,
                        target_entity_id=company_name,
                        relationship_type="WORKED_AT",
                        confidence=0.92,
                        source_document_id=document_id,
                        source_chunk_id=chunk_id,
                        source_page=page_number,
                        valid_from=v_from,
                        valid_to=v_to,
                    )
                )

        # Check investments
        for p in self.investment_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                investor_name = add_entity(groups[0], "Investor")
                target_name = add_entity(groups[1], "Startup")
                year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                relationships.append(
                    RelationshipCreate(
                        source_entity_id=investor_name,
                        target_entity_id=target_name,
                        relationship_type="INVESTED_IN",
                        confidence=0.93,
                        source_document_id=document_id,
                        source_chunk_id=chunk_id,
                        source_page=page_number,
                        valid_from=year,
                        valid_to=year,
                    )
                )

        # Check products
        for p in self.product_patterns:
            for match in p.finditer(text):
                groups = match.groups()
                comp_name = add_entity(groups[0], "Company")
                prod_name = add_entity(groups[1], "Product")
                year = int(groups[2]) if len(groups) > 2 and groups[2] else None
                relationships.append(
                    RelationshipCreate(
                        source_entity_id=comp_name,
                        target_entity_id=prod_name,
                        relationship_type="DEVELOPED",
                        confidence=0.90,
                        source_document_id=document_id,
                        source_chunk_id=chunk_id,
                        source_page=page_number,
                        valid_from=year,
                        valid_to=None,
                    )
                )

        return list(entities_dict.values()), relationships


class LLMEntityExtractor(BaseEntityExtractor):
    """LLM-based entity and relationship extractor with fast circuit breaker and fallback."""

    def __init__(self, llm: Optional[LLMProvider] = None):
        self.llm = llm or get_llm_provider()
        self.fallback = RuleBasedEntityExtractor()
        self._circuit_broken = False

    async def extract(
        self,
        text: str,
        document_id: str,
        chunk_id: str,
        page_number: Optional[int] = None,
    ) -> Tuple[List[EntityCreate], List[RelationshipCreate]]:
        if not text or len(text) < 10:
            return [], []

        if self._circuit_broken or getattr(settings, "LLM_PROVIDER", "mock") == "mock":
            return await self.fallback.extract(text, document_id, chunk_id, page_number)

        # Pre-filter: if no relationship keywords exist, fallback immediately
        text_lower = text.lower()
        if not any(k in text_lower for k in TRIGGER_KEYWORDS):
            return [], []

        prompt = f"""You are a Knowledge Graph Information Extraction specialist.
Analyze the following text and extract entities and relationships.

ALLOWED ENTITY TYPES:
{', '.join(sorted(list(VALID_NODE_TYPES)))}

ALLOWED RELATIONSHIPS:
{', '.join(sorted(list(VALID_RELATIONSHIPS)))}

INSTRUCTIONS:
1. Extract canonical entity names, appropriate entity type, confidence score (0.0 to 1.0), and any aliases.
2. Extract relationships between extracted entities with temporal years (valid_from, valid_to) if mentioned.
3. NEVER make up relationships without direct evidence in the text.
4. Output STRICT JSON only with keys "entities" and "relationships".

TEXT:
\"\"\"
{text}
\"\"\"

JSON output:
{{
  "entities": [
    {{"name": "Microsoft", "type": "Company", "aliases": ["MSFT"], "confidence": 0.98}}
  ],
  "relationships": [
    {{"source": "Microsoft", "target": "XYZ AI", "type": "ACQUIRED", "valid_from": 2025, "valid_to": 2025, "confidence": 0.95}}
  ]
}}
"""
        messages = [
            {"role": "system", "content": "You output only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self.llm.generate(messages, temperature=0.0)
            content = response.content.strip()
            # Extract JSON block if wrapped in markdown
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                content = match.group(0)

            data = json.loads(content)
            extracted_entities: List[EntityCreate] = []
            for item in data.get("entities", []):
                name = item.get("name", "").strip()
                etype = item.get("type", "Company")
                if name and etype in VALID_NODE_TYPES:
                    extracted_entities.append(
                        EntityCreate(
                            name=name,
                            type=etype,
                            aliases=item.get("aliases", []),
                            confidence=float(item.get("confidence", 0.9)),
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                        )
                    )

            extracted_rels: List[RelationshipCreate] = []
            for r in data.get("relationships", []):
                src = r.get("source", "").strip()
                tgt = r.get("target", "").strip()
                rtype = r.get("type", "").upper()
                if src and tgt and rtype in VALID_RELATIONSHIPS:
                    extracted_rels.append(
                        RelationshipCreate(
                            source_entity_id=src,
                            target_entity_id=tgt,
                            relationship_type=rtype,
                            confidence=float(r.get("confidence", 0.9)),
                            source_document_id=document_id,
                            source_chunk_id=chunk_id,
                            source_page=page_number,
                            valid_from=r.get("valid_from"),
                            valid_to=r.get("valid_to"),
                        )
                    )

            if extracted_entities or extracted_rels:
                return extracted_entities, extracted_rels

        except Exception as e:
            self._circuit_broken = True
            logger.warning(f"LLM entity extraction tripped circuit breaker ({e}), using fast rule-based fallback.")

        return await self.fallback.extract(text, document_id, chunk_id, page_number)
