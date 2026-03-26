# AstroSpace

AstroSpace is a Flask application for hosting and organizing astrophotography posts on your own infrastructure. It combines image publishing, equipment tracking, plate-solving overlays, and guiding-log visualization in one self-hosted site.

You can see a public instance here: [astro.space-js.de](https://astro.space-js.de/)

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

## Docker

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
