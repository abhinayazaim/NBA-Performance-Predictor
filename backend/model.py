import pandas as pd
from utils import sanitize
import numpy as np
import os
import joblib
import time
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, r2_score
from data_loader import fetch_player_game_log, get_opponent_def_ratings, get_player_bio
from features import create_features

# --- Configuration ---
BASE_DIR = os.path.dirname(__file__)
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

TARGETS = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG_PCT', 'FT_PCT', 'FG3M', 'FPTS']

def get_model_path(player_id):
    return os.path.join(MODELS_DIR, f"model_{player_id}.pkl")

def is_cache_valid(filepath):
    if not os.path.exists(filepath): return False
    return (time.time() - os.path.getmtime(filepath)) < 259200  # 72 hours

def train_player_models(player_id, player_name):
    # 1. Fetch Data
    df = fetch_player_game_log(player_id)
    opp_def = get_opponent_def_ratings()
    
    if df is None or len(df) < 20: 
        return None, None, None

    # 2. Engineer Features
    df_features = create_features(df, opp_def)
    if df_features is None or df_features.empty:
        return None, None, None
        
    # 3. Prepare X and y
    drop_cols = ['GAME_DATE', 'MATCHUP', 'WL', 'SEASON_ID', 'OPPONENT', 'WIN_NUM', 'MIN_NUM'] + TARGETS
    
    feature_cols = [c for c in df_features.columns if 
                    c.startswith('ROLLING_') or 
                    c.startswith('IS_') or 
                    c.startswith('REST_') or 
                    c.startswith('OPP_') or 
                    c.startswith('WIN_PCT') or 
                    c.startswith('MIN_TREND')]
    
    X = df_features[feature_cols]
    
    # Split
    # Split
    from data_loader import get_current_season, get_recent_seasons
    current = get_current_season()
    recent = get_recent_seasons(3)
    train_seasons = recent[1:]
    
    train_mask = df_features['SEASON_ID'].isin(train_seasons)
    test_mask = df_features['SEASON_ID'] == current
    
    X_train = X[train_mask]
    X_test = X[test_mask]
    
    if len(X_train) < 10:
        cutoff = int(len(X) * 0.8)
        X_train = X.iloc[:cutoff]
        X_test = X.iloc[cutoff:]
        
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
        
        if not X_test.empty:
            preds = model.predict(X_test)
            mae = mean_absolute_error(y_test, preds)
            r2 = r2_score(y_test, preds)
            metrics[target] = {'MAE': mae, 'R2': r2}
        
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
    Returns dict with predictions, CIs, feature importances, etc.
    """
    bio = get_player_bio(player_id)
    player_name = bio['DISPLAY_FIRST_LAST'] if bio else "Unknown"
    
    model_path = get_model_path(player_id)
    
    # Load Models
    if is_cache_valid(model_path):
        cached_data = joblib.load(model_path)
        models = cached_data['models']
        feature_cols = cached_data['feature_cols']
        metrics = cached_data.get('metrics', {})
        df_fresh = fetch_player_game_log(player_id)
    else:
        models, _, metrics = train_player_models(player_id, player_name)
        if models is None: return None
        df_fresh = fetch_player_game_log(player_id)
        cached_data = joblib.load(model_path)
        feature_cols = cached_data['feature_cols']

    if df_fresh is None or df_fresh.empty: return None

    # Prepare Input
    opp_def = get_opponent_def_ratings()
    next_game_date = df_fresh['GAME_DATE'].max() + pd.Timedelta(days=1)
    
    dummy_row = {col: 0 for col in df_fresh.columns}
    dummy_row['GAME_DATE'] = next_game_date
    dummy_row['MATCHUP'] = "vs. TBD"
    
    df_with_next = pd.concat([df_fresh, pd.DataFrame([dummy_row])], ignore_index=True)
    df_features_next = create_features(df_with_next, opp_def)
    
    input_vector = df_features_next.iloc[-1:][feature_cols]
    
    # Predict
    predictions = {}
    cis = {}
    last_row = df_features_next.iloc[-1]
    
    for target in TARGETS:
        model = models[target]
        pred_val = model.predict(input_vector)[0]
        # Explicitly cast to Python float, never leave as numpy.float32/float64
        predictions[target] = round(float(pred_val), 1)
        
        if f'ROLLING_STD_{target}_10' in last_row:
             ci_val = last_row[f'ROLLING_STD_{target}_10']
             cis[f'{target}_ci'] = round(float(ci_val) if not pd.isna(ci_val) else 0.0, 1)
        else:
             cis[f'{target}_ci'] = 0.0

    return {
        'predictions': predictions,
        'cis': cis,
        'metrics': metrics,
        'history_df': df_fresh,
        'feature_importances': [float(x) for x in models['PTS'].feature_importances_] if 'PTS' in models else [],
        'feature_names': feature_cols
    }
