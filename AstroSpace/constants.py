ALLOWED_IMG_EXTENSIONS = {"jpg", "jpeg"}
ALLOWED_FITS_EXTENSIONS = {"fits", "fit", "xisf"}
ALLOWED_TXT_EXTENSIONS = {"txt", "log"}

ALLOWED_TAGS = [
    "b",
    "i",
    "u",
    "em",
    "strong",
    "a",
    "p",
    "br",
    "ul",
    "ol",
    "li",
    "blockquote",
    "code",
    "span",
]

ALLOWED_ATTRIBUTES = {
    "a": ["href", "title", "rel"],
    "span": ["style"],
}

ALLOWED_STYLES = ["color", "font-weight", "text-decoration"]

DB_TABLES = [
    "camera",
    "telescope",
    "reducer",
    "guide_camera",
    "guider",
    "mount",
    "tripod",
    "filter_wheel",
    "eaf",
    "dew_heater",
    "flat_panel",
    "rotator",
]

INVENTORY_TABLES = [
    "telescope",
    "reducer",
    "camera",
    "mount",
    "tripod",
    "guider",
    "cam_filter",
    "filter_wheel",
    "rotator",
    "dew_heater",
    "flat_panel",
    "eaf",
    "software",
]

IMAGE_RELATION_TABLES = [
    "image_views",
    "image_likes",
    "image_comments",
    "capture_dates",
    "image_lights",
    "image_software",
]

IMAGE_DETAIL_TABLE_NAMES = [
    "image",
    "equipment_list",
    "dates",
    "lights",
    "software_list",
    "guiding_plot",
    "calibration_plot",
    "svg_image",
    "meta_json",
]
