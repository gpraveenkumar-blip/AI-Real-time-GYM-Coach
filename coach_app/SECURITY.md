# AI-GYM Coach Security Notes

## Production requirements

- Authenticate users in the SaaS portal before establishing `saas_user_id`.
- Do not trust URL parameters as identity.
- Keep `GROQ_API_KEY` server-side in the platform secret manager.
- Keep `AI_GYM_DEMO_AUTH=0` in production.
- Use HTTPS/TLS at the reverse proxy.
- Restrict CORS to the exact frontend origin when a separate frontend is used.
- Configure CSP/HSTS/security headers at the reverse proxy.
- Back up the production database and test restoration.
- Do not log camera frames, raw health data, API keys, prompts containing personal data, or provider response payloads.
- Review and rotate credentials if they were ever committed to source control.

## Local development

Set `AI_GYM_DEMO_AUTH=1` only on a developer machine. This bypass exists solely
to make the standalone Streamlit application usable without the SaaS portal.

## AI isolation

User speech and workout metrics are treated as untrusted data. The model is
not an authorization mechanism and must never be given secrets or unrestricted
tools.

\n### Signed coach SSO handoff

The account portal may open the coach with a short-lived signed handoff containing
`coach_user_id`, `coach_username`, `coach_exp`, and `coach_sig`. The signature is
HMAC-SHA256 over:

`coach_user_id:coach_username:coach_exp`

The shared `AI_GYM_SSO_SECRET` must exist only on trusted server-side systems.
The coach rejects unsigned, expired, malformed, or long-lived handoffs and clears
the query parameters after successful validation. Never put the signing secret
in frontend JavaScript or in a URL.
