from dataclasses import dataclass, field
from enum import Enum
import re
from typing import List, Optional

YEAR_PATTERN = re.compile(r"\b(19\d\d|20\d\d)\b")

RELATIONSHIP_KEYWORDS = {
    "CEO_OF": ["ceo", "chief executive", "led", "leader", "heads", "president"],
    "FOUNDED": ["founded", "co-founded", "founder", "established", "started", "inception"],
    "WORKED_AT": ["worked at", "employed", "employee", "former", "ex-", "veteran of", "served as", "joined"],
    "ACQUIRED": ["acquired", "bought", "purchased", "acquisition", "takeover"],
    "INVESTED_IN": ["invested", "backer", "funding", "investor"],
    "DEVELOPED": ["developed", "launched", "created", "built", "released", "architecture"],
    "COMPETES_WITH": ["competes", "competitor", "rival", "vs"],
    "PARTNERED_WITH": ["partnered", "partnership", "alliance"],
}

NUMERICAL_FINANCIAL_KEYWORDS = [
    "revenue", "profit", "ebitda", "margin", "cash flow", "earnings", "eps", "diluted eps",
    "growth rate", "guidance", "balance sheet", "net income", "operating income", "financials",
    "operating expenses", "gross margin", "capital expenditures", "fiscal", "q1", "q2", "q3", "q4",
    "dividend", "repurchase", "shareholders", "debt", "cash", "market cap", "valuation", "billions",
    "millions", "$", "dollars", "spend", "cost", "token throughput", "gigawatts"
]

SPECULATIVE_FUTURE_KEYWORDS = [
    "predict", "future", "forecast", "will be in 2050", "will happen in 2040", "in 2099",
    "who will win", "stock price in", "what will happen", "secret plans"
]


class QueryCategory(str, Enum):
    FINANCIAL = "financial"
    FACTUAL = "factual"
    ANALYTICAL = "analytical"
    GRAPH = "graph"
    MULTI_HOP = "multi-hop"
    INSUFFICIENT_EVIDENCE = "insufficient-evidence"


@dataclass
class QueryAnalysis:
    question: str
    category: str = QueryCategory.FACTUAL.value
    entities: List[str] = field(default_factory=list)
    relationships: List[str] = field(default_factory=list)
    temporal_years: List[int] = field(default_factory=list)
    suggested_mode: str = "hybrid"  # "vector", "graph", "hybrid"
    suggested_hops: int = 1
    is_financial_metric: bool = False
    financial_keywords: List[str] = field(default_factory=list)


class QueryAnalyzer:
    """Analyzes natural language queries to extract intent, category, entities, temporal anchors, and retrieval strategy."""

    def analyze(self, query: str) -> QueryAnalysis:
        cleaned = query.strip()
        analysis = QueryAnalysis(question=cleaned)
        lower_q = cleaned.lower()

        # 1. Extract temporal years
        years = [int(y) for y in YEAR_PATTERN.findall(cleaned)]
        analysis.temporal_years = sorted(list(set(years)))

        # 2. Check for financial / numerical metrics
        detected_fin = [kw for kw in NUMERICAL_FINANCIAL_KEYWORDS if kw in lower_q]
        if detected_fin:
            analysis.is_financial_metric = True
            analysis.financial_keywords = detected_fin

        # 3. Detect relationships
        detected_rels = []
        for rel, kws in RELATIONSHIP_KEYWORDS.items():
            if any(kw in lower_q for kw in kws):
                detected_rels.append(rel)
        analysis.relationships = detected_rels

        # 4. Extract potential capitalized entity mentions (e.g. NVIDIA, Microsoft, Jensen Huang)
        words = re.findall(r"\b[A-Z][a-zA-Z0-9&.]*(?:\s+[A-Z][a-zA-Z0-9&.]*)*\b", cleaned)
        filtered_words = [
            w for w in words
            if w.lower() not in {
                "what", "who", "which", "where", "when", "why", "how", "is", "was",
                "are", "the", "a", "an", "in", "for", "of", "and", "or", "to", "at",
                "fiscal", "revenue", "income", "data", "center"
            }
        ]
        analysis.entities = filtered_words

        # 5. Classify Query Category
        if any(sk in lower_q for sk in SPECULATIVE_FUTURE_KEYWORDS) or any(y > 2035 for y in analysis.temporal_years):
            analysis.category = QueryCategory.INSUFFICIENT_EVIDENCE.value
            analysis.suggested_mode = "vector"
            analysis.suggested_hops = 1

        elif len(detected_rels) >= 2 or ("who" in lower_q and "acquired" in lower_q and ("founded" in lower_q or "worked" in lower_q)):
            analysis.category = QueryCategory.MULTI_HOP.value
            analysis.suggested_hops = min(3, len(detected_rels) + 1)
            analysis.suggested_mode = "hybrid"

        elif analysis.is_financial_metric:
            analysis.category = QueryCategory.FINANCIAL.value
            # Financial metrics are in document tables/chunks, graph adds little value unless company relationships involved
            if detected_rels and analysis.entities:
                analysis.suggested_mode = "hybrid"
                analysis.suggested_hops = 1
            else:
                analysis.suggested_mode = "vector"
                analysis.suggested_hops = 1

        elif detected_rels and (analysis.entities or "company" in lower_q or "founder" in lower_q or "who" in lower_q):
            analysis.category = QueryCategory.GRAPH.value
            analysis.suggested_mode = "hybrid"
            analysis.suggested_hops = 1

        elif any(w in lower_q for w in ["strategy", "compare", "analysis", "trend", "ecosystem", "infrastructure", "drivers"]):
            analysis.category = QueryCategory.ANALYTICAL.value
            analysis.suggested_mode = "hybrid"
            analysis.suggested_hops = 2

        else:
            analysis.category = QueryCategory.FACTUAL.value
            analysis.suggested_mode = "hybrid"
            analysis.suggested_hops = 1

        return analysis
