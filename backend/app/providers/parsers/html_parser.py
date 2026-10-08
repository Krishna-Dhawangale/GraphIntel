from typing import List

from bs4 import BeautifulSoup

from app.core.exceptions import UnprocessableEntityException
from app.core.logging import logger
from app.providers.parsers.base import DocumentParser, ParsedSection


class HTMLParser(DocumentParser):
    def parse(self, content: bytes, filename: str) -> List[ParsedSection]:
        try:
            # Handle encoding
            html_text = content.decode("utf-8", errors="replace")
            soup = BeautifulSoup(html_text, "html.parser")

            # Remove unwanted tags
            for tag in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
                tag.decompose()

            sections: List[ParsedSection] = []
            title = soup.title.string.strip() if soup.title and soup.title.string else filename

            # Break into logical headings or blocks
            body = soup.body or soup
            current_section = title
            current_texts: List[str] = []

            for elem in body.find_all(["h1", "h2", "h3", "h4", "p", "div", "li", "table"]):
                text = elem.get_text(" ", strip=True)
                if not text:
                    continue

                if elem.name in ["h1", "h2", "h3"]:
                    if current_texts:
                        sections.append(
                            ParsedSection(
                                text="\n\n".join(current_texts),
                                section=current_section,
                                metadata={
                                    "format": "html",
                                    "title": title,
                                    "section": current_section,
                                },
                            )
                        )
                        current_texts = []
                    current_section = text
                    current_texts.append(text)
                elif elem.name in ["p", "li", "table"]:
                    current_texts.append(text)

            if current_texts:
                sections.append(
                    ParsedSection(
                        text="\n\n".join(current_texts),
                        section=current_section,
                        metadata={"format": "html", "title": title, "section": current_section},
                    )
                )

            if not sections:
                full_text = soup.get_text(" ", strip=True)
                if full_text:
                    sections.append(
                        ParsedSection(
                            text=full_text,
                            section=title,
                            metadata={"format": "html", "title": title},
                        )
                    )

            return sections
        except Exception as e:
            logger.error(f"Failed to parse HTML {filename}: {e}")
            raise UnprocessableEntityException(f"Failed to parse HTML document: {filename}")
