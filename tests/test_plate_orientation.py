from copy import deepcopy

from astropy.io.fits import Header


def test_annotate_display_transform_uses_roworder_bottom_up():
    from AstroSpace.utils.platesolve import (
        DISPLAY_TRANSFORM_FLIPUD,
        DISPLAY_TRANSFORM_KEY,
        DISPLAY_TRANSFORM_SOURCE_KEY,
        annotate_display_transform_metadata,
    )

    header = Header()
    header["ROWORDER"] = "BOTTOM-UP"

    updated_header, display_transform = annotate_display_transform_metadata(header)

    assert display_transform == DISPLAY_TRANSFORM_FLIPUD
    assert updated_header[DISPLAY_TRANSFORM_KEY] == DISPLAY_TRANSFORM_FLIPUD
    assert updated_header[DISPLAY_TRANSFORM_SOURCE_KEY] == "ROWORDER"


def test_annotate_display_transform_falls_back_to_history_top_down_mirror():
    from AstroSpace.utils.platesolve import (
        DISPLAY_TRANSFORM_FLIPUD,
        DISPLAY_TRANSFORM_KEY,
        DISPLAY_TRANSFORM_SOURCE_KEY,
        annotate_display_transform_metadata,
    )

    header = Header()
    header["HISTORY"] = "TOP-DOWN mirror"

    updated_header, display_transform = annotate_display_transform_metadata(header)

    assert display_transform == DISPLAY_TRANSFORM_FLIPUD
    assert updated_header[DISPLAY_TRANSFORM_KEY] == DISPLAY_TRANSFORM_FLIPUD
    assert updated_header[DISPLAY_TRANSFORM_SOURCE_KEY] == "HISTORY"


def test_apply_display_transform_to_overlay_payload_flips_annotations_in_display_space():
    from AstroSpace.utils.platesolve import (
        DISPLAY_TRANSFORM_FLIPUD,
        apply_display_transform_to_overlay_payload,
    )

    payload = {
        "width": 120,
        "height": 80,
        "overlays": {
            "name": ["IC 405"],
            "x": [10.0],
            "y": [12.5],
            "rx": [30.0],
            "ry": [18.0],
            "angle": [27.0],
            "otype": ["Emission Nebula"],
        },
        "plots": {
            "hr": {
                "pixel_x": [11],
                "pixel_y": [14],
            }
        },
        "grid_lines": {
            "ra_lines": [[[1.0, 2.0], [3.0, 4.0]]],
            "dec_lines": [[[5.0, 6.0], [7.0, 8.0]]],
            "labels": [
                {"text": "05h 16m", "x": 15.0, "y": 20.0, "rotation": 45.0},
            ],
        },
    }

    transformed = apply_display_transform_to_overlay_payload(
        deepcopy(payload),
        DISPLAY_TRANSFORM_FLIPUD,
    )

    assert transformed["overlays"]["x"] == [10.0]
    assert transformed["overlays"]["y"] == [67.5]
    assert transformed["overlays"]["angle"] == [-27.0]
    assert transformed["plots"]["hr"]["pixel_y"] == [66]
    assert transformed["grid_lines"]["ra_lines"][0][0] == [1.0, 78.0]
    assert transformed["grid_lines"]["dec_lines"][0][1] == [7.0, 72.0]
    assert transformed["grid_lines"]["labels"][0]["y"] == 60.0
    assert transformed["grid_lines"]["labels"][0]["rotation"] == -45.0


def test_rebuild_plate_solve_artifacts_persists_display_transform_for_reuse(tmp_path, monkeypatch):
    from AstroSpace.utils import platesolve

    image_path = tmp_path / "image.png"
    image_path.write_bytes(b"image")

    header = Header()
    header["NAXIS"] = 2
    header["NAXIS1"] = 6172
    header["NAXIS2"] = 4122
    header["CTYPE1"] = "RA---TAN"
    header["CTYPE2"] = "DEC--TAN"
    header["CRVAL1"] = 79.03
    header["CRVAL2"] = 34.07
    header["CRPIX1"] = 3086.5
    header["CRPIX2"] = 2061.5
    header["CDELT1"] = -0.0004496322
    header["CDELT2"] = 0.0004496388
    header["ROWORDER"] = "BOTTOM-UP"

    captured = {}

    monkeypatch.setattr(platesolve, "resize_image", lambda *_args, **_kwargs: None)

    def fake_get_overlays(header_json):
        captured["header_json"] = header_json
        return {"ok": True}

    monkeypatch.setattr(platesolve, "get_overlays", fake_get_overlays)

    thumbnail_path, pixel_scale, overlays_json, updated_header_json = platesolve.rebuild_plate_solve_artifacts(
        str(image_path),
        "1/image.png",
        header.tostring(),
    )

    assert thumbnail_path == "1/image_thumbnail.jpg"
    assert pixel_scale > 0
    assert overlays_json == '{"ok": true}'
    assert captured["header_json"] == updated_header_json
    assert "ASDISP" in updated_header_json
    assert "flipud" in updated_header_json.lower()
