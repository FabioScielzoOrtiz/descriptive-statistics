"""
Download the idealista18 data for Madrid: housing listings for sale in 2018 and
the boundaries of the city's neighbourhoods.

The files come from the idealista18 data package (Rey-Blanco, Arbués, López and
Páez, 2024), published under the Open Database License (ODbL 1.0):
https://github.com/paezha/idealista18

Two R data files are downloaded into data/raw/idealista/ (about 7 MB):

- Madrid_Sale.rda      listings for sale in Madrid, one row per listing and quarter
- Madrid_Polygons.rda  boundaries of the 135 neighbourhoods used by idealista

Files that are already downloaded are skipped. Run from the project folder:

    py src/download/download_idealista.py
"""

from pathlib import Path
import urllib.request

BASE_URL = "https://raw.githubusercontent.com/paezha/idealista18/master/data"
FILES = ["Madrid_Sale.rda", "Madrid_Polygons.rda"]
PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data" / "raw" / "idealista"


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
        print(f"{name}: downloading")
        download(f"{BASE_URL}/{name}", dest)
    print(f"Done. Files in {RAW_DIR}")


if __name__ == "__main__":
    main()
