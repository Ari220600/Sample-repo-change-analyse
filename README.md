# TaskFlow v2

Same app as v1 with **exactly 7 breaking changes**. The `tests/` folder is an unchanged copy from v1.

## 7 Changes from v1

| # | v1 | v2 |
|---|----|----|
| 1 | API prefix `/api/v1` | `/api/v2` |
| 2 | Resource `/tasks` | `/items` |
| 3 | Profile `GET /users/me` | `GET /auth/me` |
| 4 | Stats keys `pending`, `completed` | `open`, `done` |
| 5 | `DELETE /tasks/{id}` | `POST /items/{id}/archive` |
| 6 | `PUT /tasks/{id}` | `PATCH /items/{id}` |
| 7 | Statuses `pending`, `completed`, … | `open`, `done` only |

## Run

```bash
cd backend && uvicorn app.main:app --reload --port 8001
cd frontend && npm install && npm run dev   # port 5174
```
