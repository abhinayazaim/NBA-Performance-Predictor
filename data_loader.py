import pandas as pd
import numpy as np
import time
import requests
from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo, playergamelog, leaguedashteamstats
from difflib import get_close_matches

# --- Constants ---
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'en-US,en;q=0.9',
    'Connection': 'keep-alive',
}

def retry_request(func, retries=3, delay=3, **kwargs):
    """
    Retry logic for NBA API calls to handle timeouts.
    """
    for i in range(retries):
        try:
            return func(**kwargs)
        except requests.exceptions.Timeout:
            print(f"Timeout error. Retrying in {delay}s... ({i+1}/{retries})")
            time.sleep(delay)
        except Exception as e:
            # If it's another error, we might want to fail immediately or retry depending on error
            print(f"API Error: {e}. Retrying in {delay}s... ({i+1}/{retries})")
            time.sleep(delay)
    return None

def get_active_players_list():
    """
    Returns a list of all active NBA players.
    """
    return players.get_active_players()

def find_player(name_query):
    """
    Finds a player by name using fuzzy matching.
    Returns the player dict or None.
    """
    active_players = get_active_players_list()
    # Create map of lower_name -> player_dict
    player_map = {p['full_name'].lower(): p for p in active_players}
    
    query = name_query.lower().strip()
    
    # Exact match check
    if query in player_map:
        return player_map[query]
    
    # Fuzzy match
    matches = get_close_matches(query, player_map.keys(), n=1, cutoff=0.6)
    if matches:
        return player_map[matches[0]]
    
    return None

def get_player_bio(player_id):
    """
    Fetches common player info like team, height, weight, etc.
    """
    try:
        # Rate limit pause
        time.sleep(0.6)
        
        info = retry_request(commonplayerinfo.CommonPlayerInfo, player_id=player_id)
        if not info:
             return None
             
        # The result set index 0 usually contains CommonPlayerInfo
        df = info.get_data_frames()[0]
        if df.empty:
            return None
            
        return df.iloc[0].to_dict()
    except Exception as e:
        print(f"Error fetching bio for {player_id}: {e}")
        return None

def get_opponent_def_ratings():
    """
    Fetches current season team defensive ratings. 
    Returns dict: {TEAM_ABBREVIATION: RANK}
    """
    try:
        time.sleep(0.6)
        # Using 2025-26 season (current)
        leaguedash = retry_request(leaguedashteamstats.LeagueDashTeamStats, 
                                   measure_type_detailed_defense='Defense',
                                   season='2025-26')
        
        if not leaguedash:
            return {}
            
        df = leaguedash.get_data_frames()[0]
        
        # We need DEF_RATING rank. The API returns DEF_RATING_RANK usually.
        # Let's ensure columns exist.
        if 'TEAM_ABBREVIATION' in df.columns and 'DEF_RATING_RANK' in df.columns:
            return pd.Series(df.DEF_RATING_RANK.values, index=df.TEAM_ABBREVIATION).to_dict()
        
        # Fallback: Sort by DEF_RATING and assign rank
        if 'DEF_RATING' in df.columns and 'TEAM_ABBREVIATION' in df.columns:
            df = df.sort_values('DEF_RATING', ascending=True) # Lower is better
            df['RANK'] = range(1, len(df) + 1)
            return pd.Series(df['RANK'].values, index=df['TEAM_ABBREVIATION']).to_dict()
            
        return {}
        
    except Exception as e:
        print(f"Error fetching defensive ratings: {e}")
        return {}

def calculate_fantasy_points(row):
    """
    Calculates DraftKings FPTS.
    """
    pts = row['PTS']
    reb = row['REB']
    ast = row['AST']
    stl = row['STL']
    blk = row['BLK']
    tov = row['TOV']
    fg3m = row['FG3M']
    
    fpts = (pts * 1) + (reb * 1.25) + (ast * 1.5) + (stl * 2) + (blk * 2) + (tov * -0.5)
    
    # 3PM Bonus
    if fg3m >= 3:
        fpts += 1.5
    
    # Double-Double / Triple-Double Bonus
    # Statistical categories: PTS, REB, AST, STL, BLK
    stats = [pts, reb, ast, stl, blk]
    thresholds = [10, 10, 10, 5, 5] # Note: Double digit for PTS/REB/AST usually, 5+ for STL/BLK? 
    # DraftKings rules actually usually state Double-Double is 10+ in 2 cats from (PTS, REB, AST, STL, BLK).
    # Wait, 10+ assists/rebounds/points. 
    # User prompt says: [PTS>=10, REB>=10, AST>=10, STL>=5, BLK>=5]
    # This is a bit non-standard (usually it's 10 across the board) but I will follow the Prompt EXACTLY.
    
    count_bonus = 0
    if pts >= 10: count_bonus += 1
    if reb >= 10: count_bonus += 1
    if ast >= 10: count_bonus += 1
    if stl >= 5: count_bonus += 1
    if blk >= 5: count_bonus += 1
    
    if count_bonus >= 2:
        fpts += 1.5
    if count_bonus >= 3:
        fpts += 3
        
    return fpts

def fetch_player_game_log(player_id):
    """
    Fetches last 2 seasons, concatenates, keeps last 50 games.
    Adds FPTS column.
    """
    seasons = ['2023-24', '2024-25', '2025-26']
    all_logs = []
    
    for season in seasons:
        try:
            time.sleep(0.6)
            gamelog = retry_request(playergamelog.PlayerGameLog, player_id=player_id, season=season)
            if gamelog:
                df = gamelog.get_data_frames()[0]
                if not df.empty:
                    df['SEASON_ID'] = season
                    all_logs.append(df)
        except Exception as e:
            print(f"Error fetching game log for {season}: {e}")
            continue
            
    if not all_logs:
        return None
        
    # Concatenate
    full_df = pd.concat(all_logs, ignore_index=True)
    
    # Columns to keep
    # Note: STL, BLK, TOV, FGM, FGA, FG_PCT, FG3M, FG3A, FG3_PCT, FTM, FTA, FT_PCT, PLUS_MINUS
    cols = ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 
            'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'PLUS_MINUS', 'SEASON_ID']
    
    # Ensure columns exist
    available = [c for c in cols if c in full_df.columns]
    full_df = full_df[available]
    
    # Sort by Date Descending
    full_df['GAME_DATE'] = pd.to_datetime(full_df['GAME_DATE'])
    full_df = full_df.sort_values(by='GAME_DATE', ascending=False).reset_index(drop=True)
    
    # Keep last 50 games
    full_df = full_df.head(50)
    
    # Sort Ascending for Rolling Calcs (Important!)
    # We return Descending usually for display, but for feature engineering we need Ascending.
    # The Prompt says "Sort by GAME_DATE descending. Keep only the last 50 games."
    # I will keep it Descending here as requested, but `features.py` must handle sort order.
    # Actually, for features, typically we want chronological.
    # I will stick to returning the DF as requested (Descending, Last 50).
    
    # Add FPTS
    if not full_df.empty:
        # Convert necessary columns to numeric just in case
        num_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG3M']
        for c in num_cols:
            full_df[c] = pd.to_numeric(full_df[c], errors='coerce').fillna(0)
            
        full_df['FPTS'] = full_df.apply(calculate_fantasy_points, axis=1)
        
    return full_df

if __name__ == "__main__":
    # Test
    p = find_player("LeBron James")
    if p:
        print(f"Found: {p['full_name']} (ID: {p['id']})")
        bio = get_player_bio(p['id'])
        print(f"Team: {bio.get('TEAM_ABBREVIATION')} | School: {bio.get('SCHOOL')}")
        
        logs = fetch_player_game_log(p['id'])
        if logs is not None:
            print(logs[['GAME_DATE', 'MATCHUP', 'PTS', 'FPTS']].head())
    
    def_ratings = get_opponent_def_ratings()
    print("Def Ratings Sample:", list(def_ratings.items())[:5])
