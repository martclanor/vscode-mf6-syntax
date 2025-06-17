# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "jinja2",
# ]
# ///

"""
This script processes MODFLOW 6 definition (dfn) files to generate configuration and
data files for the extension.

Classes:
    Line: Represents a single line in a dfn file, with a key-value structure.
    Section: Represents a group of related lines (a section) in a dfn file, including
        metadata such as block, keyword, description, etc
    Dfn: Represents an entire dfn file, providing methods to parse, filter, and
        extract data for further processing.

Generated Files:
    - package.json: Contains metadata about the extension, including supported file
      extensions.
    - syntaxes/mf6.tmLanguage.json: Defines syntax highlighting configuration
    - src/providers/hover-keyword.json: Provides hover description data for MF6 keywords
    - src/providers/hover-block.json: Provides hover description data for MF6 blocks

Usage:
    - Download dfn files from the MODFLOW 6 repository using:
        utils/download-dfn.sh
    - Run this script to generate the output files:
        uv run utils/gen_from_dfn.py
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
    types: list[str]
    type_record: bool
    type_recarray: bool
    block_var: bool
    shape: str
    reader: str
    in_rec: bool
    valid: tuple[str, ...]
    layered: bool
    netcdf: bool
    tagged: bool
    just_data: bool
    optional: bool
    description: str

    @classmethod
    def from_file(cls, data: str) -> "Section":
        # Set default values
        types = []
        type_record = False
        type_recarray = False
        block_var = False
        shape = ""
        reader = ""
        in_rec = False
        valid = None
        layered = False
        netcdf = False
        tagged = True
        just_data = False
        optional = False
        description = None

        for _line in data.strip().split("\n"):
            if _line.split(maxsplit=1)[0] not in {
                "block",
                "name",
                "type",
                "block_variable",
                "shape",
                "reader",
                "in_record",
                "valid",
                "layered",
                "netcdf",
                "tagged",
                "just_data",
                "optional",
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
                    if "record" in types:
                        type_record = True
                    if "recarray" in types:
                        type_recarray = True
                case "block_variable":
                    if line.value is not None and "true" in line.value.lower():
                        block_var = True
                case "shape":
                    if (value := line.value) is not None:
                        shape = value
                case "reader":
                    if (value := line.value) is not None:
                        reader = value
                case "in_record":
                    if line.value == "true":
                        in_rec = True
                case "valid":
                    if (value := line.value) is not None:
                        valid = tuple(value.split())
                case "layered":
                    if line.value is not None and "true" in line.value.lower():
                        layered = True
                case "netcdf":
                    if line.value is not None and "true" in line.value.lower():
                        netcdf = True
                case "tagged":
                    if line.value is not None and "false" in line.value:
                        tagged = False
                case "just_data":
                    if line.value is not None and "true" in line.value:
                        just_data = True
                case "optional":
                    if line.value is not None and "true" in line.value:
                        optional = True
                case "description":
                    description = line.value

        return cls(
            block=block,
            keyword=keyword,
            types=types,
            type_record=type_record,
            type_recarray=type_recarray,
            block_var=block_var,
            shape=shape,
            reader=reader,
            in_rec=in_rec,
            valid=valid,
            layered=layered,
            netcdf=netcdf,
            tagged=tagged,
            just_data=just_data,
            optional=optional,
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
            self._data = tuple(
                # Strip comment lines
                "\n".join(
                    line
                    for line in section.splitlines()
                    if not line.strip().startswith("#")
                )
                for section in f.read().split("\n\n")
            )

    @property
    def data(self) -> tuple[str, ...]:
        return self._data

    def get_data(self, prefix: str = "") -> Generator[str, None, None]:
        if prefix == "":
            return (data for data in self.data if data != "")
        return (data for data in self.data if data.startswith(prefix))

    @property
    def sections(self) -> tuple[Section, ...]:
        sections = []
        for data in self.get_data():
            section = Section.from_file(data)
            if section.type_record or section.type_recarray:
                continue
            sections.append(section)
        return tuple(sections)

    @property
    def sections_all(self) -> tuple[Section, ...]:
        sections = []
        for data in self.get_data():
            section = Section.from_file(data)
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

    @staticmethod
    def export_hover_block(output: str) -> dict[str, dict[str, str]]:
        hover = defaultdict(lambda: defaultdict(list))
        for dfn in Dfn.get_dfns():
            # in_record sections that are not of type record, recarray or block_variable
            # are excluded from the outer loop
            # these will be handled in the inner loop instead
            skip = [
                (section.block, section.keyword)
                for section in dfn.sections_all
                if section.in_rec
                and not (
                    section.block_var or section.type_record or section.type_recarray
                )
            ]

            for section in dfn.sections_all:
                # Initialize the hover entry with BEGIN line
                if not hover[section.block][dfn.path.stem]:
                    hover[section.block][dfn.path.stem].append(
                        f"BEGIN {section.block.upper()}"
                    )

                # Skip dev options
                if section.keyword.startswith("dev_"):
                    continue

                # Skip as these will be handled in the inner loop
                if (section.block, section.keyword) in skip:
                    continue

                # Sections that are of type record or recarray have child sections
                if section.type_record or section.type_recarray:
                    section_types = section.types[1:]
                    entry_list = []

                    # Skip keystrings
                    if "keystring" in section.types:
                        continue

                    for t in section_types:
                        for s in dfn.sections_all:
                            if t == s.keyword and s.block == section.block:
                                # Retrieve the child section of interest
                                section_inner = s
                                break
                        if section_inner.in_rec:
                            if "keyword" not in section_inner.types:
                                # Some of the shapes are not enclosed in (), ignore these
                                e = f"<{section_inner.keyword}{'' if '(' not in section_inner.shape else section_inner.shape}>"
                            else:
                                # Capitalize if it is a keyword
                                e = section_inner.keyword.upper()
                            if section_inner.optional:
                                # Enclose in () if optional
                                e = f"[{e}]"
                            entry_list.append(e)
                            entry = " ".join(entry_list)
                            if section.optional:
                                # Enclose the entire entry in () if optional
                                entry = f"[{entry}]"
                    hover[section.block][dfn.path.stem].append(entry)

                    if section.type_recarray:
                        # Add duplicate entry and ellipsis for recarray types
                        hover[section.block][dfn.path.stem].append(entry)
                        hover[section.block][dfn.path.stem].append("...")
                    continue

                if section.just_data:
                    entry = ""
                elif section.block_var:
                    entry = f"<{section.keyword}>"
                    hover[section.block][dfn.path.stem][0] += f" {entry}"
                    continue
                else:
                    # Base case
                    entry = section.keyword.upper()

                # Special handling for readarray reader
                if section.reader == "readarray":
                    if section.layered:
                        entry = f"{entry} [LAYERED]"
                    if section.netcdf:
                        entry = f"{entry} [NETCDF]"
                    entry = f"{entry}\n      <{section.keyword}{section.shape}> -- READARRAY"
                elif "keyword" not in section.types:
                    # Some of the shapes are not enclosed in (), ignore these
                    entry = f"{entry} <{section.keyword}{'' if '(' not in section.shape else section.shape}>"

                if section.optional:
                    entry = f"[{entry}]"

                hover[section.block][dfn.path.stem].append(entry)

        for block in hover:
            for dfn in hover[block]:
                for i, line in enumerate(hover[block][dfn]):
                    if not line.startswith("BEGIN"):
                        # Indent lines within the block
                        hover[block][dfn][i] = "  " + line

                # Add END line: take first two words from the first line
                hover[block][dfn].append(
                    " ".join(hover[block][dfn][0].split()[:2]).replace("BEGIN", "END")
                )
                # Join list into a single string
                hover[block][dfn] = "\n".join(hover[block][dfn])

        hover_sorted = {
            block: {dfn: lines for dfn, lines in sorted(subval.items())}
            for block, subval in sorted(hover.items())
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

    # Export hover keyword and hover block data from dfn files
    Dfn.export_hover_keyword("src/providers/hover-keyword.json")
    Dfn.export_hover_block("src/providers/hover-block.json")
