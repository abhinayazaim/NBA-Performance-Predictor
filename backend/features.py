import pandas as pd
import numpy as np


def create_features(df, opp_def_ratings=None):
    """
    Engineers features from the last 50 games.
    Optimized for speed and model accuracy.
    Assumes PCT columns are already scaled to 0-100.
    """
    if df is None or df.empty:
        return None

    # Work on a copy, sort chronologically for rolling calcs
    df = df.copy().sort_values(by='GAME_DATE').reset_index(drop=True)

    # ── 1. GAME CONTEXT FEATURES ──────────────────────────────────────────────

    df['IS_HOME'] = df['MATCHUP'].apply(lambda x: 1 if 'vs.' in str(x) else 0)

    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df['REST_DAYS'] = df['GAME_DATE'].diff().dt.days.clip(upper=14).fillna(3)
    # Bucket rest into categories: 0 (back-to-back), 1 (1 day), 2+ (rested)
    df['REST_B2B']    = (df['REST_DAYS'] <= 1).astype(int)
    df['REST_NORMAL'] = ((df['REST_DAYS'] >= 2) & (df['REST_DAYS'] <= 4)).astype(int)
    df['REST_LONG']   = (df['REST_DAYS'] >= 5).astype(int)

    # Day of week (fatigue proxy — Thursday/Friday back-to-backs matter)
    df['DAY_OF_WEEK'] = df['GAME_DATE'].dt.dayofweek  # 0=Mon, 6=Sun

    # Month of season (players peak mid-season, dip late)
    df['MONTH'] = df['GAME_DATE'].dt.month

    # ── 2. OPPONENT DEFENSIVE RATING ─────────────────────────────────────────

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

    # Normalize def rank to 0-1 (1 = easiest matchup = worst defense = rank 30)
    df['OPP_DEF_NORM'] = df['OPP_DEF_RANK'] / 30.0

    # ── 3. WIN/LOSS & MINUTES ─────────────────────────────────────────────────

    df['WIN_NUM'] = df['WL'].map({'W': 1, 'L': 0}).fillna(0.5)

    # Minutes — handle "34:12" string format
    if df['MIN'].dtype == object:
        df['MIN_NUM'] = (
            df['MIN'].astype(str)
            .str.extract(r'(\d+)', expand=False)
            .astype(float)
            .fillna(0)
        )
    else:
        df['MIN_NUM'] = pd.to_numeric(df['MIN'], errors='coerce').fillna(0)

    # ── 4. ROLLING AVERAGES ───────────────────────────────────────────────────

    STAT_COLS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV',
                 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']
    WINDOWS   = [3, 5, 10, 20]

    # Ensure numeric
    for col in STAT_COLS + ['MIN_NUM', 'WIN_NUM']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    for col in STAT_COLS:
        for w in WINDOWS:
            # shift(1) so we never leak current game into the feature
            df[f'ROLLING_{col}_{w}'] = (
                df[col].rolling(window=w, min_periods=max(1, w // 2))
                .mean().shift(1)
            )

    # ── 5. ROLLING VOLATILITY (STD DEV) ──────────────────────────────────────

    VOL_COLS = ['PTS', 'REB', 'AST', 'FPTS', 'FG_PCT', 'TOV']
    for col in VOL_COLS:
        df[f'ROLLING_STD_{col}_10'] = (
            df[col].rolling(window=10, min_periods=3).std().shift(1)
        )

    # ── 6. TREND FEATURES (slope of last N games) ────────────────────────────
    # A positive slope means the player is trending up — very predictive

    def rolling_slope(series, window):
        """Compute rolling linear regression slope."""
        def slope(y):
            if len(y) < 2:
                return 0.0
            x = np.arange(len(y), dtype=float)
            x -= x.mean()
            y = np.array(y, dtype=float)
            y -= y.mean()
            denom = (x * x).sum()
            return float((x * y).sum() / denom) if denom != 0 else 0.0
        return series.rolling(window=window, min_periods=2).apply(slope, raw=True).shift(1)

    TREND_COLS = ['PTS', 'REB', 'AST', 'FPTS']
    for col in TREND_COLS:
        df[f'TREND_{col}_5']  = rolling_slope(df[col], 5)
        df[f'TREND_{col}_10'] = rolling_slope(df[col], 10)

    # ── 7. FORM FEATURES ──────────────────────────────────────────────────────

    df['WIN_PCT_LAST5']  = df['WIN_NUM'].rolling(5,  min_periods=1).mean().shift(1) * 100
    df['WIN_PCT_LAST10'] = df['WIN_NUM'].rolling(10, min_periods=1).mean().shift(1) * 100
    df['MIN_TREND']      = df['MIN_NUM'].rolling(5,  min_periods=1).mean().shift(1)

    # Hot/cold streak: consecutive wins or losses
    def streak(series):
        result = []
        count = 0
        prev = None
        for v in series:
            if v == prev:
                count += 1
            else:
                count = 1
                prev = v
            result.append(count if v == 1 else -count)
        return pd.Series(result, index=series.index)

    df['STREAK'] = streak(df['WIN_NUM']).shift(1).fillna(0)

    # ── 8. INTERACTION FEATURES ───────────────────────────────────────────────
    # These capture effects like "scores more at home vs weak defense"

    df['HOME_VS_WEAK_DEF'] = df['IS_HOME'] * df['OPP_DEF_NORM']
    df['RESTED_HOME']      = df['REST_NORMAL'] * df['IS_HOME']

    # ── 9. EFFICIENCY RATIOS ──────────────────────────────────────────────────

    # Points per minute trend (efficiency)
    safe_min = df['MIN_NUM'].replace(0, np.nan)
    df['PTS_PER_MIN'] = (df['PTS'] / safe_min).fillna(0)
    df['ROLLING_PPM_5'] = df['PTS_PER_MIN'].rolling(5, min_periods=1).mean().shift(1)

    # ── 10. SEASON PROGRESS ───────────────────────────────────────────────────
    # Game number within season (proxy for fatigue / rhythm)
    df['GAME_NUM'] = df.groupby('SEASON_ID').cumcount() + 1 if 'SEASON_ID' in df.columns else range(len(df))

    # ── 11. CLEANUP ───────────────────────────────────────────────────────────

    df_clean = df.dropna(subset=[
        f'ROLLING_PTS_5', f'ROLLING_REB_5', f'ROLLING_AST_5'
    ]).reset_index(drop=True)

    # Replace any remaining inf values
    df_clean = df_clean.replace([np.inf, -np.inf], np.nan).fillna(0)

    return df_clean