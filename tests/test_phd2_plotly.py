from pathlib import Path

from AstroSpace.utils.phd2logparser import build_plotly_payloads, deserialize_plot_payload


def test_build_plotly_payloads_parses_guiding_and_calibration():
    log_path = Path("tests/fixtures/sample_phd2.log")
    guiding, calibration = build_plotly_payloads(str(log_path))

    assert guiding["kind"] == "guiding"
    assert calibration["kind"] == "calibration"
    assert guiding["sessions"]
    assert calibration["sessions"]
    assert guiding["sessions"][0]["stats"]["pixel_scale"] == 1.5
    assert calibration["sessions"][0]["axis_limit"] >= 5


def test_deserialize_plot_payload_marks_legacy_html():
    payload = deserialize_plot_payload("<div>legacy</div>", "Guiding")
    assert payload["legacy"] is True
