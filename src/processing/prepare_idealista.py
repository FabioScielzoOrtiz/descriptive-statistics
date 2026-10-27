"""
Build the clean dataset of the course from the idealista18 files downloaded by
src/download/download_idealista.py.

Input : data/raw/idealista/Madrid_Sale.rda, data/raw/idealista/Madrid_Polygons.rda
Output: data/processed/idealista/madrid_listings_2018.csv
        one row per dwelling listed for sale in Madrid during 2018

Steps:

1. Read the R data files with the `rdata` package (no R installation needed).
2. Keep one row per listing: a dwelling advertised in several quarters appears
   several times in the original file; we keep its last appearance.
3. Locate each listing in its neighbourhood (point-in-polygon), and derive the
   district from the neighbourhood code. Listings whose coordinates fall outside
   the city (a few geocoding errors) are dropped.
4. Rename and code the variables in English.

Run from the project folder (after src/download/download_idealista.py):

    py src/processing/prepare_idealista.py
"""

import warnings
from pathlib import Path

import numpy as np
import polars as pl
import rdata
from matplotlib.path import Path as PolygonPath

PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_DIR / "data" / "raw" / "idealista"
OUT_FILE = PROJECT_DIR / "data" / "processed" / "idealista" / "madrid_listings_2018.csv"

# The 21 districts of Madrid, by their official code (the eighth field of the
# idealista neighbourhood code, e.g. 0-EU-ES-28-07-001-079-16-002 -> 16).
DISTRICTS = {
    "01": "Centro", "02": "Arganzuela", "03": "Retiro", "04": "Salamanca",
    "05": "Chamartín", "06": "Tetuán", "07": "Chamberí", "08": "Fuencarral-El Pardo",
    "09": "Moncloa-Aravaca", "10": "Latina", "11": "Carabanchel", "12": "Usera",
    "13": "Puente de Vallecas", "14": "Moratalaz", "15": "Ciudad Lineal",
    "16": "Hortaleza", "17": "Villaverde", "18": "Villa de Vallecas", "19": "Vicálvaro",
    "20": "San Blas-Canillejas", "21": "Barajas",
}
# Districts 1-7 lie (almost entirely) inside the M-30 ring road.
CENTRE_DISTRICTS = {"01", "02", "03", "04", "05", "06", "07"}
QUARTERS = {201803: "2018Q1", 201806: "2018Q2", 201809: "2018Q3", 201812: "2018Q4"}


def read_rda(path: Path):
    """Read the single object stored in an .rda file as a pandas DataFrame."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # rdata warns about the spatial classes of R's sf
        objects = rdata.read_rda(path, default_encoding="utf8", force_default_encoding=True)
    (data,) = objects.values()
    return data


def to_polars(pdf) -> pl.DataFrame:
    """Convert the pandas DataFrame returned by rdata to Polars, column by column."""
    columns = {}
    for name in pdf.columns:
        name_str = str(name)
        if name_str == "geometry":
            continue
        col = pdf[name]
        if col.dtype.name == "category" or col.dtype == object:
            columns[name_str] = pl.Series(name_str, [None if v is None else str(v) for v in col])
        else:
            values = col.to_numpy(dtype="float64", na_value=np.nan)
            columns[name_str] = pl.Series(name_str, values).fill_nan(None)
    return pl.DataFrame(columns)


def neighbourhood_of(lon: np.ndarray, lat: np.ndarray, polygons) -> np.ndarray:
    """Return, for each point, the index of the neighbourhood that contains it (-1 if none)."""
    points = np.column_stack([lon, lat])
    result = np.full(len(points), -1)
    for k, multipolygon in enumerate(polygons["geometry"]):
        inside = np.zeros(len(points), dtype=bool)
        for polygon in multipolygon:          # a multipolygon is a list of polygons
            exterior, *holes = polygon        # each polygon: exterior ring and holes
            in_polygon = PolygonPath(np.asarray(exterior)).contains_points(points)
            for hole in holes:
                in_polygon &= ~PolygonPath(np.asarray(hole)).contains_points(points)
            inside |= in_polygon
        result[(result == -1) & inside] = k
    return result


def yes_no(col: str, name: str) -> pl.Expr:
    return (pl.col(col) == 1).alias(name)


def main() -> None:
    for name in ["Madrid_Sale.rda", "Madrid_Polygons.rda"]:
        if not (RAW_DIR / name).exists():
            raise SystemExit(f"{RAW_DIR / name} not found: run src/download/download_idealista.py first")

    print("Reading the R data files (about 20 seconds)...")
    sale = read_rda(RAW_DIR / "Madrid_Sale.rda")
    polygons = read_rda(RAW_DIR / "Madrid_Polygons.rda")
    listings = to_polars(sale)
    n_rows = listings.height

    # 2. One row per listing: its last quarter on the market
    listings = (
        listings.sort("ASSETID", "PERIOD")
        .group_by("ASSETID", maintain_order=True).last()
    )
    n_listings = listings.height

    # 3. Neighbourhood and district
    k = neighbourhood_of(listings["LONGITUDE"].to_numpy(), listings["LATITUDE"].to_numpy(), polygons)
    location_ids = [str(v) for v in polygons["LOCATIONID"]]
    location_names = [str(v) for v in polygons["LOCATIONNAME"]]
    listings = listings.with_columns(
        neighbourhood=pl.Series([location_names[i] if i >= 0 else None for i in k]),
        district_code=pl.Series([location_ids[i].split("-")[7] if i >= 0 else None for i in k]),
    ).filter(pl.col("district_code").is_not_null())

    # 4. Clean variables
    condition = (
        pl.when(pl.col("BUILTTYPEID_1") == 1).then(pl.lit("New"))
        .when(pl.col("BUILTTYPEID_2") == 1).then(pl.lit("To renovate"))
        .when(pl.col("BUILTTYPEID_3") == 1).then(pl.lit("Good"))
        .otherwise(None)
    )
    clean = listings.select(
        pl.col("ASSETID").alias("listing_id"),
        pl.col("PERIOD").cast(pl.Int64).replace_strict(QUARTERS, return_dtype=pl.String).alias("quarter"),
        pl.col("district_code").replace_strict(DISTRICTS, return_dtype=pl.String).alias("district"),
        pl.col("neighbourhood"),
        pl.when(pl.col("district_code").is_in(list(CENTRE_DISTRICTS)))
          .then(pl.lit("Centre")).otherwise(pl.lit("Periphery")).alias("zone"),
        pl.col("PRICE").alias("price"),
        pl.col("UNITPRICE").round(1).alias("price_m2"),
        pl.col("CONSTRUCTEDAREA").cast(pl.Int64).alias("area_m2"),
        pl.col("ROOMNUMBER").cast(pl.Int64).alias("bedrooms"),
        pl.col("BATHNUMBER").cast(pl.Int64).alias("bathrooms"),
        pl.col("FLOORCLEAN").cast(pl.Int64).alias("floor"),
        pl.when(pl.col("FLATLOCATIONID") == 1).then(True)
          .when(pl.col("FLATLOCATIONID") == 2).then(False).otherwise(None).alias("exterior"),
        yes_no("HASLIFT", "lift"),
        yes_no("HASTERRACE", "terrace"),
        yes_no("HASAIRCONDITIONING", "air_conditioning"),
        yes_no("HASPARKINGSPACE", "parking"),
        yes_no("HASSWIMMINGPOOL", "swimming_pool"),
        yes_no("HASDOORMAN", "doorman"),
        yes_no("HASGARDEN", "garden"),
        yes_no("ISSTUDIO", "studio"),
        yes_no("ISINTOPFLOOR", "top_floor"),
        condition.alias("condition"),
        pl.col("CADCONSTRUCTIONYEAR").cast(pl.Int64).alias("construction_year"),
        pl.col("CADMAXBUILDINGFLOOR").cast(pl.Int64).alias("building_floors"),
        pl.col("CADDWELLINGCOUNT").cast(pl.Int64).alias("dwellings_in_building"),
        pl.when(pl.col("CADASTRALQUALITYID") > 0).then(pl.col("CADASTRALQUALITYID"))
          .otherwise(None).cast(pl.Int64).alias("cadastral_quality"),
        pl.col("DISTANCE_TO_CITY_CENTER").round(3).alias("dist_centre_km"),
        pl.col("DISTANCE_TO_METRO").round(3).alias("dist_metro_km"),
        pl.col("LONGITUDE").round(5).alias("longitude"),
        pl.col("LATITUDE").round(5).alias("latitude"),
    ).sort("listing_id")

    # Checks
    print(f"rows in the original file        : {n_rows:,}")
    print(f"distinct listings                : {n_listings:,}")
    print(f"dropped (outside the city)       : {n_listings - clean.height:,}")
    print(f"listings in the clean file       : {clean.height:,}")
    print(f"median price per m2              : {clean['price_m2'].median():,.0f} euros")
    print(f"districts                        : {clean['district'].n_unique()}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    clean.write_csv(OUT_FILE)
    print(f"Clean file written to {OUT_FILE}")


if __name__ == "__main__":
    main()
