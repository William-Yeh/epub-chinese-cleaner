#!/usr/bin/env python3
"""Convert Chinese epub from vertical (直排) to horizontal (橫排) layout."""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import zipfile

V2H_PUNCTUATION = {
    "︒": "。", "︑": "、", "︐": "，", "︔": "；", "︓": "：",
    "︕": "！", "︖": "？", "﹁": "「", "﹂": "」", "﹃": "『",
    "﹄": "』", "︽": "《", "︾": "》", "︵": "（", "︶": "）",
    "︷": "｛", "︸": "｝", "﹇": "［", "﹈": "］",
}

_v2h_re = re.compile("|".join(re.escape(k) for k in V2H_PUNCTUATION))


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
        if re.search(r"""page-progression-direction\s*=\s*["']rtl["']""", opf_content):
            result["has_rtl_spine"] = True

        for name in zf.namelist():
            if name.endswith((".css", ".xhtml", ".html", ".htm", ".xml")):
                content = zf.read(name).decode("utf-8", errors="replace")
                if re.search(r"(-(?:epub|webkit)-)?writing-mode\s*:\s*vertical-(rl|lr)", content):
                    result["has_vertical_css"] = True
                    break

    result["needs_conversion"] = result["has_vertical_css"] or result["has_rtl_spine"]
    return result


_WRITING_MODE_RE = re.compile(
    r"(-(?:epub|webkit)-)?writing-mode\s*:\s*vertical-(rl|lr)",
)


def rewrite_css_horizontal(content):
    """Replace vertical writing-mode with horizontal-tb in CSS/XHTML content."""
    return _WRITING_MODE_RE.sub(
        lambda m: f"{m.group(1) or ''}writing-mode: horizontal-tb", content
    )


def fix_spine_direction(opf_content):
    """Remove page-progression-direction='rtl' from <spine>."""
    return re.sub(
        r"""\s+page-progression-direction\s*=\s*["']rtl["']""",
        "",
        opf_content,
    )


def replace_punctuation(content):
    """Replace vertical-form Unicode punctuation with horizontal equivalents."""
    return _v2h_re.sub(lambda m: V2H_PUNCTUATION[m.group()], content)


def convert_direct(epub_path, output_path):
    """Convert epub to horizontal layout via direct file manipulation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract
        with zipfile.ZipFile(epub_path, "r") as zf:
            zf.extractall(tmpdir)
            opf_rel_path = find_opf_path(zf)
            names = zf.namelist()

        opf_full = os.path.join(tmpdir, opf_rel_path)

        # Fix OPF spine
        with open(opf_full, "r", encoding="utf-8") as f:
            opf_content = f.read()
        opf_content = fix_spine_direction(opf_content)
        with open(opf_full, "w", encoding="utf-8") as f:
            f.write(opf_content)

        # Fix CSS/XHTML files
        for name in names:
            if not name.endswith((".css", ".xhtml", ".html", ".htm")):
                continue
            full = os.path.join(tmpdir, name)
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
            original = content
            content = rewrite_css_horizontal(content)
            content = replace_punctuation(content)
            if content != original:
                with open(full, "w", encoding="utf-8") as f:
                    f.write(content)

        # Re-zip: mimetype must be first, uncompressed
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            mimetype_path = os.path.join(tmpdir, "mimetype")
            if os.path.exists(mimetype_path):
                zout.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype":
                    continue
                zout.write(os.path.join(tmpdir, name), name)

    print(f"Converted (direct): {output_path}")


_CALIBRE_PATHS = [
    "calibre-debug",  # in PATH
    "/Applications/calibre.app/Contents/MacOS/calibre-debug",  # macOS
]


def find_calibre_debug():
    """Find calibre-debug executable. Returns path or None."""
    for path in _CALIBRE_PATHS:
        if shutil.which(path):
            return path
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


_CALIBRE_PLUGIN_SCRIPT = (
    "from calibre_plugins.chinese_text.main import main; "
    "import sys; sys.exit(main(sys.argv[1:], ('cli','0.0')))"
)


def convert_via_calibre(epub_path, output_path, calibre_debug):
    """Convert epub using Calibre's TradSimpChinese plugin CLI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "_plugin_runner.py")
        with open(script_path, "w") as f:
            f.write(_CALIBRE_PLUGIN_SCRIPT)

        result = subprocess.run(
            [
                calibre_debug, "-e", script_path,
                "--",
                "-td", "h",
                "-up",
                "-d", "t2t",
                "-od", tmpdir,
                "-f",
                epub_path,
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"Calibre plugin failed: {result.stderr}", file=sys.stderr)
            return False

        # Find the output file in tmpdir
        outputs = [f for f in os.listdir(tmpdir) if f.endswith(".epub")]
        if not outputs:
            print("Calibre plugin produced no output", file=sys.stderr)
            return False

        generated = os.path.join(tmpdir, outputs[0])

        # Post-process: fix spine direction (plugin may not handle this)
        _fix_spine_in_epub(generated, output_path)

    print(f"Converted (Calibre): {output_path}")
    return True


def _fix_spine_in_epub(epub_path, output_path):
    """Read epub, fix spine direction, write to output_path."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(epub_path, "r") as zf:
            zf.extractall(tmpdir)
            opf_rel = find_opf_path(zf)
            names = zf.namelist()

        opf_full = os.path.join(tmpdir, opf_rel)
        with open(opf_full, "r", encoding="utf-8") as f:
            content = f.read()
        fixed = fix_spine_direction(content)
        if fixed != content:
            with open(opf_full, "w", encoding="utf-8") as f:
                f.write(fixed)

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zout:
            mimetype_path = os.path.join(tmpdir, "mimetype")
            if os.path.exists(mimetype_path):
                zout.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
            for name in names:
                if name == "mimetype":
                    continue
                zout.write(os.path.join(tmpdir, name), name)


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
            "<body><p>測試內容︒︑︐</p></body>\n"
            "</html>",
        )


def _run_self_test():
    """Create a test epub, convert it, verify results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_in = os.path.join(tmpdir, "test_vertical.epub")
        test_out = os.path.join(tmpdir, "test_horizontal.epub")

        _make_test_epub(test_in, writing_mode="vertical-rl", page_direction="rtl")

        # Should need conversion
        info = detect_vertical(test_in)
        assert info["needs_conversion"], "Detection should find vertical layout"
        assert info["has_vertical_css"], "Should detect vertical CSS"
        assert info["has_rtl_spine"], "Should detect RTL spine"

        # Convert
        convert_direct(test_in, test_out)

        # Verify output is horizontal
        info2 = detect_vertical(test_out)
        assert not info2["needs_conversion"], "Output should be horizontal"
        assert not info2["has_vertical_css"], "Output should have no vertical CSS"
        assert not info2["has_rtl_spine"], "Output should have no RTL spine"

        # Verify punctuation replacement
        with zipfile.ZipFile(test_out, "r") as zf:
            for name in zf.namelist():
                content = zf.read(name).decode("utf-8", errors="replace")
                if name.endswith(".xhtml"):
                    assert "︒" not in content, f"Vertical punct still in {name}"
                    assert "。" in content, f"Horizontal punct missing in {name}"
                if name.endswith(".css"):
                    assert "vertical-rl" not in content, f"vertical-rl still in {name}"

        # Test already-horizontal epub
        test_h = os.path.join(tmpdir, "test_already_h.epub")
        _make_test_epub(test_h, writing_mode=None, page_direction=None)
        info3 = detect_vertical(test_h)
        assert not info3["needs_conversion"], "Horizontal epub should not need conversion"

    print("All self-tests passed.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Convert Chinese epub from vertical (直排) to horizontal (橫排) layout."
    )
    parser.add_argument("input", nargs="?", help="Input epub file path")
    parser.add_argument("-o", "--output", help="Output epub file path (default: <input>_horizontal.epub)")
    parser.add_argument("--self-test", action="store_true", help="Run self-test with a generated test epub")
    args = parser.parse_args()

    if args.self_test:
        return _run_self_test()

    if not args.input:
        parser.print_help()
        return 1

    if not os.path.isfile(args.input):
        print(f"File not found: {args.input}", file=sys.stderr)
        return 1

    # Detection
    info = detect_vertical(args.input)
    if not info["needs_conversion"]:
        print("Already horizontal — no conversion needed.")
        return 0

    print(f"Detected: vertical_css={info['has_vertical_css']}, rtl_spine={info['has_rtl_spine']}")

    # Output path
    output = args.output
    if not output:
        base, ext = os.path.splitext(args.input)
        output = f"{base}_horizontal{ext}"

    # Try Calibre first
    calibre = find_calibre_debug()
    if calibre:
        print(f"Using Calibre: {calibre}")
        if convert_via_calibre(args.input, output, calibre):
            return 0
        print("Calibre failed, falling back to direct manipulation.", file=sys.stderr)

    # Fallback: direct manipulation
    convert_direct(args.input, output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
