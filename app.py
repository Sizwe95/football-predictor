import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import random

try:
    import requests
except ImportError:
    requests = None

# import core predictors
try:
    from predictor_core import calculate_prediction as core_calculate_prediction, get_live_fixtures as core_get_live_fixtures
except Exception:
    core_calculate_prediction = None
    core_get_live_fixtures = None
st.set_page_config(
    page_title="Amapanta Predictor",
    page_icon="⚽",
    layout="wide",
)

st.markdown(
    """
    <style>
        .stApp {
            background-color: #f8f9fb;
        }
        .stSidebar {
            background-color: #0a2540;
            color: #ffffff;
        }
        .css-1d391kg {
            background-color: #0a2540;
        }
        .stButton>button {
            background-color: #0a3b6f;
            color: white;
        }
        .stMetric .value {
            color: #0a2540;
        }
        .stAlert {
            border-radius: 12px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

SANITY_PROJECT_ID = os.getenv("SANITY_PROJECT_ID", "").strip()
SANITY_DATASET = os.getenv("SANITY_DATASET", "").strip()
SANITY_API_TOKEN = os.getenv("SANITY_API_TOKEN", "").strip()
FOOTBALL_DATA_API_KEY = os.getenv("FOOTBALL_DATA_API_KEY", "").strip()

supported_live_leagues = {
    "Premier League": "PL",
    "Champions League": "CL",
}

leagues = {
    "PSL": {
        "name": "Premier Soccer League (South Africa)",
        "teams": [
            "Mamelodi Sundowns",
            "Orlando Pirates",
            "Kaizer Chiefs",
            "Stellenbosch FC",
            "TS Galaxy",
            "AmaZulu",
            "Cape Town City",
            "SuperSport United",
            "Richards Bay",
        ],
    },
    "CAF Champions League": {
        "name": "CAF Champions League",
        "teams": [
            "Mamelodi Sundowns",
            "Orlando Pirates",
            "Al Ahly",
            "TP Mazembe",
            "Simba SC",
            "Wydad AC",
            "Esperance Tunis",
            "Kaizer Chiefs",
        ],
    },
    "Premier League": {
        "name": "English Premier League",
        "teams": [
            "Manchester City",
            "Arsenal",
            "Liverpool",
            "Chelsea",
            "Tottenham Hotspur",
            "Newcastle United",
        ],
    },
    "Champions League": {
        "name": "UEFA Champions League",
        "teams": [
            "Real Madrid",
            "Bayern Munich",
            "Manchester City",
            "Paris Saint-Germain",
            "Inter Milan",
            "Barcelona",
        ],
    },
}

# Initialize ELO ratings in session state (persist across reruns)
if "elo_ratings" not in st.session_state:
    base = 1500
    ratings = {}
    for lk in leagues.values():
        for t in lk["teams"]:
            ratings.setdefault(t, base)
    st.session_state["elo_ratings"] = ratings


def make_session_with_retries(total_retries=3, backoff_factor=1):
    if not requests:
        return None
    try:
        from requests.adapters import HTTPAdapter, Retry
    except Exception:
        return None

    session = requests.Session()
    retries = Retry(
        total=total_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


st.sidebar.header("Data Settings")
selected_league = st.sidebar.selectbox("League", options=list(leagues.keys()))
league_info = leagues[selected_league]

days_ahead = st.sidebar.slider("Fixtures horizon (days)", 1, 30, 10)
search_term = st.sidebar.text_input(
    "Search team or competition",
    placeholder="e.g. Mamelodi Sundowns, Manchester City",
)

use_live_data = st.sidebar.checkbox("Fetch live data when available", value=False)
use_groq_search = st.sidebar.checkbox("Enable GROQ search", value=False)

# ELO editor in sidebar
st.sidebar.markdown("---")
st.sidebar.header("ELO Ratings")
all_teams = sorted(list(st.session_state["elo_ratings"].keys()))
team_to_edit = st.sidebar.selectbox("Select team to edit ELO", options=all_teams)
current_elo = int(st.session_state["elo_ratings"].get(team_to_edit, 1500))
new_elo = st.sidebar.number_input("Set ELO", min_value=800, max_value=2400, value=current_elo, step=10)
if st.sidebar.button("Update ELO"):
    st.session_state["elo_ratings"][team_to_edit] = int(new_elo)
    st.sidebar.success(f"Updated {team_to_edit} to ELO {new_elo}")

if st.sidebar.button("Reset all ELOs to default"):
    for k in st.session_state["elo_ratings"].keys():
        st.session_state["elo_ratings"][k] = 1500
    st.sidebar.success("Reset all ELOs to 1500")

# Auto-refresh controls
st.sidebar.markdown("---")
st.sidebar.header("Auto-refresh")
auto_refresh_secs = st.sidebar.number_input("Auto-refresh interval (seconds, 0 to disable)", min_value=0, max_value=3600, value=0, step=30)
last_refresh = st.session_state.get("last_refresh", datetime.now().isoformat())
if st.sidebar.button("Refresh now"):
    try:
        cached_live_fixtures.clear()
    except Exception:
        pass
    st.session_state["last_refresh"] = datetime.now().isoformat()
    st.experimental_rerun()

# Handle automatic refresh by elapsed time
if auto_refresh_secs > 0:
    try:
        last = datetime.fromisoformat(st.session_state.get("last_refresh", datetime.now().isoformat()))
    except Exception:
        last = datetime.now()
    elapsed = (datetime.now() - last).total_seconds()
    if elapsed >= auto_refresh_secs:
        try:
            cached_live_fixtures.clear()
        except Exception:
            pass
        st.session_state["last_refresh"] = datetime.now().isoformat()
        st.experimental_rerun()

st.sidebar.markdown("---")
if FOOTBALL_DATA_API_KEY:
    st.sidebar.success("Football-data.org API key configured")
elif use_live_data:
    st.sidebar.warning("Set FOOTBALL_DATA_API_KEY to enable live fixtures")

if SANITY_PROJECT_ID and SANITY_DATASET and SANITY_API_TOKEN:
    st.sidebar.success("Sanity GROQ search configured")
elif use_groq_search:
    st.sidebar.warning("Set SANITY_PROJECT_ID, SANITY_DATASET, SANITY_API_TOKEN for GROQ search")

st.sidebar.markdown(
    """
    **Environment Variables**
    - `FOOTBALL_DATA_API_KEY`: optional real fixtures source for PL / CL.
    - `SANITY_PROJECT_ID`, `SANITY_DATASET`, `SANITY_API_TOKEN`: optional GROQ search.
    """
)

st.title("⚽ Amapanta Predictor")
st.markdown(
    "Professional fixture forecasting with optional live data and GROQ search support.",
)


def format_match_time(utc_date_str):
    return pd.to_datetime(utc_date_str).strftime("%a %d %b • %H:%M")


def get_simulated_fixtures(league_key, days):
    teams = leagues[league_key]["teams"]
    fixtures = []
    start = datetime.now()

    for i in range(12):
        home = random.choice(teams)
        away = random.choice([team for team in teams if team != home])
        date = start + timedelta(days=random.randint(1, days), hours=random.randint(12, 21))
        fixtures.append(
            {
                "id": i,
                "homeTeam": {"name": home},
                "awayTeam": {"name": away},
                "utcDate": date.isoformat(),
                "competition": {"name": leagues[league_key]["name"]},
            }
        )

    return pd.DataFrame(fixtures)


def get_live_fixtures(league_key, days, api_key):
    # Delegate to predictor_core implementation when available for easier testing
    if core_get_live_fixtures:
        return core_get_live_fixtures(league_key, days, api_key, supported_live_leagues, requests)

    if not api_key or league_key not in supported_live_leagues or not requests:
        return None

    code = supported_live_leagues[league_key]
    today = datetime.now().date()
    end_date = today + timedelta(days=days)
    url = f"https://api.football-data.org/v4/competitions/{code}/matches"

    session = make_session_with_retries() or requests
    try:
        response = session.get(
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
                    "competition": {"name": match.get("competition", {}).get("name", leagues[league_key]["name"])},
                }
            )
        return pd.DataFrame(rows)
    except requests.exceptions.RequestException:
        st.warning("Live fixture lookup failed due to network error. Showing simulated fixtures instead.")
        return None
    except Exception:
        st.warning("Live fixture lookup failed. Showing simulated fixtures instead.")
        return None


def calculate_prediction(home, away):
    # ELO-based probability estimation
    DEFAULT_ELO = 1500
    HOME_ADV_POINTS = 100  # home advantage in ELO points

    ratings = st.session_state.get("elo_ratings", {})
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


def filter_fixtures(df, keyword):
    if not keyword:
        return df
    keyword = keyword.lower()
    return df[df.apply(
        lambda row: keyword in row["homeTeam"]["name"].lower()
        or keyword in row["awayTeam"]["name"].lower()
        or keyword in row["competition"]["name"].lower(),
        axis=1,
    )].reset_index(drop=True)


def fetch_sanity_search(query_term):
    if not requests or not (SANITY_PROJECT_ID and SANITY_DATASET and SANITY_API_TOKEN):
        return []

    query_term = query_term.replace('"', "").strip()
    if not query_term:
        return []

    wildcard = f"*{query_term}*"
    groq = (
        "*[_type == 'fixture' && (homeTeam.name match $wildcard || awayTeam.name match $wildcard "
        "|| competition.title match $wildcard)]{_id, date, homeTeam{name}, awayTeam{name}, competition{title}}"
    )
    url = f"https://{SANITY_PROJECT_ID}.api.sanity.io/v2024-03-16/data/query/{SANITY_DATASET}"

    try:
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {SANITY_API_TOKEN}"},
            params={"query": groq, "wildcard": wildcard},
            timeout=15,
        )
        response.raise_for_status()
        return response.json().get("result", [])
    except Exception:
        return []

live_fixtures = None
@st.cache_data(ttl=300)
def cached_live_fixtures(league_key, days, api_key):
    return get_live_fixtures(league_key, days, api_key)

live_fixtures = None
if use_live_data:
    live_fixtures = cached_live_fixtures(selected_league, days_ahead, FOOTBALL_DATA_API_KEY)

fixtures_df = live_fixtures if live_fixtures is not None else get_simulated_fixtures(selected_league, days_ahead)
fixtures_df = filter_fixtures(fixtures_df, search_term)

matches_count = len(fixtures_df)

summary_cols = st.columns([1, 1, 1, 2])
summary_cols[0].metric("League", league_info["name"])
summary_cols[1].metric("Fixtures", matches_count)
summary_cols[2].metric("Data Mode", "Live" if live_fixtures is not None else "Simulated")
summary_cols[3].metric("Search", search_term or "None")

# ELO leaderboard display
with st.expander("ELO Ratings (leaderboard)", expanded=False):
    ratings_df = (
        pd.DataFrame(
            list(st.session_state["elo_ratings"].items()), columns=["team", "elo"]
        )
        .sort_values(by="elo", ascending=False)
        .reset_index(drop=True)
    )
    st.dataframe(ratings_df)

if matches_count == 0:
    st.warning("No fixtures matched your search. Try a broader team or competition term.")
else:
    for _, row in fixtures_df.iterrows():
        home = row["homeTeam"]["name"]
        away = row["awayTeam"]["name"]
        match_time = format_match_time(row["utcDate"])
        competition_name = row["competition"]["name"]

        with st.expander(f"{home} vs {away} — {competition_name} • {match_time}", expanded=False):
            pred = calculate_prediction(home, away)
            left, right = st.columns([2, 1])

            with left:
                st.markdown(
                    f"**Match details**  \n"
                    f"Competition: {competition_name}  \n"
                    f"Kick-off: {match_time}  \n"
                    f"Selected league: {league_info['name']}"
                )
                st.markdown("**Team confidence**")
                st.progress(pred["home"] / 100, text=f"{home}: {pred['home']}%")
                st.progress(pred["draw"] / 100, text=f"Draw: {pred['draw']}%")
                st.progress(pred["away"] / 100, text=f"{away}: {pred['away']}%")

            with right:
                st.metric(label=home, value=f"{pred['home']}%")
                st.metric(label="Draw", value=f"{pred['draw']}%")
                st.metric(label=away, value=f"{pred['away']}%")
                st.success(pred["recommendation"])

            st.caption(
                "Note: This app is designed for analysis and learning. Always cross-check predictions with official odds and team news."
            )

st.markdown("---")
st.info(
    "**Responsible play:** Use this predictor for insight only. Odds and outcomes cannot be guaranteed."
)

if use_groq_search:
    st.markdown("## GROQ Search")
    if SANITY_PROJECT_ID and SANITY_DATASET and SANITY_API_TOKEN:
        if search_term:
            analytics = fetch_sanity_search(search_term)
            if analytics:
                st.write("### Sanity results")
                st.dataframe(
                    pd.DataFrame(
                        [
                            {
                                "home": item.get("homeTeam", {}).get("name", ""),
                                "away": item.get("awayTeam", {}).get("name", ""),
                                "competition": item.get("competition", {}).get("title", ""),
                                "date": item.get("date", ""),
                            }
                            for item in analytics
                        ]
                    )
                )
            else:
                st.warning("No GROQ results found for the query. Check spelling or dataset contents.")
        else:
            st.info("Enter a search term in the sidebar to query your Sanity dataset.")
    else:
        st.error("Sanity GROQ search requires SANITY_PROJECT_ID, SANITY_DATASET, and SANITY_API_TOKEN.")

st.caption("Version 1.0 — Improved UI, optional live data, and GROQ search support.")
