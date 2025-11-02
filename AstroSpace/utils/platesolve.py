import os
from astropy.io import fits
from astropy.wcs import WCS

import numpy as np
import math
# from astroquery.vizier import Vizier
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.io.fits import Header
import pandas as pd
import hashlib
from flask import current_app
from astroquery.astrometry_net import AstrometryNet
from AstroSpace.utils.utils import resize_image
from AstroSpace.utils.xisf_reader import xisf_header
import json
# import scipy

pc_to_ly = 3.26156  # 1 parsec = 3.26156 light years

# Vizier.ROW_LIMIT = -1 # No limit on the number of rows returned

def make_grid_lines(wcs, ra_limits, dec_limits, ra_count=6, dec_count=6):
    ra_lines = []
    dec_lines = []
    labels = []

    ra_min, ra_max = ra_limits
    dec_min, dec_max = dec_limits

    # RA lines (constant RA, varying Dec)
    ras = np.linspace(ra_min, ra_max, ra_count)
    decs = np.linspace(dec_min, dec_max, dec_count)

    for ra in ras:
        coords = np.column_stack((np.full_like(decs, ra), decs))
        pix = wcs.all_world2pix(coords, 0)
        ra_lines.append(pix.tolist())

        mid = ra_count // 2
        if 1 < mid < len(pix) - 1:
            dx = pix[mid + 1][0] - pix[mid - 1][0]
            dy = pix[mid + 1][1] - pix[mid - 1][1]
            angle = math.degrees(math.atan2(dy, dx))
        else:
            angle = -90  # Fallback
        hrs = ra // 15 
        mins = (ra%15)*4
        secs = (mins % 1) * 60
        labels.append(
            {
                "text": f"{hrs:02.0f}h {int(mins):02.0f}m {secs:02.1f}s",
                "x": float(pix[mid][0] - 15),
                "y": float(pix[mid][1] - 10),
                 "rotation": angle
            }
        )

    # Dec lines (constant Dec, varying RA)
    for dec in decs:
        coords = np.column_stack((ras, np.full_like(ras, dec)))
        pix = wcs.all_world2pix(coords, 0)
        dec_lines.append(pix.tolist())

        mid = dec_count // 2
        if 1 < mid < len(pix) - 1:
                dx = pix[mid + 1][0] - pix[mid - 1][0]
                dy = pix[mid + 1][1] - pix[mid - 1][1]
                angle = math.degrees(math.atan2(dy, dx))
        else:
            angle = 0  # Fallback

        labels.append(
            {
                "text": f"{int(dec):+03d}°{int(abs(dec % 1) * 60):02d}′",
                "x": float(pix[mid][0] + 20),
                "y": float(pix[mid][1] - 15),
                "rotation": angle
            }
        )

    return {
        "ra_lines": ra_lines,
        "dec_lines": dec_lines,
        "labels": labels
    }


def platesolve(image_path, user_id, fits_file=None):
    print("Plate solving image....")
    if fits_file:
        # If a FITS file is provided, use it to extract the WCS header
        fits_name = fits_file.filename.lower()
        if fits_name.endswith(".xisf"):
            wcs_header = xisf_header(fits_file)
        elif fits_name.endswith(".fits") or fits_name.endswith(".fit"):
            with fits.open(fits_file, mode="update") as hdul:
                wcs_header = hdul[0].header

    else:
        print("Plate solving using AstrometryNet...")
        # Initialize AstrometryNet with your API key
        ast = AstrometryNet()
        ast.api_key = current_app.config["ASTROMETRY_API_KEY"]
        wcs_header = ast.solve_from_image(image_path, solve_timeout=1800)

    if "CRPIX1" not in wcs_header:
        raise ValueError("FITS file does not contain WCS information. Plate Solve the Fits file first!")
    
    wcs = WCS(wcs_header)
    try:
        wcs = wcs.dropaxis(2)  # Drop any unused axes
        #wcs_header = wcs.to_header()
    except:
        pass 

    ps_x, ps_y = wcs.proj_plane_pixel_scales()[:2]
    pixel_scale = float(np.mean([ps_x.value, ps_y.value]) * 3600)

    header_json = wcs_header.tostring()
    svg_image = json.dumps(get_overlays(header_json))
    print("Plate solving done.")

    print("Resizing image...")
    path, ext = os.path.splitext(image_path)
    thumbnail_path = path + "_thumbnail" + ext
    resize_image(image_path, thumbnail_path)
    thumbnail_path = f"{user_id}/{os.path.basename(thumbnail_path)}"
    return header_json, svg_image, thumbnail_path, pixel_scale


def otype_to_color(otype):
    """Generate a consistent hex color for a given otype string."""
    hash_bytes = hashlib.md5(otype.encode()).digest()  # 16 bytes
    r, g, b = hash_bytes[:3]  # Take first 3 bytes
    return f"#{r:02x}{g:02x}{b:02x}"  # Format as hex color


favs = [
    "?",
    "..4",
    "*",
    "**",
    "AGN",
    "BD*",
    "BH",
    "BiC",
    "Bla",
    "CGG",
    "ClG",
    "DNeEm*",
    "EmG",
    "Ev*",
    "G",
    "GiC",
    "GiG",
    "GlC",
    "gLe",
    "H2G",
    "HI",
    "HII",
    "IG",
    "LSB",
    "Ma*",
    "MoC",
    "MS*",
    "N*",
    "OpC",
    "PaG",
    "PoC",
    "PN",
    "Psr",
    "QSO",
    "RNe",
    "s*b",
    "s*r",
    "SBG",
    "SFR",
    "sg*",
    "SN*",
    "SNR",
    "V*",
    "WD*",
    "Y*O",
]


def get_overlays(wcs_header):
    wcs_header = Header.fromstring(wcs_header)
    wcs = WCS(wcs_header)
    try:
        wcs = wcs.dropaxis(2)  # Drop any unused axes
        #wcs_header = wcs.to_header()
    except:
        pass 

    ps_x, ps_y = wcs.proj_plane_pixel_scales()[:2]
    pixel_scale = np.mean([ps_x.value, ps_y.value]) * 3600

    simbad_desc = os.path.join(
        current_app.config["root_path"], "utils", "simbad_object_description.json"
    )
    with open(simbad_desc) as f:
        otypes = pd.read_json(f, orient="index")

    # chosen_stars = otypes.query("index.isin(@favs)").to_dict()[0]
    chosen_stars = otypes.to_dict()[0]

    try:
        nx, ny = wcs_header["IMAGEW"], wcs_header["IMAGEH"]
    except:
        nx, ny = wcs_header["NAXIS1"], wcs_header["NAXIS2"]

    corners_pix = np.array([[0, 0], [nx, 0], [nx, ny], [0, ny]])
    corners_world = wcs.pixel_to_world_values(corners_pix[:, 0], corners_pix[:, 1])
    ra_vals, dec_vals = corners_world
    ra_min, ra_max = ra_vals.min(), ra_vals.max()
    dec_min, dec_max = dec_vals.min(), dec_vals.max()
    ra_center, dec_center = wcs_header.get("CRVAL1", 0), wcs_header.get("CRVAL2", 0)

    radius = max(abs(ra_max - ra_min), abs(dec_max - dec_min)) / 2
    coord = SkyCoord(ra_center, dec_center, unit="deg")

    Simbad.reset_votable_fields()  # Reset to default fields
    Simbad.add_votable_fields(
        "galdim_majaxis",
        "galdim_minaxis",
        "galdim_angle",
        "otype",
    )

    print("Querying Simbad for objects in the field of view...")
    result = Simbad.query_region(coord, radius=radius * u.deg)
    df = result.to_pandas()
    df = df[
        [
            "main_id",
            "ra",
            "dec",
            "galdim_majaxis",
            "galdim_minaxis",
            "galdim_angle",
            "otype",
        ]
    ]

    df = df.dropna(subset=["ra", "dec"])
    box = (df.ra > ra_min) * (df.ra < ra_max) * (df.dec > dec_min) * (df.dec < dec_max)
    df = df[box]

    df.sort_values(["galdim_majaxis", "galdim_minaxis"], ascending=False, inplace=True)

    x, y = wcs.world_to_pixel_values(df["ra"], df["dec"])

    df["rx"] = (df["galdim_majaxis"] * 60) / pixel_scale / 2
    df["ry"] = (df["galdim_minaxis"] * 60) / pixel_scale / 2

    df = df.dropna(subset=["rx", "ry"])

    db = {
        "name": df["main_id"].astype(str).tolist(),
        "x": x.round(1).tolist(),
        "y": y.round(1).tolist(),
        "rx": [0 if np.isnan(i) else round(i, 1) for i in df.rx],
        "ry": [0 if np.isnan(i) else round(i, 1) for i in df.ry],
        "angle": [0 if pd.isna(i) or i == 32767 else int(i) for i in df.galdim_angle],
        "otype": [chosen_stars.get(o, "Unknown") for o in df["otype"].astype(str)],
    }

    Simbad.reset_votable_fields()  # Reset to default fields
    Simbad.add_votable_fields(
        "otype",
        "plx_value",
        "U",
        "B",
        "V",
        "pmra",
        "pmdec",
        "sp_type",
    )

    print("Querying Simbad for objects in the field of view...")
    result = Simbad.query_region(coord, radius=radius * u.deg)

    df2 = result.to_pandas()
    df2= df2[
        [
            "main_id",
            "otype",
            "plx_value",
            "U",
            "B",
            "V",
            "pmra",
            "pmdec",
            "sp_type"
        ]
    ]

    # Convert parallax to distance in light years
    d_ly = (df2["plx_value"] ** -1) * pc_to_ly * 1e3

    #HR Diagram data
    df2["HR_x"] = df2.B - df2.V
    df2["HR_y"] = df2.V - 5 * np.log10(100/df2.plx_value)
    hr = df2.dropna(subset=["HR_x", "HR_y"])[['main_id','otype','sp_type','HR_x','HR_y']]
    hr = {
        "name": hr["main_id"].astype(str).tolist(), 
        "x": [round(i, 2) for i in hr["HR_x"]],
        "y": [round(i, 2) for i in hr["HR_y"]],
        "Object Type": [chosen_stars.get(o, "Unknown") for o in hr["otype"].astype(str)],
        "Spectral Class": [None if i.strip() == "" else i for i in hr["sp_type"]],
    }

    #proper motion diagram data
    pm = df2.dropna(subset=["pmra", "pmdec"])[['main_id','otype','sp_type','pmra','pmdec']]
    pm = {
        "name": pm["main_id"].astype(str).tolist(),
        "x": [round(i, 2) for i in pm["pmra"]],
        "y": [round(i, 2) for i in pm["pmdec"]],
        "Object Type": [chosen_stars.get(o, "Unknown") for o in pm["otype"].astype(str)],
        "Spectral Class": [None if i.strip() == "" else i for i in pm["sp_type"]],
    }
    

    print("Generating grid lines...")
    grid_lines = make_grid_lines(
        wcs, ra_limits=[ra_min, ra_max], dec_limits=[dec_min, dec_max]
    )

    return {
        "width": nx,
        "height": ny,
        "overlays": db,
        "plots": {'hr': hr, 'pm': pm},
        "grid_lines": grid_lines,
    }
