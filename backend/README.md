# HooThatShow Backend

## Setup

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install
```

## Environment

Required env vars:
- `SECRET_KEY`
- `DATABASE_URL`
- `SERPAPI_KEY`
- `QWEN_SERVICE_PORT`
- `FRONTEND_BASE_URL`

Optional:
- `LLM_SERVICE_URL` (defaults to `http://localhost:${QWEN_SERVICE_PORT}`)

## Run

```
python manage.py migrate
python manage.py runserver
```

Start RQ worker:

```
python manage.py rqworker default
```

On Windows, set `ENABLE_RQ=0` to run jobs synchronously or run the worker inside WSL/Linux.

## API
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/analyze`
- `GET /api/v1/analyze/{id}`
- `GET /api/v1/history`
