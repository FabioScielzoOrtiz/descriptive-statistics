"""
Build the clean datasets of the course from the INE Household Budget Survey
(EPF) microdata downloaded by src/download/download_epf.py.

Input : data/raw/epf/datos_<YEAR>.zip
Output: data/processed/epf/households.csv        one row per household
        data/processed/epf/members.csv           one row per person
        data/processed/epf/expenditures.parquet  one row per household and expenditure item

Variables are renamed and coded in English. Categorical variables are
decoded with the INE code lists, and the script stops if it finds a code that
is not in them. Expenditures are converted from population totals to amounts
per household (see the note below).

Note on expenditures. In the INE files every expenditure is "elevado temporal
y poblacionalmente": the household's annual expenditure multiplied by its
weight (FACTOR). Dividing by FACTOR gives the annual expenditure of the
household itself, which is what the clean files contain.

Run from the project folder (after download_epf.py):

    py src/processing/prepare_epf.py
"""

import io
import json
import zipfile
from pathlib import Path

import polars as pl

YEAR = 2025
PROJECT_DIR = Path(__file__).resolve().parents[2]
RAW_ZIP = PROJECT_DIR / "data" / "raw" / "epf" / f"datos_{YEAR}.zip"
OUT_DIR = PROJECT_DIR / "data" / "processed" / "epf"

# --------------------------------------------------------------------------
# Code lists (INE codes -> English labels). The order of each dictionary is
# the order of the categories (pl.Enum), so ordinal variables are ordered.
# --------------------------------------------------------------------------

REGION = {
    "01": "Andalusia", "02": "Aragon", "03": "Asturias", "04": "Balearic Islands",
    "05": "Canary Islands", "06": "Cantabria", "07": "Castile and Leon",
    "08": "Castile-La Mancha", "09": "Catalonia", "10": "Valencian Community",
    "11": "Extremadura", "12": "Galicia", "13": "Madrid", "14": "Murcia",
    "15": "Navarre", "16": "Basque Country", "17": "La Rioja", "18": "Ceuta",
    "19": "Melilla",
}
MUNICIPALITY_SIZE = {  # ordered from small to large
    "5": "Less than 10,000", "4": "10,000 to 19,999", "3": "20,000 to 49,999",
    "2": "50,000 to 99,999", "1": "100,000 or more",
}
DENSITY = {"3": "Thinly populated", "2": "Intermediate", "1": "Densely populated"}
RESIDENTIAL_AREA = {"4": "Rural", "3": "Urban, low", "2": "Urban, middle", "1": "Urban, high"}
SEX = {"1": "Male", "6": "Female"}
NATIONALITY = {"1": "Spanish", "2": "Foreign", "3": "Spanish and foreign"}
EDUCATION = {
    "1": "Below lower secondary", "2": "Lower secondary",
    "3": "Upper secondary", "4": "Tertiary",
}
ACTIVITY = {"1": "Active", "2": "Inactive"}
SOCIOECONOMIC = {
    "1": "Manual worker", "2": "Non-manual worker",
    "3": "Self-employed or agricultural", "4": "Unemployed", "5": "Retired",
    "6": "Other inactive", "7": "Other",
}
TENURE = {
    "1": "Owned outright", "2": "Owned with mortgage", "3": "Rented",
    "4": "Rented below market", "5": "Provided at reduced cost", "6": "Provided free",
}
TENURE_GROUP = {"1": "Owned", "2": "Owned", "3": "Rented", "4": "Rented", "5": "Other", "6": "Other"}
BUILDING_AGE = {"1": "Less than 25 years", "6": "25 years or more"}
INCOME_SOURCE = {
    "2": "Employee earnings", "1": "Self-employment and property income",
    "3": "Pensions and benefits",
}
INCOME_BAND = {  # net monthly household income
    "0": "No regular income", "01": "Less than 500", "02": "500 to 999",
    "03": "1,000 to 1,499", "04": "1,500 to 1,999", "05": "2,000 to 2,499",
    "06": "2,500 to 2,999", "07": "3,000 to 4,999", "08": "5,000 to 6,999",
    "09": "7,000 to 8,999", "10": "9,000 or more",
}
MEMBER_TYPE = {"1": "Household member", "2": "Domestic worker", "3": "Lodger", "4": "Guest"}
MARITAL_STATUS = {
    "1": "Single", "2": "Married", "3": "Widowed", "4": "Divorced", "5": "Separated",
}
EMPLOYED = {"1": "Employed", "2": "Not employed"}
WORKING_TIME = {"1": "Full-time", "2": "Part-time"}
YES_NO = {"1": True, "6": False}

# COICOP 2018 divisions (first two digits of the expenditure code).
DIVISIONS = {
    "01": ("food", "Food and non-alcoholic beverages"),
    "02": ("alcohol_tobacco", "Alcoholic beverages and tobacco"),
    "03": ("clothing", "Clothing and footwear"),
    "04": ("housing", "Housing, water, electricity, gas and other fuels"),
    "05": ("furnishings", "Furnishings and household equipment"),
    "06": ("health", "Health"),
    "07": ("transport", "Transport"),
    "08": ("communication", "Information and communication"),
    "09": ("recreation", "Recreation, sport and culture"),
    "10": ("education", "Education services"),
    "11": ("restaurants", "Restaurants and accommodation services"),
    "12": ("insurance_finance", "Insurance and financial services"),
    "13": ("personal_care_misc", "Personal care and miscellaneous"),
}

MISSING_CODES = ["-9"]  # "No consta" in the INE code lists


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def read_file(outer: zipfile.ZipFile, name: str, columns: list[str] | None = None) -> tuple[pl.DataFrame, dict]:
    """Read one INE file (e.g. 'EPFhogar') from the nested zip, all columns as text.

    Only `columns` are read, if given. Returns the data and its record layout
    (JSON with variable descriptions and code lists).
    """
    inner = zipfile.ZipFile(io.BytesIO(outer.read(f"{name}.zip")))
    data = pl.read_csv(
        inner.read(f"CSV/{name}_{YEAR}.tab"), separator="\t", infer_schema=False,
        columns=columns,
    )
    layout = json.loads(inner.read(f"dr_{name}_{YEAR}.json").decode("utf-8-sig"))
    return data, layout


def decode(col: str, mapping: dict, name: str | None = None) -> pl.Expr:
    """Translate INE codes with `mapping`; missing codes (-9) become null.

    replace_strict raises an error if a code is not in the mapping, so a change
    in the INE coding is detected instead of silently producing nulls.
    """
    values = list(dict.fromkeys(mapping.values()))
    dtype = pl.Boolean if all(isinstance(v, bool) for v in values) else pl.Enum(values)
    clean = pl.when(pl.col(col).is_in(MISSING_CODES)).then(None).otherwise(pl.col(col))
    return clean.replace_strict(mapping, return_dtype=dtype).alias(name or col)


def number(col: str, name: str | None = None, dtype=pl.Float64, missing_as_null=True) -> pl.Expr:
    """Cast a text column to a number; -9 ("No consta") becomes null."""
    x = pl.col(col).cast(dtype)
    if missing_as_null:
        x = pl.when(x == -9).then(None).otherwise(x)
    return x.alias(name or col)


def per_household(col: str, name: str) -> pl.Expr:
    """Population-elevated amount -> annual amount of the household (euros)."""
    return (pl.col(col).cast(pl.Float64) / pl.col("FACTOR").cast(pl.Float64)).round(2).alias(name)


# --------------------------------------------------------------------------
# The three tables
# --------------------------------------------------------------------------

def build_households(raw: pl.DataFrame) -> pl.DataFrame:
    division_cols = [
        per_household(f"GASTOTGR{code}", f"exp_{short}")
        for code, (short, _) in DIVISIONS.items()
    ]
    return raw.select(
        pl.col("NUMERO").cast(pl.Int64).alias("household_id"),
        number("FACTOR", "weight"),
        # Location
        decode("CCAA", REGION, "region"),
        decode("TAMAMU", MUNICIPALITY_SIZE, "municipality_size"),
        decode("DENSIDAD", DENSITY, "population_density"),
        decode("ZONARES", RESIDENTIAL_AREA, "residential_area"),
        # Composition
        number("NMIEMB", "household_size", pl.Int64),
        number("NMIEM2", "n_under_14", pl.Int64),
        (pl.col("NMIEM12").cast(pl.Int64) + pl.col("NMIEM13").cast(pl.Int64)).alias("n_65_plus"),
        number("NUMOCUP", "n_employed", pl.Int64),
        number("NUMPERI", "n_earners", pl.Int64),
        number("UC2", "equivalent_size"),
        # Reference person (sustentador principal)
        decode("SEXOSP", SEX, "ref_sex"),
        number("EDADSP", "ref_age", pl.Int64),
        decode("NACIONASP", NATIONALITY, "ref_nationality"),
        decode("ESTUDREDSP", EDUCATION, "ref_education"),
        decode("SITUREDSP", ACTIVITY, "ref_activity"),
        decode("SITSOCIRE", SOCIOECONOMIC, "ref_socioeconomic"),
        # Dwelling
        decode("REGTEN", TENURE, "tenure"),
        decode("REGTEN", TENURE_GROUP, "tenure_group"),
        number("SUPERF", "floor_area_m2", pl.Int64),
        number("NHABIT", "n_rooms", pl.Int64),
        decode("ANNOCON", BUILDING_AGE, "building_age"),
        number("VALOREST", "dwelling_value"),
        # Income (net, monthly)
        number("IMPEXAC", "monthly_income"),
        decode("INTERIN", INCOME_BAND, "income_band"),
        decode("FUENPRINRED", INCOME_SOURCE, "main_income_source"),
        # Expenditure (annual, euros)
        per_household("GASTOT", "exp_total"),
        per_household("GASTMON", "exp_monetary"),
        per_household("GASTNOM4", "exp_imputed_rent"),
        *division_cols,
        number("IMPUTGAS", "pct_exp_imputed"),
    ).sort("household_id")


def build_members(raw: pl.DataFrame) -> pl.DataFrame:
    return raw.select(
        pl.col("NUMERO").cast(pl.Int64).alias("household_id"),
        pl.col("NORDEN").cast(pl.Int64).alias("person_id"),
        number("FACTOR", "weight"),
        decode("CATEGMH", MEMBER_TYPE, "member_type"),
        decode("SUSPRIN", YES_NO, "is_reference_person").fill_null(False),
        decode("SEXO", SEX, "sex"),
        number("EDAD", "age", pl.Int64),
        decode("ESTADOCIVIL", MARITAL_STATUS, "marital_status"),
        decode("NACIONA", NATIONALITY, "nationality"),
        decode("ESTUDRED", EDUCATION, "education"),
        decode("SITURED", ACTIVITY, "activity"),
        decode("OCU", EMPLOYED, "employed"),
        decode("JORNADA", WORKING_TIME, "working_time"),
        number("IMPEXACP", "monthly_income"),
    ).sort("household_id", "person_id")


def build_expenditures(raw: pl.DataFrame, layout: dict) -> pl.DataFrame:
    items = layout["codelists"]["ECOICOP"]  # 5-character code -> Spanish label
    division_names = {code: long for code, (_, long) in DIVISIONS.items()}
    return raw.select(
        pl.col("NUMERO").cast(pl.Int64).alias("household_id"),
        pl.col("CODIGO").alias("code"),
        pl.col("CODIGO").str.slice(0, 2).replace_strict(
            division_names, return_dtype=pl.Enum(list(division_names.values()))
        ).alias("division"),
        pl.col("CODIGO").replace_strict(items, return_dtype=pl.String).alias("item_es"),
        per_household("GASTO", "expenditure"),
        per_household("GASTMON", "exp_monetary"),
        per_household("CANTIDAD", "quantity"),
        number("PORCENIMP", "pct_imputed"),
    ).sort("household_id", "code")


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------

def check(households: pl.DataFrame, members: pl.DataFrame, expenditures: pl.DataFrame) -> None:
    w = households["weight"]
    print(f"households: {households.height:,} rows, representing {w.sum():,.0f} households")
    print(f"members   : {members.height:,} rows")
    print(f"items     : {expenditures.height:,} rows")
    mean_exp = (households["exp_total"] * w).sum() / w.sum()
    print(f"weighted mean annual expenditure per household: {mean_exp:,.0f} euros "
          f"(INE press release for 2025: 35,101)")

    # The items of each household add up to its total expenditure.
    by_hh = expenditures.group_by("household_id").agg(pl.col("expenditure").sum().alias("sum_items"))
    diff = households.join(by_hh, on="household_id", how="left").select(
        (pl.col("exp_total") - pl.col("sum_items").fill_null(0)).abs().max()
    ).item()
    print(f"largest |total - sum of items| (euros): {diff:.2f}")

    # Every household has exactly one reference person.
    n_ref = members.filter(pl.col("is_reference_person")).group_by("household_id").len()
    ok = n_ref.height == households.height and (n_ref["len"] == 1).all()
    print(f"one reference person per household: {ok}")


def main() -> None:
    if not RAW_ZIP.exists():
        raise SystemExit(f"{RAW_ZIP} not found: run src/download/download_epf.py first")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(RAW_ZIP) as outer:
        print("Reading households...")
        households = build_households(read_file(outer, "EPFhogar")[0])
        print("Reading members...")
        members = build_members(read_file(outer, "EPFmhogar")[0])
        print("Reading expenditures (about 2 million rows)...")
        raw, layout = read_file(outer, "EPFgastos", columns=[
            "NUMERO", "CODIGO", "GASTO", "GASTMON", "CANTIDAD", "PORCENIMP", "FACTOR"])
        expenditures = build_expenditures(raw, layout)
        del raw

    check(households, members, expenditures)

    households.write_csv(OUT_DIR / "households.csv")
    members.write_csv(OUT_DIR / "members.csv")
    expenditures.write_parquet(OUT_DIR / "expenditures.parquet")
    print(f"Clean files written to {OUT_DIR}")


if __name__ == "__main__":
    main()
