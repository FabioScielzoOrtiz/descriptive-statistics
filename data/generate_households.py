"""
Generate `households.csv`: a SIMULATED household survey used throughout the notes.

The data mimic the structure of real income and living-conditions surveys (for
example, the Spanish Survey on Income and Living Conditions), but they are
fictitious. A fixed seed makes all the material reproducible.

Usage (from the project root):
    python data/generate_households.py
"""

from pathlib import Path

import numpy as np
import polars as pl

SEED = 2026
N = 500

rng = np.random.default_rng(SEED)

# --- Qualitative variables ---------------------------------------------------
regions = ["Madrid", "Catalonia", "Andalusia", "Valencia", "Galicia", "Basque Country"]
region = rng.choice(regions, size=N, p=[0.22, 0.24, 0.22, 0.14, 0.09, 0.09])

levels = ["Primary", "Secondary", "Tertiary"]
education = rng.choice(levels, size=N, p=[0.22, 0.43, 0.35])

tenure = rng.choice(["Owned", "Rented", "Rent-free"], size=N, p=[0.72, 0.23, 0.05])

# --- Discrete quantitative variable ------------------------------------------
household_size = rng.choice([1, 2, 3, 4, 5, 6], size=N,
                            p=[0.26, 0.31, 0.20, 0.16, 0.05, 0.02])

# --- Continuous quantitative variables ---------------------------------------
# Annual net household income (euros): log-normal, right-skewed, with effects of
# education, region and household size.
education_effect = pl.Series(education).replace_strict(
    {"Primary": -0.30, "Secondary": 0.0, "Tertiary": 0.35}
).to_numpy()
region_effect = pl.Series(region).replace_strict(
    {"Madrid": 0.15, "Catalonia": 0.10, "Basque Country": 0.20,
     "Andalusia": -0.15, "Valencia": -0.05, "Galicia": -0.05}
).to_numpy()
log_income = (
    np.log(30_000)
    + education_effect
    + region_effect
    + 0.08 * (household_size - 2)
    + rng.normal(0, 0.45, size=N)
)
income = np.round(np.exp(log_income), -1)

# Monthly food expenditure (euros): increases with income and household size.
food_expenditure = np.round(
    120 + 95 * household_size + 0.004 * income + rng.normal(0, 60, size=N), 2
)
food_expenditure = np.clip(food_expenditure, 80, None)

households = pl.DataFrame(
    {
        "household_id": np.arange(1, N + 1),
        "region": region,
        "education": education,
        "tenure": tenure,
        "household_size": household_size,
        "annual_income": income,
        "food_expenditure": food_expenditure,
    }
)

output = Path(__file__).parent / "households.csv"
households.write_csv(output)
print(f"Saved {output} ({households.height} rows)")
