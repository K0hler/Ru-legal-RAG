"""Source regions, markers and logical paragraphs used by the owner parser."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Region:
    order: int
    page: int
    index: int
    region_id: str
    category: str
    bbox: list
    page_size: list
    raw: str
    text: str
    text_node_ids: list
    role: str = "content"  # content | noise | picture | table
    repeats: int = 0  # running header/footer: regions with exactly the same text
    repeat_index: int = 0  # 0 for the first of those regions in reading order
    row_cell: bool = False  # cycle 10 B3: a right-hand cell of a printed row that starts with a table or long text
    source_start: int = 0  # offsets in concatenated, unchanged text-node raw_text
    source_end: int = 0


@dataclass
class Marker:
    # roman | decimal | int | paren | letter | dash | none, and named law units:
    # section_named | chapter | paragraph_sign | article
    kind: str = "none"
    value: object = None
    label: str = ""
    # «1.» after a table or an unmarked heading that follows an «N.» of the same scope: the
    # numbering may start again (RESTART_COST) instead of nesting into the last point
    restart: bool = False
    # inserted unit «2¹.», «3²)», «е¹)»: value is the base number, sup the superscript index
    sup: int | str = 0  # compound printed indices such as2-1 remain strings
    # step 16 C1: the other reading of a marker OCR confuses («б)» / «6)», «з)» / «3)»); the solver tries it at
    # OCR_READING_COST and keeps it only where the sequence fits better
    alt: "Marker | None" = None


@dataclass
class Paragraph:
    flow: str  # body | footnote
    regions: list = field(default_factory=list)
    marker: Marker = field(default_factory=Marker)
    kind: str = "text"  # text | heading | approval | annex | table | signature | requisite | footnote | picture
    footnote: int | None = None
    owner: str | None = None
    evidence: list = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(r.text for r in self.regions)

    @property
    def first(self) -> Region:
        return self.regions[0]
