"""
Assignment: Data Preparation & Pipeline Project (AI Engineering Bootcamp)
Author    : Kanza Az Zahrawani <rexxar280903@gmail.com>

ETL pipeline sederhana untuk mengolah automobileEDA_dirty_training.csv
menjadi processed dataset yang bersih dan siap untuk tahap modeling:
    Extract   -> load_data()      : baca CSV mentah dari data/raw/
    Transform -> inspect_data()   : inspeksi awal kualitas data
                 clean_data()     : handling missing value, duplikat, teks, dtypes
                 transform_data() : Min-Max scaling & categorical encoding
    Load      -> save_data()      : simpan output ke data/processed/

Jalankan dari root folder:
    python src/pipeline.py
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "automobileEDA_dirty_training.csv"
PROCESSED_PATH = PROJECT_ROOT / "data" / "processed" / "automobileEDA_processed.csv"

CATEGORICAL_COLS = [
    "make", "aspiration", "num-of-doors", "body-style", "drive-wheels",
    "engine-location", "engine-type", "num-of-cylinders", "fuel-system",
    "horsepower-binned",
]

# Columns used to recognise "the same car model" when imputing a missing make.
SPEC_COLS = ["wheel-base", "length", "width", "height", "engine-size", "bore"]

# Numeric columns normalised with Min-Max scaling (different units / ranges).
MINMAX_COLS = [
    "price", "horsepower", "engine-size", "curb-weight",
    "peak-rpm", "city-mpg", "highway-mpg",
]

# Nominal categories -> One-Hot Encoding (no natural order).
ONEHOT_COLS = [
    "aspiration", "body-style", "drive-wheels", "engine-location",
    "engine-type", "fuel-system",
]

# Ordinal categories -> mapped to numbers that keep their order.
WORD_TO_NUMBER = {
    "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "eight": 8, "twelve": 12,
}
HP_BIN_ORDER = {"Low": 0, "Medium": 1, "High": 2}

LINE = "=" * 78


def section(title: str) -> None:
    print(f"\n{LINE}\n{title}\n{LINE}")


# --------------------------------------------------------------------------- #
# EXTRACT
# --------------------------------------------------------------------------- #
def load_data(path: Path = RAW_PATH) -> pd.DataFrame:
    """Read the raw CSV. The source file is opened read-only."""
    section("1. EXTRACT - Load raw dataset")
    if not path.exists():
        raise FileNotFoundError(f"Raw dataset not found: {path}")
    df = pd.read_csv(path)
    print(f"Source : {path.relative_to(PROJECT_ROOT)}")
    print(f"Loaded : {df.shape[0]} rows x {df.shape[1]} columns")
    return df


# --------------------------------------------------------------------------- #
# TRANSFORM - inspection
# --------------------------------------------------------------------------- #
def inspect_data(df: pd.DataFrame) -> dict:
    """Print an initial data-quality report and return its key numbers."""
    section("2. INSPECTION - Initial condition of the dataset")

    with pd.option_context("display.max_columns", None, "display.width", 200):
        print("\n[First 5 rows]")
        print(df.head())

    print(f"\n[Shape] {df.shape[0]} rows, {df.shape[1]} columns")
    print("\n[Column names]")
    print(", ".join(df.columns))

    print("\n[Data types]")
    print(df.dtypes.astype(str).to_string())

    missing = df.isna().sum()
    print("\n[Missing values per column] (only columns > 0)")
    print(missing[missing > 0].to_string() if missing.any() else "none")
    print(f"Total missing cells: {int(missing.sum())}")

    n_dup = int(df.duplicated().sum())
    print(f"\n[Duplicate records] {n_dup} fully duplicated rows")

    print("\n[Unique values in categorical columns]")
    for col in CATEGORICAL_COLS:
        values = df[col].dropna().unique().tolist()
        print(f"- {col} ({len(values)}): {sorted(map(repr, values))}")

    # Hints that the categorical text is inconsistent (case / whitespace).
    print("\n[Inconsistent text detected]")
    found = False
    for col in CATEGORICAL_COLS:
        s = df[col].dropna().astype(str)
        bad_case = s[s != s.str.lower()].unique().tolist() if col != "horsepower-binned" else []
        bad_space = s[s != s.str.strip()].unique().tolist()
        if bad_case or bad_space:
            found = True
            print(f"- {col}: case={bad_case} whitespace={bad_space}")
    if not found:
        print("none")

    print("\n[transaction_date formats]")
    formats = df["transaction_date"].dropna().map(_date_pattern).value_counts()
    print(formats.to_string())

    print("\n[Numeric summary]")
    print(df.describe().T[["min", "50%", "max"]].to_string())

    print("\n[Potential outliers - IQR rule (1.5 x IQR), reported only]")
    for col, n in _iqr_outlier_counts(df).items():
        if n:
            print(f"- {col}: {n} rows outside the IQR fences")

    return {"rows": len(df), "missing": int(missing.sum()), "duplicates": n_dup}


def _date_pattern(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return "YYYY-MM-DD"
    if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        return "DD/MM/YYYY"
    if re.fullmatch(r"\d{2}-\d{2}-\d{4}", value):
        return "MM-DD-YYYY"
    if re.fullmatch(r"\d{2}-[A-Za-z]{3}-\d{4}", value):
        return "DD-Mon-YYYY"
    return "other"


def _iqr_outlier_counts(df: pd.DataFrame) -> dict:
    out = {}
    for col in df.select_dtypes("number").columns:
        if col in ("diesel", "gas"):
            continue
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        out[col] = int(((df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)).sum())
    return out


# --------------------------------------------------------------------------- #
# TRANSFORM - cleaning
# --------------------------------------------------------------------------- #
def parse_mixed_date(value) -> pd.Timestamp:
    """Parse the four date formats found in the raw file.

    The slash format is day-first (DD/MM/YYYY) while the numeric dash format is
    month-first (MM-DD-YYYY); this was verified against the row order, where
    each row is one day after the previous one starting at 2025-01-01.
    """
    if pd.isna(value):
        return pd.NaT
    value = str(value).strip()
    formats = {
        "YYYY-MM-DD": "%Y-%m-%d",
        "DD/MM/YYYY": "%d/%m/%Y",
        "MM-DD-YYYY": "%m-%d-%Y",
        "DD-Mon-YYYY": "%d-%b-%Y",
    }
    fmt = formats.get(_date_pattern(value))
    return pd.to_datetime(value, format=fmt) if fmt else pd.NaT


def clean_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """Clean the dataset based on the problems found during inspection."""
    section("3. CLEANING")
    df = df_raw.copy()  # never mutate the raw frame
    rows_before = len(df)
    missing_before = int(df.isna().sum().sum())
    changed_cols: dict[str, str] = {}

    # 3.1 Text: strip spaces + lowercase (horsepower-binned keeps Title case).
    for col in CATEGORICAL_COLS:
        original = df[col].copy()
        df[col] = df[col].astype("string").str.strip()
        if col != "horsepower-binned":
            df[col] = df[col].str.lower()
        n = int((original.fillna("<NA>") != df[col].fillna("<NA>")).sum())
        if n:
            changed_cols[col] = f"{n} values standardised (trim/lowercase)"

    # 3.2 Duplicates: remove after text standardisation so that rows differing
    #     only by case/whitespace are also caught.
    n_dup = int(df.duplicated().sum())
    df = df.drop_duplicates().reset_index(drop=True)
    print(f"Duplicate rows removed: {n_dup}")

    # 3.3 transaction_date: unify 4 formats -> datetime, fill 2 gaps.
    df["transaction_date"] = df["transaction_date"].map(parse_mixed_date)
    n_date_na = int(df["transaction_date"].isna().sum())
    # Records are one per day in row order, so a missing date is the midpoint of
    # its neighbours (linear interpolation on the timestamp).
    epoch = pd.Timestamp("1970-01-01")
    days = (df["transaction_date"] - epoch).dt.days.astype("float")
    days = days.interpolate(limit_direction="both").round()
    df["transaction_date"] = epoch + pd.to_timedelta(days, unit="D")
    changed_cols["transaction_date"] = (
        f"parsed from 4 formats to datetime; {n_date_na} missing interpolated"
    )

    # 3.4 price is the target variable -> drop rows where it is missing.
    n_price_na = int(df["price"].isna().sum())
    df = df.dropna(subset=["price"]).reset_index(drop=True)
    changed_cols["price"] = f"{n_price_na} rows with missing target dropped"

    # 3.5 make: infer from cars with identical technical specs, else 'unknown'.
    n_make_na = int(df["make"].isna().sum())
    if n_make_na:
        known = df.dropna(subset=["make"])
        lookup = known.groupby(SPEC_COLS)["make"].agg(lambda s: s.mode().iat[0])
        for idx in df.index[df["make"].isna()]:
            key = tuple(df.loc[idx, SPEC_COLS])
            guess = lookup.get(key)
            if guess is None:
                # Rows are sorted by make: if both neighbours share a brand,
                # the missing row belongs to that brand too.
                prev_make = df["make"].iloc[idx - 1] if idx > 0 else pd.NA
                next_make = df["make"].iloc[idx + 1] if idx + 1 < len(df) else pd.NA
                same = pd.notna(prev_make) and prev_make == next_make
                guess = prev_make if same else "unknown"
            df.loc[idx, "make"] = guess
        changed_cols["make"] = (
            changed_cols.get("make", "") + f"; {n_make_na} missing imputed (identical specs / neighbouring rows)"
        ).lstrip("; ")

    # 3.6 num-of-doors: mode within the same make + body-style.
    n_door_na = int(df["num-of-doors"].isna().sum())
    if n_door_na:
        group_mode = df.groupby(["make", "body-style"])["num-of-doors"].transform(
            lambda s: s.mode().iat[0] if s.notna().any() else pd.NA
        )
        df["num-of-doors"] = df["num-of-doors"].fillna(group_mode)
        df["num-of-doors"] = df["num-of-doors"].fillna(df["num-of-doors"].mode().iat[0])
        changed_cols["num-of-doors"] = f"{n_door_na} missing filled with mode per make+body-style"

    # 3.7 horsepower: median of cars with the same engine-size AND the same
    #     horsepower-binned label (the label is still present and constrains the
    #     range), falling back to the median of the label group.
    n_hp_na = int(df["horsepower"].isna().sum())
    if n_hp_na:
        keys = ["engine-size", "horsepower-binned"]
        by_engine = df.groupby(keys, observed=True, dropna=False)["horsepower"].transform("median")
        by_bin = df.groupby("horsepower-binned", observed=True, dropna=False)["horsepower"].transform("median")
        df["horsepower"] = df["horsepower"].fillna(by_engine).fillna(by_bin)
        changed_cols["horsepower"] = (
            f"{n_hp_na} missing filled with median by engine-size + horsepower-binned"
        )

    # 3.8 stroke: the missing rows are Mazda rotary engines (no piston stroke).
    #     Fill with the overall median (skew-robust) and keep a flag column.
    n_stroke_na = int(df["stroke"].isna().sum())
    if n_stroke_na:
        df["stroke_was_missing"] = df["stroke"].isna().astype(int)
        df["stroke"] = df["stroke"].fillna(df["stroke"].median())
        changed_cols["stroke"] = f"{n_stroke_na} missing filled with median (+ flag column)"

    # 3.9 horsepower-binned: learn the bin edges already used in the data
    #     (upper bound of Low and Medium) and use them to fill the gap, so the
    #     existing labels are respected instead of re-binned with a new rule.
    n_bin_na = int(df["horsepower-binned"].isna().sum())
    if n_bin_na:
        edges = df.groupby("horsepower-binned", observed=True)["horsepower"].max()
        bins = [-np.inf, edges["Low"], edges["Medium"], np.inf]
        derived = pd.cut(df["horsepower"], bins, labels=["Low", "Medium", "High"]).astype("string")
        n_inconsistent = int((df["horsepower-binned"].notna()
                              & (df["horsepower-binned"] != derived)).sum())
        df["horsepower-binned"] = df["horsepower-binned"].fillna(derived)
        changed_cols["horsepower-binned"] = (
            f"{n_bin_na} missing filled from horsepower using existing bin edges "
            f"(Low<={edges['Low']:.0f}, Medium<={edges['Medium']:.0f}); "
            f"{n_inconsistent} existing labels inconsistent"
        )

    # 3.10 dtypes: integer-valued columns back to int, categoricals to category.
    df["horsepower"] = df["horsepower"].round().astype(int)
    df["peak-rpm"] = df["peak-rpm"].round().astype(int)
    for col in CATEGORICAL_COLS:
        df[col] = df[col].astype("category")
    changed_cols.setdefault("horsepower", "")
    changed_cols["horsepower"] = (changed_cols["horsepower"] + "; dtype float -> int").lstrip("; ")
    changed_cols["peak-rpm"] = "dtype float -> int"

    # 3.11 sanity checks on implausible values (none expected to fail).
    assert (df[["price", "horsepower", "engine-size", "curb-weight"]] > 0).all().all()
    assert ((df["diesel"] + df["gas"]) == 1).all(), "fuel flags must be exclusive"

    missing_after = int(df.isna().sum().sum())
    print(f"Rows           : {rows_before} -> {len(df)}")
    print(f"Missing cells  : {missing_before} -> {missing_after}")
    print("\n[Columns changed]")
    for col, note in changed_cols.items():
        print(f"- {col}: {note}")
    return df


# --------------------------------------------------------------------------- #
# TRANSFORM - transformation
# --------------------------------------------------------------------------- #
def min_max_scale(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return pd.Series(0.0, index=series.index)
    return (series - lo) / (hi - lo)


def transform_data(df_clean: pd.DataFrame) -> pd.DataFrame:
    """Normalise numeric columns and encode categorical columns."""
    section("4. TRANSFORMATION")
    df = df_clean.copy()

    # 4.1 Min-Max scaling -> new <col>_minmax columns, originals kept so the
    #     values before and after can be compared.
    for col in MINMAX_COLS:
        df[f"{col}_minmax"] = min_max_scale(df[col]).round(6)

    # 4.2 Ordinal encoding (categories with a natural order).
    df["num-of-doors_num"] = df["num-of-doors"].astype(str).map(WORD_TO_NUMBER).astype(int)
    df["num-of-cylinders_num"] = df["num-of-cylinders"].astype(str).map(WORD_TO_NUMBER).astype(int)
    df["horsepower-binned_ordinal"] = df["horsepower-binned"].astype(str).map(HP_BIN_ORDER).astype(int)

    # 4.3 Frequency encoding for 'make' (22 brands -> one compact numeric column).
    df["make_freq"] = df["make"].astype(str).map(df["make"].astype(str).value_counts(normalize=True)).round(6)

    # 4.4 One-hot encoding for nominal categories.
    dummies = pd.get_dummies(df[ONEHOT_COLS].astype(str), prefix=ONEHOT_COLS, dtype=int)
    df = pd.concat([df, dummies], axis=1)

    # 4.5 Date features + ISO string for the CSV.
    df["transaction_month"] = df["transaction_date"].dt.month
    df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")

    # Drop the text columns that are now represented numerically; keep `make`
    # as a readable identifier.
    df = df.drop(columns=ONEHOT_COLS + ["num-of-doors", "num-of-cylinders", "horsepower-binned"])

    print(f"Min-Max scaled : {', '.join(MINMAX_COLS)}")
    print("Ordinal encoded: num-of-doors, num-of-cylinders, horsepower-binned")
    print("Frequency enc. : make")
    print(f"One-hot encoded: {', '.join(ONEHOT_COLS)} -> {dummies.shape[1]} columns")

    print("\n[Before vs after - Min-Max scaling (first 5 rows)]")
    cmp_cols = []
    for col in ("price", "horsepower", "engine-size"):
        cmp_cols += [col, f"{col}_minmax"]
    print(df[cmp_cols].head().to_string())

    print("\n[Before vs after - encoding (first 5 rows)]")
    before = df_clean[["make", "num-of-doors", "num-of-cylinders", "drive-wheels"]].head()
    after = df[["make_freq", "num-of-doors_num", "num-of-cylinders_num",
                "drive-wheels_fwd", "drive-wheels_rwd"]].head()
    print(pd.concat([before, after], axis=1).to_string())

    print(f"\nShape after transformation: {df.shape[0]} rows x {df.shape[1]} columns")
    return df


# --------------------------------------------------------------------------- #
# LOAD
# --------------------------------------------------------------------------- #
def save_data(df: pd.DataFrame, path: Path = PROCESSED_PATH) -> Path:
    """Write the processed dataset to a new file in data/processed/."""
    section("5. LOAD - Save processed dataset")
    if path.resolve() == RAW_PATH.resolve():
        raise ValueError("Refusing to overwrite the raw dataset")
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    print(f"Saved  : {path.relative_to(PROJECT_ROOT)}")
    print(f"Shape  : {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"Missing: {int(df.isna().sum().sum())} cells")
    return path


# --------------------------------------------------------------------------- #
# PIPELINE
# --------------------------------------------------------------------------- #
def run_pipeline() -> pd.DataFrame:
    raw = load_data()                     # Extract
    stats = inspect_data(raw)             # Transform (inspect)
    clean = clean_data(raw)               # Transform (clean)
    processed = transform_data(clean)     # Transform (transform)
    save_data(processed)                  # Load

    section("SUMMARY")
    print(f"Rows   : {stats['rows']} raw -> {len(clean)} clean -> {len(processed)} processed")
    print(f"Columns: {raw.shape[1]} raw -> {processed.shape[1]} processed")
    print(f"Missing: {stats['missing']} -> {int(processed.isna().sum().sum())}")
    print(f"Duplicates removed: {stats['duplicates']}")
    return processed


if __name__ == "__main__":
    run_pipeline()
