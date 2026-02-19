import pandas as pd
import numpy as np

def create_features(df, opp_def_ratings=None):
    """
    Engineers features from the last 50 games.
    Assumes df has PCT columns already scaled to 0-100.
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
    df['REST_DAYS'] = df['GAME_DATE'].diff().dt.days.fillna(3)
    
    # OPP_DEF_RANK
    if opp_def_ratings:
        def get_opp(matchup):
            if ' vs. ' in matchup:
                return matchup.split(' vs. ')[1]
            elif ' @ ' in matchup:
                return matchup.split(' @ ')[1]
            return None
            
        df['OPPONENT'] = df['MATCHUP'].apply(get_opp)
        df['OPP_DEF_RANK'] = df['OPPONENT'].map(opp_def_ratings).fillna(15) 
    else:
        df['OPP_DEF_RANK'] = 15

    # --- 2. Rolling Stats ---
    # PCT columns are already 0-100 from data_loader
    targets = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']
    windows = [5, 10, 20]
    
    for col in targets:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        for w in windows:
            # Shift(1) for prediction
            df[f'ROLLING_{col}_{w}'] = df[col].rolling(window=w).mean().shift(1)
            
    # --- 3. Rolling Volatility (Std Dev) ---
    vol_targets = ['PTS', 'REB', 'AST', 'FPTS', 'FG_PCT']
    for col in vol_targets:
        df[f'ROLLING_STD_{col}_10'] = df[col].rolling(window=10).std().shift(1)

    # --- 4. Advanced Window Features ---
    df['WIN_NUM'] = df['WL'].map({'W': 1, 'L': 0}).fillna(0.5)
    df['WIN_PCT_LAST10'] = df['WIN_NUM'].rolling(window=10).mean().shift(1) * 100 # Scale to 0-100
    
    # MIN_TREND
    # MIN might be string "34:12" or float. data_loader doesn't fix this universally?
    # Let's handle it here safely.
    if df['MIN'].dtype == object:
         df['MIN_NUM'] = df['MIN'].astype(str).str.extract(r'(\d+)').astype(float).fillna(0)
    else:
         df['MIN_NUM'] = df['MIN']
         
    df['MIN_TREND'] = df['MIN_NUM'].rolling(window=5).mean().shift(1)

    # --- 5. Cleanup ---
    df_clean = df.dropna().reset_index(drop=True)
    
    return df_clean
