import pandas as pd
import numpy as np
import time
import requests
import json
import os
import pickle
from datetime import datetime, timedelta
from nba_api.stats.static import players, teams as nba_teams
from nba_api.stats.endpoints import commonplayerinfo, playergamelog, leaguedashteamstats, scoreboardv2, commonteamroster
from difflib import get_close_matches

def get_current_season():
    """
    Dynamically returns the current NBA season string e.g. '2025-26'.
    NBA seasons start in October. If current month is October or later,
    the season is current_year-(current_year+1).
    If before October, it's (current_year-1)-current_year.
    """
    from datetime import datetime
    now = datetime.now()
    if now.month >= 10:
        return f"{now.year}-{str(now.year + 1)[-2:]}"
    else:
        return f"{now.year - 1}-{str(now.year)[-2:]}"

def get_recent_seasons(n=3):
    """Returns the last n season strings including current, most recent first."""
    from datetime import datetime
    now = datetime.now()
    if now.month >= 10:
        end_year = now.year + 1
    else:
        end_year = now.year
    seasons = []
    for i in range(n):
        y = end_year - i
        seasons.append(f"{y-1}-{str(y)[-2:]}")
    return seasons

# --- Helper ---
def row_to_dict(df: pd.DataFrame) -> dict:
    """Convert the first row of a DataFrame to a plain Python dict with native types."""
    if df.empty: return {}
    row = df.iloc[0]
    # Replace NaNs with None immediately
    return {col: (None if pd.isna(val) else val) for col, val in row.to_dict().items()}


# --- Constants ---
CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)

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
            print(f"API Error: {e}. Retrying in {delay}s... ({i+1}/{retries})")
            time.sleep(delay)
    return None

# --- API Functions ---

def get_active_players_list():
    """Returns a list of all active NBA players. Caches for 24h."""
    cache_path = os.path.join(CACHE_DIR, "players_list.json")
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
             data = json.load(f)
             if time.time() < data['expires_at']:
                 return data['payload']

    active_players = players.get_active_players()
    payload = [{'id': p['id'], 'name': p['full_name']} for p in active_players]
    
    with open(cache_path, 'w') as f:
        json.dump({
            'payload': payload,
            'expires_at': time.time() + 86400
        }, f)
        
    return payload

def find_player(name_query):
    # This is handled by Frontend filtering usually, but kept for backend utilities
    all_players = get_active_players_list()
    # Create map
    player_map = {p['name'].lower(): p for p in all_players}
    
    query = name_query.lower().strip()
    if query in player_map:
        return player_map[query]
    
    matches = get_close_matches(query, player_map.keys(), n=1, cutoff=0.6)
    if matches:
        return player_map[matches[0]]
    return None

def get_player_bio(player_id):
    """Fetches common player info. Caches for 6h."""
    try:
        time.sleep(0.3)
        info = retry_request(commonplayerinfo.CommonPlayerInfo, player_id=player_id)
        if not info: return None
        
        df = info.get_data_frames()[0]
        if df.empty: return None
        
        return row_to_dict(df)
    except Exception as e:
        print(f"Error fetching bio: {e}")
        return None

def get_team_info(team_id):
    """Returns team dict with full_name and abbreviation for a given team_id."""
    all_teams = nba_teams.get_teams()
    for t in all_teams:
        if t['id'] == int(team_id):
            return {
                'id': int(team_id),
                'name': t['full_name'],
                'abbreviation': t['abbreviation'],
                'nickname': t['nickname'],
            }
    return {'id': int(team_id), 'name': 'Opponent', 'abbreviation': '---', 'nickname': 'Opponent'}

def get_next_game(team_id):
    try:
        today = datetime.now()
        for i in range(7):
            date_str = (today + timedelta(days=i)).strftime('%m/%d/%Y')
            time.sleep(0.3)
            board = retry_request(scoreboardv2.ScoreboardV2, game_date=date_str)
            if board:
                games = board.get_data_frames()[0]
                if not games.empty:
                    team_game = games[
                        (games['HOME_TEAM_ID'] == team_id) |
                        (games['VISITOR_TEAM_ID'] == team_id)
                    ]
                    if not team_game.empty:
                        game = team_game.iloc[0]
                        is_home = int(game['HOME_TEAM_ID']) == int(team_id)
                        opp_id = int(game['VISITOR_TEAM_ID']) if is_home else int(game['HOME_TEAM_ID'])
                        opp_info = get_team_info(opp_id)
                        return {
                            'date': date_str,
                            'is_home': bool(is_home),
                            'game_id': str(game['GAME_ID']),
                            'opp_id': opp_id,
                            'opp_name': opp_info['name'],
                            'opp_abbreviation': opp_info['abbreviation'],
                            'opp_nickname': opp_info['nickname'],
                        }
    except Exception as e:
        print(f"get_next_game error: {e}")
    return None

def get_key_matchup(opp_team_id, player_position):
    """
    Returns the opposing team's best player at the same position group.
    Position groups: Guard (PG/SG), Forward (SF/PF), Center (C)
    """
    cache_path = os.path.join(CACHE_DIR, f"roster_{opp_team_id}.json")
    if os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < 86400:  # 1 day cache
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return data

    try:
        time.sleep(0.3)
        roster = retry_request(commonteamroster.CommonTeamRoster,
                               team_id=opp_team_id,
                               season=get_current_season()) # Using current season
        if not roster:
            return None

        df = roster.get_data_frames()[0]
        if df.empty:
            return None

        # Map position groups
        def pos_group(pos):
            if not pos: return 'F'
            pos = str(pos).upper()
            if 'C' in pos and 'F' not in pos: return 'C'
            if 'G' in pos: return 'G'
            return 'F'

        player_group = pos_group(player_position)

        # Filter to same position group
        df['POS_GROUP'] = df['POSITION'].apply(pos_group)
        same_pos = df[df['POS_GROUP'] == player_group]
        if same_pos.empty:
            same_pos = df  # fallback to whole roster

        # Pick the player with most experience (proxy for best player)
        # Use EXP column if available, otherwise just take first
        if 'EXP' in same_pos.columns:
            same_pos = same_pos.copy()
            same_pos['EXP_NUM'] = pd.to_numeric(same_pos['EXP'], errors='coerce').fillna(0)
            top = same_pos.sort_values('EXP_NUM', ascending=False).iloc[0]
        else:
            top = same_pos.iloc[0]

        result = {
            'player_id': int(top['PLAYER_ID']),
            'name': str(top['PLAYER']),
            'position': str(top.get('POSITION', '')),
            'jersey': str(top.get('NUM', '')),
            'headshot_url': f"https://cdn.nba.com/headshots/nba/latest/1040x760/{int(top['PLAYER_ID'])}.png"
        }

        with open(cache_path, 'w') as f:
            json.dump(result, f)

        return result

    except Exception as e:
        print(f"get_key_matchup error: {e}")
        return None

def get_opponent_def_ratings():
    """Fetches def ratings. Caches for 24h."""
    cache_path = os.path.join(CACHE_DIR, "def_ratings.json")
    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
             data = json.load(f)
             if time.time() < data['expires_at']:
                 return data['payload']

    try:
        time.sleep(0.6)
        leaguedash = retry_request(leaguedashteamstats.LeagueDashTeamStats, 
                                   measure_type_detailed_defense='Defense',
                                   season=get_current_season())
        if not leaguedash: return {}
        
        df = leaguedash.get_data_frames()[0]
        # FIX: Ensure bracket access
        if 'DEF_RATING' in df.columns and 'TEAM_ABBREVIATION' in df.columns:
            df = df.sort_values('DEF_RATING', ascending=True)
            df['RANK'] = range(1, len(df) + 1)
            ratings = pd.Series(df['RANK'].values, index=df['TEAM_ABBREVIATION']).to_dict()
            
            with open(cache_path, 'w') as f:
                json.dump({'payload': ratings, 'expires_at': time.time() + 86400}, f)
            return ratings
    except Exception as e:
        print(f"Error fetching def ratings: {e}")
    return {}

def calculate_fantasy_points(row):
    pts = row['PTS']
    reb = row['REB']
    ast = row['AST']
    stl = row['STL']
    blk = row['BLK']
    tov = row['TOV']
    fg3m = row['FG3M']
    
    fpts = (pts * 1) + (reb * 1.25) + (ast * 1.5) + (stl * 2) + (blk * 2) + (tov * -0.5)
    
    if fg3m >= 3: fpts += 1.5
    
    stats = [pts, reb, ast, stl, blk]
    
    cb = 0
    if pts >= 10: cb += 1
    if reb >= 10: cb += 1
    if ast >= 10: cb += 1
    if stl >= 5: cb += 1
    if blk >= 5: cb += 1

    if cb >= 2: fpts += 1.5
    if cb >= 3: fpts += 3
        
    return fpts

def fetch_player_game_log(player_id):
    """Fetches game log + FPTS + PCT Fixes. Caches for 3h per player using pickle."""
    cache_path = os.path.join(CACHE_DIR, f"gamelog_{player_id}.pkl")
    if os.path.exists(cache_path):
        age = time.time() - os.path.getmtime(cache_path)
        if age < 10800:  # 3 hours
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                pass # Fallback to fetch if pickle load fails

    seasons = get_recent_seasons(3) # Only using relevant recent seasons
    all_logs = []
    
    for season in seasons:
        try:
            time.sleep(0.3)
            gamelog = retry_request(playergamelog.PlayerGameLog, player_id=player_id, season=season)
            if gamelog:
                df = gamelog.get_data_frames()[0]
                if not df.empty:
                    df['SEASON_ID'] = season
                    all_logs.append(df)
        except:
             continue
    
    if not all_logs: return None
    
    full_df = pd.concat(all_logs, ignore_index=True)
    
    # Columns
    cols = ['GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 
            'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT', 'FTM', 'FTA', 'FT_PCT', 'PLUS_MINUS', 'SEASON_ID']
    available = [c for c in cols if c in full_df.columns]
    full_df = full_df[available]
    
    full_df['GAME_DATE'] = pd.to_datetime(full_df['GAME_DATE'])
    full_df = full_df.sort_values(by='GAME_DATE', ascending=False).reset_index(drop=True)
    full_df = full_df.head(50)
    
    # Numeric conversion
    num_cols = ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG3M', 'FG_PCT', 'FT_PCT', 'FG3_PCT']
    for c in num_cols:
        full_df[c] = pd.to_numeric(full_df[c], errors='coerce').fillna(0)
    
    # FIX 1: PERCENTAGES -> 0-100
    for col in ['FG_PCT', 'FT_PCT', 'FG3_PCT']:
        full_df[col] = full_df[col] * 100
        
    # Add FPTS (This applies before cleaning, returns float)
    full_df['FPTS'] = full_df.apply(calculate_fantasy_points, axis=1)

    # Replace all NaN/NaT/Inf with None so JSON serialization never fails
    # Use object dtype to allow None
    full_df = full_df.astype(object).where(pd.notnull(full_df), None)
    
    # Save to cache
    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(full_df, f)
    except Exception as e:
        print(f"Cache write error: {e}")
    
    return full_df
