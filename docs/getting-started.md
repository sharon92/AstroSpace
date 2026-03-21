# Getting Started

This guide matches the current application behavior and deployment flow in this repository.

## Prerequisites

- Python 3.11 or newer
- PostgreSQL
- A writable upload directory
- Optional: Node.js for rebuilding Tailwind CSS
- Optional: Docker for containerized deployment

## Install for Development

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## Configure the Application

AstroSpace loads configuration in this order:

1. environment variables
2. the file pointed to by `ASTROSPACE_SETTINGS`
3. `instance/config.py`

Minimum required settings:

- `SECRET_KEY`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `UPLOAD_PATH`

Example:

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

## Run Locally

```bash
set ASTROSPACE_SETTINGS=path\to\config.py
flask --app AstroSpace run
```

Debug mode:

```bash
flask --app AstroSpace run --debug
```

You can also enable logging without the Flask debug reloader:

```bash
set ASTROSPACE_DEBUG=1
flask --app AstroSpace run
```

## Run with Docker

Build:

```bash
docker build -t astrospace .
```

Run:

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

Enable container debug logging:

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

## Run Tests

```bash
python -m pytest -q
```

## Rebuild Tailwind Assets

```bash
cd AstroSpace
npm install
npx tailwindcss -i ./static/input.css -o ./static/styles.css
```

## First Steps After Boot

1. Register the first user account.
2. Configure the site name and welcome message from `My Profile`.
3. Create a first post to verify uploads, database writes, and thumbnail generation.
4. Enable debug logging if you need deeper startup or request traces.
