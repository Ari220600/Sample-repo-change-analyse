# TaskFlow v1

Minimal React + FastAPI task manager.

## Run

```bash
# Backend
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload

# Frontend
cd frontend && npm install && npm run dev

# Tests
cd backend && python -m pytest --cov=app --cov-report=term-missing
cd frontend && npm test
```

## API

- `POST /api/v1/auth/register` · `POST /api/v1/auth/login`
- `GET /api/v1/users/me`
- `GET/POST /api/v1/tasks` · `GET/PUT/DELETE /api/v1/tasks/{id}` · `GET /api/v1/tasks/stats`
