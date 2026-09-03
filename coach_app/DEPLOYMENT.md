# Deployment

## Local

```bash
cd coach_app
python -m venv .venv
# activate the environment
pip install -r requirements.txt
cp .env.example .env
# set GROQ_API_KEY for AI coaching
streamlit run main.py
```

For standalone development, set `AI_GYM_DEMO_AUTH=1`.

## Production

1. Build a clean environment from `requirements.txt`; do not ship `venv/`.
2. Store `GROQ_API_KEY` in the deployment platform's secret manager.
3. Keep `AI_GYM_DEMO_AUTH=0`.
4. Set `AI_GYM_DB_PATH` to a persistent, private database location.
5. Put the application behind HTTPS/TLS.
6. Restrict inbound access to the Streamlit service.
7. Configure security headers and the exact allowed origin at the reverse proxy.
8. Back up `data.db` (or, preferably, use the organization's production database service).
9. Run `pytest -q` and `python -m compileall -q .` before release.
10. Run `pip-audit -r requirements.txt` during CI.

### Local authentication troubleshooting

The Coach loads `.env` from the repository root before evaluating the authentication gate. For local development, use:

```env
AI_GYM_DEMO_AUTH=1
```

Restart Streamlit after changing `.env`. Verify with:

```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); print(os.getenv('AI_GYM_DEMO_AUTH'))"
```

It should print `1`. Do not enable demo authentication in production.
