import chardet
import codecs
import logging

from rococo.exceptions import EncodingNotFoundException

logger = logging.getLogger(__name__)


def _lookup_encoding(encoding):
    try:
        return codecs.lookup(encoding).name
    except LookupError:
        return None


def _get_encoding_mapping(encoding):
    """
    Some encodings parsed from the email parser do not confirm to the encodings in the standard python encoding.
    Therefore, this function serves as the lookup for the equivalent python standard encodings using the encoding
    passed as parameter. A default 'utf-8' is returned if no match is found

    For more information, please read the documentation at the provided url
    https://docs.python.org/3.11/library/codecs.html#standard-encodings

    About ansi_X3.4-1968:
    https://stackoverflow.com/questions/48743106/whats-ansi-x3-4-1968-encoding

    NOTE: keep on adding new encodings to this map as they come from newer emails
    """
    encodings_map = {
        "utf-8": "utf-8",
        "unicode": "utf-8",
        "utf8": "utf-8",
        "utf-8-bom": "utf-8-sig",
        "utf-16": "utf-16",
        "gb2312": "gb2312",
        "windows-874": "cp874",
        "windows-1250": "cp1250",
        "windows-1251": "cp1251",
        "windows-1252": "cp1252",
        "windows-1253": "cp1253",
        "windows-1254": "cp1254",
        "windows-1255": "cp1255",
        "windows-1256": "cp1256",
        "windows-1257": "cp1257",
        "windows-1258": "cp1258",
        "3dus-ascii": "us-ascii",
        "us-ascii": "us-ascii",
        "ascii": "us-ascii",
        "ansi_x3.4-1968": "us-ascii",
        "charset=us-ascii": "us-ascii",
        "x-mac-turkish": "mac_turkish",
        "iso-8859-8-i": "iso8859_8",
        "iso-8859-15": "iso8859_15",
        "iso-8859-1": "latin_1",
        "iso8859-1": "latin_1",
        "iso 8859-1": "latin_1",
        "iso-8859-2": "iso8859_2",
        "iso-2022-jp": "iso2022_jp",
        "koi8-r": "koi8_r",
        "koi8-u": "koi8_u",
        "ibm437": "cp437",
    }

    if encoding:
        encoding = encoding.lower()

    if encoding not in encodings_map:
        raise EncodingNotFoundException(
            message=f"{encoding} not found in encodings map")

    return encodings_map[encoding]


def _decode_content(encoding, raw_content):
    if not encoding:
        result = chardet.detect(raw_content)

        encoding = result['encoding']
        confidence = result['confidence']
        logger.info(
            f'Detected: encoding: {encoding}, confidence: {confidence} using chardet')

    standard_encoding = _lookup_encoding(encoding)
    if not standard_encoding:
        standard_encoding = _get_encoding_mapping(encoding)

    content = raw_content.decode(encoding=standard_encoding)
    return content
