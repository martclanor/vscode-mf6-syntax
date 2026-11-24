# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "modflow-devtools[ecosystem] @ git+https://github.com/MODFLOW-ORG/modflow-devtools.git@develop",
# ]
# ///

"""This script downloads the definition files from the MODFLOW 6 repository for each
version listed in `mf6-versions.txt` and saves them to `data/dfns/{version}`. Versions
with existing DFN files are skipped"""

from pathlib import Path

from modflow_devtools.dfns import fetch_dfns

if __name__ == "__main__":
    with open("mf6-versions.txt") as f:
        for version in (line.strip() for line in f if line.strip()):
            outdir = Path("data/dfns") / version
            if any(path.is_file() for path in outdir.glob("*.dfn")):
                print(f"Skipping {version}: DFN files already exist in {outdir}")
                continue
            fetch_dfns(
                owner="MODFLOW-ORG",
                repo="modflow6",
                ref=version,
                outdir=outdir,
                verbose=True,
            )
