import io
from typing import List

import pandas as pd

from app.core.exceptions import UnprocessableEntityException
from app.core.logging import logger
from app.providers.parsers.base import DocumentParser, ParsedSection


class CSVParser(DocumentParser):
    def parse(self, content: bytes, filename: str) -> List[ParsedSection]:
        try:
            # Try utf-8 then latin-1
            try:
                df = pd.read_csv(io.BytesIO(content))
            except UnicodeDecodeError:
                df = pd.read_csv(io.BytesIO(content), encoding="latin-1")

            sections: List[ParsedSection] = []
            columns = list(df.columns)
            total_rows = len(df)

            # Metadata header section
            header_summary = (
                f"CSV Dataset: {filename}\n"
                f"Total Rows: {total_rows}\n"
                f"Columns: {', '.join(str(c) for c in columns)}\n"
            )
            sections.append(
                ParsedSection(
                    text=header_summary,
                    section="Dataset Overview",
                    metadata={
                        "columns": [str(c) for c in columns],
                        "total_rows": total_rows,
                        "format": "csv",
                    },
                )
            )

            # Chunk rows in batches of 20 for rich textual representation
            batch_size = 20
            for i in range(0, total_rows, batch_size):
                batch_df = df.iloc[i : i + batch_size]
                row_texts = []
                for idx, row in batch_df.iterrows():
                    row_desc = " | ".join(
                        f"{col}: {val}" for col, val in row.items() if pd.notna(val)
                    )
                    row_texts.append(f"Row {idx + 1}: {row_desc}")

                batch_text = "\n".join(row_texts)
                sections.append(
                    ParsedSection(
                        text=batch_text,
                        section=f"Rows {i + 1} to {min(i + batch_size, total_rows)}",
                        metadata={
                            "format": "csv",
                            "start_row": i + 1,
                            "end_row": min(i + batch_size, total_rows),
                        },
                    )
                )

            return sections
        except Exception as e:
            logger.error(f"Failed to parse CSV {filename}: {e}")
            raise UnprocessableEntityException(f"Failed to parse CSV document: {filename}")
