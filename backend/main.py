from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request
import uvicorn
import pandas as pd
import numpy as np
import time

from data_loader import (
    get_active_players_list,
    get_player_bio,
    get_next_game,
    get_key_matchup,
    row_to_dict,
)
from model import predict_next_game, TARGETS
from utils import sanitize

app = FastAPI()

# ── CORS ──────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Global error handler ──────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error":  type(exc).__name__,
            "detail": str(exc),
            "path":   str(request.url),
        }
    )

# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    """
    On startup: pre-load the players list into cache so the first /api/players
    request is instant. We deliberately do NOT pre-train models here to avoid
    hammering the NBA API on startup and triggering rate limits.
    Models train on first request per player and then cache for 72h.
    """
    print("Pre-warming player list cache...")
    get_active_players_list()
    print("Startup complete.")

# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ok", "message": "CourtVision API", "version": "3.1.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

# ── Players list ──────────────────────────────────────────────────────────────

@app.get("/api/players")
def get_players():
    """Returns sorted list of all active NBA players."""
    players = get_active_players_list()
    return sanitize(sorted(players, key=lambda x: x['name']))

# ── Player profile ────────────────────────────────────────────────────────────

@app.get("/api/player/{player_id}/profile")
def get_profile(player_id: int):
    """
    Returns player bio, headshot URL, next scheduled game, and key matchup.
    key_matchup finds the most experienced same-position player on the opposing team.
    """
    bio = get_player_bio(player_id)
    if not bio:
        raise HTTPException(status_code=404, detail="Player not found")

    team_id   = bio.get('TEAM_ID')
    position  = bio.get('POSITION', 'F')
    next_game = get_next_game(team_id) if team_id else None

    key_matchup = None
    if next_game and next_game.get('opp_id'):
        key_matchup = get_key_matchup(next_game['opp_id'], position)

    return sanitize({
        "bio":          bio,
        "headshot_url": f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png",
        "next_game":    next_game,
        "key_matchup":  key_matchup,
    })

# ── Predictions ───────────────────────────────────────────────────────────────

@app.get("/api/player/{player_id}/predict")
def get_prediction(player_id: int):
    """
    Returns ML predictions for the player's next game.

    Response shape:
    {
      predictions: {
        PTS: { value, ci, higher_is_better, season_avg },
        ...
      },
      history: [ game log rows ... ],
      feature_importance: [ { name, importance } ... ]
    }

    Notes on FG_PCT / FT_PCT:
      - Raw game logs store these as 0-100 (e.g. 52.3 for 52.3%)
      - features.py normalizes rolling PCT features to 0-1 for the model
      - model.py scales predictions back to 0-100 before returning here
      - season_avg is computed from raw history (0-100), so it matches
    """
    try:
        result = predict_next_game(player_id)
        if not result:
            raise HTTPException(status_code=404, detail="Insufficient data for prediction")

        predictions   = result['predictions']
        cis           = result['cis']
        history_df    = result['history_df']
        feat_imp      = result['feature_importances']
        feat_names    = result['feature_names']

        # Season averages from raw history (0-100 for PCT, counts for others)
        numeric_targets = [t for t in TARGETS if t in history_df.columns]
        season_avgs     = {}
        for t in numeric_targets:
            col = pd.to_numeric(history_df[t], errors='coerce')
            season_avgs[t] = round(float(col.mean()), 1) if not col.isna().all() else 0.0

        # Build formatted prediction dict
        formatted_preds = {}
        for target in TARGETS:
            formatted_preds[target] = {
                "value":            float(predictions.get(target, 0)),
                "ci":               float(cis.get(f"{target}_ci", 0)),
                "higher_is_better": target != 'TOV',
                "season_avg":       season_avgs.get(target, 0.0),
            }

        # Serialize history — convert dates to strings
        history_df = history_df.copy()
        if 'GAME_DATE' in history_df.columns:
            history_df['GAME_DATE'] = pd.to_datetime(
                history_df['GAME_DATE'], errors='coerce'
            ).dt.strftime('%Y-%m-%d')

        history_json = history_df.to_dict(orient='records')

        # Top 10 feature importances
        top_features = []
        if feat_imp and feat_names and len(feat_imp) == len(feat_names):
            paired = sorted(zip(feat_names, feat_imp), key=lambda x: x[1], reverse=True)
            top_features = [{"name": n, "importance": round(float(v), 4)} for n, v in paired[:10]]

        return sanitize({
            "predictions":       formatted_preds,
            "history":           history_json,
            "feature_importance": top_features,
        })

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# ── Career stats ──────────────────────────────────────────────────────────────

@app.get("/api/player/{player_id}/career")
def get_career(player_id: int):
    """Returns per-season career stats with per-game averages computed."""
    try:
        from nba_api.stats.endpoints import playercareerstats
        time.sleep(0.6)

        career = playercareerstats.PlayerCareerStats(player_id=player_id)
        df     = career.get_data_frames()[0]

        if df.empty:
            return sanitize([])

        for col in ['GP', 'PTS', 'REB', 'AST', 'STL', 'BLK', 'MIN']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        df['PPG'] = (df['PTS'] / df['GP'].replace(0, np.nan)).round(1).fillna(0)
        df['RPG'] = (df['REB'] / df['GP'].replace(0, np.nan)).round(1).fillna(0)
        df['APG'] = (df['AST'] / df['GP'].replace(0, np.nan)).round(1).fillna(0)
        df['SPG'] = (df['STL'] / df['GP'].replace(0, np.nan)).round(1).fillna(0)
        df['BPG'] = (df['BLK'] / df['GP'].replace(0, np.nan)).round(1).fillna(0)
        df['MPG'] = (df['MIN'] / df['GP'].replace(0, np.nan)).round(1).fillna(0)

        # PCT columns come as decimals (0.0-1.0) from career endpoint
        for col in ['FG_PCT', 'FT_PCT', 'FG3_PCT']:
            if col in df.columns:
                df[col] = (pd.to_numeric(df[col], errors='coerce').fillna(0) * 100).round(1)

        KEEP      = ['SEASON_ID', 'TEAM_ABBREVIATION', 'GP', 'MPG',
                     'PPG', 'RPG', 'APG', 'SPG', 'BPG', 'FG_PCT', 'FT_PCT', 'FG3_PCT']
        available = [c for c in KEEP if c in df.columns]

        return sanitize(df[available].to_dict(orient='records'))

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Player intel ──────────────────────────────────────────────────────────────

@app.get("/api/player/{player_id}/intel")
def get_player_intel(player_id: int):
    """Returns curated facts and awards for a player."""
    try:
        from nba_api.stats.endpoints import commonplayerinfo, playerawards
        time.sleep(0.3)

        info   = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
        bio_df = info.get_data_frames()[0]

        if bio_df.empty:
            return sanitize({"facts": []})

        bio   = row_to_dict(bio_df)
        facts = []

        # Draft
        draft_number = bio.get('DRAFT_NUMBER')
        draft_year   = bio.get('DRAFT_YEAR')
        if draft_number and draft_year and str(draft_number) not in ('0', 'Undrafted', 'None'):
            n      = int(draft_number)
            suffix = 'th' if 11 <= n <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
            facts.append({"label": "Draft", "value": f"{n}{suffix} pick, {draft_year}"})

        # College
        school = bio.get('SCHOOL')
        if school and str(school).strip() and str(school) != 'None':
            facts.append({"label": "College", "value": str(school)})

        # Country
        country = bio.get('COUNTRY')
        if country and country not in ('USA', 'None', None):
            facts.append({"label": "Country", "value": str(country)})

        # Experience
        exp = bio.get('SEASON_EXP')
        if exp is not None:
            exp_int = int(exp)
            facts.append({"label": "Experience", "value": f"{exp_int} season{'s' if exp_int != 1 else ''}"})

        # Jersey
        jersey = bio.get('JERSEY')
        if jersey:
            facts.append({"label": "Jersey", "value": f"#{jersey}"})

        # Height / Weight
        height = bio.get('HEIGHT')
        weight = bio.get('WEIGHT')
        if height:
            facts.append({"label": "Height", "value": str(height)})
        if weight:
            facts.append({"label": "Weight", "value": f"{weight} lbs"})

        # Awards
        try:
            time.sleep(0.3)
            awards    = playerawards.PlayerAwards(player_id=player_id)
            awards_df = awards.get_data_frames()[0]
            if not awards_df.empty:
                IMPORTANT = ['Champion', 'MVP', 'All-Star', 'All-NBA', 'Defensive', 'Rookie', 'Scoring']
                counts    = awards_df['DESCRIPTION'].value_counts()
                for award, count in counts.items():
                    if any(k in str(award) for k in IMPORTANT):
                        facts.append({
                            "label": str(award),
                            "value": f"× {count}" if count > 1 else "× 1",
                        })
        except Exception:
            pass

        return sanitize({"facts": facts})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8008, reload=True)