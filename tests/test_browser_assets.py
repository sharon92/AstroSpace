from pathlib import Path

from flask import g, render_template


def test_favicon_route_returns_no_content_without_404(client):
    response = client.get("/favicon.ico")

    assert response.status_code == 204
    assert response.data == b""


def test_base_template_uses_lato_preloads_without_explicit_favicon(app):
    with app.test_request_context("/"):
        g.user = None
        html = render_template("base.html", WebName="AstroSpace Test")

    assert 'rel="icon"' not in html
    assert "fonts/Lato-Medium.woff2" in html
    assert "fonts/Lato-Black.woff2" in html
    assert "fonts/Patung.woff2" not in html


def test_home_template_adds_patung_preload(app):
    with app.test_request_context("/"):
        g.user = None
        html = render_template("home.html", top_images=[])

    assert "fonts/Lato-Medium.woff2" in html
    assert "fonts/Lato-Black.woff2" in html
    assert "fonts/Patung.woff2" in html


def test_image_detail_template_does_not_include_headlessui_react_cdn():
    template_path = Path(__file__).resolve().parents[1] / "AstroSpace" / "templates" / "image_detail.html"
    template_source = template_path.read_text(encoding="utf-8")

    assert "@headlessui/react" not in template_source


def test_image_detail_template_uses_clear_icon_tooltips_and_lazy_fullscreen_viewer_init():
    template_path = Path(__file__).resolve().parents[1] / "AstroSpace" / "templates" / "image_detail.html"
    template_source = template_path.read_text(encoding="utf-8")

    assert ".author-pill {" in template_source
    assert ".author-pill-text {" in template_source
    assert ".author-pill.is-expanded .author-pill-text," in template_source
    assert ".image-meta-strip {" in template_source
    assert ".inline-media-caption-strip {" in template_source
    assert 'title="Full Screen"' in template_source
    assert template_source.count('title="Resize"') >= 2
    assert 'title="Graticule"' in template_source
    assert 'title="Moon Size Comparison"' in template_source
    assert 'title="Object Annotation"' in template_source
    assert 'title="Remove Stars"' in template_source
    assert 'let fullscreenViewer = null;' in template_source
    assert 'function ensureFullscreenViewer()' in template_source
    assert 'const fullscreenViewer = createViewer("fullscreen-");' not in template_source
    assert 'id="fullscreen-tool-tray-{{il.image.id}}"' in template_source
    assert ".inline-media-arrow {" in template_source
    assert ".inline-media-arrow.is-hover {" in template_source
    assert ".inline-media-arrow.is-active {" in template_source
    assert ".inline-corner-control {" in template_source
    assert ".inline-corner-control.is-visible {" in template_source
    assert 'class="inline-corner-control absolute bottom-3 left-3 z-20' in template_source
    assert 'class="inline-corner-control absolute bottom-3 right-3 z-20' in template_source
    assert 'class="inline-media-arrow absolute left-3 top-1/2 z-20' in template_source
    assert 'class="inline-media-arrow absolute right-3 top-1/2 z-20' in template_source
    assert 'id="zoomable-video-{{il.image.id}}"' in template_source
    assert 'id="fullscreen-zoomable-video-{{il.image.id}}"' in template_source
    assert 'id="media-prev-{{il.image.id}}"' in template_source
    assert 'id="media-next-{{il.image.id}}"' in template_source
    assert 'x-data="{ expanded: false }"' in template_source
    assert '@click="if (window.innerWidth < 768 && !expanded) { $event.preventDefault(); expanded = true }"' in template_source
    assert ':class="{ \'is-expanded\': expanded }"' in template_source
    assert 'class="author-pill shrink-0 flex items-center rounded-full' in template_source
    assert 'class="author-pill-text flex min-w-0 flex-col leading-tight"' in template_source
    assert ".inline-tool-tray {" in template_source
    assert ".inline-tool-tray.is-visible {" in template_source
    assert 'id="inline-tool-tray-{{il.image.id}}"' in template_source
    assert 'id="inline-media-caption-{{il.image.id}}"' in template_source
    assert 'id="inline-tools-{{il.image.id}}"' in template_source
    assert 'const primaryCaption = {{ il.image.title | tojson | safe }};' in template_source
    assert 'caption: primaryCaption,' in template_source
    assert 'inlineToolTray.appendChild(inlineTools);' in template_source
    assert 'window.setTimeout(() => setInlineToolTrayVisible(false), 6000);' in template_source
    assert 'window.setTimeout(() => {' in template_source
    assert '}, 5000);' in template_source
    assert 'button.classList.toggle("is-hover", arrowsShouldHover || inlineChromeActive);' in template_source
    assert 'button.classList.toggle("is-visible", inlineChromeActive);' in template_source
    assert 'inlineContainer?.addEventListener("mousemove", pokeInlineToolTray);' in template_source
    assert 'inlineContainer?.addEventListener("mousemove", pokeInlineChrome);' in template_source
    assert 'inlineContainer?.addEventListener("mouseleave", () => {' in template_source
    assert 'id="starless-toggle-{{il.image.id}}"' in template_source
    assert 'inlineTools.classList.toggle("hidden", !astroEnabled);' in template_source
    assert 'inlineTools.classList.toggle("opacity-90", !astroEnabled);' not in template_source
    assert 'pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-end justify-between' not in template_source
    assert 'pointer-events-auto flex max-w-[70%] items-center gap-3 rounded-full' not in template_source
    assert 'class="image-meta-strip px-1 text-sm text-gray-600 dark:text-gray-300"' in template_source
    assert 'class="inline-media-caption-strip min-h-[1.5rem] px-2 text-center text-sm text-gray-600 dark:text-gray-300"' in template_source
    assert '@media (max-width: 920px)' not in template_source


def test_image_detail_template_uses_unified_details_and_explore_radio_switch():
    template_path = Path(__file__).resolve().parents[1] / "AstroSpace" / "templates" / "image_detail.html"
    template_source = template_path.read_text(encoding="utf-8")

    assert "validMainTabs = ['image', 'details', 'explore'];" in template_source
    assert "const validExplorePanes = ['hr'" in template_source
    assert "validDetailTabs" not in template_source
    assert "{% set detail_tabs =" not in template_source
    assert "('nights', 'Nights')" not in template_source
    assert 'x-show="mainTab === \'analyse\'"' not in template_source
    assert 'name="explore-pane-{{il.image.id}}"' in template_source
    assert 'x-model="explorePane"' in template_source
    assert "Explore view mode" in template_source
    assert "explorePane === 'hr'" in template_source
    assert "explorePane === 'analyse'" in template_source
    assert "explorePane === 'guiding'" in template_source
    assert "explorePane === 'calibration'" in template_source
    assert "Plotly.Plots.resize(plot);" in template_source
    assert 'id="guiding-root-{{il.image.id}}"' in template_source
    assert 'id="calibration-root-{{il.image.id}}"' in template_source
    assert 'aria-label="Guiding session"' in template_source
    assert 'aria-label="Calibration session"' in template_source
    assert 'name="guiding-pane-{{il.image.id}}"' not in template_source
    assert "peer-checked:bg-blue-600" in template_source


def test_image_detail_template_uses_consistent_details_cards_and_table_exports():
    template_path = Path(__file__).resolve().parents[1] / "AstroSpace" / "templates" / "image_detail.html"
    template_source = template_path.read_text(encoding="utf-8")

    assert ".detail-card {" in template_source
    assert ".detail-table {" in template_source
    assert ".detail-sticky-col {" in template_source
    assert "--detail-card-surface:" in template_source
    assert ".details-two-up," in template_source
    assert ".details-three-up {" in template_source
    assert 'html-id="light-{{il.image.id}}"' in template_source
    assert 'class="detail-card-title">Lights</h3>' in template_source
    assert 'class="detail-sticky-col min-w-[11rem]">Filter</th>' in template_source
    assert 'html-id="weighted-{{il.image.id}}"' in template_source
    assert "Weighted Exposure" in template_source
    assert 'html-id="night-summary-{{il.image.id}}"' in template_source
    assert 'class="detail-card-title">Nights</h3>' in template_source
    assert 'html-id="equipment-{{il.image.id}}"' in template_source
    assert 'class="detail-card-title">Equipment</h3>' in template_source
    assert 'html-id="software-{{il.image.id}}"' in template_source
    assert 'class="detail-card-title">Software</h3>' in template_source
    assert 'class="details-two-up"' in template_source
    assert 'class="details-three-up"' in template_source
    assert template_source.count('class="detail-card detail-card-scroll"') >= 3
    assert 'table[html-id="weighted-${id}"]' in template_source
    assert 'table[html-id="night-summary-${id}"]' in template_source
    assert 'table[html-id="equipment-${id}"]' in template_source
    assert 'table[html-id="software-${id}"]' in template_source
    assert "Weighted Total Exposure" not in template_source
    assert "Weighted Red Channel Exposure" not in template_source


def test_image_detail_template_keeps_details_tabs_outside_image_panel():
    template_path = Path(__file__).resolve().parents[1] / "AstroSpace" / "templates" / "image_detail.html"
    template_source = template_path.read_text(encoding="utf-8")

    assert template_source.count("<div") == template_source.count("</div>")
    assert '</div>\n\n          <p id="inline-media-caption-{{il.image.id}}"' in template_source
