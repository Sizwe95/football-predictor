import pytest
import pandas as pd
from predictor_core import calculate_prediction, get_live_fixtures


def test_calculate_prediction_basic():
    ratings = {"Home FC": 1600, "Away United": 1500}
    res = calculate_prediction("Home FC", "Away United", ratings)
    assert isinstance(res, dict)
    assert set(res.keys()) == {"home", "draw", "away", "recommendation"}
    total = res["home"] + res["draw"] + res["away"]
    assert pytest.approx(100.0, rel=1e-2) == total
    assert 0 <= res["home"] <= 100
    assert 0 <= res["draw"] <= 100
    assert 0 <= res["away"] <= 100


def test_get_live_fixtures_with_fake_requests():
    class FakeResponse:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    class FakeRequests:
        def get(self, url, params=None, headers=None, timeout=None):
            payload = {
                "matches": [
                    {
                        "id": 1,
                        "homeTeam": {"name": "A Team"},
                        "awayTeam": {"name": "B Team"},
                        "utcDate": "2026-07-07T15:00:00Z",
                        "competition": {"name": "Premier League"},
                    }
                ]
            }
            return FakeResponse(payload)

    fr = FakeRequests()
    df = get_live_fixtures("Premier League", 7, api_key="fakekey", supported_live_leagues={"Premier League": "PL"}, requests_module=fr)
    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["homeTeam"]["name"] == "A Team"


def test_get_live_fixtures_no_key_or_unsupported():
    # No API key
    assert get_live_fixtures("Premier League", 7, api_key=None) is None
    # Unsupported league
    assert get_live_fixtures("Unknown League", 7, api_key="fakekey") is None
