import pandas as pd
import numpy as np


def create_features(df, opp_def_ratings=None):
    """
    Engineers features from game log data.
    PCT columns (FG_PCT, FT_PCT) are stored as 0-100 in the raw data
    but normalized to 0-1 in rolling features for the linear models.
    """
    if df is None or df.empty:
        return None

    df = df.copy().sort_values(by='GAME_DATE').reset_index(drop=True)

    # ── 1. GAME CONTEXT ───────────────────────────────────────────────────────

    df['IS_HOME'] = df['MATCHUP'].apply(lambda x: 1 if 'vs.' in str(x) else 0)

    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df['REST_DAYS'] = df['GAME_DATE'].diff().dt.days.clip(upper=14).fillna(3)

    df['REST_B2B']    = (df['REST_DAYS'] <= 1).astype(int)
    df['REST_NORMAL'] = ((df['REST_DAYS'] >= 2) & (df['REST_DAYS'] <= 4)).astype(int)
    df['REST_LONG']   = (df['REST_DAYS'] >= 5).astype(int)

    df['DAY_OF_WEEK'] = df['GAME_DATE'].dt.dayofweek
    df['MONTH']       = df['GAME_DATE'].dt.month

    # ── 2. OPPONENT DEFENSE ───────────────────────────────────────────────────

    def extract_opp(matchup):
        m = str(matchup)
        if ' vs. ' in m:
            return m.split(' vs. ')[1].strip()
        elif ' @ ' in m:
            return m.split(' @ ')[1].strip()
        return None

    df['OPPONENT'] = df['MATCHUP'].apply(extract_opp)

    if opp_def_ratings:
        df['OPP_DEF_RANK'] = df['OPPONENT'].map(opp_def_ratings).fillna(15).astype(float)
    else:
        df['OPP_DEF_RANK'] = 15.0

    df['OPP_DEF_NORM'] = df['OPP_DEF_RANK'] / 30.0

    # ── 3. WIN/LOSS & MINUTES ─────────────────────────────────────────────────

    df['WIN_NUM'] = df['WL'].map({'W': 1, 'L': 0}).fillna(0.5)

    if df['MIN'].dtype == object:
        df['MIN_NUM'] = (
            df['MIN'].astype(str)
            .str.extract(r'(\d+)', expand=False)
            .astype(float)
            .fillna(0)
        )
    else:
        df['MIN_NUM'] = pd.to_numeric(df['MIN'], errors='coerce').fillna(0)

    # ── 4. ENSURE NUMERIC ─────────────────────────────────────────────────────

    STAT_COLS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV',
                 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']

    for col in STAT_COLS + ['MIN_NUM', 'WIN_NUM']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # ── 5. ROLLING AVERAGES ───────────────────────────────────────────────────
    # PCT columns are 0-100 in raw data.
    # We normalize them to 0-1 in rolling features so Ridge/Huber models
    # don't see huge scales and get confused.

    WINDOWS = [3, 5, 10, 20]
    PCT_COLS = {'FG_PCT', 'FT_PCT'}

    for col in STAT_COLS:
        is_pct = col in PCT_COLS
        for w in WINDOWS:
            feat_col = f'ROLLING_{col}_{w}'
            rolled = df[col].rolling(window=w, min_periods=max(1, w // 2)).mean().shift(1)
            # Normalize PCT to 0-1 for model features
            df[feat_col] = (rolled / 100.0) if is_pct else rolled

    # ── 6. ROLLING VOLATILITY (STD DEV) ──────────────────────────────────────

    VOL_COLS = ['PTS', 'REB', 'AST', 'FPTS', 'FG_PCT', 'TOV', 'FT_PCT']
    for col in VOL_COLS:
        is_pct = col in PCT_COLS
        std_col = f'ROLLING_STD_{col}_10'
        rolled_std = df[col].rolling(window=10, min_periods=3).std().shift(1)
        df[std_col] = (rolled_std / 100.0) if is_pct else rolled_std

    # ── 7. TREND (SLOPE) ─────────────────────────────────────────────────────

    def rolling_slope(series, window):
        def slope(y):
            if len(y) < 2:
                return 0.0
            x = np.arange(len(y), dtype=float)
            x -= x.mean()
            y = np.array(y, dtype=float) - np.mean(y)
            denom = (x * x).sum()
            return float((x * y).sum() / denom) if denom != 0 else 0.0
        return series.rolling(window=window, min_periods=2).apply(slope, raw=True).shift(1)

    for col in ['PTS', 'REB', 'AST', 'FPTS']:
        df[f'TREND_{col}_5']  = rolling_slope(df[col], 5)
        df[f'TREND_{col}_10'] = rolling_slope(df[col], 10)

    # ── 8. FORM & STREAK ──────────────────────────────────────────────────────

    df['WIN_PCT_LAST5']  = df['WIN_NUM'].rolling(5,  min_periods=1).mean().shift(1) * 100
    df['WIN_PCT_LAST10'] = df['WIN_NUM'].rolling(10, min_periods=1).mean().shift(1) * 100
    df['MIN_TREND']      = df['MIN_NUM'].rolling(5,  min_periods=1).mean().shift(1)

    def streak(series):
        result, count, prev = [], 0, None
        for v in series:
            count = count + 1 if v == prev else 1
            prev  = v
            result.append(count if v == 1 else -count)
        return pd.Series(result, index=series.index)

    df['STREAK'] = streak(df['WIN_NUM']).shift(1).fillna(0)

    # ── 9. INTERACTION FEATURES ───────────────────────────────────────────────

    df['HOME_VS_WEAK_DEF'] = df['IS_HOME'] * df['OPP_DEF_NORM']
    df['RESTED_HOME']      = df['REST_NORMAL'] * df['IS_HOME']

    # ── 10. EFFICIENCY ────────────────────────────────────────────────────────

    safe_min = df['MIN_NUM'].replace(0, np.nan)
    df['PTS_PER_MIN']  = (df['PTS'] / safe_min).fillna(0)
    df['ROLLING_PPM_5'] = df['PTS_PER_MIN'].rolling(5, min_periods=1).mean().shift(1)

    # ── 11. SEASON PROGRESS ───────────────────────────────────────────────────

    if 'SEASON_ID' in df.columns:
        df['GAME_NUM'] = df.groupby('SEASON_ID').cumcount() + 1
    else:
        df['GAME_NUM'] = range(1, len(df) + 1)

    # ── 12. CLEANUP ───────────────────────────────────────────────────────────

    # Drop rows missing the core rolling features
    df_clean = df.dropna(subset=['ROLLING_PTS_5', 'ROLLING_REB_5', 'ROLLING_AST_5'])
    df_clean = df_clean.reset_index(drop=True)

    # Fix FutureWarning: use infer_objects before fillna
    df_clean = df_clean.replace([np.inf, -np.inf], np.nan)
    df_clean = df_clean.infer_objects(copy=False).fillna(0)

    return df_clean