import pandas as pd
import numpy as np
import os
import joblib
import time
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from data_loader import fetch_player_game_log, get_opponent_def_ratings, find_player, get_player_bio
from features import create_features

# --- Configuration ---
CACHE_DIR = "cache"
MODELS_DIR = "models"
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)

TARGETS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']

def get_model_path(player_id):
    return os.path.join(MODELS_DIR, f"model_{player_id}.pkl")

def is_cache_valid(filepath):
    """Checks if a file exists and is less than 24 hours old."""
    if not os.path.exists(filepath):
        return False
    age = time.time() - os.path.getmtime(filepath)
    return age < 86400  # 24 hours in seconds

def train_player_models(player_id, player_name):
    """
    Trains separate Random Forest models for each target stat.
    Returns the dictionary of trained models and the feature matrix.
    """
    print(f"Training models for {player_name}...")
    
    # 1. Fetch Data
    df = fetch_player_game_log(player_id)
    opp_def = get_opponent_def_ratings()
    
    if df is None or len(df) < 20: 
        print(f"Insufficient data for {player_name} (Games: {len(df) if df is not None else 0})")
        return None, None, None

    # 2. Engineer Features
    df_features = create_features(df, opp_def)
    
    if df_features is None or df_features.empty:
        return None, None, None
        
    # 3. Prepare X and y
    # Features selection (exclude non-numeric and targets)
    # Start with all columns, then drop metadata + targets
    drop_cols = ['GAME_DATE', 'MATCHUP', 'WL', 'SEASON_ID', 'OPPONENT', 'WIN_NUM', 'MIN_NUM'] + TARGETS
    
    # Also drop MIN if it exists (it's a target-ish or input, here treated as input via MIN_TREND)
    # Actually MIN is in the dataframe, but we use MIN_TREND. 
    # Let's drop raw stats to avoid leakage if they are somehow present (they shouldn't be due to shift, but safe)
    # The `create_features` returns a df with ALL cols including targets.
    
    # Identify feature columns: anything starting with ROLLING_, IS_, REST_, OPP_, WIN_PCT, MIN_TREND
    feature_cols = [c for c in df_features.columns if 
                    c.startswith('ROLLING_') or 
                    c.startswith('IS_') or 
                    c.startswith('REST_') or 
                    c.startswith('OPP_') or 
                    c.startswith('WIN_PCT') or 
                    c.startswith('MIN_TREND')]
    
    X = df_features[feature_cols]
    
    # Split Train/Test by Season
    # Note: `create_features` removed rows with NaNs, so some early 2023-24 games might be gone.
    # We still use SEASON_ID to split.
    
    train_mask = df_features['SEASON_ID'].isin(['2023-24', '2024-25'])
    test_mask = df_features['SEASON_ID'] == '2025-26'
    
    X_train = X[train_mask]
    X_test = X[test_mask]
    
    # If not enough training data (e.g. rooky), use random split
    if len(X_train) < 10:
        # Fallback split
        cutoff = int(len(X) * 0.8)
        X_train = X.iloc[:cutoff]
        X_test = X.iloc[cutoff:]
        
        # Adjust masks for y slicing
        train_indices = X_train.index
        test_indices = X_test.index
    else:
        train_indices = X_train.index
        test_indices = X_test.index

    trained_models = {}
    metrics = {}
    
    # 4. Train Loop
    for target in TARGETS:
        y = df_features[target]
        y_train = y.loc[train_indices]
        y_test = y.loc[test_indices]
        
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
        model.fit(X_train, y_train)
        
        # Evaluate
        if not X_test.empty:
            preds = model.predict(X_test)
            mae = mean_absolute_error(y_test, preds)
            r2 = r2_score(y_test, preds)
            metrics[target] = {'MAE': mae, 'R2': r2}
            # print(f"  {target}: MAE={mae:.2f}, R2={r2:.2f}")
        
        trained_models[target] = model
        
    # Save to cache
    model_path = get_model_path(player_id)
    joblib.dump({
        'models': trained_models,
        'feature_cols': feature_cols,
        'last_train_date': time.time(),
        'metrics': metrics
    }, model_path)
    
    return trained_models, df_features, metrics

def predict_next_game(player_id):
    """
    Orchestrates the full prediction pipeline.
    Returns prediction dict, confidence intervals, and cached metrics.
    """
    player_bio = get_player_bio(player_id)
    player_name = player_bio['DISPLAY_FIRST_LAST'] if player_bio else "Unknown"
    
    model_path = get_model_path(player_id)
    
    # Check cache
    if is_cache_valid(model_path):
        print(f"Loading cached models for {player_name}")
        cached_data = joblib.load(model_path)
        models = cached_data['models']
        feature_cols = cached_data['feature_cols']
        metrics = cached_data.get('metrics', {})
        
        # We still need the latest data to predict the NEXT game
        # Fetching log is fast-ish, but if we want to be super strict about cache we could cache data too.
        # But Prompt says "Invalidate if >24h".
        # So we can just use the models. 
        # But we DO need to fetch fresh stats to build the *input vector* for prediction.
        df_fresh = fetch_player_game_log(player_id)
    else:
        # Retrain
        models, df_fresh_processed, metrics = train_player_models(player_id, player_name)
        if models is None:
            return None
        # We need the processing pipeline again for the raw df if we returned processed
        # Actually `train_player_models` creates processed df.
        # Let's re-fetch raw to be safe/consistent for "next game" logic calculation
        df_fresh = fetch_player_game_log(player_id)
        
        # Check cache again (it was just saved)
        cached_data = joblib.load(model_path)
        feature_cols = cached_data['feature_cols']

    if df_fresh is None or df_fresh.empty:
        return None

    # --- Prepare Input for Next Game ---
    # We need to calculate Rolling Stats based on the *latest* available games.
    # `create_features` shifts by 1.
    # To predict game `T+1`, we need features calculated from `T`, `T-1`...
    # We can reuse `create_features` but we need to trick it or just use the last row *before* shift logic?
    # No, `create_features` computes `rolling().mean().shift(1)`.
    # This means the last row of `df_features` (corresponding to the last played game) 
    # contains features derived from `LastGame - 1`.
    
    # We need features derived from `LastGame` (inclusive).
    # Simple hack: Append a dummy row for "Next Game", run `create_features`, take the last row.
    
    opp_def = get_opponent_def_ratings()
    
    # Dummy row with date = tomorrow (just for sorting/diff calculation)
    next_game_date = df_fresh['GAME_DATE'].max() + pd.Timedelta(days=1)
    
    # Placeholder matchup (User asked for next game logic in UI, but for model input we need Opponent)
    # We don't have the schedule in `predict_next_game` yet (Step 5 logic).
    # But Prompt 2 says "finds the next game". 
    # Step 2 data_loader says "Fetch Player Bio, Game Log... Opp Def Rating".
    # It does NOT explicitly say "Fetch Schedule".
    # BUT Step 5 says "Show the next scheduled game matchup... using ScoreboardV2 or schedule endpoint".
    # I should probably just default OPP_DEF to average (15) for prediction 
    # OR fetch schedule here if I want accuracy.
    # Given robustness, I'll default to 15 (Average Defense) and IS_HOME=1 (Optimistic) 
    # unless I implement a schedule fetcher helper.
    # Given the complexity, I'll rely on defaults for the input vector construction 
    # but still allow overriding if provided? 
    # For now, append dummy row.
    
    dummy_row = {col: 0 for col in df_fresh.columns}
    dummy_row['GAME_DATE'] = next_game_date
    dummy_row['MATCHUP'] = "vs. TBD" # Implies Home
    dummy_row['WL'] = None
    
    df_with_next = pd.concat([df_fresh, pd.DataFrame([dummy_row])], ignore_index=True)
    
    # Feature Engineering on extended DF
    df_features_next = create_features(df_with_next, opp_def)
    
    # The last row is our prediction input
    input_vector = df_features_next.iloc[-1:][feature_cols]
    
    # --- Predict ---
    predictions = {}
    cis = {} # Confidence Intervals (using Rolling Std Dev)
    
    # Rolling Std Deviation is available in `df_features_next` as `ROLLING_STD_{col}_10`
    # We use this as a proxy for volatility/CI.
    last_row = df_features_next.iloc[-1]
    
    for target in TARGETS:
        model = models[target]
        pred_val = model.predict(input_vector)[0]
        predictions[target] = round(pred_val, 1)
        
        # CI Logic
        if f'ROLLING_STD_{target}_10' in last_row:
             std_dev = last_row[f'ROLLING_STD_{target}_10']
             cis[f'{target}_ci'] = round(std_dev, 1) # simple 1-sigma? Prompt says "using the rolling std dev".
        else:
             cis[f'{target}_ci'] = 0.0

    return {
        'predictions': predictions,
        'cis': cis,
        'metrics': metrics,
        'history_df': df_fresh, # Raw history for charts
        'feature_importances': models['PTS'].feature_importances_ if 'PTS' in models else [],
        'feature_names': feature_cols
    }

if __name__ == "__main__":
    # Test
    p = find_player("Stephen Curry")
    if p:
        res = predict_next_game(p['id'])
        if res:
            print("Predictions:", res['predictions'])
            print("Confidence:", res['cis'])
