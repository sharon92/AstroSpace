# Image detail page: contract and performance guide

## Ownership

- Route: `AstroSpace/blog.py` — `image_detail(image_id, image_name)`.
- Template: `AstroSpace/templates/image_detail.html`.
- Viewer helpers: `static/js/plotHR.js`, `static/js/subFramePlot.js`, and `static/js/phd2Plotly.js`.
- Styles: `static/input.css` and generated `static/styles.css`.
- Regression tests: `tests/test_image_detail_navigation.py`, `tests/test_browser_assets.py`, and `tests/test_cookie_engagement.py`.

## Page contract

The route passes a list named `images`. Each entry is constructed from `IMAGE_DETAIL_TABLE_NAMES` and includes:

| Key | Meaning |
| --- | --- |
| `image` | Primary post: title, author, description, date, image path, optional starless image, location, and plate scale. |
| `equipment_list`, `lights`, `dates`, `software_list` | Capture and processing information displayed in Details. |
| `svg_image` | Plate-solving dimensions, labelled objects, and grid lines. |
| `meta_json` | FITS/XISF metadata. Its `variable` values can be very large. |
| `related_media` | Ordered image/video carousel entries with a caption and media kind. |
| `guiding_plot`, `calibration_plot` | Optional PHD2 data for Explore. |
| `engagement` | Viewer-specific `liked`, counts, and comments. |

The route also supplies `previous_post`/`next_post` for keyboard and visible navigation, the remembered anonymous commenter name, and preference-cookie consent state.

## Behaviours to preserve

- Image pan/zoom, reset, fullscreen, object labels, coordinate grid, Moon scale comparison, starless switch, and related media carousel.
- Anonymous likes and comments, including CSRF handling, rate-limit messages, and optional remembered name.
- Previous/next post links plus left/right keyboard navigation.
- Copy-link and copy-link-with-details actions.
- Responsive Details tables and optional HR, metadata, guiding, and calibration views.
- No raw `localStorage`; optional tab preferences go through `window.AstroSpaceConsent`.

## Known performance constraints

The historic implementation renders the full Explore payload in inline script tags and eagerly loads Plotly, Panzoom, and Alpine. A representative image page measured roughly 4.4 MB of HTML before its main image is decoded. Full-page blurred image backdrops add extra paint/compositing work.

For all future work:

1. Keep the initial response to the primary image, concise metadata, and engagement state.
2. Fetch plate-solve/plot/large frame metadata only when an overlay or Explore view is opened.
3. Load Plotly only alongside that request; never block the image viewer on charting code.
4. Use a plain dark/gradient viewing canvas, not a blurred duplicate of the image.
5. Avoid deep parent cards. On desktop, use a wide viewing stage with a compact inspector; stack it naturally on phones.
6. Do not load or initialise hidden Plotly plots. Initialise once and resize after their panel becomes visible.

## Target interaction hierarchy

1. Title, date, and direct return to the collection.
2. Primary image and media navigation.
3. Clear, always-available image controls and a small author/action inspector.
4. Description and comments.
5. Details and Explore as explicit progressive sections.

This is inspired by the focus and navigation clarity of astrophotography galleries, but should remain an original AstroSpace interface.
