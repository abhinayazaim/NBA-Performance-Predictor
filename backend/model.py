import pandas as pd
import numpy as np
import os
import joblib
import time
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_absolute_error, r2_score
from data_loader import fetch_player_game_log, get_opponent_def_ratings, get_player_bio
from features import create_features

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_DIR   = os.path.dirname(__file__)
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

TARGETS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']

# Feature column prefixes to include in model input
FEATURE_PREFIXES = (
    'ROLLING_', 'IS_', 'REST_', 'OPP_', 'WIN_PCT',
    'MIN_TREND', 'TREND_', 'STREAK', 'HOME_VS', 'RESTED_',
    'ROLLING_PPM', 'GAME_NUM', 'DAY_OF_WEEK', 'MONTH'
)

# ── Model factory ─────────────────────────────────────────────────────────────

def make_model(target: str):
    """
    Returns the best model for each target stat.
    GradientBoosting outperforms RandomForest for time-series tabular data.
    Ridge is used for percentage targets which are more linear.
    """
    pct_targets = {'FG_PCT', 'FT_PCT'}

    if target in pct_targets:
        # Percentages are smoother — Ridge with scaling works great
        return Pipeline([
            ('scaler', StandardScaler()),
            ('model', Ridge(alpha=1.0))
        ])
    else:
        # GradientBoosting: better than RF for small datasets, handles non-linearity
        return GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.05,
            max_depth=4,
            min_samples_leaf=3,
            subsample=0.8,
            random_state=42
        )


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
    Fetches data, engineers features, trains one model per target.
    Returns (models, df_features, metrics) or (None, None, None) on failure.
    """
    # 1. Fetch data
    df = fetch_player_game_log(player_id)
    opp_def = get_opponent_def_ratings()

    if df is None or len(df) < 15:
        print(f"[{player_name}] Not enough data ({len(df) if df is not None else 0} games)")
        return None, None, None

    # 2. Feature engineering
    df_features = create_features(df, opp_def)
    if df_features is None or df_features.empty:
        print(f"[{player_name}] Feature engineering returned empty DataFrame")
        return None, None, None

    # 3. Build feature matrix
    feature_cols = [
        c for c in df_features.columns
        if any(c.startswith(p) for p in FEATURE_PREFIXES)
        and c not in TARGETS
    ]

    if not feature_cols:
        print(f"[{player_name}] No feature columns found")
        return None, None, None

    X = df_features[feature_cols].copy()

    # 4. Train / test split — use current season as test, prior as train
    from data_loader import get_current_season, get_recent_seasons
    current      = get_current_season()
    recent       = get_recent_seasons(3)
    train_seasons = recent[1:]  # e.g. ['2024-25', '2023-24']

    if 'SEASON_ID' in df_features.columns:
        train_mask = df_features['SEASON_ID'].isin(train_seasons)
        test_mask  = df_features['SEASON_ID'] == current
    else:
        train_mask = pd.Series([True] * len(df_features))
        test_mask  = pd.Series([False] * len(df_features))

    X_train = X[train_mask]
    X_test  = X[test_mask]

    # Fallback: not enough seasons — use 80/20 time split
    if len(X_train) < 10:
        cutoff  = max(10, int(len(X) * 0.8))
        X_train = X.iloc[:cutoff]
        X_test  = X.iloc[cutoff:]
        train_mask = pd.Series([True] * cutoff + [False] * (len(X) - cutoff), index=X.index)
        test_mask  = ~train_mask

    train_idx = X_train.index
    test_idx  = X_test.index

    # 5. Train one model per target
    trained_models = {}
    metrics        = {}

    for target in TARGETS:
        if target not in df_features.columns:
            continue

        y       = df_features[target]
        y_train = y.loc[train_idx]
        y_test  = y.loc[test_idx]

        model = make_model(target)
        model.fit(X_train, y_train)

        if not X_test.empty and len(y_test) > 0:
            preds = model.predict(X_test)
            metrics[target] = {
                'MAE': float(mean_absolute_error(y_test, preds)),
                'R2':  float(r2_score(y_test, preds)) if len(y_test) > 1 else 0.0
            }

        trained_models[target] = model
        print(f"  ✓ {target}: MAE={metrics.get(target, {}).get('MAE', '?'):.2f}")

    # 6. Save to disk
    model_path = get_model_path(player_id)
    joblib.dump({
        'models':          trained_models,
        'feature_cols':    feature_cols,
        'last_train_date': time.time(),
        'metrics':         metrics,
    }, model_path, compress=3)

    print(f"[{player_name}] Model saved → {model_path}")
    return trained_models, df_features, metrics


# ── Inference ─────────────────────────────────────────────────────────────────

def predict_next_game(player_id):
    """
    Returns a dict with predictions, CIs, feature importances, and game history.
    Uses cached model if valid, otherwise trains fresh.
    """
    bio         = get_player_bio(player_id)
    player_name = bio['DISPLAY_FIRST_LAST'] if bio else str(player_id)
    model_path  = get_model_path(player_id)

    # Load or train models
    if is_cache_valid(model_path):
        cached       = joblib.load(model_path)
        models       = cached['models']
        feature_cols = cached['feature_cols']
        metrics      = cached.get('metrics', {})
        df_fresh     = fetch_player_game_log(player_id)
    else:
        print(f"[{player_name}] Training fresh model...")
        models, _, metrics = train_player_models(player_id, player_name)
        if models is None:
            return None
        df_fresh     = fetch_player_game_log(player_id)
        cached       = joblib.load(model_path)
        feature_cols = cached['feature_cols']

    if df_fresh is None or df_fresh.empty:
        return None

    # Build a dummy "next game" row for prediction
    opp_def       = get_opponent_def_ratings()
    max_date      = df_fresh['GAME_DATE'].max()
    next_game_date = max_date + pd.Timedelta(days=2)

    dummy_row = {col: 0 for col in df_fresh.columns}
    dummy_row.update({
        'GAME_DATE': next_game_date,
        'MATCHUP':   'vs. TBD',
        'WL':        'W',
        'SEASON_ID': df_fresh['SEASON_ID'].iloc[0] if 'SEASON_ID' in df_fresh.columns else '2025-26',
    })

    df_with_next    = pd.concat([df_fresh, pd.DataFrame([dummy_row])], ignore_index=True)
    df_features_next = create_features(df_with_next, opp_def)

    if df_features_next is None or df_features_next.empty:
        return None

    # Align columns — model may have been trained with different features
    missing_cols = [c for c in feature_cols if c not in df_features_next.columns]
    for c in missing_cols:
        df_features_next[c] = 0.0

    input_vector = df_features_next.iloc[-1:][feature_cols].fillna(0)
    last_row     = df_features_next.iloc[-1]

    # Run predictions
    predictions = {}
    cis         = {}

    for target in TARGETS:
        if target not in models:
            predictions[target] = 0.0
            cis[f'{target}_ci'] = 0.0
            continue

        raw = models[target].predict(input_vector)[0]

        # Clip to sane ranges per stat
        limits = {
            'PTS': (0, 70), 'REB': (0, 30), 'AST': (0, 25),
            'STL': (0, 6),  'BLK': (0, 8),  'TOV': (0, 12),
            'FG_PCT': (0, 100), 'FT_PCT': (0, 100), 'FG3M': (0, 14),
            'FPTS': (0, 120)
        }
        lo, hi = limits.get(target, (0, 9999))
        predictions[target] = round(float(np.clip(raw, lo, hi)), 1)

        # CI from rolling std dev
        ci_key = f'ROLLING_STD_{target}_10'
        if ci_key in last_row.index:
            ci_val = last_row[ci_key]
            cis[f'{target}_ci'] = round(float(ci_val) if pd.notna(ci_val) else 0.0, 1)
        else:
            cis[f'{target}_ci'] = 0.0

    # Feature importances — only RF/GB models have this attribute
    feat_imp = []
    if 'PTS' in models:
        m = models['PTS']
        # Pipeline wraps Ridge which has no feature_importances_
        inner = m.named_steps['model'] if hasattr(m, 'named_steps') else m
        if hasattr(inner, 'feature_importances_'):
            feat_imp = [float(x) for x in inner.feature_importances_]

    return {
        'predictions':       predictions,
        'cis':               cis,
        'metrics':           metrics,
        'history_df':        df_fresh,
        'feature_importances': feat_imp,
        'feature_names':     feature_cols,
    }