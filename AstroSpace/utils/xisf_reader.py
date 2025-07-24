from astropy.io import fits
from xisf import XISF
import xml.etree.ElementTree as ET

class customXISF(XISF):
    def _read(self):
        if isinstance(self._fname, str):
            f = open(self._fname, "rb")
        else:
            f = self._fname  # Assume it's a file-like object

        # Check XISF signature
        signature = f.read(len(self._signature))
        if signature != self._signature:
            raise ValueError("File doesn't have XISF signature")

        # Get header length
        self._headerlength = int.from_bytes(f.read(self._headerlength_len), byteorder="little")
        # Equivalent:
        # self._headerlength = np.fromfile(f, dtype=np.uint32, count=1)[0]

        # Skip reserved field
        _ = f.read(self._reserved_len)

        # Get XISF (XML) Header
        self._xisf_header = f.read(self._headerlength)
        self._xisf_header_xml = ET.fromstring(self._xisf_header)

        if isinstance(self._fname, str):
            f.close()

        self._analyze_header()

    def _read_attached_data_block(self, elem):
        # Position and size of the Data Block containing the image data
        method, pos, size = elem["location"]

        assert method == "attachment"

        if isinstance(self._fname, str):
            f = open(self._fname, "rb")
        else:
            f = self._fname  # Assume it's a file-like object

        f.seek(pos)
        data = f.read(size)

        if isinstance(self._fname, str):
            f.close()

        if "compression" in elem:
            data = XISF._decompress(data, elem)

        return data

def xisf_header(xisf_file):
    f = customXISF(xisf_file)
    meta = f.get_images_metadata()[0]
    wcs_header = fits.Header()

    projection = meta['XISFProperties']['PCL:AstrometricSolution:ProjectionSystem']['value']

    # Mapping PixInsight to FITS CTYPE codes
    projection_map = {
        'Gnomonic': ('RA---TAN', 'DEC--TAN'),
        'PlateCarree': ('RA---CAR', 'DEC--CAR'),
        'Stereographic': ('RA---STG', 'DEC--STG'),
        'Orthographic': ('RA---SIN', 'DEC--SIN'),
        'Aitoff': ('RA---AIT', 'DEC--AIT'),
        'HammerAitoff': ('RA---AIT', 'DEC--AIT'),
        'Mercator': ('RA---MER', 'DEC--MER'),
    }

    ctype1, ctype2 = projection_map.get(projection, ('RA---TAN', 'DEC--TAN'))  # default to TAN

    wcs_header['CTYPE1'] = ctype1
    wcs_header['CTYPE2'] = ctype2

    # CRVAL: celestial coordinates at reference pixel
    crval = meta['XISFProperties']['PCL:AstrometricSolution:ReferenceCelestialCoordinates']['value']
    wcs_header['CRVAL1'] = crval[0]  # RA in degrees
    wcs_header['CRVAL2'] = crval[1]  # DEC in degrees

    # CRPIX: reference pixel (image coordinates)
    crpix = meta['XISFProperties']['PCL:AstrometricSolution:ReferenceImageCoordinates']['value']
    wcs_header['CRPIX1'] = crpix[0]
    wcs_header['CRPIX2'] = crpix[1]

    # CD matrix: transformation matrix
    cd = meta['XISFProperties']['PCL:AstrometricSolution:LinearTransformationMatrix']['value']
    wcs_header['CD1_1'] = cd[0][0]
    wcs_header['CD1_2'] = cd[0][1]
    wcs_header['CD2_1'] = cd[1][0]
    wcs_header['CD2_2'] = cd[1][1]

    # Optionally, image size
    shape = meta['geometry']  # (height, width, channels)
    wcs_header['NAXIS'] = 2
    wcs_header['NAXIS1'] = shape[1]
    wcs_header['NAXIS2'] = shape[0]

    wcs_header['RADESYS'] = meta['XISFProperties']['Observation:CelestialReferenceSystem']['value']
    wcs_header['EQUINOX'] = meta['XISFProperties']['Observation:Equinox']['value']

    wcs_header["IMAGEW"] = meta["geometry"][0]
    wcs_header["IMAGEh"] = meta["geometry"][1]


    return wcs_header