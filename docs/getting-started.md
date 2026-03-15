# Getting Started

## Prerequisites

- Python 3.11+
- PostgreSQL
- Optional: Node.js if you want to rebuild Tailwind assets

## Install

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e .[dev]
```

## Configure

Set `ASTROSPACE_SETTINGS` to a Python config file that defines:

- `SECRET_KEY`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`
- `UPLOAD_PATH`
- `TITLE`
- `MAX_USERS`

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

## Run the App

```bash
set ASTROSPACE_SETTINGS=path\to\config.py
flask --app AstroSpace run
```

The application will start on `http://127.0.0.1:5000` by default.

## Run Tests

```bash
pytest
```

## Optional Frontend Build

If you change Tailwind source files:

```bash
cd AstroSpace
npm install
npx tailwindcss -i ./static/input.css -o ./static/styles.css
```

## First Steps After Boot

1. Register the first user.
2. Open `My Profile` to set the site name and welcome note.
3. Create an image post from `New Post`.
4. Upload guiding logs again for older posts if you want the new Plotly graphs instead of legacy plot placeholders.
