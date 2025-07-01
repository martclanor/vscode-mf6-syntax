# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "jinja2",
# ]
# ///

"""
This script processes MODFLOW 6 definition (DFN) files to generate configuration and
data files for the extension.

Classes:
    Line: Represents a single line in a DFN file with a key-value structure.
    Section: Represents a group of related lines  in a DFN file, including metadata such
        as block, keyword, description, etc
    Dfn: Represents an entire DFN file, providing methods to parse, filter, and extract
        data.

Generated Files:
    - package.json: Contains metadata about the extension, including supported file
      extensions.
    - syntaxes/mf6.tmLanguage.json: Defines syntax highlighting configuration
    - src/providers/hover-keyword.json: Provides hover description data for MF6 keywords
    - src/providers/hover-block.json: Provides hover description data for MF6 blocks

Usage:
    - Download DFN files from the MODFLOW 6 repository using:
        utils/download-dfn.sh
    - Run this script to generate the output files:
        uv run utils/gen_from_dfn.py
"""

import ast
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Callable, ClassVar, Generator, Optional

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


@dataclass
class Line:
    """Abstraction of each line from the DFN file."""

    key: str
    value: str = ""

    @classmethod
    def from_dfn(cls, data: str) -> "Line":
        return cls(*data.split(maxsplit=1))

    @classmethod
    def from_replace(cls, data: str) -> "Line":
        return cls(data.split()[1])


@dataclass
class Section:
    """Abstraction of each group of lines (separated by \n\n) from the DFN file."""

    keyword: str
    block: str
    reader: str = ""
    description: str = ""
    shape: str = ""
    type_: str = ""
    recs: tuple[str, ...] = ()  # Not explicit in DFN, but part of type
    valid: tuple[str, ...] = ()
    optional: bool = False
    tagged: bool = True
    in_record: bool = False
    layered: bool = False
    netcdf: bool = False
    just_data: bool = False
    block_variable: bool = False

    @property
    def type_rec(self) -> bool:
        return self.type_ == "record" or self.type_ == "recarray"

    @property
    def dev_option(self) -> bool:
        return self.keyword.startswith("dev_")

    def get_hover_keyword(self) -> str:
        if "REPLACE" not in self.description:
            desc = self.description
        else:
            keyword = Line.from_replace(self.description).key
            # Create replacement dictionary from the original description
            replacement = ast.literal_eval(
                self.description.lstrip(f"REPLACE {keyword} ")
            )
            # Take new description from common.dfn, then replace placeholders
            desc = Dfn._common[keyword]
            for key, value in replacement.items():
                desc = desc.replace(key, value)
        return desc.replace("``", "`").replace("''", "`").replace("\\", "")

    def get_block_begin(self) -> str:
        return f"BEGIN {self.block.upper()}"

    def get_block_end(self, block) -> str:
        return f"\n{' '.join(block.split()[:2]).replace('BEGIN', 'END')}"

    def get_block_variable(self) -> str:
        return f" <{self.keyword}>"

    def get_block_optional(self, text: str) -> str:
        return f"[{text}]"

    def get_block_type_rec(self, text: str):
        if self.optional:
            text = self.get_block_optional(text)
        if self.type_ == "recarray":
            return f"\n  {text}\n  {text}\n  ..."
        return f"\n  {text}"

    def get_block_in_record(self, prefix: str) -> str:
        if self.type_ != "keyword":
            text = f"<{self.keyword}{self.shape}>"
        else:
            text = self.keyword.upper()
        if self.optional:
            text = self.get_block_optional(text)
        return f"{prefix} {text}".strip()

    def get_block_body(self) -> str:
        body = self.keyword.upper()
        if self.reader == "readarray":
            if self.layered:
                body += " [LAYERED]"
            if self.netcdf:
                body += " [NETCDF]"
            body = f"{body if not self.just_data else ''}\n      <{self.keyword}{self.shape}> -- READARRAY"
        elif self.type_ != "keyword":
            body = f"{body} <{self.keyword}{self.shape}>"

        if self.optional:
            body = self.get_block_optional(body)

        if self.type_ == "recarray":
            body += f"\n {body}\n  ..."

        return f"\n  {body}"

    @staticmethod
    def format_block_hover(text: str, block: str, dfn_name: str) -> str:
        return f"```\n# Structure of {block.upper()} block in {dfn_name.upper()}\n{text}\n```"

    @staticmethod
    def _parse_bool(value: str) -> bool:
        return value.lower() == "true"

    @staticmethod
    def _parse_tuple(value: str) -> tuple[str, ...]:
        return tuple(value.split())

    @staticmethod
    def _parse_shape(value: str) -> str:
        # Ignore if shape is not enclosed in parentheses, e.g. time_series_name in utl-tas.dfn
        # Ignore if shape == "(:)", e.g. slnmnames in sim-nam.dfn
        if value == "" or value[0] != "(" or value == "(:)":
            return ""
        return value

    @staticmethod
    def _parse_type(value: str) -> str:
        if "record" in value or "recarray" in value or "keystring" in value:
            return value.split(maxsplit=1)[0]
        if "double precision" in value:
            return " ".join(value.split(maxsplit=2)[0:2])
        return value

    @staticmethod
    def _parse_recs(value: str) -> tuple[str, ...]:
        if "record" in value or "recarray" in value:
            return tuple(value.split()[1:])
        return ()

    @classmethod
    def from_dfn(cls, data: str) -> "Section":
        kwargs: dict[str, str | bool | tuple] = {}
        for line in [Line.from_dfn(_line) for _line in data.strip().split("\n")]:
            match line.key:
                case "name":
                    kwargs["keyword"] = line.value
                case "block":
                    kwargs["block"] = line.value
                case "reader":
                    kwargs["reader"] = line.value
                case "description":
                    kwargs["description"] = line.value
                case "shape":
                    kwargs["shape"] = cls._parse_shape(line.value)
                case "type":
                    kwargs["type_"] = cls._parse_type(line.value)
                    kwargs["recs"] = cls._parse_recs(line.value)
                case "valid":
                    kwargs["valid"] = cls._parse_tuple(line.value)
                case "optional":
                    kwargs["optional"] = cls._parse_bool(line.value)
                case "tagged":
                    kwargs["tagged"] = cls._parse_bool(line.value)
                case "in_record":
                    kwargs["in_record"] = cls._parse_bool(line.value)
                case "layered":
                    kwargs["layered"] = cls._parse_bool(line.value)
                case "netcdf":
                    kwargs["netcdf"] = cls._parse_bool(line.value)
                case "block_variable":
                    kwargs["block_variable"] = cls._parse_bool(line.value)
                case "just_data":
                    kwargs["just_data"] = cls._parse_bool(line.value)
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
                    # For completeness, these fields are in the DFNs but are not used in the current implementation
                    pass
                case _:
                    raise ValueError(f"Unknown key '{line.key}' in section:\n\n{data}")

        return cls(**kwargs)


@dataclass
class Dfn:
    """Abstraction of each DFN file. DFN files are definition files from MODFLOW 6 which
    contains metadata for each block and keyword in the MF6 input files."""

    path: Path
    dfn_path: ClassVar[Path] = Path("data/dfn")
    _common: ClassVar[dict[str, str]] = {}

    @cached_property
    def data(self) -> tuple[str, ...]:
        with self.path.open() as f:
            return tuple(
                "\n".join(
                    line
                    for line in section.splitlines()
                    if not line.lstrip().startswith("#")
                )
                for section in f.read().split("\n\n")
            )

    def get_data(self, prefix: Optional[str] = None) -> Generator[str, None, None]:
        if prefix is None:
            return (data for data in self.data if data != "")
        return (data for data in self.data if data.startswith(prefix))

    def get_sections(
        self, filter_fn: Optional[Callable[[Section], bool]] = None
    ) -> Generator[Section, None, None]:
        sections = (Section.from_dfn(data) for data in self.get_data())
        if filter_fn is None:
            return sections
        return (section for section in sections if filter_fn(section))

    @property
    def name(self) -> str:
        return self.path.stem

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
        return {valid for section in self.get_sections() for valid in section.valid}

    @property
    def extension(self) -> str:
        return f".{self.name.partition('-')[-1]}"

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
        # which are used to replace placeholders in other DFN files
        common = {}
        for data in Dfn(Dfn.dfn_path / "common.dfn").get_data(prefix="name"):
            name, description = [Line.from_dfn(d) for d in data.split("\n")]
            common[name.value] = description.value
        return common

    @staticmethod
    def _sort_hover_data(obj: list | str | dict) -> list | str | dict:
        # Base case: lowest level of the data structure, list or string
        if isinstance(obj, list):
            return sorted(obj)
        elif isinstance(obj, str):
            return obj
        # Recursive case: apply function to the dictionary values
        return {key: Dfn._sort_hover_data(value) for key, value in sorted(obj.items())}

    @staticmethod
    def export_hover_keyword(output: str) -> None:
        hover: defaultdict[str, defaultdict[str, defaultdict[str, list[str]]]] = (
            defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )
        # Assign class variable that holds data for DFN text replacements
        Dfn._common = Dfn._parse_common()

        for dfn in Dfn.get_dfns():
            for section in dfn.get_sections(lambda s: not s.type_rec):
                hover[section.keyword][section.block][
                    section.get_hover_keyword()
                ].append(dfn.name)

        hover_sorted = Dfn._sort_hover_data(hover)
        Path(output).write_text(json.dumps(hover_sorted, indent=2) + "\n")
        log.info(f"Generated from DFN: {output}")

    @staticmethod
    def export_hover_block(output: str) -> None:
        hover: defaultdict[str, defaultdict[str, str]] = defaultdict(
            lambda: defaultdict(str)
        )
        for dfn in Dfn.get_dfns():
            # Exclude dev_options and sections that are handled in the inner loop
            for section in dfn.get_sections(
                lambda s: not s.dev_option
                and (not s.in_record or s.block_variable or s.type_rec)
            ):
                if not hover[section.block][dfn.name]:
                    hover[section.block][dfn.name] = section.get_block_begin()

                # Sections that are of type record or recarray have child sections
                if section.type_rec:
                    entry = ""
                    for rec in section.recs:
                        for sec in dfn.get_sections():
                            if rec == sec.keyword and section.block == sec.block:
                                # Retrieve child section
                                section_rec = sec
                                break
                        if section_rec.in_record:
                            entry = section_rec.get_block_in_record(entry)
                    # Ignore if one of the recs are "in_record"
                    if not entry:
                        continue
                    hover[section.block][dfn.name] += section.get_block_type_rec(entry)

                elif section.block_variable:
                    hover[section.block][dfn.name] += section.get_block_variable()

                else:
                    hover[section.block][dfn.name] += section.get_block_body()

        # Another pass to add the block end line and format
        for block in hover:
            for dfn_name in hover[block]:
                hover[block][dfn_name] += section.get_block_end(hover[block][dfn_name])
                hover[block][dfn_name] = Section.format_block_hover(
                    hover[block][dfn_name], block, dfn_name
                )

        hover_sorted = Dfn._sort_hover_data(hover)
        Path(output).write_text(json.dumps(hover_sorted, indent=2) + "\n")
        log.info(f"Generated from DFN: {output}")

    @staticmethod
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
    # Collect blocks, keywords, valids, and extensions from DFN files
    extensions, blocks, keywords, valids = set(), set(), set(), set()
    for dfn in Dfn.get_dfns():
        extensions.add(dfn.extension)
        blocks.update(dfn.blocks)
        keywords.update(dfn.keywords)
        valids.update(dfn.valids)

    # Insert collected data into the corresponding Jinja2 templates
    Dfn.render_template("package.json", extensions=extensions)
    Dfn.render_template(
        "syntaxes/mf6.tmLanguage.json",
        blocks=blocks,
        keywords=keywords,
        valids=valids,
    )

    # Export hover keyword and hover block data from DFN files
    Dfn.export_hover_keyword("src/providers/hover-keyword.json")
    Dfn.export_hover_block("src/providers/hover-block.json")
