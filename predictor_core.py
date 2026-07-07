import random
from datetime import datetime, timedelta
import pandas as pd


def calculate_prediction(home, away, ratings=None):
    """ELO-based probability estimation.
    ratings: dict mapping team name -> elo rating. If None, defaults to 1500.
    Returns dict with keys: home, draw, away, recommendation
    """
    DEFAULT_ELO = 1500
    HOME_ADV_POINTS = 100  # home advantage in ELO points

    if ratings is None:
        ratings = {}

    home_rating = ratings.get(home, DEFAULT_ELO)
    away_rating = ratings.get(away, DEFAULT_ELO)

    # Apply home advantage
    home_adj = home_rating + HOME_ADV_POINTS

    # Expected score for home (ELO expected win probability)
    exp_home = 1 / (1 + 10 ** ((away_rating - home_adj) / 400))

    # Draw probability is higher when ratings are close
    rating_gap = abs(home_rating - away_rating)
    draw_prob = max(0.06, 0.35 - (rating_gap / 800))

    home_prob = exp_home * (1 - draw_prob)
    away_prob = (1 - exp_home) * (1 - draw_prob)

    # Normalize and convert to percentages
    total = home_prob + away_prob + draw_prob
    home_pct = round(home_prob / total * 100, 1)
    draw_pct = round(draw_prob / total * 100, 1)
    away_pct = round(away_prob / total * 100, 1)

    if home_pct >= 60:
        recommendation = f"Strong Home pick: {home}"
    elif away_pct >= 60:
        recommendation = f"Strong Away pick: {away}"
    elif draw_pct >= 35:
        recommendation = "Draw is plausible — market looks balanced."
    else:
        recommendation = "Tight game — monitor odds and team news."

    return {
        "home": home_pct,
        "draw": draw_pct,
        "away": away_pct,
        "recommendation": recommendation,
    }


def get_live_fixtures(league_key, days, api_key, supported_live_leagues=None, requests_module=None):
    """Lightweight live fixtures helper for testing.
    If api_key is falsy or the league isn't supported, returns None.
    Does not perform network calls when requests_module is None.
    """
    if not api_key:
        return None
    if supported_live_leagues is None:
        supported_live_leagues = {"Premier League": "PL", "Champions League": "CL"}
    if league_key not in supported_live_leagues:
        return None

    # If no requests module provided, avoid network in tests
    if requests_module is None:
        return None

    code = supported_live_leagues[league_key]
    today = datetime.now().date()
    end_date = today + timedelta(days=days)
    url = f"https://api.football-data.org/v4/competitions/{code}/matches"

    try:
        response = requests_module.get(
            url,
            params={"dateFrom": today.isoformat(), "dateTo": end_date.isoformat()},
            headers={"X-Auth-Token": api_key},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
        matches = data.get("matches", [])

        rows = []
        for match in matches:
            rows.append(
                {
                    "id": match.get("id"),
                    "homeTeam": {"name": match.get("homeTeam", {}).get("name", "")},
                    "awayTeam": {"name": match.get("awayTeam", {}).get("name", "")},
                    "utcDate": match.get("utcDate", ""),
                    "competition": {"name": match.get("competition", {}).get("name", "")},
                }
            )
        return pd.DataFrame(rows)
    except Exception:
        return None
