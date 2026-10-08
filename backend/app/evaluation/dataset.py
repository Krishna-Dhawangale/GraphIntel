import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

DATASET_VERSION = "1.0.0"


class EvalQuestion(BaseModel):
    id: str
    category: str  # factual, relationship, multihop, temporal, comparative, insufficient_evidence
    question: str
    expected_answer: str
    ground_truth_entities: List[str] = Field(default_factory=list)
    ground_truth_relations: List[Dict[str, str]] = Field(default_factory=list)
    relevant_chunk_keywords: List[str] = Field(default_factory=list)
    requires_temporal: bool = False
    requires_multihop: bool = False
    temporal_year: Optional[int] = None
    expected_insufficient: bool = False


# Versioned Benchmark Dataset (24 representative, curated market intelligence test cases)
BENCHMARK_ITEMS: List[Dict[str, Any]] = [
    # 1. Simple Factual Questions
    {
        "id": "fact-01",
        "category": "factual",
        "question": "What is OpenAI and when was it established?",
        "expected_answer": "OpenAI is an artificial intelligence research organization founded in December 2015.",
        "ground_truth_entities": ["OpenAI", "San Francisco"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": ["OpenAI", "founded", "2015"],
        "requires_temporal": True,
        "requires_multihop": False,
        "temporal_year": 2015,
        "expected_insufficient": False,
    },
    {
        "id": "fact-02",
        "category": "factual",
        "question": "When was Anthropic founded?",
        "expected_answer": "Anthropic was founded in 2021 by former members of OpenAI.",
        "ground_truth_entities": ["Anthropic", "OpenAI"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": ["Anthropic", "founded", "2021"],
        "requires_temporal": True,
        "requires_multihop": False,
        "temporal_year": 2021,
        "expected_insufficient": False,
    },
    {
        "id": "fact-03",
        "category": "factual",
        "question": "What is DeepMind?",
        "expected_answer": "DeepMind is an AI research laboratory based in London, founded in 2010.",
        "ground_truth_entities": ["DeepMind", "Google"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": ["DeepMind", "artificial intelligence", "research"],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": False,
    },
    {
        "id": "fact-04",
        "category": "factual",
        "question": "When was Snowflake founded?",
        "expected_answer": "Snowflake Inc. was founded in 2012 by Benoit Dageville and Thierry Cruanes.",
        "ground_truth_entities": ["Snowflake"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": ["Snowflake", "cloud", "data warehouse"],
        "requires_temporal": True,
        "requires_multihop": False,
        "temporal_year": 2012,
        "expected_insufficient": False,
    },

    # 2. Entity Relationship Questions
    {
        "id": "rel-01",
        "category": "relationship",
        "question": "Who founded DeepMind?",
        "expected_answer": "DeepMind was founded by Demis Hassabis, Shane Legg, and Mustafa Suleyman.",
        "ground_truth_entities": ["Demis Hassabis", "Shane Legg", "Mustafa Suleyman", "DeepMind"],
        "ground_truth_relations": [
            {"source": "Demis Hassabis", "type": "FOUNDED", "target": "DeepMind"},
            {"source": "Shane Legg", "type": "FOUNDED", "target": "DeepMind"},
            {"source": "Mustafa Suleyman", "type": "FOUNDED", "target": "DeepMind"},
        ],
        "relevant_chunk_keywords": ["Demis Hassabis", "DeepMind", "co-founder"],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": False,
    },
    {
        "id": "rel-02",
        "category": "relationship",
        "question": "Which company acquired DeepMind?",
        "expected_answer": "Google acquired DeepMind in 2014.",
        "ground_truth_entities": ["Google", "DeepMind"],
        "ground_truth_relations": [
            {"source": "Google", "type": "ACQUIRED", "target": "DeepMind"},
        ],
        "relevant_chunk_keywords": ["Google", "acquired", "DeepMind", "2014"],
        "requires_temporal": True,
        "requires_multihop": False,
        "temporal_year": 2014,
        "expected_insufficient": False,
    },
    {
        "id": "rel-03",
        "category": "relationship",
        "question": "Who founded Databricks?",
        "expected_answer": "Databricks was founded by the creators of Apache Spark, including Ali Ghodsi and Matei Zaharia.",
        "ground_truth_entities": ["Ali Ghodsi", "Matei Zaharia", "Databricks"],
        "ground_truth_relations": [
            {"source": "Ali Ghodsi", "type": "FOUNDED", "target": "Databricks"},
        ],
        "relevant_chunk_keywords": ["Databricks", "Apache Spark", "Ali Ghodsi"],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": False,
    },
    {
        "id": "rel-04",
        "category": "relationship",
        "question": "Which companies invested in Anthropic?",
        "expected_answer": "Amazon and Google have made major strategic investments in Anthropic.",
        "ground_truth_entities": ["Amazon", "Google", "Anthropic"],
        "ground_truth_relations": [
            {"source": "Amazon", "type": "INVESTED_IN", "target": "Anthropic"},
            {"source": "Google", "type": "INVESTED_IN", "target": "Anthropic"},
        ],
        "relevant_chunk_keywords": ["Anthropic", "investment", "Amazon", "Google"],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": False,
    },

    # 3. Multi-Hop Questions
    {
        "id": "hop-01",
        "category": "multihop",
        "question": "Which companies acquired startups founded by people who previously worked at Google?",
        "expected_answer": "Companies such as Microsoft and Alphabet acquired startups led by former Google researchers and executives.",
        "ground_truth_entities": ["Google", "Microsoft", "Inflection AI", "Mustafa Suleyman"],
        "ground_truth_relations": [
            {"source": "Mustafa Suleyman", "type": "WORKED_AT", "target": "Google"},
            {"source": "Mustafa Suleyman", "type": "FOUNDED", "target": "Inflection AI"},
            {"source": "Microsoft", "type": "PARTNERED_WITH", "target": "Inflection AI"},
        ],
        "relevant_chunk_keywords": ["worked at Google", "founded", "acquired"],
        "requires_temporal": False,
        "requires_multihop": True,
        "expected_insufficient": False,
    },
    {
        "id": "hop-02",
        "category": "multihop",
        "question": "What is the connection between Demis Hassabis, DeepMind, Google, and Gemini?",
        "expected_answer": "Demis Hassabis founded DeepMind, which was acquired by Google, and Hassabis subsequently led the Google DeepMind team developing Gemini.",
        "ground_truth_entities": ["Demis Hassabis", "DeepMind", "Google", "Gemini"],
        "ground_truth_relations": [
            {"source": "Demis Hassabis", "type": "FOUNDED", "target": "DeepMind"},
            {"source": "Google", "type": "ACQUIRED", "target": "DeepMind"},
            {"source": "DeepMind", "type": "DEVELOPED", "target": "Gemini"},
        ],
        "relevant_chunk_keywords": ["Demis Hassabis", "DeepMind", "Google", "Gemini"],
        "requires_temporal": False,
        "requires_multihop": True,
        "expected_insufficient": False,
    },
    {
        "id": "hop-03",
        "category": "multihop",
        "question": "How are OpenAI co-founders related to Anthropic?",
        "expected_answer": "Dario Amodei and Daniela Amodei worked as VP of Research and VP of Safety at OpenAI before leaving to found Anthropic.",
        "ground_truth_entities": ["Dario Amodei", "Daniela Amodei", "OpenAI", "Anthropic"],
        "ground_truth_relations": [
            {"source": "Dario Amodei", "type": "WORKED_AT", "target": "OpenAI"},
            {"source": "Dario Amodei", "type": "FOUNDED", "target": "Anthropic"},
        ],
        "relevant_chunk_keywords": ["Dario Amodei", "OpenAI", "Anthropic", "safety"],
        "requires_temporal": False,
        "requires_multihop": True,
        "expected_insufficient": False,
    },
    {
        "id": "hop-04",
        "category": "multihop",
        "question": "Did any investor who funded Stripe also back OpenAI?",
        "expected_answer": "Yes, Peter Thiel and Sequoia Capital participated in early funding rounds for both Stripe and OpenAI.",
        "ground_truth_entities": ["Peter Thiel", "Sequoia Capital", "Stripe", "OpenAI"],
        "ground_truth_relations": [
            {"source": "Peter Thiel", "type": "INVESTED_IN", "target": "Stripe"},
            {"source": "Peter Thiel", "type": "INVESTED_IN", "target": "OpenAI"},
        ],
        "relevant_chunk_keywords": ["investor", "Stripe", "OpenAI", "Peter Thiel"],
        "requires_temporal": False,
        "requires_multihop": True,
        "expected_insufficient": False,
    },

    # 4. Temporal Questions
    {
        "id": "temp-01",
        "category": "temporal",
        "question": "Which acquisitions happened between 2022 and 2025?",
        "expected_answer": "Major acquisitions between 2022 and 2025 included Figma by Adobe (announced 2022, terminated 2023), Splunk by Cisco (2024), and Databricks acquiring MosaicML (2023).",
        "ground_truth_entities": ["Splunk", "Cisco", "MosaicML", "Databricks"],
        "ground_truth_relations": [
            {"source": "Cisco", "type": "ACQUIRED", "target": "Splunk"},
            {"source": "Databricks", "type": "ACQUIRED", "target": "MosaicML"},
        ],
        "relevant_chunk_keywords": ["acquisition", "2023", "2024", "MosaicML", "Splunk"],
        "requires_temporal": True,
        "requires_multihop": False,
        "temporal_year": 2023,
        "expected_insufficient": False,
    },
    {
        "id": "temp-02",
        "category": "temporal",
        "question": "What major AI funding rounds occurred in 2023?",
        "expected_answer": "In 2023, Microsoft invested $10 billion into OpenAI, and Amazon committed up to $4 billion to Anthropic.",
        "ground_truth_entities": ["Microsoft", "OpenAI", "Amazon", "Anthropic"],
        "ground_truth_relations": [
            {"source": "Microsoft", "type": "INVESTED_IN", "target": "OpenAI"},
            {"source": "Amazon", "type": "INVESTED_IN", "target": "Anthropic"},
        ],
        "relevant_chunk_keywords": ["2023", "billion", "investment", "OpenAI", "Anthropic"],
        "requires_temporal": True,
        "requires_multihop": False,
        "temporal_year": 2023,
        "expected_insufficient": False,
    },
    {
        "id": "temp-03",
        "category": "temporal",
        "question": "Who was CEO of OpenAI in 2020 versus late 2023?",
        "expected_answer": "Sam Altman served as CEO in 2020. In November 2023, he was briefly ousted and Mira Murati served as interim CEO for several days before Altman was reinstated.",
        "ground_truth_entities": ["Sam Altman", "Mira Murati", "OpenAI"],
        "ground_truth_relations": [
            {"source": "Sam Altman", "type": "LEADS", "target": "OpenAI"},
        ],
        "relevant_chunk_keywords": ["Sam Altman", "CEO", "OpenAI", "2020", "2023"],
        "requires_temporal": True,
        "requires_multihop": False,
        "temporal_year": 2023,
        "expected_insufficient": False,
    },

    # 5. Comparative Questions
    {
        "id": "comp-01",
        "category": "comparative",
        "question": "Which company has more AI investments between Microsoft and Apple?",
        "expected_answer": "Microsoft has significantly more disclosed external AI investments and strategic partnerships than Apple, including multi-billion dollar stakes in OpenAI, Inflection, and Mistral AI.",
        "ground_truth_entities": ["Microsoft", "Apple", "OpenAI", "Mistral AI"],
        "ground_truth_relations": [
            {"source": "Microsoft", "type": "INVESTED_IN", "target": "OpenAI"},
        ],
        "relevant_chunk_keywords": ["Microsoft", "Apple", "investments", "venture"],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": False,
    },
    {
        "id": "comp-02",
        "category": "comparative",
        "question": "Compare the founding dates and initial core focuses of Anthropic and OpenAI.",
        "expected_answer": "OpenAI was founded in 2015 focused on general digital intelligence and safety, while Anthropic was founded in 2021 with a primary focus on AI alignment, steerability, and constitutional AI.",
        "ground_truth_entities": ["Anthropic", "OpenAI"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": ["OpenAI", "Anthropic", "founded", "alignment", "safety"],
        "requires_temporal": True,
        "requires_multihop": False,
        "expected_insufficient": False,
    },
    {
        "id": "comp-03",
        "category": "comparative",
        "question": "Between Snowflake and Databricks, which company pioneered Apache Spark?",
        "expected_answer": "Databricks was founded by the original creators of Apache Spark at UC Berkeley AMPLab, whereas Snowflake pioneered cloud-native SQL data warehousing.",
        "ground_truth_entities": ["Databricks", "Snowflake", "Apache Spark"],
        "ground_truth_relations": [
            {"source": "Databricks", "type": "DEVELOPED", "target": "Apache Spark"},
        ],
        "relevant_chunk_keywords": ["Snowflake", "Databricks", "Apache Spark", "UC Berkeley"],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": False,
    },

    # 6. Insufficient-Evidence Questions
    {
        "id": "insuf-01",
        "category": "insufficient_evidence",
        "question": "What is Google's proprietary secret recipe for its internal quantum cola beverage?",
        "expected_answer": "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question.",
        "ground_truth_entities": ["Google"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": [],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": True,
    },
    {
        "id": "insuf-02",
        "category": "insufficient_evidence",
        "question": "Which Martian corporation acquired Apple in the year 2099?",
        "expected_answer": "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question.",
        "ground_truth_entities": ["Apple"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": [],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": True,
    },
    {
        "id": "insuf-03",
        "category": "insufficient_evidence",
        "question": "What was the exact personal bank balance of Steve Jobs on July 4th, 1982?",
        "expected_answer": "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question.",
        "ground_truth_entities": ["Steve Jobs"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": [],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": True,
    },
    {
        "id": "insuf-04",
        "category": "insufficient_evidence",
        "question": "How many aliens did Anthropic employ in the Andromeda galaxy during 2020?",
        "expected_answer": "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question.",
        "ground_truth_entities": ["Anthropic"],
        "ground_truth_relations": [],
        "relevant_chunk_keywords": [],
        "requires_temporal": False,
        "requires_multihop": False,
        "expected_insufficient": True,
    },
]


class EvaluationDataset:
    """Provides access to versioned test cases and persistence."""

    def __init__(self, version: str = DATASET_VERSION):
        self.version = version
        self.questions: List[EvalQuestion] = [EvalQuestion(**item) for item in BENCHMARK_ITEMS]

    def get_by_category(self, category: str) -> List[EvalQuestion]:
        return [q for q in self.questions if q.category == category]

    def get_question(self, question_id: str) -> Optional[EvalQuestion]:
        for q in self.questions:
            if q.id == question_id:
                return q
        return None

    def export_json(self, output_path: Path) -> None:
        data = {
            "version": self.version,
            "total_questions": len(self.questions),
            "questions": [q.model_dump() for q in self.questions],
        }
        output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# Default dataset instance
evaluation_dataset = EvaluationDataset()
