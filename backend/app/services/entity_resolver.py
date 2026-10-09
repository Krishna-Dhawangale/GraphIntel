from difflib import SequenceMatcher
import re
from typing import Dict, List, Optional, Set, Tuple

COMMON_ALIASES: Dict[str, str] = {
    "msft": "Microsoft",
    "microsoft corp": "Microsoft",
    "microsoft corporation": "Microsoft",
    "goog": "Google",
    "googl": "Google",
    "google llc": "Google",
    "google inc": "Google",
    "alphabet": "Google",
    "alphabet inc": "Google",
    "alphabet google": "Google",
    "aapl": "Apple",
    "apple inc": "Apple",
    "apple computer": "Apple",
    "amzn": "Amazon",
    "amazon com": "Amazon",
    "amazon com inc": "Amazon",
    "meta platforms": "Meta",
    "facebook": "Meta",
    "facebook inc": "Meta",
    "openai inc": "OpenAI",
    "openai llc": "OpenAI",
    "anthropic pbc": "Anthropic",
    "anthropic ai": "Anthropic",
    "nvidia corp": "NVIDIA",
    "nvidia corporation": "NVIDIA",
    "nvda": "NVIDIA",
    "tsmc": "TSMC",
    "taiwan semiconductor manufacturing company": "TSMC",
}

SUFFIX_REGEX = re.compile(
    r"\b(inc|inc\.|incorporated|corp|corp\.|corporation|llc|l\.l\.c\.|ltd|ltd\.|limited|co|co\.|company|pbc|group|holdings|technologies|tech|ai)\b",
    re.IGNORECASE,
)


import functools

@functools.lru_cache(maxsize=4096)
def _fast_normalize(text: str) -> str:
    clean = text.strip()
    clean = SUFFIX_REGEX.sub("", clean)
    clean = re.sub(r"[^\w\s]", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip().lower()
    return clean or text.strip().lower()


class EntityResolver:
    """Handles entity canonicalization, alias resolution, fuzzy matching, and deduplication."""

    def __init__(self, fuzzy_threshold: float = 0.88):
        self.fuzzy_threshold = fuzzy_threshold

    @staticmethod
    def normalize(text: str) -> str:
        """Strip punctuation, excessive whitespace, and common legal suffixes with LRU caching."""
        return _fast_normalize(text)

    @staticmethod
    def similarity(s1: str, s2: str) -> float:
        """Compute string similarity ratio."""
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    def resolve(
        self,
        name: str,
        entity_type: str,
        existing_entities: List[Dict[str, any]],
    ) -> Tuple[str, List[str], float]:
        """
        Resolves an entity candidate against a pool of existing entities.
        Returns: (canonical_name, new_aliases, confidence)
        """
        raw_name = name.strip()
        norm_input = self.normalize(raw_name)
        raw_lower = raw_name.lower()
        type_lower = entity_type.lower()

        # 1. Check known global alias dictionary
        if norm_input in COMMON_ALIASES:
            canonical = COMMON_ALIASES[norm_input]
            aliases = [raw_name] if raw_name.lower() != canonical.lower() else []
            return canonical, aliases, 0.98

        # 2. Fast exact and normalized matches
        for existing in existing_entities:
            existing_type = existing.get("type", "")
            if existing_type.lower() != type_lower:
                continue

            existing_canonical = existing.get("name", "")
            existing_canon_lower = existing_canonical.lower()

            # Exact canonical match
            if raw_lower == existing_canon_lower:
                return existing_canonical, [], 1.0

            norm_canon = self.normalize(existing_canonical)
            # Exact normalized match
            if norm_input == norm_canon:
                aliases = [raw_name] if raw_name not in existing.get("aliases", []) else []
                return existing_canonical, aliases, 0.95

            # Alias match
            for alias in existing.get("aliases", []):
                if raw_lower == alias.lower() or norm_input == self.normalize(alias):
                    return existing_canonical, [], 0.96

        # 3. Fuzzy matching with strict threshold to prevent blind merges
        if len(norm_input) >= 4:
            best_match: Optional[str] = None
            best_score = 0.0

            for existing in existing_entities:
                if existing.get("type", "").lower() != type_lower:
                    continue

                existing_canonical = existing.get("name", "")
                norm_canon = self.normalize(existing_canonical)

                if len(norm_canon) < 4:
                    continue

                # Fast length pre-filter
                len_ratio = min(len(norm_input), len(norm_canon)) / max(len(norm_input), len(norm_canon))
                if len_ratio < self.fuzzy_threshold * 0.8:
                    continue

                score = self.similarity(norm_input, norm_canon)
                if score > best_score and score >= self.fuzzy_threshold:
                    best_score = score
                    best_match = existing_canonical

            if best_match and best_score >= self.fuzzy_threshold:
                return best_match, [raw_name], round(best_score, 2)

        # 4. No high-confidence match found -> keep as new distinct canonical entity
        return raw_name, [], 1.0
