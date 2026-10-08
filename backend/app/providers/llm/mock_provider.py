import re
from typing import Dict, List

from app.providers.llm.base import LLMProvider, LLMResponse


class MockLLMProvider(LLMProvider):
    """Deterministic, high-quality Mock LLM provider for unit tests, offline demos, and CI verification."""

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 1000,
    ) -> LLMResponse:
        user_content = ""
        for m in messages:
            if m.get("role") == "user":
                user_content = m.get("content", "")

        # Look for source markers in the context
        source_matches = re.findall(r"\[Source (\d+)\]", user_content)
        graph_matches = re.findall(r"Knowledge Graph (?:Fact|Multi-Hop Path):\s*(.*?)(?:\n|$)", user_content)

        # Check if the user asked a question
        question_match = re.search(r"Question:\s*(.*?)(?:\n|$)", user_content)
        question_text = (
            question_match.group(1).strip() if question_match else "your market intelligence query"
        )

        if source_matches or graph_matches:
            # Build grounded response referencing available sources and graph facts
            parts = []
            if source_matches:
                citations_str = " ".join([f"[{s}]" for s in source_matches[:3]])
                parts.append(f"the retrieved document evidence confirms relevant findings {citations_str}.")
            if graph_matches:
                graph_summary = "; ".join(graph_matches[:2])
                parts.append(f"Knowledge graph relationships confirm: {graph_summary}.")

            evidence_detail = " ".join(parts)
            answer = (
                f"Based on the analyzed market intelligence documents and knowledge graph, regarding {question_text}, "
                f"{evidence_detail} "
                f"Key metrics, strategic drivers, and operational disclosures are detailed in the referenced filings."
            )
        else:
            answer = (
                "Based on the provided documents and knowledge graph, there is insufficient evidence to answer this question. "
                "No matching chunks or relationships were found in the uploaded documents."
            )


        return LLMResponse(
            content=answer,
            model="graphintel-mock-v1",
            prompt_tokens=len(user_content) // 4,
            completion_tokens=len(answer) // 4,
        )
