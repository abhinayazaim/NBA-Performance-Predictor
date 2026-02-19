import pandas as pd
import numpy as np

def create_features(df, opp_def_ratings=None):
    """
    Engineers features from the last 50 games.
    
    Args:
        df: DataFrame containing game logs (must include FPTS).
        opp_def_ratings: Dict mapping team abbreviation to defensive rank.
        
    Returns:
        Cleaned feature matrix (DataFrame).
    """
    if df is None or df.empty:
        return None

    # Ensure chronological order for rolling calcs (Ascending)
    df = df.sort_values(by='GAME_DATE').reset_index(drop=True)

    # --- 1. Base Features ---
    # IS_HOME
    df['IS_HOME'] = df['MATCHUP'].apply(lambda x: 1 if 'vs.' in x else 0)
    
    # REST_DAYS
    df['GAME_DATE'] = pd.to_datetime(df['GAME_DATE'])
    df['REST_DAYS'] = df['GAME_DATE'].diff().dt.days.fillna(3) # Default to 3 days rest for first game
    
    # OPP_DEF_RANK
    # Extract opponent team from Matchup (e.g. "LAL vs. GSW" -> GSW, "LAL @ GSW" -> GSW)
    if opp_def_ratings:
        def get_opp(matchup):
            # Split by ' vs. ' or ' @ '
            if ' vs. ' in matchup:
                return matchup.split(' vs. ')[1]
            elif ' @ ' in matchup:
                return matchup.split(' @ ')[1]
            return None
            
        df['OPPONENT'] = df['MATCHUP'].apply(get_opp)
        # Map rank, default to 15 (average) if not found
        df['OPP_DEF_RANK'] = df['OPPONENT'].map(opp_def_ratings).fillna(15) 
    else:
        df['OPP_DEF_RANK'] = 15

    # --- 2. Rolling Stats ---
    targets = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']
    windows = [5, 10, 20]
    
    for col in targets:
        # Convert to numeric just in case
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        for w in windows:
            # We want PREVIOUS game stats to predict NEXT game.
            # Shift(1) so that at row `t`, we look at `t-1` backwards.
            df[f'ROLLING_{col}_{w}'] = df[col].rolling(window=w).mean().shift(1)
            
    # --- 3. Rolling Volatility (Std Dev) ---
    # Used for Confidence Intervals
    vol_targets = ['PTS', 'REB', 'AST', 'FPTS']
    for col in vol_targets:
        df[f'ROLLING_STD_{col}_10'] = df[col].rolling(window=10).std().shift(1)

    # --- 4. Advanced Window Features ---
    
    # WIN_PCT_LAST10
    # WL column is 'W' or 'L'. Map to 1/0
    df['WIN_NUM'] = df['WL'].map({'W': 1, 'L': 0}).fillna(0.5)
    df['WIN_PCT_LAST10'] = df['WIN_NUM'].rolling(window=10).mean().shift(1)
    
    # MIN_TREND (Rolling 5-game minutes)
    df['MIN_NUM'] = df['MIN'].astype(str).str.extract(r'(\d+)').astype(float).fillna(0) # Handle "34:12" or float
    df['MIN_TREND'] = df['MIN_NUM'].rolling(window=5).mean().shift(1)

    # --- 5. Cleanup ---
    # Drop rows with NaN (due to rolling windows/shifting)
    # With max window=20 and shift=1, we lose first 20 rows.
    # Since we fetch 50 games, we should have ~30 training samples left.
    df_clean = df.dropna().reset_index(drop=True)
    
    # Return features + targets
    # We need to keep the Target columns (un-shifted) for training Y
    # And keep Metadata for reference if needed
    
    return df_clean

if __name__ == "__main__":
    # Test
    try:
        from data_loader import fetch_player_game_log, find_player, get_opponent_def_ratings
        p = find_player("LeBron James")
        if p:
            raw = fetch_player_game_log(p['id'])
            defs = get_opponent_def_ratings()
            feats = create_features(raw, defs)
            print("Feature Matrix Shape:", feats.shape)
            print("Columns:", feats.columns.tolist()[:10])
            print("Sample Row:", feats.iloc[-1][['GAME_DATE', 'PTS', 'ROLLING_PTS_5', 'IS_HOME']])
    except Exception as e:
        print(e)
