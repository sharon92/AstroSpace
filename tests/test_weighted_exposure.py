from io import BytesIO

import pytest

from AstroSpace import blog
from AstroSpace.repositories.images import _aggregate_wbpp_weights


def test_aggregate_wbpp_weights_uses_per_frame_stats():
    metadata = {
        "variable": {
            "WBPP weight 1": [99.0],
            "WBPP weight 2": [99.0],
            "WBPP weight 3": [99.0],
        },
        "wbpp_stats": {
            "frame-1": {
                "WBPP weight 1": 0.5,
                "WBPP weight 2": 0.4,
                "WBPP weight 3": 0.3,
            },
            "frame-2": {
                "WBPP weight 1": 0.6,
                "WBPP weight 2": 0.7,
                "WBPP weight 3": 0.8,
            },
        },
    }

    assert _aggregate_wbpp_weights(metadata) == pytest.approx(
        {
            "WBPP weight 1": 1.1,
            "WBPP weight 2": 1.1,
            "WBPP weight 3": 1.1,
        }
    )


def test_aggregate_wbpp_weights_keeps_legacy_variable_metadata():
    metadata = {
        "variable": {
            "WBPP weight 1": [1.5, 0.5],
            "WBPP weight 2": [1.0],
            "WBPP weight 3": [0.25],
        }
    }

    assert _aggregate_wbpp_weights(metadata) == pytest.approx(
        {
            "WBPP weight 1": 2.0,
            "WBPP weight 2": 1.0,
            "WBPP weight 3": 0.25,
        }
    )


def test_extracted_wbpp_log_stats_feed_weight_aggregation(app):
    log = (
        "[2026-08-15 11:55:31] Normalized image weights:\n"
        "[2026-08-15 11:55:31] [    1] D:/registered/frame-1.xisf\n"
        "[2026-08-15 11:55:31] 0.5 0.4 0.3\n"
        "[2026-08-15 11:55:31] [    2] D:/registered/frame-2.xisf\n"
        "[2026-08-15 11:55:31] 0.6 0.7 0.8\n"
        "[2026-08-15 11:55:31] Integration of 2 frames\n"
    ).encode("utf-8")

    with app.test_request_context(
        "/extract_stats",
        method="POST",
        data={"wbpp_log_file": (BytesIO(log), "session.log")},
    ):
        response = blog.extract_stats()

    assert response.status_code == 200
    metadata = {"wbpp_stats": response.get_json()}
    assert _aggregate_wbpp_weights(metadata) == pytest.approx(
        {
            "WBPP weight 1": 1.1,
            "WBPP weight 2": 1.1,
            "WBPP weight 3": 1.1,
        }
    )
