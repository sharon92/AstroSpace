from PIL import Image
import requests 
import os
import re
import unicodedata

def slugify(text):
    # Normalize unicode and remove accents
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii')
    # Lowercase and remove non-alphanumeric characters
    text = re.sub(r'[^\w\s-]', '', text).strip().lower()
    # Replace spaces and underscores with hyphens
    return re.sub(r'[\s_-]+', '-', text)

def resize_image(input_path, output_path, base_width=500):
    with Image.open(input_path) as img:
        img = img.convert("RGB")
        wpercent = base_width / float(img.size[0])
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((base_width, hsize), Image.Resampling.LANCZOS)
        if os.path.exists(output_path):
            os.remove(output_path)
        img.save(output_path, "JPEG")

def print_time(sec):
    if sec < 60:
        return f"{sec} sec"
    elif sec < 3600:
        return f"{sec // 60:.0f} min {sec % 60:0f} sec"
    elif sec < 86400:
        hours = sec // 3600
        minutes = (sec % 3600) // 60
        return f"{hours:.0f} hr {minutes:.0f} min"
    else:
        days = sec // 86400
        hours = (sec % 86400) // 3600
        return f"{days:.0f} days {hours:.0f} hr"

def geocode(place):
    r = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": place, "format": "json", "limit": 1},
        headers={"User-Agent": "AstroApp"},
    )
    if r.ok and r.json():
        loc = r.json()[0]
        return float(loc["lat"]), float(loc["lon"])
    return None, None