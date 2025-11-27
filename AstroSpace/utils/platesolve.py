import os
import re
from astropy.io import fits
from astropy.wcs import WCS

import numpy as np
import math
# from astroquery.vizier import Vizier
from astroquery.simbad import Simbad
from astropy.coordinates import SkyCoord, Angle
import astropy.units as u
from astropy.io.fits import Header
import pandas as pd
import hashlib
from flask import current_app, g
from astroquery.astrometry_net import AstrometryNet
from AstroSpace.utils.utils import resize_image
from AstroSpace.utils.xisf_reader import xisf_header
import json
# import scipy

pc_to_ly = 3.26156  # 1 parsec = 3.26156 light years

# Vizier.ROW_LIMIT = -1 # No limit on the number of rows returned


popular_catalogs = [
    r'\bM\s*\d+\b',                       # Messier (M31, M 31)
    r'\bNGC\s*\d+\b',                     # NGC (NGC 6871, NGC6871)
    r'\bIC\s*\d+\b',                      # IC
    r'(?<!\[)\bC\s*(?:10[0-9]|[1-9][0-9]?)(?![0-9+\-\]])\b',  # Caldwell 1-109 (no coords, no [C...])
    r'\bSH\s*\d+\s*[-–—]\s*\d+\b',        # Sharpless SH 2-101 (handles multiple spaces and different dashes)
    r'\bSh\s*\d+\s*[-–—]\s*\d+\b',        # Sharpless mixed case
    r'\bBarnard\s*\d+\b(?![.+-])',
    r'\bLBN\s*\d+\b(?![.+-])',            # LBN integer-only (prefer this)
    r'\bLDN\s*\d+\b(?![.+-])',             # LDN coordinate-style
    r'\bTGU\s*H\d+\sP\d+\b'
]

def extract_popular_id(ids_str):
    if not isinstance(ids_str, str):
        return None

    # normalize: collapse whitespace, normalize dashes
    s = ids_str
    s = re.sub(r'[–—]', '-', s)           # en/em dash -> hyphen
    s = re.sub(r'\s+', ' ', s).strip()    # collapse runs of whitespace to single space

    # split on pipe and attempt matches on each token (preferred)
    tokens = [t.strip() for t in s.split('|') if t.strip()]
    for pattern in popular_catalogs:
        prog = re.compile(pattern, flags=re.IGNORECASE)
        for tok in tokens:
            m = prog.search(tok)
            if m:
                # normalize spacing around hyphen: 'SH  2-101' -> 'SH 2-101'
                res = re.sub(r'\s+', ' ', m.group(0)).replace(' - ', '-')
                return res
    return None

def luminosity_size(sptype):
    if not isinstance(sptype, str) or sptype == '':
        return 0.227
    sptype = sptype.upper()
    # match Roman numeral or letters at end
    m = re.search(r'(0|I[AB]?|II|III|IV|V|VI|VII)$', sptype)
    if m:
        cls = m.group(0)
        size_map = {
            '0': 1,
            'IA': 0.909, 'IAB': 0.909, 'IB': 0.818,
            'II': 0.681,
            'III': 0.454,
            'IV': 0.318,
            'V': 0.227,
            'VI': 0.136,
            'VII': 0.09
        }
        return size_map.get(cls, 0.227)
    else:
        # fallback: supergiant keywords in type
        if 'S' in sptype and 'III' in sptype:
            return 0.818
        return 0.227

def bv2rgb(bv):
    t = (5000 / (bv + 1.84783)) + (5000 / (bv + .673913))
    x, y = 0, 0
    
    if 1667 <= t <= 4000:
        x = .17991 - (2.66124e8 / t**3) - (234358 / t**2) + (877.696 / t)
    elif 4000 < t:
        x = .24039 - (3.02585e9 / t**3) + (2.10704e6 / t**2) + (222.635 / t)
        
    if 1667 <= t <= 2222:
        y = (-1.1063814 * x**3) - (1.34811020 * x**2) + 2.18555832 * x - .20219683
    elif 2222 < t <= 4000:
        y = (-.9549476 * x**3) - (1.37418593 * x**2) + 2.09137015 * x - .16748867
    elif 4000 < t:
        y = (3.0817580 * x**3) - (5.87338670 * x**2) + 3.75112997 * x - .37001483
        
    X = 0 if y == 0 else x / y
    Z = 0 if y == 0 else (1 - x - y) / y
    
    r, g, b = np.dot([X, 1., Z],
        [[3.2406, -.9689, .0557], [-1.5372, 1.8758, -.204], [-.4986, .0415, 1.057]])
    
    R = np.clip(12.92 * r if (r <= 0.0031308) else 1.4 * (r**2 - .285714), 0, 1)
    G = np.clip(12.92 * g if (g <= 0.0031308) else 1.4 * (g**2 - .285714), 0, 1)
    B = np.clip(12.92 * b if (b <= 0.0031308) else 1.4 * (b**2 - .285714), 0, 1)
    
    return (int(R*255), int(G*255), int(B*255))

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

def pa_world_to_pixel(wcs, ra, dec, pa_deg):
    # center point
    c = SkyCoord(ra=ra*u.deg, dec=dec*u.deg)

    # move 1 arcsec in direction of PA
    pa = Angle(pa_deg, u.deg)
    d = 1 * u.arcsec
    c2 = c.directional_offset_by(pa, d)

    # convert both points to pixel coords
    x0, y0 = wcs.world_to_pixel(c)
    x1, y1 = wcs.world_to_pixel(c2)

    # compute pixel angle (atan2 correct orientation)
    ang = np.degrees(np.arctan2(y1 - y0, x1 - x0))

    return ang

def platesolve(image_path, user_id, fits_file=None):
    print("Plate solving image....")
    if fits_file:
        # If a FITS file is provided, use it to extract the WCS header
        print("Plate solving using Fits/XISF...")
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
        ast.api_key = g.user["astrometry_api_key"]
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
    print("Plate solving done.")
    
    print("Resizing image...")
    path, ext = os.path.splitext(image_path)
    thumbnail_path = path + "_thumbnail" + ext
    resize_image(image_path, thumbnail_path)
    thumbnail_path = f"{user_id}/{os.path.basename(thumbnail_path)}"
    return header_json, thumbnail_path, pixel_scale


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
    print("Generating overlays...")
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
    ra_vals, dec_vals = wcs.pixel_to_world_values(corners_pix[:, 0], corners_pix[:, 1])

    ra_min, ra_max = ra_vals.min(), ra_vals.max()
    dec_min, dec_max = dec_vals.min(), dec_vals.max()
    ra_center, dec_center = wcs_header.get("CRVAL1", 0), wcs_header.get("CRVAL2", 0)

    coord = SkyCoord(ra_center, dec_center, unit="deg")
    corners = SkyCoord(ra_vals, dec_vals, unit="deg")
    radius = coord.separation(corners).max()   # accurate angular radius   

    Simbad.reset_votable_fields()  # Reset to default fields
    Simbad.add_votable_fields(
        "ids",
        "galdim_majaxis",
        "galdim_minaxis",
        "galdim_angle",
        "otype",
    )

    print("Querying Simbad for objects in the field of view...")
    big_objects = "('G', 'GiC', 'GiG', 'GiP', 'GrG','HII', 'PN', 'SNR', 'Cl*', 'OpC', 'GlC', 'Neb', 'Cld', 'DNe','..27','..28','..30','BiC','CGC','ClG','EmG','flt','GNe','IG', 'LSB','MoC','PaG','PCG','rG','RNe', 'SBG','Sy1','Sy2','SyG')"
    result = Simbad.query_region(coord, radius=radius)#, criteria=f"otype IN {big_objects}")

    df = result.to_pandas()
    df['name'] = df['ids']#.apply(extract_popular_id)
    df = df[
        [   
            "name",
            "main_id",
            #"ids",
            "ra",
            "dec",
            "galdim_majaxis",
            "galdim_minaxis",
            "galdim_angle",
            "otype",
        ]
    ]
    
    df = df.dropna(subset=["ra", "dec"])#,"name"])
    box = (df.ra > ra_min) * (df.ra < ra_max) * (df.dec > dec_min) * (df.dec < dec_max)
    df = df[box]

    df.sort_values(["galdim_majaxis", "galdim_minaxis"], ascending=False, inplace=True)

    df["rx"] = (df["galdim_majaxis"] * 60) / pixel_scale / 2
    df["ry"] = (df["galdim_minaxis"] * 60) / pixel_scale / 2

    df = df.dropna(subset=["rx","ry"])
    df = df[df["rx"] >= 25]
    df = df[df["ry"] >= 25]
   
    x, y = wcs.world_to_pixel_values(df["ra"], df["dec"])
    angle = [
        pa_world_to_pixel(wcs, ra, dec, pa)
        if not pd.isna(pa) and pa != 32767 else 0
        for ra, dec, pa in zip(df["ra"], df["dec"], df["galdim_angle"])
    ]

    db = {
        "name": df["main_id"].astype(str).tolist(),
        #"ids": df["name"].astype(str).tolist(),
        "x": x.round(1).tolist(),
        "y": y.round(1).tolist(),
        "rx": [0 if np.isnan(i) else round(i, 1) for i in df.rx],
        "ry": [0 if np.isnan(i) else round(i, 1) for i in df.ry],
        "angle": angle,
        "otype": [chosen_stars.get(o, "Unknown") for o in df["otype"].astype(str)],
    }

    Simbad.reset_votable_fields()  # Reset to default fields
    Simbad.add_votable_fields(
        "otype",
        "plx_value",
        "U",
        "B",
        "V",
        "sp_type",
    )

    print("Querying Simbad for objects in the field of view...")
    result2 = Simbad.query_region(coord, radius=radius, criteria=f"otype NOT IN {big_objects}")

    df2 = result2.to_pandas()
    df2= df2[
        [
            "main_id",
            "ra",
            "dec",
            "otype",
            "plx_value",
            "U",
            "B",
            "V",
            "sp_type"
        ]
    ]
   
    # Convert parallax to distance in light years
    #d_ly = (df2["plx_value"] ** -1) * pc_to_ly * 1e3

    #HR Diagram data
    df2["HR_x"] = df2.B - df2.V
    df2["HR_y"] = df2.V - 5 * np.log10(100/df2.plx_value)
    hr = df2.dropna(subset=["HR_x", "HR_y"])
    x, y = wcs.world_to_pixel_values(hr["ra"], hr["dec"])
    hr = hr[['main_id','otype','sp_type','HR_x','HR_y']]
    
    hr = {
        "name": hr["main_id"].astype(str).tolist(), 
        "x": [round(i, 2) for i in hr["HR_x"]],
        "y": [round(i, 2) for i in hr["HR_y"]],
        "Object Type": [chosen_stars.get(o, "Unknown") for o in hr["otype"].astype(str)],
        "Spectral Class": [None if i.strip() == "" else i for i in hr["sp_type"]],
        "size": [luminosity_size(s) for s in hr.sp_type.values],
        "color": ['#%02x%02x%02x' % bv2rgb(s) for s in hr.HR_x.values],
        "pixel_x": x.astype(int).tolist(),
        "pixel_y": y.astype(int).tolist(),
        "label_x": "Color Index (B–V)",
        "label_y": "Absolute Magnitude (Mv)",
        "y_range": [20, -15],
        "plot_title": "Hertzsprung-Russell Diagram",
    }


    print("Generating grid lines...")
    grid_lines = make_grid_lines(
        wcs, ra_limits=[ra_min, ra_max], dec_limits=[dec_min, dec_max]
    )

    return {
        "width": nx,
        "height": ny,
        "overlays": db,
        "plots": {'hr': hr},
        "grid_lines": grid_lines,
    }
