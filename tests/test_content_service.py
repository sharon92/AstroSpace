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


def test_parse_meta_store_rejects_invalid_json():
    assert parse_meta_store("{bad json}") == "{}"
