"""
This script parses MODFLOW 6 definition (dfn) files and extracts metadata for each block
and keyword. It defines classes to represent lines, groups of lines, and the entire dfn
file, and provides methods to parse and access this data.

Classes:
    Line: Represents a single line in a dfn file.
    Section: Represents a section of lines in a dfn file.
    Dfn: Represents an entire dfn file.

Usage:
    The script can be run as a standalone program to parse dfn files in the 'data/dfn'
    directory and preprocess the data to be copied into the regex in the grammar files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple


@dataclass
class Line:
    """Abstraction of each line as read from the dfn file.
    Line objects form a Section object."""

    key: str
    value: Optional[str] = None

    @classmethod
    def from_file(cls, data: str) -> "Line":
        return cls(*data.split(maxsplit=1))


@dataclass
class Section:
    """Abstraction of each group of lines (separated by \n\n) as read from the dfn file.
    A Section object is made up of Line objects."""

    keyword: str
    block: str
    data_type: Optional[str] = None
    valid: Optional[Tuple[str, ...]] = None

    @classmethod
    def from_file(cls, data: str) -> "Section":
        lines = (
            Line.from_file(line)
            for line in data.split("\n")
            if any(line.startswith(s) for s in {"block", "name", "type", "valid"})
        )
        line_dict = {line.key: line.value for line in lines}
        return cls(
            block=line_dict.get("block", ""),
            keyword=line_dict.get("name", ""),
            data_type=line_dict.get("type", None),
            valid=None if (x := line_dict.get("valid")) is None else tuple(x.split()),
        )


@dataclass
class Dfn:
    """Abstraction of each dfn file. Dfn files are definition files from MODFLOW 6 which
    contains metadata for each block and keyword in the MF6 input files."""

    path: Path

    def __post_init__(self):
        with self.path.open() as f:
            data = tuple(f.read().split("\n\n"))
        self._data = data

    @property
    def data(self) -> Tuple[str, ...]:
        return self._data

    @property
    def sections(self) -> Tuple[Section, ...]:
        return tuple(Section.from_file(x) for x in self.data if x.startswith("block"))

    @property
    def blocks(self) -> set:
        return {p.block for p in self.sections}

    @property
    def keywords(self) -> set:
        return {p.keyword for p in self.sections}

    @property
    def valids(self) -> set:
        return {p.valid for p in self.sections if p.valid is not None}

    @property
    def extension(self) -> Optional[str]:
        parts = self.path.stem.split("-")
        return f".{parts[-1]}" if len(parts) > 1 else None


if __name__ == "__main__":
    blocks = set()
    keywords = set()
    valid = set()
    extensions = set()
    for dfn_file in Path("data/dfn").glob("*.dfn"):
        dfn = Dfn(dfn_file)
        blocks |= dfn.blocks
        keywords |= dfn.keywords
        valid.update(*dfn.valids)
        if ext := dfn.extension:
            extensions.add(dfn.extension)
