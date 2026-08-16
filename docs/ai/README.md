# AI maintenance notes

This directory is the quick orientation for an AI or contributor making a targeted change to AstroSpace.

Read in this order:

1. [Architecture](architecture.md) for the application boundaries and request flow.
2. [Image detail page](image-detail.md) before changing `templates/image_detail.html`, its route, or its browser code.
3. The root `AGENTS.md` for this workspace's local server, Docker, and release commands.

## Guardrails

- The working tree can contain user changes. Inspect `git status --short` before editing and do not discard unrelated work.
- Treat public image-detail URLs as unauthenticated pages. Keep user content escaped unless it is deliberately sanitised server-side.
- Preserve the image-detail DOM IDs unless the matching browser code and tests are updated in the same change. The viewer, likes, comments, media carousel, and keyboard navigation all use them.
- `AstroSpace/static/input.css` is the Tailwind source. Rebuild `AstroSpace/static/styles.css` after changing it; the compiled file is served by the application.
- For a browser-facing change, run the focused tests first, then `python -m pytest -q` when practical.

## Design direction

The image page should be an image-first workspace, not a stack of nested cards. Prioritise the image, its author and story, then offer capture details and analysis progressively. Analysis data and third-party charting must load only when a visitor asks for it.
