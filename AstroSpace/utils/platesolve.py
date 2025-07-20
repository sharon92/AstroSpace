import os
from astropy.wcs import WCS
import numpy as np

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
        hrs = ra // 15 
        mins = (ra%15)*4
        secs = (mins % 1) * 60
        labels.append(
            {
                "text": f"{hrs:02.0f}h {int(mins):02.0f}m {secs:02.1f}s",
                "x": float(pix[mid][0] - 15),
                "y": float(pix[mid][1] - 10),
                 "rotation": -90
            }
        )

    # Dec lines (constant Dec, varying RA)
    for dec in decs:
        coords = np.column_stack((ras, np.full_like(ras, dec)))
        pix = wcs.all_world2pix(coords, 0)
        dec_lines.append(pix.tolist())

        mid = dec_count // 2
        labels.append(
            {
                "text": f"{int(dec):+03d}°{int(abs(dec % 1) * 60):02d}′",
                "x": float(pix[mid][0] + 20),
                "y": float(pix[mid][1] - 15),
                "rotation": 0
            }
        )

    return {
        "ra_lines": ra_lines,
        "dec_lines": dec_lines,
        "labels": labels
    }



def platesolve(image_path, user_id):
    print("Plate solving image....")
    # Initialize AstrometryNet with your API key
    ast = AstrometryNet()
    ast.api_key = current_app.config["ASTROMETRY_API_KEY"]
    wcs_header = ast.solve_from_image(image_path, solve_timeout=1800)

    wcs = WCS(wcs_header)
    ps_x, ps_y = wcs.proj_plane_pixel_scales()
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

    ps_x, ps_y = wcs.proj_plane_pixel_scales()
    pixel_scale = np.mean([ps_x.value, ps_y.value]) * 3600

    simbad_desc = os.path.join(
        current_app.config["root_path"], "utils", "simbad_object_description.json"
    )
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
    Simbad.reset_votable_fields()  # Reset to default fields
    Simbad.add_votable_fields(
        "galdim_majaxis",
        "galdim_minaxis",
        "galdim_angle",
        "otype",
        "mesdistance",
        "plx_value",
    )

    print("Querying Simbad for objects in the field of view...")
    result = Simbad.query_region(coord, radius=radius * u.deg)

    Simbad.reset_votable_fields()
    Simbad.add_votable_fields(
        "mesdiameter",
        "U",
        "B",
        "V",
        "R",
        "I",
        "pmra",
        "pmdec",
        "rvz_radvel",
        "rvz_redshift",
        "sp_type",
    )
    result2 = Simbad.query_region(coord, radius=radius * u.deg)

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
            "mesdistance.dist",
            "mesdistance.unit",
            "plx_value",
        ]
    ]
    df2 = result2.to_pandas()
    df2 = df2[
        [
            "main_id",
            "ra",
            "dec",
            "mesdiameter.diameter",
            "mesdiameter.unit",
            "V",
            "U",
            "R",
            "B",
            "I",
            "pmra",
            "pmdec",
            "rvz_radvel",
            "rvz_redshift",
            "sp_type",
        ]
    ]

    # df = df[df["otype"].isin(chosen_stars.keys())].copy()
    df = df.dropna(subset=["ra", "dec"])
    box = (df.ra > ra_min) * (df.ra < ra_max) * (df.dec > dec_min) * (df.dec < dec_max)
    df = df[box]

    df2 = df2.dropna(subset=["ra", "dec"])
    box = (
        (df2.ra > ra_min)
        * (df2.ra < ra_max)
        * (df2.dec > dec_min)
        * (df2.dec < dec_max)
    )
    df2 = df2[box]

    group = df.groupby("main_id", as_index=False, dropna=False)
    df = group.aggregate(
        {
            "ra": "first",
            "dec": "first",
            "galdim_majaxis": "max",
            "galdim_minaxis": "max",
            "galdim_angle": "max",
            "otype": "first",
            # "mesdiameter.diameter": "first",
            # "mesdiameter.unit": "first",
            "mesdistance.dist": "first",
            "mesdistance.unit": "first",
            "plx_value": "first",
        }
    )
    group2 = df2.groupby("main_id", as_index=False, dropna=False)
    df2 = group2.aggregate(
        {
            "V": "first",
            "U": "first",
            "R": "first",
            "B": "first",
            "I": "first",
            "pmra": "first",
            "pmdec": "first",
            "rvz_radvel": "first",
            "rvz_redshift": "first",
            "sp_type": "first",
        }
    )
    
    df.sort_values(["galdim_majaxis", "galdim_minaxis"], ascending=False, inplace=True)

    # df.loc[pd.isna(df["flux"]), "flux"] = 0.0
    dist = df["mesdistance.dist"]
    unit = [
        0
        if len(i) == 0
        else 1e3
        if i.lower()[0] == "k"
        else 1e6
        if i.lower()[0] == "m"
        else 1
        for i in df["mesdistance.unit"]
    ]
    distance = dist * unit * pc_to_ly  # Convert distance to light years
    plx = (
        (df["plx_value"] ** -1) * pc_to_ly * 1e3
    )  # Convert parallax to distance in light years

    d_ly = np.nanmean([distance.values, plx.values], axis=0)
    # df["dist"] = d_ly
    # df = df.dropna(subset=["dist"])

    x, y = wcs.world_to_pixel_values(df["ra"], df["dec"])

    df["rx"] = (df["galdim_majaxis"] * 60) / pixel_scale / 2
    df["ry"] = (df["galdim_minaxis"] * 60) / pixel_scale / 2

    # catalogs = Vizier.query_region(coord, radius=radius * u.deg, catalog="IV/38/tic")

    # if catalogs:
    #     tic = catalogs[0]
    #     df2 = tic.to_pandas()[["TIC","RAJ2000", "DEJ2000", "Teff", "logg", "Mass","Dist", "Rad"]]
    #     df2.rename(columns={
    #         "TIC": "main_id",
    #         "RAJ2000": "ra",
    #         "DEJ2000": "dec",
    #     }, inplace=True)
    #     df2 = df2.dropna(subset=["ra", "dec","Teff", "logg", "Mass","Dist", "Rad"])
    #     box = (df2.ra > ra_min) * (df2.ra < ra_max) * (df2.dec > dec_min) * (df2.dec < dec_max)
    #     df2 = df2[box]
    #     df2["Dist"] *= pc_to_ly  # Convert distance to light years

    #     # For df2
    #     coords_df2 = SkyCoord(ra=df2["ra"].values * u.deg,
    #                         dec=df2["dec"].values * u.deg,
    #                         distance=df2["Dist"].values * u.lyr)
    #     xyz_df2 = coords_df2.cartesian.xyz.value.T  # shape (N, 3)

    #     # For df
    #     coords_df = SkyCoord(ra=df["ra"].values * u.deg,
    #                         dec=df["dec"].values * u.deg,
    #                         distance=df["dist"].values * u.lyr)
    #     xyz_df = coords_df.cartesian.xyz.value.T

    #     tree = scipy.spatial.cKDTree(xyz_df)
    #     n_dist,n_idx = tree.query(xyz_df2)

    #     df = pd.concat([df, df2], ignore_index=True)

    db = {
        "name": df["main_id"].astype(str).tolist(),
        "x": x.round(1).tolist(),
        "y": y.round(1).tolist(),
        "rx": [0 if np.isnan(i) else round(i, 1) for i in df.rx],
        "ry": [0 if np.isnan(i) else round(i, 1) for i in df.ry],
        "angle": [0 if pd.isna(i) or i == 32767 else int(i) for i in df.galdim_angle],
        "otype": [chosen_stars.get(o, "Unknown") for o in df["otype"].astype(str)],
        "dist": [None if np.isnan(i) else round(i, 1) for i in d_ly],
    }

    db2 = {
        # "diameter": [],
        "V": [None if np.isnan(i) else round(i, 1) for i in df2.V],
        "U": [None if np.isnan(i) else round(i, 1) for i in df2.U],
        "R": [None if np.isnan(i) else round(i, 1) for i in df2.R],
        "B": [None if np.isnan(i) else round(i, 1) for i in df2.B],
        "I": [None if np.isnan(i) else round(i, 1) for i in df2.I],
        "pmra": [None if np.isnan(i) else round(i, 1) for i in df2["pmra"]],
        "pmdec": [None if np.isnan(i) else round(i, 1) for i in df2["pmdec"]],
        "rvz_radvel": [None if np.isnan(i) else round(i, 1) for i in df2["rvz_radvel"]],
        "rvz_redshift": [
            None if np.isnan(i) else round(i, 8) for i in df2["rvz_redshift"]
        ],
        "sp_type": [None if i.strip() == "" else i for i in df2["sp_type"]],
    }

    print("Generating grid lines...")
    grid_lines = make_grid_lines(
        wcs, ra_limits=[ra_min, ra_max], dec_limits=[dec_min, dec_max]
    )

    return {
        "width": nx,
        "height": ny,
        "overlays": json.dumps(db),
        "plots": json.dumps(db2),
        "grid_lines": json.dumps(grid_lines),
    }
