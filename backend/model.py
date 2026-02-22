import pandas as pd
import numpy as np
import os
import joblib
import time
from sklearn.linear_model import Ridge, HuberRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
from data_loader import fetch_player_game_log, get_opponent_def_ratings, get_player_bio
from features import create_features

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(__file__)
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

TARGETS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']

FEATURE_PREFIXES = (
    'ROLLING_', 'IS_', 'REST_', 'OPP_', 'WIN_PCT',
    'MIN_TREND', 'TREND_', 'STREAK', 'HOME_VS', 'RESTED_',
    'ROLLING_PPM', 'GAME_NUM', 'DAY_OF_WEEK', 'MONTH'
)

# Output clipping — hard physical limits per stat
LIMITS = {
    'PTS':    (0, 70),
    'REB':    (0, 30),
    'AST':    (0, 25),
    'STL':    (0, 6),
    'BLK':    (0, 8),
    'TOV':    (0, 12),
    'FG_PCT': (0, 100),
    'FT_PCT': (0, 100),
    'FG3M':   (0, 14),
    'FPTS':   (0, 120),
}


# ── Model factory ─────────────────────────────────────────────────────────────

def make_model(target):
    """
    Algorithm selection rationale for small NBA player datasets (~50-80 games):

    HuberRegressor — used for high-variance counting stats (PTS, REB, AST, FPTS, TOV)
      NBA game logs contain outliers: garbage-time sit-outs, blowout DNPs, injury
      limited minutes. Huber loss automatically down-weights those outlier games
      without removing them, making predictions much more stable than OLS/MSE.
      epsilon=1.35 (PTS/FPTS/TOV) is aggressive — it ignores the top ~25% of residuals.
      epsilon=1.5 (REB/AST) is slightly more lenient because those are less volatile.

    Ridge — used for percentages (FG_PCT, FT_PCT) and low-frequency events (STL, BLK, FG3M)
      Percentages have a strong linear relationship with their rolling averages.
      L2 regularization (Ridge) handles the collinearity between ROLLING_FG_PCT_5/10/20
      gracefully. For rare events (STL/BLK often 0-1 per game), simple is better —
      complex models overfit noise on 50-game datasets.

    StandardScaler — mandatory for both because feature scales vary wildly
      (ROLLING_PTS_5 ~20-30, OPP_DEF_NORM 0-1, GAME_NUM 1-82, etc).
      Without scaling, the optimizer treats high-magnitude features as more important.
    """

    if target in ('PTS', 'FPTS', 'TOV'):
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', HuberRegressor(epsilon=1.35, alpha=0.01, max_iter=500))
        ])

    elif target in ('AST', 'REB'):
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', HuberRegressor(epsilon=1.5, alpha=0.005, max_iter=500))
        ])

    elif target in ('FG_PCT', 'FT_PCT'):
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', Ridge(alpha=2.0))
        ])

    else:  # STL, BLK, FG3M
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', Ridge(alpha=1.0))
        ])


# ── Cache helpers ─────────────────────────────────────────────────────────────

def get_model_path(player_id):
    return os.path.join(MODELS_DIR, f"model_{player_id}.pkl")

def is_cache_valid(filepath):
    if not os.path.exists(filepath):
        return False
    return (time.time() - os.path.getmtime(filepath)) < 259200  # 72 hours


# ── Training ──────────────────────────────────────────────────────────────────

def train_player_models(player_id, player_name="Unknown"):
    """
    Fetches game log → engineers features → trains one model per target.

    Split strategy: time-aware holdout — hold out the 5 most recent games
    for evaluation. This is the only honest evaluation for time-series data.
    We never shuffle or do k-fold because future games can't train past models.

    Returns (models_dict, df_features, metrics_dict) or (None, None, None).
    """
    df      = fetch_player_game_log(player_id)
    opp_def = get_opponent_def_ratings()

    if df is None or len(df) < 15:
        n = len(df) if df is not None else 0
        print(f"  [{player_name}] Not enough games ({n}). Need at least 15.")
        return None, None, None

    df_features = create_features(df, opp_def)

    if df_features is None or df_features.empty:
        print(f"  [{player_name}] Feature engineering produced no rows.")
        return None, None, None

    # Select only engineered feature columns (not raw stat targets)
    feature_cols = [
        c for c in df_features.columns
        if any(c.startswith(p) for p in FEATURE_PREFIXES)
        and c not in TARGETS
    ]

    if not feature_cols:
        print(f"  [{player_name}] No feature columns found after engineering.")
        return None, None, None

    X = df_features[feature_cols].fillna(0)

    # Time-aware holdout — 5 games or 20% of data, whichever is smaller
    holdout = min(5, max(1, len(X) // 5))
    if len(X) - holdout < 10:
        holdout = max(1, len(X) - 10)  # ensure at least 10 training samples

    X_train = X.iloc[:-holdout]
    X_test  = X.iloc[-holdout:]

    trained_models = {}
    metrics        = {}

    for target in TARGETS:
        if target not in df_features.columns:
            continue

        y       = df_features[target]
        y_train = y.iloc[:len(X_train)]
        y_test  = y.iloc[len(X_train):len(X_train) + len(X_test)]

        model = make_model(target)

        try:
            model.fit(X_train, y_train)
        except Exception as e:
            print(f"  ✗ {target}: training failed — {e}")
            continue

        if len(X_test) > 0 and len(y_test) > 0:
            raw_preds = model.predict(X_test)

            # Scale PCT predictions back to 0-100 for metric calculation
            if target in ('FG_PCT', 'FT_PCT'):
                eval_preds = raw_preds * 100.0
                eval_true  = y_test.values  # already 0-100
            else:
                eval_preds = raw_preds
                eval_true  = y_test.values

            mae = float(mean_absolute_error(eval_true, eval_preds))
            r2  = float(r2_score(eval_true, eval_preds)) if len(y_test) > 1 else 0.0
            metrics[target] = {'MAE': mae, 'R2': r2}
            print(f"  ✓ {target}: MAE={mae:.2f}  R²={r2:.2f}")
        else:
            metrics[target] = {'MAE': 0.0, 'R2': 0.0}

        trained_models[target] = model

    if not trained_models:
        print(f"  [{player_name}] All targets failed to train.")
        return None, None, None

    # Persist to disk
    joblib.dump({
        'models':          trained_models,
        'feature_cols':    feature_cols,
        'last_train_date': time.time(),
        'metrics':         metrics,
    }, get_model_path(player_id), compress=3)

    print(f"  [{player_name}] Saved → models/model_{player_id}.pkl")
    return trained_models, df_features, metrics


# ── Inference ─────────────────────────────────────────────────────────────────

def predict_next_game(player_id):
    """
    Returns a dict with predictions, CIs, feature importances, history df, metrics.
    Loads from disk cache if valid, otherwise retrains.

    Prediction works by:
    1. Appending a synthetic "next game" row to the game log
    2. Running create_features on the extended log
    3. Using the last row (the synthetic next game) as input
    This ensures all rolling features are correctly computed from real history.
    """
    bio         = get_player_bio(player_id)
    player_name = bio['DISPLAY_FIRST_LAST'] if bio else str(player_id)
    model_path  = get_model_path(player_id)

    # Load or retrain
    if is_cache_valid(model_path):
        cached       = joblib.load(model_path)
        models       = cached['models']
        feature_cols = cached['feature_cols']
        metrics      = cached.get('metrics', {})
        df_fresh     = fetch_player_game_log(player_id)
    else:
        print(f"\n[{player_name}] Cache stale or missing — training...")
        models, _, metrics = train_player_models(player_id, player_name)
        if models is None:
            return None
        df_fresh     = fetch_player_game_log(player_id)
        cached       = joblib.load(model_path)
        feature_cols = cached['feature_cols']

    if df_fresh is None or df_fresh.empty:
        return None

    opp_def = get_opponent_def_ratings()

    # Build synthetic "next game" row — all stats 0, date is +2 days from last game
    next_game_date = pd.to_datetime(df_fresh['GAME_DATE']).max() + pd.Timedelta(days=2)
    dummy_row      = {col: 0 for col in df_fresh.columns}
    dummy_row.update({
        'GAME_DATE': next_game_date,
        'MATCHUP':   'vs. TBD',
        'WL':        'W',
        'SEASON_ID': df_fresh['SEASON_ID'].iloc[0] if 'SEASON_ID' in df_fresh.columns else '2025-26',
        'MIN':       '30',
    })

    df_with_next     = pd.concat([df_fresh, pd.DataFrame([dummy_row])], ignore_index=True)
    df_features_next = create_features(df_with_next, opp_def)

    if df_features_next is None or df_features_next.empty:
        return None

    # Ensure all expected features exist (fill missing with 0)
    for c in feature_cols:
        if c not in df_features_next.columns:
            df_features_next[c] = 0.0

    input_row = df_features_next.iloc[-1:][feature_cols].fillna(0)
    last_row  = df_features_next.iloc[-1]

    # ── Predict ───────────────────────────────────────────────────────────────

    predictions = {}
    cis         = {}

    for target in TARGETS:
        if target not in models:
            predictions[target] = 0.0
            cis[f'{target}_ci'] = 0.0
            continue

        raw = float(models[target].predict(input_row)[0])

        # features.py normalizes FG_PCT / FT_PCT rolling features to 0-1.
        # The model therefore predicts in 0-1 space. Scale back to 0-100 for display.
        if target in ('FG_PCT', 'FT_PCT'):
            raw = raw * 100.0

        lo, hi = LIMITS.get(target, (0, 9999))
        predictions[target] = round(float(np.clip(raw, lo, hi)), 1)

        # Confidence interval from rolling standard deviation of that stat
        ci_key = f'ROLLING_STD_{target}_10'
        if ci_key in last_row.index and pd.notna(last_row[ci_key]):
            ci_val = float(last_row[ci_key])
            # PCT std was also normalized to 0-1 — scale back
            if target in ('FG_PCT', 'FT_PCT'):
                ci_val = ci_val * 100.0
            cis[f'{target}_ci'] = round(max(0.0, ci_val), 1)
        else:
            cis[f'{target}_ci'] = 0.0

    # ── Feature importances ───────────────────────────────────────────────────
    # Linear models (Huber, Ridge) expose coef_ — use absolute values as importance.
    # Tree models expose feature_importances_ — supported too for easy future swap.

    feat_imp = []
    if 'PTS' in models:
        m     = models['PTS']
        inner = m.named_steps['model'] if hasattr(m, 'named_steps') else m
        if hasattr(inner, 'coef_'):
            feat_imp = [float(abs(x)) for x in inner.coef_]
        elif hasattr(inner, 'feature_importances_'):
            feat_imp = [float(x) for x in inner.feature_importances_]

    return {
        'predictions':         predictions,
        'cis':                 cis,
        'metrics':             metrics,
        'history_df':          df_fresh,
        'feature_importances': feat_imp,
        'feature_names':       feature_cols,
    }