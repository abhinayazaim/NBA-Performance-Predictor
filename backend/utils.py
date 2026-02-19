import numpy as np
import pandas as pd
import math
from typing import Any

def sanitize(obj: Any) -> Any:
    """
    Recursively converts all numpy/pandas types to native Python types.
    Handles numpy >= 1.24 where numpy.bool_ behavior changed.
    """
    if obj is None:
        return None

    # --- Dict ---
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}

    # --- List / tuple ---
    if isinstance(obj, (list, tuple)):
        return [sanitize(v) for v in obj]

    # --- numpy bool (must check BEFORE np.integer since bool is subclass of int) ---
    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    # --- numpy integers ---
    if isinstance(obj, np.integer):
        return int(obj)

    # --- numpy floats ---
    if isinstance(obj, np.floating):
        val = float(obj)
        if math.isnan(val) or math.isinf(val):
            return None
        return val

    # --- numpy arrays ---
    if isinstance(obj, np.ndarray):
        return sanitize(obj.tolist())

    # --- pandas Series ---
    if isinstance(obj, pd.Series):
        return sanitize(obj.tolist())

    # --- pandas DataFrame ---
    if isinstance(obj, pd.DataFrame):
        return sanitize(obj.to_dict(orient="records"))

    # --- pandas NA / NaT / NaN ---
    if isinstance(obj, type(pd.NaT)) or obj is pd.NaT:
        return None
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass

    # --- Python native float NaN/Inf ---
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj

    # --- Python int, str, bool ---
    if isinstance(obj, (int, str, bool)):
        return obj

    # --- Fallback: try converting to string to avoid crash ---
    return obj
