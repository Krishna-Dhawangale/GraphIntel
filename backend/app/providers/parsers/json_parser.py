import json
from typing import List

from app.core.exceptions import UnprocessableEntityException
from app.core.logging import logger
from app.providers.parsers.base import DocumentParser, ParsedSection


class JSONParser(DocumentParser):
    def parse(self, content: bytes, filename: str) -> List[ParsedSection]:
        try:
            raw_text = content.decode("utf-8", errors="replace")
            data = json.loads(raw_text)

            sections: List[ParsedSection] = []

            if isinstance(data, dict):
                # Overview
                keys = list(data.keys())
                sections.append(
                    ParsedSection(
                        text=f"JSON Document: {filename}\nTop-level keys: {', '.join(keys)}",
                        section="Overview",
                        metadata={"format": "json", "type": "dict", "keys": keys},
                    )
                )

                # Each major key as section
                for key, val in data.items():
                    val_str = json.dumps(val, indent=2, ensure_ascii=False)
                    # Limit very huge blocks to reasonable length or summarize
                    sections.append(
                        ParsedSection(
                            text=f"Section: {key}\nContent:\n{val_str}",
                            section=f"Key: {key}",
                            metadata={"format": "json", "key": key},
                        )
                    )

            elif isinstance(data, list):
                total_items = len(data)
                sections.append(
                    ParsedSection(
                        text=f"JSON Array Document: {filename}\nTotal records: {total_items}",
                        section="Overview",
                        metadata={"format": "json", "type": "list", "total_items": total_items},
                    )
                )

                # Batch items in groups of 10
                batch_size = 10
                for i in range(0, total_items, batch_size):
                    batch = data[i : i + batch_size]
                    batch_str = json.dumps(batch, indent=2, ensure_ascii=False)
                    sections.append(
                        ParsedSection(
                            text=f"Records {i + 1} to {min(i + batch_size, total_items)}:\n{batch_str}",
                            section=f"Items {i + 1}-{min(i + batch_size, total_items)}",
                            metadata={
                                "format": "json",
                                "start_index": i + 1,
                                "end_index": min(i + batch_size, total_items),
                            },
                        )
                    )
            else:
                sections.append(
                    ParsedSection(
                        text=f"JSON Literal Value:\n{json.dumps(data, indent=2)}",
                        section="Root",
                        metadata={"format": "json"},
                    )
                )

            return sections
        except Exception as e:
            logger.error(f"Failed to parse JSON {filename}: {e}")
            raise UnprocessableEntityException(f"Failed to parse JSON document: {filename}")
