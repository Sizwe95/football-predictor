# football-predictor
# Amapanta Predictor

A lightweight Streamlit app for football fixture forecasts with optional live data and Sanity GROQ search support.

[![codecov](https://codecov.io/gh/Sizwe95/football-predictor/branch/main/graph/badge.svg)](https://codecov.io/gh/Sizwe95/football-predictor)

## Quickstart

1. Create and activate a Python virtual environment (recommended):

```bash
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in any API keys you want to use:

```bash
copy .env.example .env
# then edit .env with your keys
```

- `FOOTBALL_DATA_API_KEY` (optional): API key for football-data.org (used for PL/CL live fixtures)
- `SANITY_PROJECT_ID`, `SANITY_DATASET`, `SANITY_API_TOKEN` (optional): for GROQ dataset searches

4. Run the app:

```bash
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

## Notes
- The app falls back to simulated fixtures when live lookups fail or no API key is provided.
- Keep secrets out of source control; use environment variables or a secrets manager for production.

## Next steps
- Add Dockerfile and CI pipeline.
- Harden live API calls (retry/backoff) and add caching for fixtures.

## Coverage

- CI uploads coverage to Codecov. To enable uploads for private repositories, add a `CODECOV_TOKEN` secret in your repository settings.
- Replace the badge in this README with your repository's Codecov badge URL. Example badge (replace `OWNER/REPO` and `REPLACE_TOKEN`):

```
// Public repo badge example (no token required):
[![codecov](https://codecov.io/gh/Sizwe95/football-predictor/branch/main/graph/badge.svg)](https://codecov.io/gh/Sizwe95/football-predictor)
```

For private repositories, add a `CODECOV_TOKEN` secret in your repository settings and the CI will use it to upload coverage reports.

If you prefer a different coverage reporter (e.g., Coveralls), update the CI workflow accordingly.
