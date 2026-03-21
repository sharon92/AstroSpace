from astropy.io import fits
import logging
from xisf import XISF
import xml.etree.ElementTree as ET
import numpy as np
import ast 
from AstroSpace.logging_utils import debug_log

class customXISF(XISF):
    def _read(self):
        if isinstance(self._fname, str):
            f = open(self._fname, "rb")
        else:
            f = self._fname  # Assume it's a file-like object

        # Check XISF signature
        signature = f.read(len(self._signature))
        if signature != self._signature:
            debug_log(
                "XISF signature mismatch while reading file=%s",
                getattr(self._fname, "name", self._fname),
                level=logging.WARNING,
            )
            raise ValueError("File doesn't have XISF signature")

        # Get header length
        self._headerlength = int.from_bytes(f.read(self._headerlength_len), byteorder="little")
        # Equivalent:
        # self._headerlength = np.fromfile(f, dtype=np.uint32, count=1)[0]

        # Skip reserved field
        _ = f.read(self._reserved_len)

        # Get XISF (XML) Header
        #print('header length',self._headerlength)
        self._xisf_header = f.read(self._headerlength)
        #print(self._xisf_header[:100])
        self._xisf_header_xml = ET.fromstring(self._xisf_header)

        if isinstance(self._fname, str):
            f.close()

        self._analyze_header()

    def _process_property(self, p_et):
        p_dict = p_et.attrib.copy()

        if p_dict["type"] == "TimePoint":
            # Timepoint 'value' attribute already set (as str)
            # TODO: convert to datetime?
            pass
        elif p_dict["type"] == "String":
            p_dict["value"] = p_et.text
            if "location" in p_dict:
                # Process location and compression attributes to find data block
                self._process_location_compression(p_dict)
                p_dict["value"] = self._read_data_block(p_dict).decode("utf-8")
        elif p_dict["type"] == "Boolean":
            # Boolean valid values are "true" and "false"
            p_dict["value"] = p_dict["value"] == "true"
        elif "value" in p_et.attrib:
            # Scalars (Float64, UInt32, etc.) and Complex*
            p_dict["value"] = ast.literal_eval(p_dict["value"])
        elif "Vector" in p_dict["type"]:
            p_dict["value"] = p_et.text
            p_dict["length"] = int(p_dict["length"])
            p_dict["dtype"] = self._parse_vector_dtype(p_dict["type"])
            self._process_location_compression(p_dict)
            raw_data = self._read_data_block(p_dict)
            if raw_data == b'':
                p_dict["value"] = None
            else: 
                p_dict["value"] = np.frombuffer(raw_data, dtype=p_dict["dtype"], count=p_dict["length"])
        elif "Matrix" in p_dict["type"]:
            p_dict["value"] = p_et.text
            p_dict["rows"] = int(p_dict["rows"])
            p_dict["columns"] = int(p_dict["columns"])
            length = p_dict["rows"] * p_dict["columns"]
            p_dict["dtype"] = self._parse_vector_dtype(p_dict["type"])
            self._process_location_compression(p_dict)
            raw_data = self._read_data_block(p_dict)
            if raw_data == b'':
                p_dict["value"] = None
            else: 
                p_dict["value"] = np.frombuffer(raw_data, dtype=p_dict["dtype"], count=length)
                p_dict["value"] = p_dict["value"].reshape((p_dict["rows"], p_dict["columns"]))

        else:
            debug_log(
                "Unsupported XISF property type=%s",
                p_dict["type"],
                level=logging.WARNING,
            )
            p_dict = False

        return p_dict

    def _read_attached_data_block(self, elem):
        # Position and size of the Data Block containing the image data
        
        method, pos, size = elem["location"]

        assert method == "attachment"

        if isinstance(self._fname, str):
            f = open(self._fname, "rb")
        else:
            f = self._fname  # Assume it's a file-like object

        f.seek(0,2)
        if pos > f.tell():
            debug_log(
                "Requested XISF attachment position exceeds file size (requested=%s, total=%s)",
                pos,
                f.tell(),
                level=logging.WARNING,
            )
            return b''
        
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
