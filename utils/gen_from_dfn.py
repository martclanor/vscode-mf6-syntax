# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "jinja2",
# ]
# ///

"""
This script parses MODFLOW 6 definition (dfn) files and extracts metadata for each block
and keyword. It defines classes to represent lines, groups of lines, and the entire dfn
file, and provides methods to parse and access this data in order to generate
configuration files for the syntax highlighting and hover feature.

Classes:
    Line: Represents a single line in a dfn file.
    Section: Represents a section of lines in a dfn file.
    Dfn: Represents an entire dfn file.

Usage:
    The script can be run to parse dfn files in 'data/dfn' (downloaded from mf6 repo via
    'utils/download_dfn.sh') and preprocess the data to generate 'package.json',
    'syntaxes/mf6.tmLanguage.json' and 'src/providers/hover.json' files.
"""

import ast
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Optional

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


@dataclass
class Line:
    """Abstraction of each line from the dfn file."""

    key: str
    value: Optional[str | bool] = None

    @classmethod
    def from_file(cls, data: str) -> "Line":
        if "tagged" in data:
            return cls("tagged", "true" in data)
        return cls(*data.split(maxsplit=1))

    @classmethod
    def from_replace(cls, data: str) -> "Line":
        return cls(data.split()[1], value=None)


@dataclass
class Section:
    """Abstraction of each group of lines (separated by \n\n) from the dfn file."""

    keyword: str
    block: str
    data_type: Optional[tuple[str, ...]] = None
    valid: Optional[tuple[str, ...]] = None
    tagged: bool = True
    description: Optional[str] = None

    @classmethod
    def from_file(cls, data: str) -> "Section":
        lines = (
            Line.from_file(line)
            for line in data.split("\n")
            if any(
                line.startswith(s)
                for s in {"block", "name", "type", "valid", "tagged", "description"}
            )
        )
        line_dict: dict[str, str] = {line.key: line.value for line in lines}
        return cls(
            block=line_dict.get("block", ""),
            keyword=line_dict.get("name", ""),
            data_type=None
            if (x := line_dict.get("type")) is None
            else tuple(x.split()),
            valid=None if (x := line_dict.get("valid")) is None else tuple(x.split()),
            tagged=line_dict.get("tagged", True),
            description=line_dict.get("description", None),
        )


@dataclass
class Dfn:
    """Abstraction of each dfn file. Dfn files are definition files from MODFLOW 6 which
    contains metadata for each block and keyword in the MF6 input files."""

    path: Path
    dfn_path: ClassVar[Path] = Path("data/dfn")

    def __post_init__(self):
        with self.path.open() as f:
            self._data = tuple(f.read().split("\n\n"))

    @property
    def data(self) -> tuple[str, ...]:
        return self._data

    @property
    def sections(self) -> tuple[Section, ...]:
        sections = []
        for data in self.data:
            if not data.startswith("block"):
                continue
            section = Section.from_file(data)
            if "record" in section.data_type or "recarray" in section.data_type:
                continue
            sections.append(section)
        return tuple(sections)

    @property
    def blocks(self) -> set[str]:
        return {p.block for p in self.sections}

    @property
    def keywords(self) -> set[str]:
        keywords = set()
        for section in self.sections:
            if not section.tagged:
                continue
            keywords.add(section.keyword)
        return keywords

    @property
    def valids(self) -> set[tuple[str, ...]]:
        return {p.valid for p in self.sections if p.valid is not None}

    @property
    def extension(self) -> Optional[str]:
        return f".{self.path.stem.partition('-')[-1]}"

    @staticmethod
    def get_dfns() -> tuple[str, ...]:
        return (
            Dfn(filename)
            for filename in Dfn.dfn_path.glob("*.dfn")
            if filename.name != "common.dfn"
        )

    @staticmethod
    def parse_common() -> dict[str, str]:
        # common.dfn is a special file that contains common descriptions for keywords
        # which are used to replace placeholders in other dfn files
        common = {}
        for section in Dfn(Dfn.dfn_path / "common.dfn").data:
            if not section.startswith("name"):
                continue
            name, description = [
                Line.from_file(data) for data in section.strip().split("\n")
            ]
            if not (name.key == "name" and description.key == "description"):
                continue
            common[name.value] = description.value
        return common

    @staticmethod
    def export_hover_keyword() -> dict[str, dict[str, dict[str, list[str]]]]:
        hover = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        common = Dfn.parse_common()

        for dfn in Dfn.get_dfns():
            for section in dfn.sections:
                if (description := section.description) is None:
                    continue
                if "REPLACE" in description:
                    keyword = Line.from_replace(description).key
                    if r"{}" in description:
                        # No placeholders to replace
                        description = common[keyword]
                    else:
                        # Create replacement dictionary from the original description
                        replacement = ast.literal_eval(
                            section.description.strip(f"REPLACE {keyword} ")
                        )
                        # Take new description from common, then replace placeholders
                        description = common[keyword]
                        for key, value in replacement.items():
                            description = description.replace(key, value)
                description = (
                    description.replace("``", "`").replace("''", "`").replace("\\", "")
                )
                hover[section.keyword][section.block][description].append(dfn.path.stem)
        hover_sorted = {
            key: {
                subkey: {desc: sorted(paths) for desc, paths in sorted(subval.items())}
                for subkey, subval in sorted(val.items())
            }
            for key, val in sorted(hover.items())
        }
        output_path = "src/providers/hover.json"
        with open(output_path, "w") as f:
            json.dump(hover_sorted, f, indent=2)
            f.write("\n")
        log.info(f"Generated from DFN: {output_path}")


def render_template(output: str, **context):
    """Render a Jinja2 template and write the output to a file."""
    output_path = Path(output)
    template = Environment(
        loader=FileSystemLoader("templates"), keep_trailing_newline=True
    ).get_template(f"{output_path.name}.j2")
    context_sorted = {
        k: sorted(v) if isinstance(v, set) else v for k, v in context.items()
    }
    output_path.write_text(template.render(**context_sorted))
    log.info(f"Generated from DFN: {output_path}")


if __name__ == "__main__":
    # Collect blocks, keywords, valids, and extensions from dfn files
    extensions, blocks, keywords, valids = set(), set(), set(), set()
    for dfn in Dfn.get_dfns():
        extensions.add(dfn.extension)
        blocks.update(dfn.blocks)
        keywords.update(dfn.keywords)
        valids.update(*dfn.valids)

    # Insert collected data into the corresponding Jinja2 templates
    render_template("package.json", extensions=extensions)
    render_template(
        "syntaxes/mf6.tmLanguage.json",
        blocks=blocks,
        keywords=keywords,
        valids=valids,
    )

    # Export hover keyword data from dfn files
    Dfn.export_hover_keyword()
