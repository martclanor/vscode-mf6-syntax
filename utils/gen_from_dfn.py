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
    - syntaxes/mf6.tmLanguage.json: Defines syntax highlighting config for input files
    - syntaxes/mf6-lst.tmLanguage.json: Defines syntax highlighting config for lst files
    - src/providers/hover-keyword/<version>.json: Provides hover data for MF6 keywords
    - src/providers/hover-block/<version>.json: Provides hover data for MF6 blocks
    - src/providers/hover-recarray/<version>.json: Provides hover data for MF6 recarrays
    - src/providers/symbol-defn/<version>.json: Defines symbols for MF6 input files
    - src/providers/symbol-defn-lst/<version>.json: Defines symbols for MF6 lst files

Usage:
    - Download DFN files from the MODFLOW 6 repository using:
        utils/download-dfn.sh
    - Run this script to generate the output files:
        uv run utils/gen_from_dfn.py
"""

import ast
import json
import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, ClassVar, Generator, Optional, overload

from jinja2 import Environment, FileSystemLoader, Template

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
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

    def parse_shape(self) -> str:
        # Ignore if shape not enclosed in (), e.g. time_series_name in utl-tas.dfn
        # Ignore if shape == "(:)", e.g. slnmnames in sim-nam.dfn
        if self.value == "" or self.value[0] != "(" or self.value == "(:)":
            return ""
        return self.value


FIELD_PARSERS: dict[str, Callable[[Line], str | bool]] = {
    "name": Line.parse_as_is,
    "block": Line.parse_as_is,
    "reader": Line.parse_as_is,
    "description": Line.parse_as_is,
    "type": Line.parse_as_is,
    "valid": Line.parse_as_is,
    "shape": Line.parse_shape,
    "optional": Line.parse_bool,
    "tagged": Line.parse_bool,
    "in_record": Line.parse_bool,
    "layered": Line.parse_bool,
    "netcdf": Line.parse_bool,
    "block_variable": Line.parse_bool,
    "just_data": Line.parse_bool,
    "prerelease": Line.parse_bool,
}

IGNORED_FIELDS: frozenset[str] = frozenset(
    {
        "default",
        "default_value",
        "deprecated",
        "extended",
        "jagged_array",
        "longname",
        "mf6internal",
        "numeric_index",
        "other_names",
        "preserve_case",
        "removed",
        "repeating",
        "support_negative_index",
        "time_series",
        "valid_values",
    }
)

MTYPES: frozenset[str] = frozenset(("gwe", "gwf", "gwt", "prt"))


@dataclass(frozen=True, slots=True)
class Section:
    """Abstraction of each group of lines (separated by \n\n) from the DFN file."""

    name: str
    block: str = ""
    reader: str = ""
    description: str = ""
    type: str = ""
    valid: str = ""
    shape: str = ""
    optional: bool = False
    tagged: bool = True
    in_record: bool = False
    layered: bool = False
    netcdf: bool = False
    just_data: bool = False
    block_variable: bool = False
    prerelease: bool = False

    @classmethod
    def from_dfn(cls, data: str) -> "Section":
        kwargs: dict[str, str | bool | tuple] = {}
        for line in (Line.from_dfn(_line) for _line in data.strip().split("\n")):
            if line.key in IGNORED_FIELDS:
                continue
            if parser := FIELD_PARSERS.get(line.key):
                kwargs[line.key] = parser(line)
            else:
                raise ValueError(f"Unknown key '{line.key}' in section:\n\n{data}")
        return cls(**kwargs)  # type: ignore[arg-type]

    @property
    def is_keyword(self) -> bool:
        return self.type.startswith("keyword")

    @property
    def is_recarray(self) -> bool:
        return self.type.startswith("recarray")

    @property
    def is_record(self) -> bool:
        return self.type.startswith("record")

    @property
    def is_rec(self) -> bool:
        return self.is_recarray or self.is_record

    @property
    def is_readarray(self) -> bool:
        return self.reader == "readarray"

    @property
    def is_replaced(self) -> bool:
        return "REPLACE" in self.description

    @property
    def is_dev_option(self) -> bool:
        return self.name.startswith("dev_")

    @property
    def recs(self) -> tuple[str, ...]:
        if self.is_rec:
            return tuple(self.type.split()[1:])
        return ()

    def get_hover_keyword(self, common: dict[str, str]) -> str:
        if not self.is_replaced:
            desc = self.description
        else:
            keyword = Line.from_replace(self.description).key
            # Create replacement dictionary from the original description
            replacement_str = self.description.lstrip(f"REPLACE {keyword} ")

            # Fix for typo in 6.0.2 gwf-maw.dfn's cellid description
            if replacement_str[-1] != "}":
                match = re.search(r".*\}", replacement_str)
                replacement_str = match.group(0) if match else "{}"

            replacement = ast.literal_eval(replacement_str)
            # Take new description from common.dfn, then replace placeholders
            desc = common[keyword]
            for key, value in replacement.items():
                desc = desc.replace(key, value)
        return desc.replace("``", "`").replace("''", "`").replace("\\", "")

    def get_block_begin(self) -> str:
        return f"BEGIN {self.block.upper()}"

    def get_block_variable(self) -> str:
        return f" <{self.name}>"

    def get_block_type_rec(self, text: str):
        if self.optional:
            text = self.get_block_optional(text)
        if self.is_recarray:
            return f"\n  {text}\n  {text}\n  ..."
        return f"\n  {text}"

    def get_block_in_record(self, prefix: str) -> str:
        if not self.is_keyword:
            text = f"<{self.name}{self.shape}>"
        else:
            text = self.name.upper()
        if self.optional:
            text = self.get_block_optional(text)
        return f"{prefix} {text}".strip()

    def get_block_body(self) -> str:
        body = self.name.upper()
        if self.is_readarray:
            if self.layered:
                body += " [LAYERED]"
            if self.netcdf:
                body += " [NETCDF]"
            body = (
                f"{body if not self.just_data else ''}\n      "
                f"<{self.name}{self.shape}> -- READARRAY"
            )
        elif not self.is_keyword:
            body = f"{body} <{self.name}{self.shape}>"

        if self.optional:
            body = self.get_block_optional(body)

        if self.is_recarray:
            body += f"\n {body}\n  ..."

        return f"\n  {body}"

    @staticmethod
    def get_block_optional(text: str) -> str:
        return f"[{text}]"

    @staticmethod
    def get_block_end(block) -> str:
        return f"\nEND {block.upper()}"

    @staticmethod
    def format_block_hover(text: str, block: str, dfn_name: str) -> str:
        return (
            f"```\n# Structure of {block.upper()} block in "
            f"{dfn_name.upper()}\n{text}\n```"
        )


@dataclass
class Dfn:
    """Abstraction of each DFN file. DFN files are definition files from MODFLOW 6 which
    contains metadata for each block and keyword in the MF6 input files."""

    path: Path
    sections: tuple[Section, ...]

    dfn_path: ClassVar[Path]
    cache: ClassVar[dict[Path, "Dfn"]] = {}
    common: ClassVar[dict[str, str]] = {}

    @classmethod
    def load(cls, path: Path) -> "Dfn":
        if path in cls.cache:
            return cls.cache[path]
        return cls.cache.setdefault(path, cls(path, cls._read_sections(path)))

    @staticmethod
    def get_versions() -> list[str]:
        with open("mf6-versions.txt") as f:
            versions = [line.strip() for line in f if line.strip()]
        return versions

    @staticmethod
    def _read_sections(path: Path) -> tuple[Section, ...]:
        with path.open() as f:
            data = (
                section
                for section in (
                    "\n".join(
                        line
                        for line in section.splitlines()
                        if not line.lstrip().startswith("#")
                    )
                    for section in f.read().split("\n\n")
                )
                if section != ""
            )
            return tuple(Section.from_dfn(d) for d in data)

    def get_sections(
        self, filter_fn: Optional[Callable[[Section], bool]] = None
    ) -> Generator[Section, None, None]:
        if filter_fn is None:
            yield from self.sections
        else:
            yield from (section for section in self.sections if filter_fn(section))

    @property
    def name(self) -> str:
        return self.path.stem

    @property
    def is_mtype(self) -> bool:
        return self.name.partition("-")[0] in MTYPES

    @property
    def ftype(self) -> str:
        return f"{self.name.partition('-')[-1]}6"

    @property
    def is_exgtype(self) -> bool:
        return self.name.startswith("exg-")

    @property
    def exgtype(self) -> str:
        name_part = self.name.partition("-")[-1]
        models = [name_part[i : i + 3] for i in range(0, len(name_part), 3)]
        return "-".join(f"{chunk}6" for chunk in models)

    @property
    def blocks(self) -> set[str]:
        return {p.block for p in self.get_sections()}

    @property
    def keywords(self) -> set[str]:
        return {
            section.name
            for section in self.get_sections(lambda s: s.tagged and not s.is_rec)
        }

    @property
    def valids(self) -> set[str]:
        return {
            valid for section in self.get_sections() for valid in section.valid.split()
        }

    @property
    def extension(self) -> str:
        return f".{self.name.partition('-')[-1]}"

    @staticmethod
    def get_dfns() -> Generator["Dfn", None, None]:
        return (
            Dfn.load(filename)
            for filename in Dfn.dfn_path.glob("*.dfn")
            if filename.name != "common.dfn"
        )

    @staticmethod
    def get_common() -> dict[str, str]:
        if Dfn.common:
            return Dfn.common
        for section in Dfn.load(Dfn.dfn_path / "common.dfn").get_sections():
            Dfn.common[section.name] = section.description
        return Dfn.common

    @staticmethod
    @overload
    def _sort_data(data: dict) -> dict: ...

    @staticmethod
    @overload
    def _sort_data(data: list) -> list: ...

    @staticmethod
    @overload
    def _sort_data(data: set) -> list: ...

    @staticmethod
    @overload
    def _sort_data(data: str) -> str: ...

    @staticmethod
    def _sort_data(data: list | set | str | dict) -> list | str | dict:
        # Base case: lowest level of the data structure, list or set or string
        if isinstance(data, (list, set)):
            return sorted(data)
        elif isinstance(data, str):
            return data
        # Recursive case: apply function to the dictionary values
        return {key: Dfn._sort_data(value) for key, value in sorted(data.items())}

    @staticmethod
    def sort_and_export(
        data: dict | set, output: str, template: Optional[Template] = None
    ) -> None:
        output_path = Path(output)
        data_sorted = Dfn._sort_data(data)
        if template is not None and isinstance(data_sorted, dict):
            output_path.write_text(template.render(**data_sorted))
        else:
            output_path.write_text(json.dumps(data_sorted, indent=2) + "\n")
        log.info(f"- {output_path}")

    @staticmethod
    def export_hover_keyword(output: str) -> None:
        hover: defaultdict[str, defaultdict[str, defaultdict[str, list[str]]]] = (
            defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
        )

        for dfn in Dfn.get_dfns():
            for section in dfn.get_sections(lambda s: not s.is_rec):
                hover[section.name][section.block][
                    section.get_hover_keyword(Dfn.get_common())
                ].append(dfn.name)

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
                lambda s: not s.is_dev_option
                and (not s.in_record or s.block_variable or s.is_rec)
            ):
                if not hover[section.block][dfn.name]:
                    hover[section.block][dfn.name] = section.get_block_begin()

                # Sections of type record or recarray have child in_record sections
                if section.is_rec:
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
                hover[block][dfn_name] += Section.get_block_end(block)
                hover[block][dfn_name] = Section.format_block_hover(
                    hover[block][dfn_name], block, dfn_name
                )

        Dfn.sort_and_export(hover, output)

    @staticmethod
    def export_hover_recarray(output: str) -> None:
        hover: defaultdict[str, dict[str, list[str]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for dfn in Dfn.get_dfns():
            for section in dfn.get_sections(lambda s: s.is_recarray):
                hover[section.block][",".join(section.recs)].append(dfn.name)

        Dfn.sort_and_export(hover, output)

    @staticmethod
    def export_symbol_defn(output: str) -> None:
        symbol_defn: defaultdict[str, set[str]] = defaultdict(set)
        for dfn in Dfn.get_dfns():
            for section in dfn.get_sections():
                _ = symbol_defn[section.block]
                if section.is_readarray:
                    symbol_defn[section.block].add(section.name)
        Dfn.sort_and_export(symbol_defn, output)

    @staticmethod
    def export_symbol_defn_lst(output: str, data: set) -> None:
        Dfn.sort_and_export({item.upper().strip(".") for item in data}, output)

    @staticmethod
    def render_template(output: str, **context) -> None:
        template = Environment(
            loader=FileSystemLoader("templates"), keep_trailing_newline=True
        ).get_template(f"{re.sub(r'-\d+(\.\d+)*', '', Path(output).name)}.j2")
        Dfn.sort_and_export(context, output, template)


if __name__ == "__main__":
    # Collect blocks, keywords, valids, and extensions from DFN files
    extensions, blocks, keywords, valids, ftypes, exgtypes = (set() for _ in range(6))

    for version in Dfn.get_versions():
        Dfn.dfn_path = Path(f"data/dfn/{version}")
        log.info(f"Generating files from DFN's of MODFLOW {version}")

        extensions_symbol_defn_lst: set[str] = set()
        for dfn in Dfn.get_dfns():
            extensions.add(dfn.extension)
            extensions_symbol_defn_lst.add(dfn.extension)
            blocks.update(dfn.blocks)
            keywords.update(dfn.keywords)
            valids.update(dfn.valids)
            if dfn.is_mtype:
                ftypes.add(dfn.ftype)
            if dfn.is_exgtype:
                exgtypes.add(dfn.exgtype)

        # Export hover keyword and hover block data from DFN files
        Dfn.export_hover_keyword(f"src/providers/hover-keyword/{version}.json")
        Dfn.export_hover_block(f"src/providers/hover-block/{version}.json")
        Dfn.export_hover_recarray(f"src/providers/hover-recarray/{version}.json")

        # Export symbol definition data from DFN files
        Dfn.export_symbol_defn(f"src/providers/symbol-defn/{version}.json")
        Dfn.export_symbol_defn_lst(
            f"src/providers/symbol-defn-lst/{version}.json",
            data=extensions_symbol_defn_lst,
        )

        # Clear version-specific cached data
        Dfn.cache = {}
        Dfn.common = {}

    # Insert collected data into the corresponding Jinja2 templates
    log.info("Rendering jinja templates with collected data")
    Dfn.render_template(
        "package.json", versions=Dfn.get_versions(), extensions=extensions
    )
    Dfn.render_template(
        "syntaxes/mf6.tmLanguage.json",
        blocks=blocks,
        keywords=keywords,
        valids=valids,
        ftypes=ftypes,
        mtypes=sorted(MTYPES),
        exgtypes=exgtypes,
    )
    Dfn.render_template("syntaxes/mf6-lst.tmLanguage.json", extensions=extensions)
