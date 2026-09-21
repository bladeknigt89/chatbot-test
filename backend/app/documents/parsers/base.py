from dataclasses import dataclass, field


@dataclass
class ExtractedBlock:
    text: str
    page_number: int | None = None
    sheet_name: str | None = None
    heading: str | None = None


@dataclass
class ExtractedDocument:
    text: str
    blocks: list[ExtractedBlock] = field(default_factory=list)
    extra: dict[str, str] = field(default_factory=dict)
