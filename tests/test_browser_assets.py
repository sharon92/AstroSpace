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

    assert 'title="Full Screen"' in template_source
    assert template_source.count('title="Resize"') >= 2
    assert 'let fullscreenViewer = null;' in template_source
    assert 'function ensureFullscreenViewer()' in template_source
    assert 'const fullscreenViewer = createViewer("fullscreen-");' not in template_source
    assert 'pointer-events-none absolute inset-x-0 bottom-4 z-20 flex justify-center px-4' in template_source
    assert 'pointer-events-auto flex items-center space-x-2 rounded-full bg-black/55 px-3 py-2 backdrop-blur-sm' in template_source
    assert 'opacity-15 border-gray-600 dark:border-white rounded-md z-20 bg-gray-200/20 hover:bg-gray-200/35 hover:opacity-100 transition' in template_source
    assert 'pointer-events-none absolute inset-x-0 bottom-0 z-20 flex items-end justify-between' in template_source
    assert 'pointer-events-auto flex max-w-[70%] items-center gap-3 rounded-full' in template_source
    assert 'pointer-events-auto flex items-center gap-2' in template_source


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
