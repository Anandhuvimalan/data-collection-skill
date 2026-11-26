"""Small helpers shared by the analysis scripts. You do not need to edit this file."""
import json
import re
import sys

import pandas as pd

import config as C

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def snake(name: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", str(name).strip())
    return re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()


def out_dir(stage: str):
    d = C.OUTPUTS / stage
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_clean() -> pd.DataFrame:
    if not C.CLEAN_TABLE.exists():
        sys.exit(f"{C.CLEAN_TABLE} not found. Run 01_prepare.py first.")
    df = pd.read_csv(C.CLEAN_TABLE)
    if C.DATE_COL and C.DATE_COL in df.columns:
        df[C.DATE_COL] = pd.to_datetime(df[C.DATE_COL], errors="coerce")
    return df


def feature_columns(df: pd.DataFrame):
    """Split usable columns into numeric and categorical, leaving out id, target, leakage and ignored columns."""
    drop = {C.ID_COL, C.TARGET, "target", C.DATE_COL, *C.LEAKAGE_COLS, *C.IGNORE_COLS}
    cols = [c for c in df.columns if c not in drop and not c.endswith("_outlier")]
    numeric = [c for c in cols if pd.api.types.is_numeric_dtype(df[c]) and df[c].nunique() > 2]
    categorical = [c for c in cols if c not in numeric and df[c].nunique() <= 50]
    return numeric, categorical


def save_table(df: pd.DataFrame, stage: str, name: str):
    path = out_dir(stage) / f"{name}.csv"
    df.to_csv(path, index=False)
    print(f"  saved {path.relative_to(C.PROJECT)}")
    return path


def save_json(obj, stage: str, name: str):
    path = out_dir(stage) / f"{name}.json"
    path.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
    print(f"  saved {path.relative_to(C.PROJECT)}")


def save_fig(fig, stage: str, name: str):
    path = out_dir(stage) / f"{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    import matplotlib.pyplot as plt
    plt.close(fig)
    print(f"  saved {path.relative_to(C.PROJECT)}")
