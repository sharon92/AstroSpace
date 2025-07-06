import os
from astropy.wcs import WCS
import numpy as np
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord
import astropy.units as u
from astropy.io.fits import Header
import pandas as pd
from collections import defaultdict
import hashlib
from flask import current_app
from astroquery.astrometry_net import AstrometryNet
from AstroSpace.utils.utils import  resize_image
import json 

pc_to_ly = 3.26156 # 1 parsec = 3.26156 light years

def platesolve(image_path,user_id):
    print("Plate solving image....")
    # Initialize AstrometryNet with your API key
    ast = AstrometryNet()
    ast.api_key = current_app.config["ASTROMETRY_API_KEY"]
    wcs_header = ast.solve_from_image(image_path, solve_timeout=1800)

    wcs = WCS(wcs_header)
    ps_x,ps_y = wcs.proj_plane_pixel_scales()
    pixel_scale = float(np.mean([ps_x.value, ps_y.value]) * 3600)

    header_json = wcs_header.tostring()
    svg_image = json.dumps(get_overlays(header_json))
    print("Plate solving done.")
    print("Resizing image...")
    path,ext = os.path.splitext(image_path)
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

    ps_x,ps_y = wcs.proj_plane_pixel_scales()
    pixel_scale = np.mean([ps_x.value, ps_y.value]) * 3600

    simbad_desc = os.path.join(current_app.config['root_path'], "utils", "simbad_object_description.json")    
    with open(simbad_desc) as f:
        otypes = pd.read_json(f, orient="index")

    # chosen_stars = otypes.query("index.isin(@favs)").to_dict()[0]
    chosen_stars = otypes.to_dict()[0]

    nx, ny = wcs_header.get("IMAGEW", 0), wcs_header.get("IMAGEH", 0)

    corners_pix = np.array([[0, 0], [nx, 0], [nx, ny], [0, ny]])
    corners_world = wcs.pixel_to_world_values(corners_pix[:, 0], corners_pix[:, 1])
    ra_vals, dec_vals = corners_world
    ra_min, ra_max = ra_vals.min(), ra_vals.max()
    dec_min, dec_max = dec_vals.min(), dec_vals.max()
    ra_center, dec_center = wcs_header.get("CRVAL1", 0), wcs_header.get("CRVAL2", 0)

    radius = max(abs(ra_max - ra_min), abs(dec_max - dec_min)) / 2
    coord = SkyCoord(ra_center, dec_center, unit="deg")
    Simbad.add_votable_fields("dimensions", "otype", "otype_txt", "mesdistance","parallax")#, "flux")
    result = Simbad.query_region(coord, radius=radius * u.deg)

    df = result.to_pandas()
    #df = df[df["otype"].isin(chosen_stars.keys())].copy()
    df = df.dropna(subset=["ra", "dec"])

    group = df.groupby("main_id", as_index=False, dropna=False)
    df = group.aggregate(
        {
            "ra": "first",
            "dec": "first",
            "galdim_majaxis": "max",
            "galdim_minaxis": "max",
            "galdim_angle": "max",
            "otype": "first",
            "mesdistance.dist": "first",
            "mesdistance.unit": "first",
            "plx_value": "first",
            # "flux": "mean",
        }
    )
    df.sort_values(["galdim_majaxis", "galdim_minaxis"], ascending=False, inplace=True)

    # df.loc[pd.isna(df["flux"]), "flux"] = 0.0
    dist = df["mesdistance.dist"]
    unit = [0 if len(i)==0 else 1e3 if i.lower()[0]=='k' else 1e6 if i.lower()[0] == 'm' else 1 for i in df["mesdistance.unit"]]
    distance = dist * unit * pc_to_ly  # Convert distance to light years
    plx = (df["plx_value"]**-1)*pc_to_ly*1e3 # Convert parallax to distance in light years

    d_ly = np.nanmean([distance.values, plx.values], axis=0)

    x, y = wcs.world_to_pixel_values(df["ra"], df["dec"])

    df["galdim_majaxis_pix"] = (df["galdim_majaxis"] * 60) / pixel_scale/2
    df["galdim_minaxis_pix"] = (df["galdim_minaxis"] * 60) / pixel_scale/2

    db = {
        "name": df["main_id"].astype(str).tolist(),
        "x": x.round(1).tolist(),
        "y": y.round(1).tolist(),
        "rx": [0 if np.isnan(i) else round(i,1) for i in df.galdim_majaxis_pix],
        "ry": [0 if np.isnan(i) else round(i,1) for i in df.galdim_minaxis_pix],
        "angle": [0 if pd.isna(i) or i==32767 else int(i) for i in df.galdim_angle],
        "otype": [chosen_stars.get(o,"Unknown") for o in df["otype"].astype(str)],
        "dist": [0 if np.isnan(i) else round(i,1) for i in d_ly],
    }

    return {
        "width": nx,
        "height": ny,
        "overlays": json.dumps(db),
    }
