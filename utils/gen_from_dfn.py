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
    'utils/download_dfn.sh') and preprocess the data to generate the following:
        'package.json'
        'syntaxes/mf6.tmLanguage.json'
        'src/providers/hover.json'
"""

import ast
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, Generator, Optional

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
        return cls(*data.split(maxsplit=1))

    @classmethod
    def from_replace(cls, data: str) -> "Line":
        return cls(data.split()[1], value=None)


@dataclass
class Section:
    """Abstraction of each group of lines (separated by \n\n) from the dfn file."""

    keyword: str
    block: str
    type_rec: bool  # whether type is either record or recarray
    valid: tuple[str, ...]
    tagged: bool
    description: str

    @classmethod
    def from_file(cls, data: str) -> "Section":
        # Set default values
        type_rec = False
        valid = None
        tagged = True
        description = None

        for _line in data.strip().split("\n"):
            if _line.split(maxsplit=1)[0] not in {
                "block",
                "name",
                "type",
                "valid",
                "tagged",
                "description",
            }:
                continue

            line = Line.from_file(_line)
            match line.key:
                case "block":
                    block = line.value
                case "name":
                    keyword = line.value
                case "type":
                    types = line.value.split()
                    if "record" in types or "recarray" in types:
                        type_rec = True
                case "valid":
                    if (value := line.value) is not None:
                        valid = tuple(value.split())
                case "tagged":
                    if line.value is not None and "false" in line.value:
                        tagged = False
                case "description":
                    description = line.value

        return cls(
            block=block,
            keyword=keyword,
            type_rec=type_rec,
            valid=valid,
            tagged=tagged,
            description=description,
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

    def get_data(self, prefix: str) -> Generator[str, None, None]:
        return (data for data in self.data if data.startswith(prefix))

    @property
    def sections(self) -> tuple[Section, ...]:
        sections = []
        for data in self.get_data(prefix="block"):
            section = Section.from_file(data)
            if section.type_rec:
                continue
            sections.append(section)
        return tuple(sections)

    @property
    def blocks(self) -> set[str]:
        return {p.block for p in self.sections}

    @property
    def keywords(self) -> set[str]:
        return {section.keyword for section in self.sections if section.tagged}

    @property
    def valids(self) -> set[str]:
        return {
            valid
            for section in self.sections
            if section.valid
            for valid in section.valid
        }

    @property
    def extension(self) -> str:
        return f".{self.path.stem.partition('-')[-1]}"

    @staticmethod
    def get_dfns() -> Generator["Dfn", None, None]:
        return (
            Dfn(filename)
            for filename in Dfn.dfn_path.glob("*.dfn")
            if filename.name != "common.dfn"
        )

    @staticmethod
    def _parse_common() -> dict[str, str]:
        # common.dfn is a special file that contains common descriptions for keywords
        # which are used to replace placeholders in other dfn files
        common = {}
        for section in Dfn(Dfn.dfn_path / "common.dfn").get_data(prefix="name"):
            name, description = [
                Line.from_file(data) for data in section.strip().split("\n")
            ]
            if not (name.key == "name" and description.key == "description"):
                continue
            common[name.value] = description.value
        return common

    @staticmethod
    def export_hover_keyword(output: str) -> dict[str, dict[str, dict[str, list[str]]]]:
        hover = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        common = Dfn._parse_common()

        for dfn in Dfn.get_dfns():
            for section in dfn.sections:
                if (description := section.description) is None:
                    continue
                if "REPLACE" in description:
                    keyword = Line.from_replace(description).key
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
            keyword: {
                block: {desc: sorted(dfn) for desc, dfn in sorted(subval.items())}
                for block, subval in sorted(val.items())
            }
            for keyword, val in sorted(hover.items())
        }

        with open(output, "w") as f:
            json.dump(hover_sorted, f, indent=2)
            f.write("\n")
        log.info(f"Generated from DFN: {output}")


def render_template(output: str, **context):
    """Render a Jinja2 template and write the output to a file."""
    output_path = Path(output)
    template = Environment(
        loader=FileSystemLoader("templates"), keep_trailing_newline=True
    ).get_template(f"{output_path.name}.j2")
    context_sorted = {k: sorted(v) for k, v in context.items()}
    output_path.write_text(template.render(**context_sorted))
    log.info(f"Generated from DFN: {output_path}")


if __name__ == "__main__":
    # Collect blocks, keywords, valids, and extensions from dfn files
    extensions, blocks, keywords, valids = set(), set(), set(), set()
    for dfn in Dfn.get_dfns():
        extensions.add(dfn.extension)
        blocks.update(dfn.blocks)
        keywords.update(dfn.keywords)
        valids.update(dfn.valids)

    # Insert collected data into the corresponding Jinja2 templates
    render_template("package.json", extensions=extensions)
    render_template(
        "syntaxes/mf6.tmLanguage.json",
        blocks=blocks,
        keywords=keywords,
        valids=valids,
    )

    # Export hover keyword data from dfn files
    Dfn.export_hover_keyword("src/providers/hover.json")
