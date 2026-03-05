# Deployment Notes

## Frontend (Vercel / Netlify)
- Build command: `flutter build web`
- Output folder: `frontend/build/web`
- Set `API_BASE_URL` to your backend URL.

## Backend (Render / Railway / VPS)
- Set env vars: `DATABASE_URL`, `SECRET_KEY`, `SERPAPI_KEY`, `FRONTEND_BASE_URL`, `ALLOWED_HOSTS`
- Run migrations: `python manage.py migrate`
- Start worker on Linux: `python manage.py rqworker default`
- Windows dev: set `ENABLE_RQ=0` to run jobs inline.

## LLM Service
- Run on the GPU host only.
- Export `MODEL_PATH` and `QWEN_SERVICE_PORT`
- Start: `uvicorn app:app --host 0.0.0.0 --port 8001`
