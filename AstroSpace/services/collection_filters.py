from datetime import date
import math
from urllib.parse import urlencode


PYTHON_UNIX_EPOCH_ORDINAL = 719163

COLLECTION_SELECT_FIELDS = (
    ("telescope_type", "Telescope Type"),
    ("telescope_name", "Telescope Name"),
    ("main_camera", "Main Camera"),
    ("guide_camera", "Guide Camera"),
    ("filter_type", "Filter Type"),
    ("mount", "Mount"),
    ("object_type", "Object Type"),
    ("moon_phase", "Moon Phase"),
    ("author", "Author"),
)


def _coerce_float(value, default, minimum=None, maximum=None, precision=None):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default

    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    if precision is not None:
        number = round(number, precision)
    return number


def _coerce_int(value, default, minimum=None, maximum=None):
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default

    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def _round_down(value, precision):
    if value is None:
        return None
    factor = 10 ** precision
    return math.floor(float(value) * factor) / factor


def _round_up(value, precision):
    if value is None:
        return None
    factor = 10 ** precision
    return math.ceil(float(value) * factor) / factor


def _drop_query_keys(args, keys):
    filtered = {
        key: value
        for key, value in args.items()
        if key not in keys and value not in (None, "")
    }
    if not filtered:
        return ""
    return f"?{urlencode(filtered)}"


def _format_date(value):
    return value.strftime("%Y-%m-%d")


def _date_from_ordinal(value):
    if value is None:
        return None
    return date.fromordinal(value)


def normalize_collection_filters(raw_args, metadata):
    dropdowns = metadata.get("dropdowns", {})
    ranges = metadata.get("ranges", {})

    state = {}
    filters = {}

    for field_name, _label in COLLECTION_SELECT_FIELDS:
        value = (raw_args.get(field_name) or "").strip()
        if value and value not in dropdowns.get(field_name, []):
            value = ""
        state[field_name] = value
        filters[field_name] = value or None

    focal_range = ranges.get("focal_length", {})
    focal_min_default = int(math.floor(focal_range.get("min") or 0))
    focal_max_default = int(math.ceil(focal_range.get("max") or focal_min_default))
    focal_min_value = _coerce_int(
        raw_args.get("focal_length_min"),
        focal_min_default,
        focal_min_default,
        focal_max_default,
    )
    focal_max_value = _coerce_int(
        raw_args.get("focal_length_max"),
        focal_max_default,
        focal_min_default,
        focal_max_default,
    )
    if focal_min_value > focal_max_value:
        focal_min_value, focal_max_value = focal_max_value, focal_min_value
    focal_active = focal_range.get("min") is not None and (
        focal_min_value != focal_min_default or focal_max_value != focal_max_default
    )
    state["focal_length_min"] = focal_min_value
    state["focal_length_max"] = focal_max_value
    state["focal_length_active"] = focal_active
    filters["focal_length_min"] = focal_min_value if focal_active else None
    filters["focal_length_max"] = focal_max_value if focal_active else None

    pixel_range = ranges.get("pixel_scale", {})
    pixel_min_default = _round_down(pixel_range.get("min"), 2)
    pixel_max_default = _round_up(pixel_range.get("max"), 2)
    if pixel_min_default is None:
        pixel_min_default = 0.0
    if pixel_max_default is None:
        pixel_max_default = pixel_min_default
    pixel_min_value = _coerce_float(
        raw_args.get("pixel_scale_min"),
        pixel_min_default,
        pixel_min_default,
        pixel_max_default,
        precision=2,
    )
    pixel_max_value = _coerce_float(
        raw_args.get("pixel_scale_max"),
        pixel_max_default,
        pixel_min_default,
        pixel_max_default,
        precision=2,
    )
    if pixel_min_value > pixel_max_value:
        pixel_min_value, pixel_max_value = pixel_max_value, pixel_min_value
    pixel_active = pixel_range.get("min") is not None and (
        pixel_min_value != pixel_min_default or pixel_max_value != pixel_max_default
    )
    state["pixel_scale_min"] = pixel_min_value
    state["pixel_scale_max"] = pixel_max_value
    state["pixel_scale_active"] = pixel_active
    filters["pixel_scale_min"] = pixel_min_value if pixel_active else None
    filters["pixel_scale_max"] = pixel_max_value if pixel_active else None

    capture_range = ranges.get("capture_dates", {})
    capture_min = capture_range.get("min")
    capture_max = capture_range.get("max")
    capture_min_ordinal_default = capture_min.toordinal() if capture_min else None
    capture_max_ordinal_default = capture_max.toordinal() if capture_max else None

    if capture_min_ordinal_default is None or capture_max_ordinal_default is None:
        capture_min_value = 0
        capture_max_value = 0
        capture_active = False
        capture_start = None
        capture_end = None
    else:
        capture_min_value = _coerce_int(
            raw_args.get("capture_date_min"),
            capture_min_ordinal_default,
            capture_min_ordinal_default,
            capture_max_ordinal_default,
        )
        capture_max_value = _coerce_int(
            raw_args.get("capture_date_max"),
            capture_max_ordinal_default,
            capture_min_ordinal_default,
            capture_max_ordinal_default,
        )
        if capture_min_value > capture_max_value:
            capture_min_value, capture_max_value = capture_max_value, capture_min_value
        capture_active = (
            capture_min_value != capture_min_ordinal_default
            or capture_max_value != capture_max_ordinal_default
        )
        capture_start = _date_from_ordinal(capture_min_value)
        capture_end = _date_from_ordinal(capture_max_value)

    state["capture_date_min"] = capture_min_value
    state["capture_date_max"] = capture_max_value
    state["capture_date_active"] = capture_active
    filters["capture_date_start"] = capture_start if capture_active else None
    filters["capture_date_end"] = capture_end if capture_active else None

    return state, filters


def build_active_collection_filters(base_url, raw_args, state):
    chips = []

    for field_name, label in COLLECTION_SELECT_FIELDS:
        value = state.get(field_name)
        if not value:
            continue
        chips.append(
            {
                "label": label,
                "value": value,
                "remove_url": f"{base_url}{_drop_query_keys(raw_args, {field_name})}",
            }
        )

    if state.get("focal_length_active"):
        chips.append(
            {
                "label": "Focal Length",
                "value": f"{state['focal_length_min']} - {state['focal_length_max']} mm",
                "remove_url": f"{base_url}{_drop_query_keys(raw_args, {'focal_length_min', 'focal_length_max'})}",
            }
        )

    if state.get("pixel_scale_active"):
        chips.append(
            {
                "label": "Pixel Scale",
                "value": f"{state['pixel_scale_min']:.2f} - {state['pixel_scale_max']:.2f} arcsec/px",
                "remove_url": f"{base_url}{_drop_query_keys(raw_args, {'pixel_scale_min', 'pixel_scale_max'})}",
            }
        )

    if state.get("capture_date_active"):
        chips.append(
            {
                "label": "Capture Dates",
                "value": (
                    f"{_format_date(date.fromordinal(state['capture_date_min']))} to "
                    f"{_format_date(date.fromordinal(state['capture_date_max']))}"
                ),
                "remove_url": f"{base_url}{_drop_query_keys(raw_args, {'capture_date_min', 'capture_date_max'})}",
            }
        )

    return chips
