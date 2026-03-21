from datetime import date


def test_build_collection_query_includes_requested_filters():
    from AstroSpace.repositories.images import build_collection_query

    query, params = build_collection_query(
        {
            "telescope_type": "refractor",
            "telescope_name": "Evolux-82ED",
            "main_camera": "VeTec571c",
            "guide_camera": "ASI174MM Mini",
            "focal_length_min": 400,
            "focal_length_max": 900,
            "capture_date_start": date(2026, 1, 10),
            "capture_date_end": date(2026, 1, 20),
            "filter_type": "Broadband",
            "mount": "AM5N",
            "object_type": "Emission Nebula",
            "pixel_scale_min": 0.95,
            "pixel_scale_max": 1.45,
            "moon_phase": "Waxing Gibbous",
            "author": "tester",
        }
    )

    assert "t.type = %s" in query
    assert "t.name = %s" in query
    assert "main_camera.name = %s" in query
    assert "guide_camera.name = %s" in query
    assert "t.focal_length BETWEEN %s AND %s" in query
    assert "i.pixel_scale BETWEEN %s AND %s" in query
    assert "i.object_type = %s" in query
    assert "FROM capture_dates cd" in query
    assert "cd.capture_date >= %s" in query
    assert "cd.capture_date <= %s" in query
    assert "cd.moon_phase = %s" in query
    assert "FROM image_lights il" in query
    assert "cf.type = %s" in query
    assert params == [
        "refractor",
        "Evolux-82ED",
        "VeTec571c",
        "ASI174MM Mini",
        "AM5N",
        "Emission Nebula",
        "tester",
        400,
        900,
        0.95,
        1.45,
        date(2026, 1, 10),
        date(2026, 1, 20),
        "Waxing Gibbous",
        "Broadband",
    ]


def test_collection_route_renders_active_filters_and_passes_normalized_values(client, monkeypatch):
    from AstroSpace import blog

    capture_start = date(2026, 1, 10)
    capture_end = date(2026, 1, 20)
    filter_metadata = {
        "dropdowns": {
            "telescope_type": ["refractor", "reflector"],
            "telescope_name": ["Evolux-82ED"],
            "main_camera": ["VeTec571c"],
            "guide_camera": ["ASI174MM Mini"],
            "filter_type": ["Broadband"],
            "mount": ["AM5N"],
            "object_type": ["Emission Nebula", "Planetary Nebula"],
            "moon_phase": ["Waxing Gibbous"],
            "author": ["tester"],
        },
        "ranges": {
            "focal_length": {"min": 160.0, "max": 1624.0},
            "pixel_scale": {"min": 0.75, "max": 2.25},
            "capture_dates": {
                "min": date(2026, 1, 1),
                "max": date(2026, 1, 31),
            },
        },
    }
    captured_filters = {}

    def fake_get_collection_images(filters):
        captured_filters.update(filters)
        return [
            {
                "id": 7,
                "title": "Rosette Nebula",
                "short_description": "RGB blend",
                "slug": "rosette-nebula",
                "image_path": "1/rosette.jpg",
                "image_thumbnail": "1/rosette-thumb.jpg",
                "created_at": date(2026, 1, 31),
            }
        ]

    monkeypatch.setattr(blog, "get_collection_filter_metadata", lambda: filter_metadata)
    monkeypatch.setattr(blog, "get_collection_images", fake_get_collection_images)

    response = client.get(
        "/collection"
        "?telescope_type=refractor"
        "&mount=AM5N"
        "&object_type=Emission%20Nebula"
        "&author=tester"
        "&focal_length_min=400"
        "&focal_length_max=800"
        "&pixel_scale_min=1.10"
        "&pixel_scale_max=1.80"
        f"&capture_date_min={capture_start.toordinal()}"
        f"&capture_date_max={capture_end.toordinal()}"
        "&moon_phase=Waxing%20Gibbous"
    )

    assert response.status_code == 200
    assert captured_filters["telescope_type"] == "refractor"
    assert captured_filters["mount"] == "AM5N"
    assert captured_filters["object_type"] == "Emission Nebula"
    assert captured_filters["author"] == "tester"
    assert captured_filters["focal_length_min"] == 400
    assert captured_filters["focal_length_max"] == 800
    assert captured_filters["pixel_scale_min"] == 1.1
    assert captured_filters["pixel_scale_max"] == 1.8
    assert captured_filters["capture_date_start"] == capture_start
    assert captured_filters["capture_date_end"] == capture_end
    assert captured_filters["moon_phase"] == "Waxing Gibbous"

    page = response.get_data(as_text=True)
    assert "Applied Filters" in page
    assert "Telescope Type:" in page
    assert "Focal Length" in page
    assert "Pixel Scale" in page
    assert "Capture Dates" in page
    assert "Object Type:" in page
    assert 'id="collectionFiltersPanel"' in page
    assert 'id="collectionFiltersForm"' in page
    assert 'data-filter-panel-label' in page
    assert 'data-range-active-track' in page
    assert 'data-auto-submit="true"' in page
    assert "Filters update automatically as you change them." in page
    assert "requestSubmit" in page
    assert "Rosette Nebula - RGB blend" in page
    assert 'option value="Emission Nebula" selected' in page
    assert 'option value="refractor" selected' in page
