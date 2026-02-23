#!/usr/bin/env python3
"""Convert Chinese epub from vertical (直排) to horizontal (橫排) layout."""

import os
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile


def find_opf_path(zf):
    """Find content.opf path from META-INF/container.xml."""
    container = ET.fromstring(zf.read("META-INF/container.xml"))
    ns = {"c": "urn:oasis:names:tc:opendocument:xmlns:container"}
    rootfile = container.find(".//c:rootfile", ns)
    return rootfile.get("full-path")


def detect_vertical(epub_path):
    """Check if epub uses vertical writing mode or RTL page direction.

    Returns dict with keys: has_vertical_css, has_rtl_spine, needs_conversion.
    """
    result = {"has_vertical_css": False, "has_rtl_spine": False}

    with zipfile.ZipFile(epub_path, "r") as zf:
        opf_path = find_opf_path(zf)
        opf_content = zf.read(opf_path).decode("utf-8")
        if re.search(r'page-progression-direction\s*=\s*"rtl"', opf_content):
            result["has_rtl_spine"] = True

        for name in zf.namelist():
            if name.endswith((".css", ".xhtml", ".html", ".htm", ".xml")):
                content = zf.read(name).decode("utf-8", errors="replace")
                if re.search(r"writing-mode\s*:\s*vertical-(rl|lr)", content):
                    result["has_vertical_css"] = True
                    break

    result["needs_conversion"] = result["has_vertical_css"] or result["has_rtl_spine"]
    return result


def _make_test_epub(path, writing_mode="vertical-rl", page_direction="rtl"):
    """Create a minimal epub for testing."""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr(
            "META-INF/container.xml",
            '<?xml version="1.0"?>\n'
            '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container"'
            ' version="1.0">\n'
            "  <rootfiles>\n"
            '    <rootfile full-path="OEBPS/content.opf"'
            ' media-type="application/oebps-package+xml"/>\n'
            "  </rootfiles>\n"
            "</container>",
        )
        spine_attr = (
            f' page-progression-direction="{page_direction}"'
            if page_direction
            else ""
        )
        zf.writestr(
            "OEBPS/content.opf",
            f'<?xml version="1.0"?>\n'
            f'<package xmlns="http://www.idpf.org/2007/opf" version="3.0">\n'
            f'  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            f"    <dc:title>Test</dc:title>\n"
            f"    <dc:language>zh-TW</dc:language>\n"
            f"  </metadata>\n"
            f"  <manifest>\n"
            f'    <item id="ch1" href="chapter1.xhtml"'
            f' media-type="application/xhtml+xml"/>\n'
            f'    <item id="css" href="style.css" media-type="text/css"/>\n'
            f'    <item id="ncx" href="toc.ncx"'
            f' media-type="application/x-dtbncx+xml"/>\n'
            f"  </manifest>\n"
            f'  <spine{spine_attr} toc="ncx">\n'
            f'    <itemref idref="ch1"/>\n'
            f"  </spine>\n"
            f"</package>",
        )
        wm = f"writing-mode: {writing_mode};" if writing_mode else ""
        zf.writestr("OEBPS/style.css", f"body {{ {wm} }}")
        zf.writestr(
            "OEBPS/chapter1.xhtml",
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            '<head><link rel="stylesheet" href="style.css"/></head>\n'
            "<body><p>測試內容</p></body>\n"
            "</html>",
        )


def main():
    print("TODO: implement")
    return 1


if __name__ == "__main__":
    sys.exit(main())
