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
from typing import ClassVar, Generator

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


@dataclass
class Line:
    """Abstraction of each line from the dfn file."""

    key: str
    value: str = ""

    @classmethod
    def from_file(cls, data: str) -> "Line":
        return cls(*data.split(maxsplit=1))

    @classmethod
    def from_replace(cls, data: str) -> "Line":
        return cls(data.split()[1])


@dataclass
class Section:
    """Abstraction of each group of lines (separated by \n\n) from the dfn file."""

    keyword: str
    block: str
    reader: str = ""
    description: str = ""
    shape: str = ""
    types: tuple[str, ...] = ()
    valid: tuple[str, ...] = ()
    optional: bool = False
    tagged: bool = True
    in_record: bool = False
    layered: bool = False
    netcdf: bool = False
    just_data: bool = False
    block_variable: bool = False

    @property
    def type_record(self) -> bool:
        return "record" in self.types

    @property
    def type_recarray(self) -> bool:
        return "recarray" in self.types

    @property
    def type_rec(self) -> bool:
        return self.type_record or self.type_recarray

    @staticmethod
    def _parse_bool(value: str) -> bool:
        return value.lower() == "true"

    @staticmethod
    def _parse_tuple(value: str) -> tuple[str, ...]:
        return tuple(value.split())

    @staticmethod
    def _parse_shape(value: str) -> str:
        # Ignore if shape is not enclosed in parentheses, e.g. time_series_name in utl-tas.dfn
        # Ignore if shape == "(:)" as in slnmnames in sim-nam.dfn
        if value == "" or value[0] != "(" or value == "(:)":
            return ""
        return value

    @classmethod
    def from_file(cls, data: str) -> "Section":
        kwargs: dict[str, str | bool | tuple] = {}
        for line in [Line.from_file(_line) for _line in data.strip().split("\n")]:
            value: str = line.value
            match line.key:
                case "name":
                    kwargs["keyword"] = value
                case "block":
                    kwargs["block"] = value
                case "reader":
                    kwargs["reader"] = value
                case "description":
                    # Use line.value instead of value to keep the case
                    kwargs["description"] = line.value
                case "shape":
                    kwargs["shape"] = cls._parse_shape(value)
                case "type":
                    kwargs["types"] = cls._parse_tuple(value)
                case "valid":
                    kwargs["valid"] = cls._parse_tuple(value)
                case "optional":
                    kwargs["optional"] = cls._parse_bool(value)
                case "tagged":
                    kwargs["tagged"] = cls._parse_bool(value)
                case "in_record":
                    kwargs["in_record"] = cls._parse_bool(value)
                case "layered":
                    kwargs["layered"] = cls._parse_bool(value)
                case "netcdf":
                    kwargs["netcdf"] = cls._parse_bool(value)
                case "block_variable":
                    kwargs["block_variable"] = cls._parse_bool(value)
                case "just_data":
                    kwargs["just_data"] = cls._parse_bool(value)
                case (
                    "longname"
                    | "default_value"
                    | "numeric_index"
                    | "time_series"
                    | "preserve_case"
                    | "mf6internal"
                    | "extended"
                    | "removed"
                    | "repeating"
                    | "deprecated"
                    | "other_names"
                    | "jagged_array"
                    | "support_negative_index"
                ):
                    # For completeness, these fields are in the dfn but are not used in the current implementation
                    pass
                case _:
                    raise ValueError(
                        f"Unknown key '{line.key}' in section:\n\n{data.strip()}"
                    )

        return cls(**kwargs)


@dataclass
class Dfn:
    """Abstraction of each dfn file. Dfn files are definition files from MODFLOW 6 which
    contains metadata for each block and keyword in the MF6 input files."""

    path: Path
    dfn_path: ClassVar[Path] = Path("data/dfn")

    @property
    def data(self) -> tuple[str, ...]:
        with self.path.open() as f:
            data = tuple(
                "\n".join(
                    line
                    for line in section.splitlines()
                    if not line.lstrip().startswith("#")
                )
                for section in f.read().split("\n\n")
            )
        return data

    def get_data(self, prefix: str = "") -> Generator[str, None, None]:
        if prefix == "":
            return (data for data in self.data if data != "")
        return (data for data in self.data if data.startswith(prefix))

    def get_sections(self, filter_fn=None) -> Generator[Section, None, None]:
        sections = (Section.from_file(data) for data in self.get_data())
        if filter_fn is None:
            return sections
        return (section for section in sections if filter_fn(section))

    @property
    def blocks(self) -> set[str]:
        return {p.block for p in self.get_sections()}

    @property
    def keywords(self) -> set[str]:
        return {
            section.keyword
            for section in self.get_sections(lambda s: s.tagged and not s.type_rec)
        }

    @property
    def valids(self) -> set[str]:
        return {
            valid
            for section in self.get_sections(lambda s: s.valid)
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
    def export_hover_keyword(output: str) -> None:
        hover: defaultdict[str, defaultdict[str, defaultdict[str, list[str]]]] = (
            defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )
        common = Dfn._parse_common()

        for dfn in Dfn.get_dfns():
            for section in dfn.get_sections(lambda s: not s.type_rec):
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

        Path(output).write_text(json.dumps(hover_sorted, indent=2) + "\n")
        log.info(f"Generated from DFN: {output}")

    @staticmethod
    def export_hover_block(output: str) -> None:
        hover: defaultdict[str, defaultdict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for dfn in Dfn.get_dfns():
            # in_record sections that are not of type record, recarray or block_variable
            # are excluded from the outer loop
            # these will be handled in the inner loop instead
            skip = [
                (section.block, section.keyword)
                for section in dfn.get_sections(
                    lambda s: s.in_record and not s.block_variable and not s.type_rec
                )
            ]

            for section in dfn.get_sections():
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
                if section.type_rec:
                    section_types = section.types[1:]
                    entry_list = []

                    # Skip keystrings
                    if "keystring" in section.types:
                        continue

                    for t in section_types:
                        for s in dfn.get_sections():
                            if t == s.keyword and s.block == section.block:
                                # Retrieve the child section of interest
                                section_inner = s
                                break
                        if section_inner.in_record:
                            if "keyword" not in section_inner.types:
                                e = f"<{section_inner.keyword}{section_inner.shape}>"
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
                elif section.block_variable:
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
                    entry = f"{entry} <{section.keyword}{section.shape}>"

                if section.optional:
                    entry = f"[{entry}]"

                hover[section.block][dfn.path.stem].append(entry)

        # Complete hover text then convert to string
        hover_str: defaultdict[str, defaultdict[str, str]] = defaultdict(
            lambda: defaultdict(str)
        )
        for block in hover:
            # Variable dfn is already used
            for dfn_ in hover[block]:
                for i, line in enumerate(hover[block][dfn_]):
                    if not line.startswith("BEGIN"):
                        # Indent lines within the block
                        hover[block][dfn_][i] = "  " + line

                # Add END line: take first two words from the first line
                hover[block][dfn_].append(
                    " ".join(hover[block][dfn_][0].split()[:2]).replace("BEGIN", "END")
                )
                # Join list into a single string
                hover_str[block][dfn_] = "\n".join(hover[block][dfn_])

        hover_sorted = {
            block: {dfn: lines for dfn, lines in sorted(subval.items())}
            for block, subval in sorted(hover_str.items())
        }

        Path(output).write_text(json.dumps(hover_sorted, indent=2) + "\n")
        log.info(f"Generated from DFN: {output}")


def render_template(output: str, **context) -> None:
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
