from io import BytesIO
from AstroSpace.services.content import parse_meta_store, sanitize_rich_text


def test_sanitize_rich_text_removes_script_tags():
    cleaned = sanitize_rich_text("<p>Hello</p><script>alert(1)</script>")
    assert "<script>" not in cleaned
    assert "Hello" in cleaned


def test_parse_meta_store_keeps_expected_keys():
    payload = '{"constant":{"GAIN": 100},"variable":{"DATE-OBS":["2025-01-01"]},"comments":{"GAIN":"Camera gain"}}'
    parsed = parse_meta_store(payload)
    assert '"GAIN": 100' in parsed
    assert '"DATE-OBS"' in parsed


def test_parse_meta_store_preserves_separate_extraction_state():
    payload = '{"constant":{},"variable":{},"comments":{},"wbpp_stats":{"frame-1":{"FWHM":2.1}},"wbpp_log_name":"session.log","light_frame_count":12}'
    parsed = parse_meta_store(payload)
    assert '"wbpp_stats"' in parsed
    assert '"wbpp_log_name": "session.log"' in parsed
    assert '"light_frame_count": 12' in parsed


def test_parse_meta_store_rejects_invalid_json():
    assert parse_meta_store("{bad json}") == "{}"


def test_extract_stats_tolerates_logs_without_normalized_weights(app):
    from AstroSpace import blog

    log = (
        "Source file /data/light_001.xisf\n"
        "Image statistics\n"
        " FWHM              : 2.10 px\n"
        " Eccentricity      : 0.42\n"
        " Number of stars   : 120\n"
    ).encode("utf-8")

    with app.test_request_context(
        "/extract_stats",
        method="POST",
        data={"wbpp_log_file": (BytesIO(log), "session.log")},
    ):
        response = blog.extract_stats()

    assert response.status_code == 200
    assert response.get_json()["light_001"]["FWHM"] == 2.1
