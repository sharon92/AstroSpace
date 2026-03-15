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


def test_deserialize_plot_payload_accepts_dict_payloads():
    payload = {"kind": "guiding", "sessions": []}
    assert deserialize_plot_payload(payload, "Guiding") == payload


def test_build_plotly_payloads_tolerates_incomplete_guiding_rows(tmp_path):
    log_path = tmp_path / "partial_phd2.log"
    log_path.write_text(
        "\n".join(
            [
                "Guiding Begins at 2025-01-01 22:00:00",
                "Pixel Scale = 1.50 arc-sec/px",
                "Frame,Time,mount,dx,dy,RARawDistance,DECRawDistance,RAGuideDistance,DECGuideDistance,RADuration,RADirection,DECDuration,DECDirection,XStep,YStep,StarMass,SNR,ErrorCode",
                "1,0.0,mount,0.0,0.0,0.10,-0.20,0.05,-0.02,50,West,0,North,1.0,1.0,100,10,0",
                "2,1.0,mount,0.0,0.0,bad,-0.18,0.06,-0.03,51,West,0,North,1.0,1.0,100,10",
            ]
        ),
        encoding="utf-8",
    )

    guiding, calibration = build_plotly_payloads(str(log_path))

    assert guiding["sessions"]
    assert calibration["sessions"] == []
    assert guiding["sessions"][0]["series"]["ra_raw"] == [-0.1, -0.0]
