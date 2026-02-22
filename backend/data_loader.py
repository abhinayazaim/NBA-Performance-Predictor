import pandas as pd
import numpy as np
import time
import requests
import json
import os
import pickle
from datetime import datetime, timedelta
from nba_api.stats.static import players, teams as nba_teams
from nba_api.stats.endpoints import (
    commonplayerinfo,
    playergamelog,
    leaguedashteamstats,
    scoreboardv2,
    commonteamroster,
)
from difflib import get_close_matches

# Increase global nba_api timeout from default 30s to 60s
try:
    import nba_api.library.http as nba_http
    nba_http.TIMEOUT = 60
except Exception:
    pass

CACHE_DIR = os.path.join(os.path.dirname(__file__), "cache")
os.makedirs(CACHE_DIR, exist_ok=True)


# ── Retry helper ──────────────────────────────────────────────────────────────

def retry_request(func, retries=3, base_delay=5, **kwargs):
    """
    Wraps nba_api calls with exponential backoff.
    Delays: 5s → 10s → 20s on consecutive failures.
    """
    for i in range(retries):
        try:
            return func(**kwargs)
        except requests.exceptions.Timeout:
            wait = base_delay * (2 ** i)
            print(f"Timeout. Retrying in {wait}s... ({i+1}/{retries})")
            time.sleep(wait)
        except Exception as e:
            wait = base_delay * (2 ** i)
            print(f"API Error: {e}. Retrying in {wait}s... ({i+1}/{retries})")
            time.sleep(wait)
    return None


# ── Season helpers ────────────────────────────────────────────────────────────

def get_current_season():
    """Returns current NBA season string e.g. '2025-26'."""
    now = datetime.now()
    if now.month >= 10:
        return f"{now.year}-{str(now.year + 1)[-2:]}"
    return f"{now.year - 1}-{str(now.year)[-2:]}"

def get_recent_seasons(n=4):
    """Returns last n season strings, most recent first. e.g. ['2025-26', '2024-25', ...]"""
    now      = datetime.now()
    end_year = now.year + 1 if now.month >= 10 else now.year
    return [f"{end_year - i - 1}-{str(end_year - i)[-2:]}" for i in range(n)]


# ── Utilities ─────────────────────────────────────────────────────────────────

def row_to_dict(df: pd.DataFrame) -> dict:
    """Converts first row of a DataFrame to a plain dict, replacing NaN with None."""
    if df.empty:
        return {}
    return {
        col: (None if pd.isna(val) else val)
        for col, val in df.iloc[0].to_dict().items()
    }


# ── Player list ───────────────────────────────────────────────────────────────

def get_active_players_list():
    """Returns all active NBA players. Caches to disk for 24h."""
    cache_path = os.path.join(CACHE_DIR, "players_list.json")

    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            data = json.load(f)
        if time.time() < data.get('expires_at', 0):
            return data['payload']

    active  = players.get_active_players()
    payload = [{'id': p['id'], 'name': p['full_name']} for p in active]

    with open(cache_path, 'w') as f:
        json.dump({'payload': payload, 'expires_at': time.time() + 86400}, f)

    return payload

def find_player(name_query):
    """Fuzzy-finds an active player by name."""
    all_players = get_active_players_list()
    player_map  = {p['name'].lower(): p for p in all_players}
    query       = name_query.lower().strip()
    if query in player_map:
        return player_map[query]
    matches = get_close_matches(query, player_map.keys(), n=1, cutoff=0.6)
    return player_map[matches[0]] if matches else None


# ── Player bio ────────────────────────────────────────────────────────────────

def get_player_bio(player_id):
    """Fetches CommonPlayerInfo. Caches for 6h."""
    cache_path = os.path.join(CACHE_DIR, f"bio_{player_id}.json")

    if os.path.exists(cache_path):
        if time.time() - os.path.getmtime(cache_path) < 21600:
            with open(cache_path, 'r') as f:
                return json.load(f)

    try:
        time.sleep(0.3)
        info = retry_request(commonplayerinfo.CommonPlayerInfo, player_id=player_id)
        if not info:
            return None
        df = info.get_data_frames()[0]
        if df.empty:
            return None
        result = row_to_dict(df)
        with open(cache_path, 'w') as f:
            json.dump(result, f, default=str)
        return result
    except Exception as e:
        print(f"get_player_bio({player_id}) error: {e}")
        return None


# ── Team info ─────────────────────────────────────────────────────────────────

def get_team_info(team_id):
    """Returns basic team info dict for a team_id."""
    for t in nba_teams.get_teams():
        if int(t['id']) == int(team_id):
            return {
                'id':           int(team_id),
                'name':         t['full_name'],
                'abbreviation': t['abbreviation'],
                'nickname':     t['nickname'],
            }
    return {
        'id':           int(team_id),
        'name':         'Opponent',
        'abbreviation': '---',
        'nickname':     'Opponent',
    }


# ── Next game ─────────────────────────────────────────────────────────────────

def get_next_game(team_id):
    """Searches the next 7 days of the schedule for the team's next game."""
    try:
        today = datetime.now()
        for i in range(7):
            check_date = today + timedelta(days=i)
            date_str   = check_date.strftime('%m/%d/%Y')
            time.sleep(0.3)
            board = retry_request(scoreboardv2.ScoreboardV2, game_date=date_str)
            if not board:
                continue
            games = board.get_data_frames()[0]
            if games.empty:
                continue
            team_game = games[
                (games['HOME_TEAM_ID'].astype(int) == int(team_id)) |
                (games['VISITOR_TEAM_ID'].astype(int) == int(team_id))
            ]
            if not team_game.empty:
                game    = team_game.iloc[0]
                is_home = int(game['HOME_TEAM_ID']) == int(team_id)
                opp_id  = int(game['VISITOR_TEAM_ID']) if is_home else int(game['HOME_TEAM_ID'])
                opp     = get_team_info(opp_id)
                return {
                    'date':             date_str,
                    'is_home':          bool(is_home),
                    'game_id':          str(game['GAME_ID']),
                    'opp_id':           opp_id,
                    'opp_name':         opp['name'],
                    'opp_abbreviation': opp['abbreviation'],
                    'opp_nickname':     opp['nickname'],
                }
    except Exception as e:
        print(f"get_next_game({team_id}) error: {e}")
    return None


# ── Key matchup ───────────────────────────────────────────────────────────────

def get_key_matchup(opp_team_id, player_position):
    """
    Returns the opposing team's most experienced player at the same position group.
    G=Guard, F=Forward, C=Center. Caches roster for 24h.
    """
    cache_path = os.path.join(CACHE_DIR, f"roster_{opp_team_id}.json")

    if os.path.exists(cache_path):
        if time.time() - os.path.getmtime(cache_path) < 86400:
            with open(cache_path, 'r') as f:
                return json.load(f)

    try:
        time.sleep(0.3)
        roster = retry_request(
            commonteamroster.CommonTeamRoster,
            team_id=opp_team_id,
            season=get_current_season()
        )
        if not roster:
            return None
        df = roster.get_data_frames()[0]
        if df.empty:
            return None

        def pos_group(pos):
            pos = str(pos).upper()
            if 'C' in pos and 'F' not in pos:
                return 'C'
            if 'G' in pos:
                return 'G'
            return 'F'

        player_group    = pos_group(player_position or 'F')
        df['POS_GROUP'] = df['POSITION'].apply(pos_group)

        same_pos = df[df['POS_GROUP'] == player_group]
        if same_pos.empty:
            same_pos = df

        if 'EXP' in same_pos.columns:
            same_pos          = same_pos.copy()
            same_pos['EXP_N'] = pd.to_numeric(same_pos['EXP'], errors='coerce').fillna(0)
            top               = same_pos.sort_values('EXP_N', ascending=False).iloc[0]
        else:
            top = same_pos.iloc[0]

        result = {
            'player_id':    int(top['PLAYER_ID']),
            'name':         str(top['PLAYER']),
            'position':     str(top.get('POSITION', '')),
            'jersey':       str(top.get('NUM', '')),
            'headshot_url': f"https://cdn.nba.com/headshots/nba/latest/1040x760/{int(top['PLAYER_ID'])}.png",
        }
        with open(cache_path, 'w') as f:
            json.dump(result, f)
        return result

    except Exception as e:
        print(f"get_key_matchup({opp_team_id}) error: {e}")
        return None


# ── Opponent defensive ratings ────────────────────────────────────────────────

def get_opponent_def_ratings():
    """
    Returns dict of {team_abbreviation: defensive_rank (1=best, 30=worst)}.
    Caches for 24h.
    """
    cache_path = os.path.join(CACHE_DIR, "def_ratings.json")

    if os.path.exists(cache_path):
        with open(cache_path, 'r') as f:
            data = json.load(f)
        if time.time() < data.get('expires_at', 0):
            return data['payload']

    try:
        time.sleep(0.6)
        leaguedash = retry_request(
            leaguedashteamstats.LeagueDashTeamStats,
            measure_type_detailed_defense='Defense',
            season=get_current_season()
        )
        if not leaguedash:
            return {}
        df = leaguedash.get_data_frames()[0]
        if 'DEF_RATING' not in df.columns or 'TEAM_ABBREVIATION' not in df.columns:
            return {}
        df         = df.sort_values('DEF_RATING', ascending=True).reset_index(drop=True)
        df['RANK'] = range(1, len(df) + 1)
        ratings    = dict(zip(df['TEAM_ABBREVIATION'], df['RANK']))
        with open(cache_path, 'w') as f:
            json.dump({'payload': ratings, 'expires_at': time.time() + 86400}, f)
        return ratings
    except Exception as e:
        print(f"get_opponent_def_ratings() error: {e}")
        return {}


# ── Fantasy points ────────────────────────────────────────────────────────────

def calculate_fantasy_points(row):
    """
    DraftKings NBA scoring:
      PTS×1 + REB×1.25 + AST×1.5 + STL×2 + BLK×2 + TOV×-0.5
      3PM bonus +0.5 per made three
      Double-double +1.5 / Triple-double +3
    """
    pts  = float(row.get('PTS',  0) or 0)
    reb  = float(row.get('REB',  0) or 0)
    ast  = float(row.get('AST',  0) or 0)
    stl  = float(row.get('STL',  0) or 0)
    blk  = float(row.get('BLK',  0) or 0)
    tov  = float(row.get('TOV',  0) or 0)
    fg3m = float(row.get('FG3M', 0) or 0)

    fpts = pts * 1.0 + reb * 1.25 + ast * 1.5 + stl * 2.0 + blk * 2.0 + tov * -0.5
    fpts += fg3m * 0.5  # 3PM bonus

    double_cats = sum([pts >= 10, reb >= 10, ast >= 10, stl >= 5, blk >= 5])
    if double_cats >= 2:
        fpts += 1.5
    if double_cats >= 3:
        fpts += 3.0

    return round(fpts, 2)


# ── Game log ──────────────────────────────────────────────────────────────────

def fetch_player_game_log(player_id):
    """
    Fetches up to 80 games across 4 seasons.

    PCT columns (FG_PCT, FT_PCT, FG3_PCT) come from nba_api as decimals (0.0–1.0).
    We multiply by 100 to store as 0-100 in the raw log.
    features.py then normalizes the rolling PCT features back to 0-1 for the model.
    model.py scales predictions back to 0-100 before returning to the API.

    Caches to disk (pickle) for 3 hours per player.
    """
    cache_path = os.path.join(CACHE_DIR, f"gamelog_{player_id}.pkl")

    if os.path.exists(cache_path):
        if time.time() - os.path.getmtime(cache_path) < 10800:  # 3 hours
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except Exception:
                pass  # corrupt pickle — re-fetch

    seasons  = get_recent_seasons(4)
    all_logs = []

    for season in seasons:
        try:
            time.sleep(0.3)
            gamelog = retry_request(
                playergamelog.PlayerGameLog,
                player_id=player_id,
                season=season
            )
            if gamelog:
                df = gamelog.get_data_frames()[0]
                if not df.empty:
                    df['SEASON_ID'] = season
                    all_logs.append(df)
        except Exception:
            continue

    if not all_logs:
        return None

    full_df = pd.concat(all_logs, ignore_index=True)

    # Keep only useful columns
    KEEP = [
        'GAME_DATE', 'MATCHUP', 'WL', 'MIN', 'PTS', 'REB', 'AST', 'STL', 'BLK',
        'TOV', 'FGM', 'FGA', 'FG_PCT', 'FG3M', 'FG3A', 'FG3_PCT',
        'FTM', 'FTA', 'FT_PCT', 'PLUS_MINUS', 'SEASON_ID'
    ]
    available = [c for c in KEEP if c in full_df.columns]
    full_df   = full_df[available].copy()

    full_df['GAME_DATE'] = pd.to_datetime(full_df['GAME_DATE'])
    full_df = (
        full_df
        .sort_values('GAME_DATE', ascending=False)
        .reset_index(drop=True)
        .head(80)
    )

    # Numeric coercion
    for c in ['PTS', 'REB', 'AST', 'STL', 'BLK', 'TOV', 'FG3M']:
        if c in full_df.columns:
            full_df[c] = pd.to_numeric(full_df[c], errors='coerce').fillna(0)

    # Convert decimal percentages to 0-100 scale for storage
    for c in ['FG_PCT', 'FT_PCT', 'FG3_PCT']:
        if c in full_df.columns:
            full_df[c] = pd.to_numeric(full_df[c], errors='coerce').fillna(0) * 100.0

    # Compute fantasy points
    full_df['FPTS'] = full_df.apply(calculate_fantasy_points, axis=1)

    # Replace NaN / inf with None for clean JSON serialization downstream
    full_df = full_df.astype(object).where(pd.notnull(full_df), None)

    try:
        with open(cache_path, 'wb') as f:
            pickle.dump(full_df, f)
    except Exception as e:
        print(f"Cache write failed for {player_id}: {e}")

    return full_df