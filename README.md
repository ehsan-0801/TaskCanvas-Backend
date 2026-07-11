# TaskCanvas — Backend

Django + Django REST Framework API for TaskCanvas: JWT auth, a date-filtered
Kanban task board, and an image-annotation service (image upload + polygon
storage).

Frontend repo: https://github.com/ehsan-0801/TaskCanvas-Frontend

---

## Tech stack

- **Python 3.14** (developed on 3.14.5)
- **Django 6.0** + **Django REST Framework**
- **djangorestframework-simplejwt** — JWT access/refresh auth
- **PostgreSQL** in production (Neon), **SQLite** as the zero-config dev default
- **Cloudinary** for annotation image storage — all uploaded images are stored on
  Cloudinary. Local `/media` is used only as a dev convenience when no credentials
  are set; **in production Cloudinary is required** (the app refuses to start
  without it, so images are never written to ephemeral local disk)
- **gunicorn** for production serving

---

## Setup & run (local)

### 1. Create and activate a virtual environment

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

Copy the example env file and fill in values:

```bash
cp .env.example .env
```

`.env` keys:

| Key | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local dev, `False` in production |
| `ALLOWED_HOSTS` | Comma-separated hosts |
| `CORS_ALLOWED_ORIGINS` | Comma-separated extra frontend origins (e.g. the deployed URL). `localhost:3000` is always allowed. |
| `DATABASE_URL` | `dj-database-url` format. Omit to use local SQLite. |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | Image storage. Leave blank to store uploads in local `/media`. |
| `CLOUDINARY_FOLDER` | Folder prefix for uploaded assets |

> With no `DATABASE_URL` and no Cloudinary keys, the app runs fully on SQLite +
> local media — no external services required.

### 4. Migrate and seed a demo user

```bash
python manage.py migrate
python seed_demo_data.py          # creates demo@example.com / demo12345 with sample tasks
```

### 5. Run the server

```bash
python manage.py runserver        # http://127.0.0.1:8000
```

Or use the helper script (runs the server; pass `--migrate` to migrate first):

```bash
./run.sh                          # start on :8000
./run.sh --migrate                # migrate, then start
./run.sh 8080                     # custom port
```

**Demo credentials:** `demo@example.com` / `demo12345`

---

## Tests

```bash
python manage.py test
```

The suite (33 tests across `auth_app`, `tasks`, `annotation`) covers email JWT
login/refresh, task CRUD + date filtering + drag-drop `reorder`, tag scoping,
image upload with Pillow dimension extraction, polygon CRUD/label editing, and
per-user isolation (a user never sees or mutates another user's data → 404).
Tests always run on an isolated in-memory SQLite database, never the configured
`DATABASE_URL`.

---

## API overview

All endpoints except `/api/auth/*` require `Authorization: Bearer <access>`.
Every queryset is scoped to the authenticated user.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/auth/login/` | `{ email, password }` → `{ access, refresh }` |
| POST | `/api/auth/refresh/` | `{ refresh }` → `{ access }` |
| GET/POST | `/api/tasks/?date=YYYY-MM-DD` | List (date-filtered) / create tasks |
| PATCH/DELETE | `/api/tasks/:id/` | Edit / delete a task |
| POST | `/api/tasks/reorder/` | Batch status+order update after drag-drop |
| GET/POST | `/api/tasks/tags/` | List / create tags |
| GET/POST | `/api/images/` | List / upload (multipart `file`) images |
| DELETE | `/api/images/:id/` | Delete image (cascades to its polygons) |
| GET/POST | `/api/images/:id/polygons/` | List / create polygons for an image |
| PATCH/DELETE | `/api/images/polygons/:id/` | Edit / delete a polygon |

---

## Deployment notes

- Set `DEBUG=False`, a real `SECRET_KEY`, and production `ALLOWED_HOSTS`.
- Set `CORS_ALLOWED_ORIGINS` to the deployed frontend origin (comma-separated for
  more than one) — no code change needed.
- Provide a persistent `DATABASE_URL` (e.g. Neon/Railway Postgres) and Cloudinary
  credentials so uploaded media survives restarts.
- Run `python manage.py collectstatic --noinput` — static assets (admin/DRF) are
  served by WhiteNoise.
- Serve with gunicorn: `gunicorn config.wsgi`.

---

## Difficulties faced and how solved

- **Image dimensions were lost after upload.** Once a file is handed to the
  Cloudinary storage backend its stream is consumed, so reading `Image.open()`
  afterwards returned zero size. **Fix:** read width/height with Pillow *before*
  saving, seeking the stream back to 0 in a `finally` block
  (`annotation/serializers.py`).

- **Polygon detail routes (PATCH/DELETE) 404'd.** The polygon queryset filtered
  on `image_id`, but the detail routes (`/images/polygons/:id/`) don't carry an
  `image_id` in the URL, so the filter excluded every row. **Fix:** always scope
  by `image__user` and only add the `image_id` filter when it's present in the
  URL kwargs (`annotation/views.py`).

- **Login is by email, but Django's default auth is username-based.** **Fix:** a
  custom `EmailTokenObtainPairSerializer` that authenticates on the email field
  while still issuing standard simplejwt tokens (`auth_app/`).

- **Drag-and-drop produced many small writes.** Moving a card can change several
  tasks' `status`/`order` at once. **Fix:** a single `reorder` action that
  applies all updates inside one `transaction.atomic()` block, updating only the
  `status` and `order` fields.

- **Wanted the app to run with zero external services for reviewers.** **Fix:**
  `DATABASE_URL` defaults to SQLite via `dj-database-url`, and media storage
  only switches to Cloudinary when credentials are present — otherwise it uses
  local `/media`.
