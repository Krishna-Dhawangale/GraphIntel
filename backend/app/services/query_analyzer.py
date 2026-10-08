from dataclasses import dataclass, field
import re
from typing import List, Optional

YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")

RELATIONSHIP_KEYWORDS = {
    "CEO_OF": ["ceo", "chief executive", "led", "leader", "heads"],
    "FOUNDED": ["founded", "co-founded", "founder", "established", "started"],
    "WORKED_AT": ["worked at", "employed", "employee", "former", "ex-", "veteran of"],
    "ACQUIRED": ["acquired", "bought", "purchased", "acquisition", "takeover"],
    "INVESTED_IN": ["invested", "backer", "funding", "investor"],
    "DEVELOPED": ["developed", "launched", "created", "built", "released"],
    "COMPETES_WITH": ["competes", "competitor", "rival", "vs"],
    "PARTNERED_WITH": ["partnered", "partnership", "alliance"],
}

NUMERICAL_FINANCIAL_KEYWORDS = [
    "revenue", "profit", "ebitda", "margin", "cash flow", "earnings",
    "growth rate", "guidance", "balance sheet", "net income", "financials", "operating expenses"
]


@dataclass
class QueryAnalysis:
    question: str
    entities: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    temporal_years: List[int] = field(default_factory=list)
    suggested_mode: str = "hybrid"  # "vector", "graph", "hybrid"
    suggested_hops: int = 1
    is_financial_metric: bool = False


class QueryAnalyzer:
    """Analyzes natural language queries to extract intent, entities, temporal anchors, and retrieval strategy."""

    def analyze(self, query: str) -> QueryAnalysis:
        cleaned = query.strip()
        analysis = QueryAnalysis(question=cleaned)

        # 1. Extract temporal years
        years = [int(y) for y in YEAR_PATTERN.findall(cleaned)]
        analysis.temporal_years = sorted(list(set(years)))

        # 2. Check for financial / numerical metrics
        lower_q = cleaned.lower()
        if any(kw in lower_q for kw in NUMERICAL_FINANCIAL_KEYWORDS):
            analysis.is_financial_metric = True

        # 3. Detect relationships
        detected_rels = []
        for rel, kws in RELATIONSHIP_KEYWORDS.items():
            if any(kw in lower_q for kw in kws):
                detected_rels.append(rel)
        analysis.relationships = detected_rels

        # 4. Extract potential capitalized entity mentions
        # E.g. "Microsoft", "Google", "XYZ AI", "Satya Nadella"
        words = re.findall(r"\b[A-Z][a-zA-Z0-9&.]*(?:\s+[A-Z][a-zA-Z0-9&.]*)*\b", cleaned)
        filtered_words = [
            w for w in words
            if w.lower() not in {"what", "who", "which", "where", "when", "why", "how", "is", "was", "are", "the", "a", "in"}
        ]
        analysis.entities = filtered_words

        # 5. Determine multi-hop complexity
        # Multiple relationships mentioned (e.g. acquired + founded + worked at) indicates multi-hop traversal
        if len(detected_rels) >= 2 or ("who" in lower_q and "acquired" in lower_q and "founded" in lower_q):
            analysis.suggested_hops = min(3, len(detected_rels) + 1)
            analysis.suggested_mode = "hybrid"
        elif analysis.is_financial_metric and not detected_rels:
            analysis.suggested_hops = 1
            analysis.suggested_mode = "vector"
        elif detected_rels and analysis.entities:
            analysis.suggested_hops = 1
            analysis.suggested_mode = "hybrid"
        else:
            analysis.suggested_hops = 1
            analysis.suggested_mode = "hybrid"

        return analysis
