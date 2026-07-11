# TaskCanvas — Backend

This is the API that TaskCanvas runs on. It's a plain Django + DRF project that
handles three things: signing people in, running the team task boards, and
storing image annotations. Everything is JSON over HTTP — the only rendered pages
are the Django admin. The Next.js frontend does the rest.

Live API: https://taskcanvas-backend-lgo8.onrender.com
Live app: https://task-canvas-annotate.vercel.app

Frontend repo: https://github.com/ehsan-0801/TaskCanvas-Frontend

## How the data is shaped

Most of the code falls out of a fairly small model, so it's worth reading this
first:

- A **Team** belongs to one person, the owner.
- A team has as many **Boards** as you want — these are the Kanban boards.
- A board holds **Tasks**, each with a status (To Do / In Progress / Done), a due
  date, a priority and some tags.
- The owner adds people to the team by email and password, then hands out access
  to individual boards. A member only ever sees the boards they've been given, and
  only the owner can create boards or manage members.

There's also an annotation tool bolted on the side: you upload images and draw
polygons on them. That part is still scoped per user rather than per team — it
predates the teams work and I left it as-is.

Auth is email + password. Django keys users on `username` by default, so under the
hood the email doubles as the username and a small custom serializer looks people
up by email when they log in.

## What it's built with

Python 3.14 and Django 6 with Django REST Framework. JWTs come from
`djangorestframework-simplejwt`. In production it talks to Postgres (I'm using
Neon) through `dj-database-url`, but with no database URL set it happily falls
back to SQLite so you can clone and run it with nothing else installed. Uploaded
images go to Cloudinary; static files are served by WhiteNoise under gunicorn.

## Running it locally

You need Python 3.12 or newer.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in what you need, or leave it for SQLite
python manage.py migrate
python seed_demo_data.py           # optional: sample teams, boards and tasks
python manage.py runserver         # http://127.0.0.1:8000
```

There's also a `run.sh` if you'd rather: `./run.sh` starts the server, `./run.sh
--migrate` migrates first, and `./run.sh 8080` picks a port.

If you leave `DATABASE_URL` and the Cloudinary keys blank, everything runs on
SQLite and local `/media` with no external services.

### The environment file

| Key | What it's for |
|---|---|
| `SECRET_KEY` | Django's secret key. Generate a real one for production. |
| `DEBUG` | `True` locally, `False` in production. |
| `ALLOWED_HOSTS` | Comma-separated hostnames. **No scheme** — `example.com`, not `https://example.com`. |
| `CORS_ALLOWED_ORIGINS` | Comma-separated frontend origins, **with** scheme, e.g. `https://app.vercel.app`. localhost:3000 is always allowed. |
| `DATABASE_URL` | Standard `dj-database-url` string. Leave it out for SQLite. |
| `CLOUDINARY_CLOUD_NAME` / `CLOUDINARY_API_KEY` / `CLOUDINARY_API_SECRET` | Image storage. Blank means uploads go to local `/media`. |
| `CLOUDINARY_FOLDER` | Folder prefix for uploaded assets. |

The seed script creates two owners, four members each, two teams per owner, and a
full month of To Do tasks on every board. It prints the logins when it finishes —
the main one is `demo@example.com` / `demo12345`.

## Tests

```bash
python manage.py test
```

47 tests across the four apps. They cover the email login and refresh flow, task
CRUD with date filtering and the drag-drop reorder, tag scoping, the annotation
upload (including reading image dimensions with Pillow) and polygon editing, and —
the part I cared most about — the access rules: a member can't see or touch a board
they weren't granted, and a non-owner can't create boards or add people. The tests
always run against a throwaway in-memory SQLite database, never whatever
`DATABASE_URL` points at, so you can't accidentally wipe real data by running them.

## The API in one table

Everything except `/api/auth/*` needs an `Authorization: Bearer <token>` header,
and every query is scoped to what the caller is allowed to see. Lists are
paginated (`{count, next, previous, results}`).

| Method | Endpoint | What it does |
|---|---|---|
| POST | `/api/auth/register/` | Sign up as a new owner, get a token pair back |
| POST | `/api/auth/login/` | `{email, password}` to `{access, refresh}` |
| POST | `/api/auth/refresh/` | `{refresh}` to a new `{access}` |
| GET/POST | `/api/teams/` | List your teams / create one (you become owner) |
| DELETE | `/api/teams/:id/` | Delete a team (owner only) |
| GET/POST | `/api/teams/:id/members/` | List members / add one by email + password |
| DELETE | `/api/teams/:id/members/:userId/` | Remove a member |
| GET/POST | `/api/boards/?team=:id` | List boards you can see / create one (owner only) |
| DELETE | `/api/boards/:id/` | Delete a board (owner only) |
| GET/POST | `/api/boards/:id/access/` | List / grant a member access to the board |
| DELETE | `/api/boards/:id/access/:userId/` | Revoke a member's access |
| GET/POST | `/api/tags/?team=:id` | List / create team tags |
| GET/POST | `/api/tasks/?board=:id&date=YYYY-MM-DD` | List (board + date) / create tasks |
| PATCH/DELETE | `/api/tasks/:id/` | Edit / delete a task |
| POST | `/api/tasks/reorder/` | Apply a batch of status/order changes after a drag |
| GET/POST | `/api/images/` | List / upload (multipart `file`) images |
| DELETE | `/api/images/:id/` | Delete an image and its polygons |
| GET/POST | `/api/images/:id/polygons/` | List / create polygons on an image |
| PATCH/DELETE | `/api/images/polygons/:id/` | Edit / delete a polygon |

## Deploying

Set `DEBUG=False`, a fresh `SECRET_KEY`, real `ALLOWED_HOSTS`, and point
`CORS_ALLOWED_ORIGINS` at the deployed frontend. Give it a Postgres `DATABASE_URL`
and Cloudinary credentials so data and uploads survive restarts. Run
`collectstatic` (WhiteNoise serves the result) and start it with
`gunicorn config.wsgi --bind 0.0.0.0:$PORT`. On production the app deliberately
refuses to boot without Cloudinary configured, so images can never end up on a
disk that gets wiped on the next deploy.

## Difficulties faced and how I solved them

Deploying was where most of the sharp edges were, honestly.

The first one cost me an embarrassing amount of time: the live site returned a
bare `400` on every single request, even the root. It turned out I'd put
`https://` in front of the host in `ALLOWED_HOSTS`. Django wants a bare hostname
there. To make it worse, `CORS_ALLOWED_ORIGINS` wants the exact opposite — a full
origin *with* the scheme. So the two settings that look similar need opposite
formats, and I now call that out in the env table above.

Migrating the teams change onto Postgres was the other one. The migration clears
the old tasks and then adds a non-null `board` column to the same table, and
Postgres refused with "cannot ALTER TABLE because it has pending trigger events" —
you can't delete rows and alter the same table inside one transaction. Marking the
migration `atomic = False` lets the delete commit before the ALTER runs, which
sorts it out.

A couple of smaller ones. Login is by email but Django authenticates on username,
so there's a custom token serializer that looks the user up by email and still
issues normal SimpleJWT tokens. Reading an uploaded image's dimensions had to
happen *before* handing the file to Cloudinary, because the storage backend
consumes the stream — so Pillow reads the size first and seeks back to the start.
And a single drag can move several cards at once, so instead of a request per card
there's one `reorder` endpoint that applies the whole batch in one transaction.
