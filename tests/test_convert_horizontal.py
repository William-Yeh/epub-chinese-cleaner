"""Tests for convert_horizontal.py."""

import os
import zipfile
from unittest.mock import patch

import pytest

from convert_horizontal import (
    V2H_PUNCTUATION,
    convert_direct,
    detect_vertical,
    find_calibre_debug,
    find_opf_path,
    fix_spine_direction,
    main,
    replace_punctuation,
    rewrite_css_horizontal,
)


# ── Unit tests: pure functions ──────────────────────────────────────────


class TestRewriteCssHorizontal:
    def test_standard(self):
        assert rewrite_css_horizontal("writing-mode: vertical-rl") == "writing-mode: horizontal-tb"

    def test_vendor_epub(self):
        assert rewrite_css_horizontal("-epub-writing-mode: vertical-rl") == "-epub-writing-mode: horizontal-tb"

    def test_vendor_webkit(self):
        assert rewrite_css_horizontal("-webkit-writing-mode: vertical-rl") == "-webkit-writing-mode: horizontal-tb"

    def test_vertical_lr(self):
        assert rewrite_css_horizontal("writing-mode: vertical-lr") == "writing-mode: horizontal-tb"

    def test_no_match(self):
        original = "writing-mode: horizontal-tb"
        assert rewrite_css_horizontal(original) == original

    def test_embedded_in_css_rule(self):
        css = "body { writing-mode: vertical-rl; color: red; }"
        assert "horizontal-tb" in rewrite_css_horizontal(css)
        assert "vertical-rl" not in rewrite_css_horizontal(css)


class TestFixSpineDirection:
    def test_double_quotes(self):
        opf = '<spine page-progression-direction="rtl" toc="ncx">'
        assert fix_spine_direction(opf) == '<spine toc="ncx">'

    def test_single_quotes(self):
        opf = "<spine page-progression-direction='rtl' toc='ncx'>"
        assert fix_spine_direction(opf) == "<spine toc='ncx'>"

    def test_no_match(self):
        opf = '<spine toc="ncx">'
        assert fix_spine_direction(opf) == opf

    def test_extra_whitespace(self):
        opf = '<spine  page-progression-direction = "rtl"  toc="ncx">'
        result = fix_spine_direction(opf)
        assert "page-progression-direction" not in result
        assert "toc" in result


class TestReplacePunctuation:
    @pytest.mark.parametrize("vertical,horizontal", list(V2H_PUNCTUATION.items()))
    def test_all_mappings(self, vertical, horizontal):
        assert replace_punctuation(vertical) == horizontal

    def test_mixed_content(self):
        text = "這是測試︒另一段︑再來"
        result = replace_punctuation(text)
        assert "︒" not in result
        assert "︑" not in result
        assert "。" in result
        assert "、" in result
        assert "這是測試" in result

    def test_no_match_passthrough(self):
        text = "This is plain English text."
        assert replace_punctuation(text) == text


class TestV2hPunctuationCompleteness:
    def test_has_19_entries(self):
        assert len(V2H_PUNCTUATION) == 19


# ── Integration tests: epub I/O ─────────────────────────────────────────


class TestFindOpfPath:
    def test_standard_oebps(self, tmp_epub):
        path = tmp_epub()
        with zipfile.ZipFile(path, "r") as zf:
            assert find_opf_path(zf) == "OEBPS/content.opf"


class TestDetectVertical:
    def test_both(self, tmp_epub):
        path = tmp_epub(writing_mode="vertical-rl", page_direction="rtl")
        info = detect_vertical(path)
        assert info["has_vertical_css"] is True
        assert info["has_rtl_spine"] is True
        assert info["needs_conversion"] is True

    def test_css_only(self, tmp_epub):
        path = tmp_epub(writing_mode="vertical-rl", page_direction=None)
        info = detect_vertical(path)
        assert info["has_vertical_css"] is True
        assert info["has_rtl_spine"] is False
        assert info["needs_conversion"] is True

    def test_spine_only(self, tmp_epub):
        path = tmp_epub(writing_mode=None, page_direction="rtl")
        info = detect_vertical(path)
        assert info["has_vertical_css"] is False
        assert info["has_rtl_spine"] is True
        assert info["needs_conversion"] is True

    def test_vendor_prefix(self, tmp_path):
        """Detect -epub-writing-mode: vertical-rl in CSS."""
        path = str(tmp_path / "vendor.epub")
        # Build a minimal epub with vendor-prefixed writing-mode
        with zipfile.ZipFile(path, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr(
                "META-INF/container.xml",
                '<?xml version="1.0"?>\n'
                '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">\n'
                "  <rootfiles>\n"
                '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
                "  </rootfiles>\n"
                "</container>",
            )
            zf.writestr(
                "OEBPS/content.opf",
                '<?xml version="1.0"?>\n'
                '<package xmlns="http://www.idpf.org/2007/opf" version="3.0">\n'
                '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
                "    <dc:title>Test</dc:title>\n"
                "  </metadata>\n"
                "  <manifest/>\n"
                '  <spine toc="ncx"/>\n'
                "</package>",
            )
            zf.writestr("OEBPS/style.css", "body { -epub-writing-mode: vertical-rl; }")
        info = detect_vertical(path)
        assert info["has_vertical_css"] is True

    def test_horizontal(self, tmp_epub):
        path = tmp_epub(writing_mode=None, page_direction=None)
        info = detect_vertical(path)
        assert info["has_vertical_css"] is False
        assert info["has_rtl_spine"] is False
        assert info["needs_conversion"] is False


class TestConvertDirect:
    def test_full_conversion(self, tmp_epub, tmp_path):
        src = tmp_epub()
        out = str(tmp_path / "output.epub")
        convert_direct(src, out)

        # Output should be horizontal
        info = detect_vertical(out)
        assert info["needs_conversion"] is False

        # Check CSS and punctuation inside output
        with zipfile.ZipFile(out, "r") as zf:
            for name in zf.namelist():
                content = zf.read(name).decode("utf-8", errors="replace")
                if name.endswith(".css"):
                    assert "vertical-rl" not in content
                    assert "horizontal-tb" in content
                if name.endswith(".xhtml"):
                    assert "︒" not in content
                    assert "。" in content

    def test_preserves_mimetype(self, tmp_epub, tmp_path):
        src = tmp_epub()
        out = str(tmp_path / "output.epub")
        convert_direct(src, out)

        with zipfile.ZipFile(out, "r") as zf:
            # mimetype must be the first entry
            assert zf.namelist()[0] == "mimetype"
            # mimetype must be stored (uncompressed)
            info = zf.getinfo("mimetype")
            assert info.compress_type == zipfile.ZIP_STORED

    def test_single_quote_spine(self, tmp_path):
        """OPF with single-quoted page-progression-direction='rtl'."""
        src = str(tmp_path / "sq.epub")
        out = str(tmp_path / "sq_out.epub")

        # Build epub with single-quoted spine attribute
        with zipfile.ZipFile(src, "w") as zf:
            zf.writestr("mimetype", "application/epub+zip")
            zf.writestr(
                "META-INF/container.xml",
                '<?xml version="1.0"?>\n'
                '<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">\n'
                "  <rootfiles>\n"
                '    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>\n'
                "  </rootfiles>\n"
                "</container>",
            )
            zf.writestr(
                "OEBPS/content.opf",
                '<?xml version="1.0"?>\n'
                '<package xmlns="http://www.idpf.org/2007/opf" version="3.0">\n'
                '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
                "    <dc:title>Test</dc:title>\n"
                "  </metadata>\n"
                "  <manifest>\n"
                '    <item id="ch1" href="ch.xhtml" media-type="application/xhtml+xml"/>\n'
                "  </manifest>\n"
                "  <spine page-progression-direction='rtl' toc='ncx'>\n"
                '    <itemref idref="ch1"/>\n'
                "  </spine>\n"
                "</package>",
            )
            zf.writestr("OEBPS/ch.xhtml", "<html><body><p>Test</p></body></html>")

        convert_direct(src, out)

        with zipfile.ZipFile(out, "r") as zf:
            opf = zf.read("OEBPS/content.opf").decode("utf-8")
            assert "page-progression-direction" not in opf


class TestFindCalibreDebug:
    def test_not_found(self):
        with patch("convert_horizontal.shutil.which", return_value=None), \
             patch("convert_horizontal.os.path.isfile", return_value=False):
            assert find_calibre_debug() is None


# ── CLI tests ────────────────────────────────────────────────────────────


class TestCLI:
    def test_self_test(self):
        assert main.__module__ == "convert_horizontal"
        # Simulate --self-test
        with patch("sys.argv", ["convert_horizontal", "--self-test"]):
            ret = main()
        assert ret == 0

    def test_no_args(self, capsys):
        with patch("sys.argv", ["convert_horizontal"]):
            ret = main()
        assert ret == 1
        captured = capsys.readouterr()
        assert "usage" in captured.out.lower() or "usage" in captured.err.lower()

    def test_missing_file(self, capsys):
        with patch("sys.argv", ["convert_horizontal", "/nonexistent/file.epub"]):
            ret = main()
        assert ret == 1
        captured = capsys.readouterr()
        assert "not found" in captured.err.lower()

    def test_already_horizontal(self, tmp_epub, capsys):
        path = tmp_epub(writing_mode=None, page_direction=None)
        with patch("sys.argv", ["convert_horizontal", path]):
            ret = main()
        assert ret == 0
        captured = capsys.readouterr()
        assert "horizontal" in captured.out.lower() or "no conversion" in captured.out.lower()
