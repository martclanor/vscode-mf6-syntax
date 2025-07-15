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
    Line: Represents a single line in a DFN file with a key-value structure
    Section: Represents a group of related lines in a DFN file, including metadata such
        as block, keyword, description, etc
    Dfn: Represents an entire DFN file, providing methods to parse, filter, process and
        extract data

Generated Files:
    - package.json: Contains extension metadata, including supported file extensions
    - syntaxes/mf6.tmLanguage.json: Defines syntax highlighting configuration
    - src/providers/hover-keyword.json: Provides hover data for MF6 keywords
    - src/providers/hover-block.json: Provides hover data for MF6 blocks

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
from enum import Enum
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

    def parse_as_is(self) -> str:
        return self.value

    def parse_bool(self) -> bool:
        return self.value.lower() == "true"

    def parse_valid(self) -> tuple[str, ...]:
        return tuple(self.value.split())

    def parse_shape(self) -> str:
        # Ignore if shape not enclosed in (), e.g. time_series_name in utl-tas.dfn
        # Ignore if shape == "(:)", e.g. slnmnames in sim-nam.dfn
        if self.value == "" or self.value[0] != "(" or self.value == "(:)":
            return ""
        return self.value

    def parse_type(self) -> tuple[str, ...]:
        return tuple(self.value.split())


class DfnField(Enum):
    """Mapping of DFN fields to Section attributes and Line parsers."""

    NAME = ("name", Line.parse_as_is)
    BLOCK = ("block", Line.parse_as_is)
    READER = ("reader", Line.parse_as_is)
    DESCRIPTION = ("description", Line.parse_as_is)
    SHAPE = ("shape", Line.parse_shape)
    TYPE = ("type", Line.parse_type)
    VALID = ("valid", Line.parse_valid)
    OPTIONAL = ("optional", Line.parse_bool)
    TAGGED = ("tagged", Line.parse_bool)
    IN_RECORD = ("in_record", Line.parse_bool)
    LAYERED = ("layered", Line.parse_bool)
    NETCDF = ("netcdf", Line.parse_bool)
    BLOCK_VARIABLE = ("block_variable", Line.parse_bool)
    JUST_DATA = ("just_data", Line.parse_bool)

    @classmethod
    def get_map(cls) -> dict[str, tuple[str, Callable[[Line], str | bool | tuple]]]:
        return {member.name.lower(): member.value for member in cls}


class IgnoredField(Enum):
    """Set of DFN fields to be ignored during parsing."""

    DEFAULT_VALUE = "default_value"
    DEPRECATED = "deprecated"
    EXTENDED = "extended"
    JAGGED_ARRAY = "jagged_array"
    LONGNAME = "longname"
    MF6INTERNAL = "mf6internal"
    NUMERIC_INDEX = "numeric_index"
    OTHER_NAMES = "other_names"
    PRESERVE_CASE = "preserve_case"
    REMOVED = "removed"
    REPEATING = "repeating"
    SUPPORT_NEGATIVE_INDEX = "support_negative_index"
    TIME_SERIES = "time_series"

    @classmethod
    def get_values(cls) -> set[str]:
        return {item.value for item in cls}


@dataclass
class Section:
    """Abstraction of each group of lines (separated by \n\n) from the DFN file."""

    name: str
    block: str
    reader: str = ""
    description: str = ""
    shape: str = ""
    type: tuple[str, ...] = ()
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
        return self.type[0] == "record" or self.type[0] == "recarray"

    @property
    def recs(self) -> tuple[str, ...]:
        if self.type_rec:
            return self.type[1:]
        return ()

    @property
    def dev_option(self) -> bool:
        return self.name.startswith("dev_")

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
            desc = Dfn.common[keyword]
            for key, value in replacement.items():
                desc = desc.replace(key, value)
        return desc.replace("``", "`").replace("''", "`").replace("\\", "")

    def get_block_begin(self) -> str:
        return f"BEGIN {self.block.upper()}"

    def get_block_end(self, block) -> str:
        return f"\n{' '.join(block.split()[:2]).replace('BEGIN', 'END')}"

    def get_block_variable(self) -> str:
        return f" <{self.name}>"

    def get_block_optional(self, text: str) -> str:
        return f"[{text}]"

    def get_block_type_rec(self, text: str):
        if self.optional:
            text = self.get_block_optional(text)
        if self.type[0] == "recarray":
            return f"\n  {text}\n  {text}\n  ..."
        return f"\n  {text}"

    def get_block_in_record(self, prefix: str) -> str:
        if self.type[0] != "keyword":
            text = f"<{self.name}{self.shape}>"
        else:
            text = self.name.upper()
        if self.optional:
            text = self.get_block_optional(text)
        return f"{prefix} {text}".strip()

    def get_block_body(self) -> str:
        body = self.name.upper()
        if self.reader == "readarray":
            if self.layered:
                body += " [LAYERED]"
            if self.netcdf:
                body += " [NETCDF]"
            body = (
                f"{body if not self.just_data else ''}\n      "
                f"<{self.name}{self.shape}> -- READARRAY"
            )
        elif self.type[0] != "keyword":
            body = f"{body} <{self.name}{self.shape}>"

        if self.optional:
            body = self.get_block_optional(body)

        if self.type[0] == "recarray":
            body += f"\n {body}\n  ..."

        return f"\n  {body}"

    @staticmethod
    def format_block_hover(text: str, block: str, dfn_name: str) -> str:
        return (
            f"```\n# Structure of {block.upper()} block in "
            f"{dfn_name.upper()}\n{text}\n```"
        )

    @classmethod
    def from_dfn(cls, data: str) -> "Section":
        kwargs: dict[str, str | bool | tuple] = {}
        field_map = DfnField.get_map()
        ignored_fields = IgnoredField.get_values()

        for line in (Line.from_dfn(_line) for _line in data.strip().split("\n")):
            if line.key in field_map:
                attr, parser = field_map[line.key]
                kwargs[attr] = parser(line)
            elif line.key in ignored_fields:
                pass
            else:
                raise ValueError(f"Unknown key '{line.key}' in section:\n\n{data}")

        return cls(**kwargs)


@dataclass
class Dfn:
    """Abstraction of each DFN file. DFN files are definition files from MODFLOW 6 which
    contains metadata for each block and keyword in the MF6 input files."""

    path: Path
    dfn_path: ClassVar[Path] = Path("data/dfn")
    cache: ClassVar[dict[Path, "Dfn"]] = {}
    common: ClassVar[dict[str, str]] = {}

    def __new__(cls, path: Path) -> "Dfn":
        return cls.cache.setdefault(path, super().__new__(cls))

    def __post_init__(self):
        self._data = self._read_data()

    def _read_data(self) -> tuple[str, ...]:
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
            return (data for data in self._data if data != "")
        return (data for data in self._data if data.startswith(prefix))

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
            section.name
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
        # common.dfn is a special file that contains template descriptions for keywords
        # which are used to replace placeholders in other DFN files
        common = {}
        for data in Dfn(Dfn.dfn_path / "common.dfn").get_data(prefix="name"):
            name, description = (Line.from_dfn(d) for d in data.split("\n"))
            common[name.value] = description.value
        return common

    @staticmethod
    def _sort_data(data: list | set | str | dict) -> list | set | str | dict:
        # Base case: lowest level of the data structure, list or set or string
        if isinstance(data, (list, set)):
            return sorted(data)
        elif isinstance(data, str):
            return data
        # Recursive case: apply function to the dictionary values
        return {key: Dfn._sort_data(value) for key, value in sorted(data.items())}

    @staticmethod
    def sort_and_export(
        data: dict, output: str, template: Optional[Environment] = None
    ) -> None:
        output_path = Path(output)
        data_sorted = Dfn._sort_data(data)
        if template is None:
            output_path.write_text(json.dumps(data_sorted, indent=2) + "\n")
        else:
            output_path.write_text(template.render(**data_sorted))
        log.info(f"Generated from DFN: {output_path}")

    @staticmethod
    def export_hover_keyword(output: str) -> None:
        hover: defaultdict[str, defaultdict[str, defaultdict[str, list[str]]]] = (
            defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )
        # Assign class variable that holds data for DFN text replacements
        Dfn.common = Dfn._parse_common()

        for dfn in Dfn.get_dfns():
            for section in dfn.get_sections(lambda s: not s.type_rec):
                hover[section.name][section.block][section.get_hover_keyword()].append(
                    dfn.name
                )

        Dfn.sort_and_export(hover, output)

    @staticmethod
    def export_hover_block(output: str) -> None:
        hover: defaultdict[str, defaultdict[str, str]] = defaultdict(
            lambda: defaultdict(str)
        )
        for dfn in Dfn.get_dfns():
            section_in_record = {
                (s.name, s.block): s for s in dfn.get_sections(lambda s: s.in_record)
            }
            # Exclude dev_options and sections that are handled in the inner loop
            for section in dfn.get_sections(
                lambda s: not s.dev_option
                and (not s.in_record or s.block_variable or s.type_rec)
            ):
                if not hover[section.block][dfn.name]:
                    hover[section.block][dfn.name] = section.get_block_begin()

                # Sections of type record or recarray have child in_record sections
                if section.type_rec:
                    section_children = [
                        section_in_record[rec, section.block]
                        for rec in section.recs
                        if (rec, section.block) in section_in_record
                    ]
                    if not section_children:
                        continue
                    entry = ""
                    for section_child in section_children:
                        entry = section_child.get_block_in_record(entry)

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

        Dfn.sort_and_export(hover, output)

    @staticmethod
    def render_template(output: str, **context) -> None:
        template = Environment(
            loader=FileSystemLoader("templates"), keep_trailing_newline=True
        ).get_template(f"{Path(output).name}.j2")
        Dfn.sort_and_export(context, output, template)


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
