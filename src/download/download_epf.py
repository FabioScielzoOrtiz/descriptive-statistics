"""
Download the microdata of the INE Household Budget Survey (Encuesta de
Presupuestos Familiares, EPF) for one year.

Two files are downloaded into data/raw/epf/ (about 225 MB in total):

- datos_<YEAR>.zip   the microdata: household, member and expenditure files,
                     each in CSV (tab-separated), parquet, R, SAS, SPSS and Stata,
                     together with its record layout in JSON;
- dr_EPF_<YEAR>.zip  the record layouts and code lists in Excel (for reading).

Source: https://www.ine.es (INEbase > Encuesta de presupuestos familiares.
Base 2006 > Microdatos). Files that are already downloaded are skipped.

Run from the project folder:

    py src/download/download_epf.py
"""

from pathlib import Path
import urllib.request

YEAR = 2025
BASE_URL = "https://www.ine.es/ftp/microdatos/epf2006"
FILES = [f"datos_{YEAR}.zip", f"dr_EPF_{YEAR}.zip"]
PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data" / "raw" / "epf"


def download(url: str, dest: Path, chunk: int = 1 << 20) -> None:
    """Download url to dest, showing progress; write to a temporary file first."""
    tmp = dest.with_suffix(dest.suffix + ".part")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=60) as response, open(tmp, "wb") as out:
        total = int(response.headers.get("Content-Length", 0))
        done = 0
        while block := response.read(chunk):
            out.write(block)
            done += len(block)
            if total:
                print(f"\r  {done / 1e6:6.1f} / {total / 1e6:.1f} MB", end="", flush=True)
    print()
    tmp.replace(dest)


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        dest = RAW_DIR / name
        if dest.exists():
            print(f"{name}: already downloaded, skipped")
            continue
        print(f"{name}: downloading from {BASE_URL}")
        download(f"{BASE_URL}/{name}", dest)
    print(f"Done. Files in {RAW_DIR}")


if __name__ == "__main__":
    main()
