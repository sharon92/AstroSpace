# AstroSpace architecture

## Purpose and stack

AstroSpace is a self-hosted Flask application for publishing astrophotography, acquisition metadata, equipment, plate-solving overlays, and PHD2 visualisations. It uses PostgreSQL through `psycopg2`, Flask-Login for authenticated areas, Flask-WTF/CSRF protection, Alembic migrations, Tailwind CSS, and browser-side JavaScript.

## Repository map

| Path | Responsibility |
| --- | --- |
| `AstroSpace/__init__.py` | Flask application factory and blueprint registration. |
| `AstroSpace/blog.py` | Public pages, image create/edit routes, image detail, uploads, likes, and comments. |
| `AstroSpace/profile/` | Public and authenticated profile/admin routes. |
| `AstroSpace/services/` | Business rules: uploads, engagement, cookies, authorisation, filters, content parsing. |
| `AstroSpace/repositories/images.py` | Image-reading queries used by public views. |
| `AstroSpace/templates/` | Jinja pages. `base.html` owns the site shell; `image_detail.html` owns the public viewer. |
| `AstroSpace/static/` | Tailwind source/compiled CSS, browser modules, local fonts, and image assets. |
| `AstroSpace/migrations/` | Alembic schema migrations. |
| `tests/` | Route, migration, upload, browser-asset, and image-navigation regression tests. |
| `nginx/` | Production nginx configuration and Docker Compose deployment. |

## Request flow

1. A blueprint route in `blog.py`, `auth.py`, or `profile/` receives the request.
2. Routes use service/repository helpers and `db.get_conn()` to assemble data.
3. A Jinja template renders the response. `base.html` provides navigation, theme/cookie behaviour, CSRF metadata, and the footer.
4. Nginx serves `/static/` and `/uploads/` directly in the Docker deployment; Flask handles application routes.

## Data and media

The `images` table stores the primary preview path and metadata. `get_image_tables()` in `AstroSpace/utils/queries.py` (or its imported public helper) combines an image with equipment, capture dates, lights, software, plate-solve overlay data, optional PHD2 plot payloads, FITS/XISF metadata, and related media. Upload paths are stored relative to `UPLOAD_PATH` and are exposed through the `blog.upload` route in development or nginx in production.

The image-detail route also records a visitor view and obtains an engagement state. Likes and anonymous comments are separate POST endpoints. Cookie consent determines whether preference/community cookies may be used.

## Styling and frontend conventions

- Tailwind v4 scans `templates/` and `static/` from `AstroSpace/tailwind.config.js`.
- Edit `AstroSpace/static/input.css`, then rebuild `AstroSpace/static/styles.css` with `npx @tailwindcss/cli -i ./static/input.css -o ./static/styles.css` from `AstroSpace/`.
- Existing browser modules live in `static/js/`; avoid moving a dependency to a CDN if it can be loaded only on demand.
- `consent.js` is the only supported persistence layer for optional preferences. Do not introduce raw `localStorage` access in templates.

## Verification

Use Python 3.12 in this workspace when available. The normal checks are:

```powershell
py -3.12 -m pytest -q
py -3.12 -m flask --app AstroSpace run --debug --host=0.0.0.0
```

The running development server is useful for checking a representative image that has overlays, related media, metadata, and plot payloads. Do not assume every image has every optional field.
