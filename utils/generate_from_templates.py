"""
This script parses MODFLOW 6 definition (dfn) files and extracts metadata for each block
and keyword. It defines classes to represent lines, groups of lines, and the entire dfn
file, and provides methods to parse and access this data.

Classes:
    Line: Represents a single line in a dfn file.
    Section: Represents a section of lines in a dfn file.
    Dfn: Represents an entire dfn file.

Usage:
    The script can be run to parse dfn files in the 'data/dfn' directory and preprocess
    the data to generate 'package.json' and 'syntaxes/mf6.tmLanguage.yaml' files.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from jinja2 import Environment, FileSystemLoader


@dataclass
class Line:
    """Abstraction of each line as read from the dfn file. Line objects form a Section
    object."""

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
    valid: Optional[tuple[str, ...]] = None

    @classmethod
    def from_file(cls, data: str) -> "Section":
        lines = (
            Line.from_file(line)
            for line in data.split("\n")
            if any(line.startswith(s) for s in {"block", "name", "type", "valid"})
        )
        line_dict: dict[str, str] = {line.key: (line.value or "") for line in lines}
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
            self._data = tuple(f.read().split("\n\n"))

    @property
    def data(self) -> tuple[str, ...]:
        return self._data

    @property
    def sections(self) -> tuple[Section, ...]:
        return tuple(Section.from_file(x) for x in self.data if x.startswith("block"))

    @property
    def blocks(self) -> set[str]:
        return {p.block for p in self.sections}

    @property
    def keywords(self) -> set[str]:
        return {p.keyword for p in self.sections}

    @property
    def valids(self) -> set[tuple[str, ...]]:
        return {p.valid for p in self.sections if p.valid is not None}

    @property
    def extension(self) -> Optional[str]:
        parts = self.path.stem.split("-")
        return f".{parts[-1]}" if len(parts) > 1 else None


def render_template(template_name: str, output_path: str, **context):
    """Render a Jinja2 template and write the output to a file."""
    template = Environment(
        loader=FileSystemLoader("templates"), keep_trailing_newline=True
    ).get_template(template_name)
    sorted_context = {
        k: sorted(v) if isinstance(v, set) else v for k, v in context.items()
    }
    output = template.render(**sorted_context)
    Path(output_path).write_text(output)
    print(f"{output_path} has been generated")


if __name__ == "__main__":
    # Collect blocks, keywords, valids, and extensions from dfn files
    blocks = set()
    keywords = set()
    valids = set()
    extensions = set()
    for dfn_file in Path("data/dfn").glob("*.dfn"):
        dfn = Dfn(dfn_file)
        blocks.update(dfn.blocks)
        keywords.update(dfn.keywords)
        valids.update(*dfn.valids)
        if ext := dfn.extension:
            extensions.add(ext)

    # Insert the collected data into the Jinja2 templates
    render_template("package.json.j2", "package.json", extensions=extensions)
    render_template(
        "mf6.tmLanguage.json.j2",
        "syntaxes/mf6.tmLanguage.json",
        blocks=blocks,
        keywords=keywords,
        valids=valids,
    )
