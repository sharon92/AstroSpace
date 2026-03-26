# AstroSpace

AstroSpace is a Flask application for hosting and organizing astrophotography posts on your own infrastructure. It combines image publishing, equipment tracking, plate-solving overlays, and guiding-log visualization in one self-hosted site.

You can see a public instance here: [astro.space-js.de](https://astro.space-js.de/)

## Preferred Docker Deployment

The preferred way to run AstroSpace in production is with `nginx/docker-compose.yml`. That stack starts:

- `astrospace_app`: the published AstroSpace image, which runs Gunicorn on internal port `9000`
- `astrospace_nginx`: the public entrypoint, which listens on port `8181`, serves static/uploaded files directly, and proxies app requests to `astrospace_app`

PostgreSQL is intentionally not included in this compose file. AstroSpace expects an existing database server, and you provide its connection details through environment variables.

### How Compose Settings Work

`nginx/docker-compose.yml` uses `${...}` placeholders for runtime settings. The simplest setup is:

1. `cd nginx`
2. create a `.env` file next to `docker-compose.yml`
3. run `docker compose ...` from that `nginx/` directory

Example `nginx/.env`:

```env
SECRET_KEY=change-me
DB_NAME=astrospace
DB_USER=astrospace
DB_PASSWORD=change-me
DB_HOST=192.168.1.20
DB_PORT=5432
TITLE=AstroSpace
MAX_USERS=2
```

What each setting is for:

- `SECRET_KEY`: Flask session and CSRF signing key. Set this to a long random value.
- `DB_NAME`: PostgreSQL database name AstroSpace should use.
- `DB_USER`: PostgreSQL username.
- `DB_PASSWORD`: PostgreSQL password.
- `DB_HOST`: hostname or IP address of your PostgreSQL server. This is usually another machine or another container stack.
- `DB_PORT`: PostgreSQL port, usually `5432`.
- `TITLE`: site title shown in the UI.
- `MAX_USERS`: maximum allowed registered users.

`UPLOAD_PATH` is already fixed inside the compose file as `/uploads`. That path must match the mounted uploads volume, so you normally do not override it in `.env`.

### Volume Mounts And Purpose

The bind mounts in `nginx/docker-compose.yml` are important because both the app and nginx need access to specific files on the host:

- `/mnt/user/AstroSpaceUploads:/uploads`
  This is the persistent data directory for uploaded preview images, thumbnails, FITS/XISF files, generated overlays, starless variants, and other user media. This path must survive container recreation.
- `/mnt/user/Astro/_web_/AstroSpace/AstroSpace/static:/static`
  This exposes AstroSpace static assets to nginx so `/static/...` can be served directly instead of going through Flask. Keep this host directory in sync with the AstroSpace version you deploy.
- `/mnt/user/Astro/_web_/AstroSpace/nginx/nginx.conf:/etc/nginx/nginx.conf:ro`
  This mounts the nginx configuration file into the nginx container as read-only.

Before first start, edit the host-side paths in `nginx/docker-compose.yml` so they match your machine. The left side of each mount is your host path; the right side is the fixed path used inside the container.

### What `nginx.conf` Does

`nginx/nginx.conf` is the reverse-proxy layer in front of AstroSpace:

- listens on port `8181`
- serves `/uploads/` directly from the mounted uploads folder
- serves `/static/` directly from the mounted static folder
- proxies all other requests to `http://astrospace_app:9000/`
- forwards the original `Host` header and visitor IP via `X-Real-IP`
- raises `client_max_body_size` to `2000M` so large astrophotography uploads are accepted
- increases proxy/read/send timeouts so long-running requests are less likely to be cut off early

In short: nginx handles public HTTP traffic and file serving, while the AstroSpace app container focuses on Flask/Gunicorn.

### Commands To Run

Use these commands from `nginx/`:

```bash
docker compose pull
docker compose run --rm astrospace_app migrate
docker compose up -d
```

What each command does:

- `docker compose pull`
  Downloads the image versions referenced by the compose file.
- `docker compose run --rm astrospace_app migrate`
  Runs Alembic migrations before the web stack starts. On compatible older AstroSpace databases, this also auto-stamps the legacy schema before applying newer revisions.
- `docker compose up -d`
  Starts the app and nginx containers in the background.

Useful follow-up commands:

```bash
docker compose logs -f astrospace_app astrospace_nginx
docker compose down
```

After startup, open `http://YOUR_HOST:8181`.

For updates, the normal sequence is the same:

```bash
docker compose pull
docker compose run --rm astrospace_app migrate
docker compose up -d
```

If you prefer to pin a specific image version instead of `latest`, change the `image:` line in `nginx/docker-compose.yml` to a concrete tag such as `sharonshaji92/astrospace:1.3.4`.

## Features

- User registration with a configurable user limit
- Rich post creation for astrophotography images and acquisition details
- Equipment inventory management for telescopes, cameras, filters, and accessories
- FITS/XISF-assisted plate solving and generated overlays
- PHD2 guiding log parsing and Plotly-based visualizations
- Public collection pages and per-image detail views
- Docker-friendly deployment
- Optional opt-in debug logging for local development and container runs

## Requirements

- Python 3.11+
- PostgreSQL
- Optional: Node.js if you want to rebuild Tailwind CSS assets
- Optional: Docker for containerized deployment

## Quick Start

### Local install

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

### Configuration

AstroSpace reads configuration from:

1. environment variables
2. the file pointed to by `ASTROSPACE_SETTINGS`
3. `instance/config.py`

Required settings:

- `SECRET_KEY`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `UPLOAD_PATH`

Common optional settings:

- `TITLE`
- `MAX_USERS`
- `SESSION_COOKIE_SECURE`

Example config file:

```python
SECRET_KEY = "change-me"
DB_NAME = "astrospace"
DB_USER = "astrospace"
DB_PASSWORD = "change-me"
DB_HOST = "localhost"
DB_PORT = 5432
UPLOAD_PATH = r"C:\astrospace\uploads"
TITLE = "My AstroSpace"
MAX_USERS = 2
```

### Run locally

Run migrations first:

```bash
python -m AstroSpace migrate
```

```bash
set ASTROSPACE_SETTINGS=path\to\config.py
flask --app AstroSpace run
```

The app starts on `http://127.0.0.1:5000` by default.

If you are upgrading an existing pre-Alembic AstroSpace database, this is usually enough:

```bash
python -m AstroSpace migrate
```

`migrate` will auto-stamp a compatible legacy AstroSpace schema before applying newer revisions. The explicit stamp command is still available if you want to control that step yourself:

```bash
python -m AstroSpace stamp
python -m AstroSpace migrate
```

## Debug Logging

AstroSpace includes opt-in runtime logging around the places most likely to block or fail: app startup, database bootstrapping, post creation, inventory updates, plate solving, and guide-log parsing.

Enable it in either of these ways:

```bash
flask --app AstroSpace run --debug
```

```bash
set ASTROSPACE_DEBUG=1
flask --app AstroSpace run
```

For the Docker image, append `--debug` to the container command or set `ASTROSPACE_DEBUG=1`.

## Manual Docker

Build the image locally:

```bash
docker build -t astrospace .
```

Run it:

```bash
docker run --rm ^
  -e SECRET_KEY=change-me ^
  -e DB_NAME=astrospace ^
  -e DB_USER=astrospace ^
  -e DB_PASSWORD=change-me ^
  -e DB_HOST=host.docker.internal ^
  -e DB_PORT=5432 ^
  -e UPLOAD_PATH=/uploads ^
  -v C:\astrospace\uploads:/uploads ^
  astrospace migrate
```

Then start the web container:

```bash
docker run ^
  --name astrospace ^
  -p 9000:9000 ^
  -e SECRET_KEY=change-me ^
  -e DB_NAME=astrospace ^
  -e DB_USER=astrospace ^
  -e DB_PASSWORD=change-me ^
  -e DB_HOST=host.docker.internal ^
  -e DB_PORT=5432 ^
  -e TITLE=AstroSpace ^
  -e MAX_USERS=2 ^
  -e UPLOAD_PATH=/uploads ^
  -v C:\astrospace\uploads:/uploads ^
  astrospace
```

Run the same container in debug mode:

```bash
docker run ^
  --name astrospace-debug ^
  -p 9000:9000 ^
  -e SECRET_KEY=change-me ^
  -e DB_NAME=astrospace ^
  -e DB_USER=astrospace ^
  -e DB_PASSWORD=change-me ^
  -e DB_HOST=host.docker.internal ^
  -e DB_PORT=5432 ^
  -e TITLE=AstroSpace ^
  -e MAX_USERS=2 ^
  -e UPLOAD_PATH=/uploads ^
  -e ASTROSPACE_DEBUG=1 ^
  -v C:\astrospace\uploads:/uploads ^
  astrospace --debug
```

The image starts Gunicorn on `0.0.0.0:9000`.

## Development

Run the test suite:

```bash
python -m pytest -q
```

If you update Tailwind sources:

```bash
cd AstroSpace
npm install
npx tailwindcss -i ./static/input.css -o ./static/styles.css
```

Useful first-run steps:

1. Register the first user. The first account becomes admin.
2. Open `My Profile` and configure the site title and welcome message.
3. Create a new post with a preview image and optional FITS/XISF metadata.
4. Add or normalize inventory entries from the profile page if needed.

## Release Workflow

Build and publish a wheel with Hatch:

```bash
python -m pip install hatch
python -m hatch build -t wheel
python -m hatch publish
```

## Project Layout

- `AstroSpace/`: application package
- `docs/`: project documentation
- `tests/`: automated tests
- `nginx/`: example reverse-proxy and compose assets

## License

This project is licensed under the GNU GPL-3.0 License.
