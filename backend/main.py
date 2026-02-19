from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import pandas as pd
import numpy as np
import threading
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from data_loader import get_active_players_list, get_player_bio, get_next_game, row_to_dict, get_key_matchup
from model import predict_next_game, TARGETS

app = FastAPI()

# --- Async Executor ---
executor = ThreadPoolExecutor(max_workers=8)

# --- CORS ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from utils import sanitize
from fastapi.responses import JSONResponse
from fastapi.requests import Request

# --- Global Exception Handler (Serialization Fix) ---
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    return JSONResponse(
        status_code=500,
        content={
            "error": type(exc).__name__,
            "detail": str(exc),
            "path": str(request.url),
        }
    )

# --- Startup ---
@app.on_event("startup")
def startup_event():
    print("Pre-warming player cache...")
    get_active_players_list()
    thread = threading.Thread(target=prewarm_top_players, daemon=True)
    thread.start()

def prewarm_top_players():
    TOP_PLAYERS = [
        2544, 201939, 203999, 203507, 1629029,
        203076, 1628369, 203954, 1629627, 1628384,
        201142, 203500, 1627759, 1628386, 203081,
        2546, 201935, 203497, 1629028, 203110,
        201566, 203944, 1627732, 1628378, 203468,
        1629630, 1630162, 1630178, 1630173, 203992,
        1630169, 1631096, 1630563, 1630228, 201587,
        202695, 203114, 203460, 201150, 202331,
        203952, 1627783, 203897, 1628973, 203085,
        1629628, 203932, 201933, 203954, 1628384
    ]
    from model import train_player_models, get_model_path, is_cache_valid
    for pid in TOP_PLAYERS:
        try:
            if not is_cache_valid(get_model_path(pid)):
                print(f"Pre-training model for player {pid}...")
                train_player_models(pid, str(pid))
                time.sleep(1.0)
        except Exception as e:
            print(f"Pre-warm failed for {pid}: {e}")

# --- Root Routes ---
@app.get("/")
def root():
    return {"status": "ok", "message": "CourtVision API is running", "version": "2.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}

# --- Endpoints ---

@app.get("/api/players")
def get_players():
    """Returns list of active players."""
    players = get_active_players_list()
    return sanitize(sorted(players, key=lambda x: x['name']))

@app.get("/api/player/{player_id}/profile")
async def get_profile(player_id: int):
    """Returns player bio, headshot, next game, and key matchup."""
    loop = asyncio.get_event_loop()
    bio = await loop.run_in_executor(executor, lambda: get_player_bio(player_id))
    
    if not bio:
        raise HTTPException(status_code=404, detail="Player not found")

    next_game = await loop.run_in_executor(
        executor, lambda: get_next_game(bio['TEAM_ID'])
    )

    key_matchup = None
    if next_game and next_game.get('opp_id'):
        key_matchup = await loop.run_in_executor(
            executor,
            lambda: get_key_matchup(next_game['opp_id'], bio.get('POSITION', 'F'))
        )

    return sanitize({
        "bio": bio,
        "headshot_url": f"https://cdn.nba.com/headshots/nba/latest/1040x760/{player_id}.png",
        "next_game": next_game,
        "key_matchup": key_matchup
    })

@app.get("/api/player/{player_id}/predict")
async def get_prediction(player_id: int):
    """Returns predictions, CIs, feature importances, and history."""
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            executor, lambda: predict_next_game(player_id)
        )
        if not result:
            raise HTTPException(status_code=404, detail="Insufficient data for prediction")

        predictions = result['predictions']
        cis = result['cis']
        history_df = result['history_df']
        feat_imp = result['feature_importances']
        feat_names = result['feature_names']

        # Season Averages for Delta
        season_avgs = {k: float(v) if not pd.isna(v) else 0.0
                       for k, v in history_df[TARGETS].mean().to_dict().items()}

        # Format Prediction Response with higher_is_better and CIs
        formatted_preds = {}
        for target in TARGETS:
            is_good = target != 'TOV'
            formatted_preds[target] = {
                "value": predictions.get(target, 0),
                "ci": cis.get(f"{target}_ci", 0),
                "higher_is_better": is_good,
                "season_avg": season_avgs.get(target, 0)
            }

        # Convert History DF to JSON
        if 'GAME_DATE' in history_df.columns:
            if not pd.api.types.is_datetime64_any_dtype(history_df['GAME_DATE']):
                history_df['GAME_DATE'] = pd.to_datetime(history_df['GAME_DATE'])
            history_df['GAME_DATE'] = history_df['GAME_DATE'].dt.strftime('%Y-%m-%d')

        history_json = history_df.to_dict(orient='records')

        # Feature Importances
        if hasattr(feat_imp, 'tolist'):
            feat_imp = feat_imp.tolist()

        top_features = []
        if len(feat_imp) > 0 and len(feat_names) == len(feat_imp):
            feats = list(zip(feat_names, feat_imp))
            feats.sort(key=lambda x: x[1], reverse=True)
            top_features = [{"name": n, "importance": v} for n, v in feats[:10]]

        return sanitize({
            "predictions": formatted_preds,
            "history": history_json,
            "feature_importance": top_features
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"Prediction Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/player/{player_id}/career")
async def get_career(player_id: int):
    """Returns per-season career stats."""
    loop = asyncio.get_event_loop()
    
    def _fetch_career():
        from nba_api.stats.endpoints import playercareerstats
        import time
        time.sleep(0.3)
        try:
            career = playercareerstats.PlayerCareerStats(player_id=player_id)
            df = career.get_data_frames()[0]

            df['PPG'] = (df['PTS'] / df['GP']).round(1)
            df['RPG'] = (df['REB'] / df['GP']).round(1)
            df['APG'] = (df['AST'] / df['GP']).round(1)
            df['SPG'] = (df['STL'] / df['GP']).round(1)
            df['BPG'] = (df['BLK'] / df['GP']).round(1)
            df['MPG'] = (df['MIN'] / df['GP']).round(1)

            for col in ['FG_PCT', 'FT_PCT', 'FG3_PCT']:
                if col in df.columns:
                    df[col] = (df[col] * 100).round(1)

            keep = ['SEASON_ID', 'TEAM_ABBREVIATION', 'GP', 'MPG', 'PPG', 'RPG',
                    'APG', 'SPG', 'BPG', 'FG_PCT', 'FT_PCT', 'FG3_PCT']
            available = [c for c in keep if c in df.columns]

            return sanitize(df[available].to_dict(orient='records'))
        except Exception as e:
            raise e

    try:
        return await loop.run_in_executor(executor, _fetch_career)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/player/{player_id}/intel")
async def get_player_intel(player_id: int):
    """Returns fun facts and accolades for a player."""
    loop = asyncio.get_event_loop()
    
    def _fetch_intel():
        import time
        time.sleep(0.3)
        try:
            from nba_api.stats.endpoints import commonplayerinfo, playerawards

            info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
            bio_df = info.get_data_frames()[0]

            if bio_df.empty:
                return sanitize({"facts": []})

            bio = row_to_dict(bio_df)
            facts = []

            # Draft context
            draft_number = bio.get('DRAFT_NUMBER')
            draft_year = bio.get('DRAFT_YEAR')
            if draft_number and draft_year:
                def ordinal(n):
                    n = int(n)
                    suffix = 'th' if 11 <= n <= 13 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
                    return f"{n}{suffix}"
                facts.append({"label": "Draft", "value": f"{ordinal(draft_number)} pick, {draft_year} NBA Draft"})

            # School
            school = bio.get('SCHOOL')
            if school and str(school).strip():
                facts.append({"label": "College", "value": str(school)})

            # Country
            country = bio.get('COUNTRY')
            if country and country != 'USA':
                facts.append({"label": "Country", "value": str(country)})

            # Experience
            exp = bio.get('SEASON_EXP')
            if exp is not None:
                exp_int = int(exp)
                facts.append({"label": "NBA Experience", "value": f"{exp_int} season{'s' if exp_int != 1 else ''}"})

            # Awards
            time.sleep(0.3)
            try:
                awards = playerawards.PlayerAwards(player_id=player_id)
                awards_df = awards.get_data_frames()[0]
                if not awards_df.empty:
                    award_counts = awards_df['DESCRIPTION'].value_counts()
                    for award, count in award_counts.items():
                        if count > 0 and any(k in str(award) for k in ['Champion', 'MVP', 'All-Star', 'All-NBA', 'Defensive']):
                            value = f"× {count}" if count > 1 else "× 1"
                            facts.append({"label": str(award), "value": value})
            except Exception:
                pass

            return sanitize({"facts": facts})
        except Exception as e:
            raise e

    try:
        return await loop.run_in_executor(executor, _fetch_intel)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8008, reload=True)