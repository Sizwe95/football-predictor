import sys
from predictor_core import calculate_prediction, get_live_fixtures

failures = 0

print('Running lightweight tests...')

try:
    ratings = {"Home FC": 1600, "Away United": 1500}
    res = calculate_prediction("Home FC", "Away United", ratings)
    assert isinstance(res, dict)
    assert set(res.keys()) == {"home", "draw", "away", "recommendation"}
    total = res["home"] + res["draw"] + res["away"]
    assert abs(total - 100.0) < 1e-6
    assert 0 <= res["home"] <= 100
    assert 0 <= res["draw"] <= 100
    assert 0 <= res["away"] <= 100
    print('test_calculate_prediction_basic: PASS')
except AssertionError as e:
    print('test_calculate_prediction_basic: FAIL')
    failures += 1

try:
    out = get_live_fixtures("Premier League", 7, api_key=None)
    assert out is None
    print('test_get_live_fixtures_no_key: PASS')
except AssertionError:
    print('test_get_live_fixtures_no_key: FAIL')
    failures += 1

try:
    out = get_live_fixtures("Some Unknown League", 7, api_key="fakekey")
    assert out is None
    out2 = get_live_fixtures("Premier League", 7, api_key="fakekey")
    assert out2 is None
    print('test_get_live_fixtures_unsupported_or_no_requests: PASS')
except AssertionError:
    print('test_get_live_fixtures_unsupported_or_no_requests: FAIL')
    failures += 1

if failures:
    print(f"{failures} tests failed")
    sys.exit(1)
else:
    print('All lightweight tests passed')
    sys.exit(0)
