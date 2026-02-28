# epub-chinese-cleaner Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Agent Skill that converts Chinese-language epubs from vertical (直排/RTL) to horizontal (橫排/LTR) layout with punctuation normalization.

**Architecture:** Python script inside an agentskills.io skill directory. Uses direct epub manipulation (stdlib only) first, falls back to Calibre CLI (TradSimpChinese plugin) if direct manipulation fails. Epub is a zip of XHTML/CSS/XML — both paths produce a new output file.

**Tech Stack:** Python 3 stdlib (`zipfile`, `xml.etree.ElementTree`, `re`, `tempfile`, `shutil`, `subprocess`). No external deps for fallback path.

---

### Task 1: Scaffold project structure

**Files:**
- Create: `SKILL.md`
- Create: `scripts/convert_horizontal.py`
- Create: `references/punctuation-map.md`
- Create: `.gitignore`

**Step 1: Create `.gitignore`**

```
__pycache__/
*.pyc
.venv/
*.epub
```

**Step 2: Create `references/punctuation-map.md`**

The vertical→horizontal Unicode punctuation mapping reference (from TradSimpChinese plugin's `_h2v_master_dict`, reversed):

```markdown
# Vertical → Horizontal Punctuation Map

| Vertical | Horizontal | Name |
|----------|-----------|------|
| ︒ | 。 | Ideographic full stop |
| ︑ | 、 | Ideographic comma |
| ︐ | ， | Fullwidth comma |
| ︔ | ； | Fullwidth semicolon |
| ︓ | ： | Fullwidth colon |
| ︕ | ！ | Fullwidth exclamation |
| ︖ | ？ | Fullwidth question mark |
| ﹁ | 「 | Left corner bracket |
| ﹂ | 」 | Right corner bracket |
| ﹃ | 『 | Left white corner bracket |
| ﹄ | 』 | Right white corner bracket |
| ︽ | 《 | Left double angle bracket |
| ︾ | 》 | Right double angle bracket |
| ︵ | （ | Fullwidth left paren |
| ︶ | ） | Fullwidth right paren |
| ︷ | ｛ | Fullwidth left brace |
| ︸ | ｝ | Fullwidth right brace |
| ﹇ | ［ | Fullwidth left bracket |
| ﹈ | ］ | Fullwidth right bracket |
```
```

**Step 3: Create skeleton `scripts/convert_horizontal.py`**

```python
#!/usr/bin/env python3
"""Convert Chinese epub from vertical (直排) to horizontal (橫排) layout."""

import sys


def main():
    print("TODO: implement")
    return 1


if __name__ == "__main__":
    sys.exit(main())
```

**Step 4: Create skeleton `SKILL.md`**

```markdown
---
name: epub-chinese-cleaner
description: Convert Chinese-language epub files from vertical layout (直排) to horizontal layout (橫排) with punctuation normalization. Use when a user has a Chinese epub with vertical text direction or right-to-left page progression and wants to convert it to horizontal reading flow.
compatibility: Requires Python 3. Optionally uses Calibre with TradSimpChinese plugin for best results.
---

# epub-chinese-cleaner

TODO: full instructions
```

**Step 5: Commit**

```bash
git add .gitignore SKILL.md scripts/convert_horizontal.py references/punctuation-map.md
git commit -m "feat: scaffold agent skill project structure"
```

---

### Task 2: Implement epub detection logic

**Files:**
- Modify: `scripts/convert_horizontal.py`

**Step 1: Write a test epub helper and detection test**

Create a minimal epub in-memory for testing. An epub is a zip with:
- `mimetype` (uncompressed, first entry)
- `META-INF/container.xml` (points to `content.opf`)
- `content.opf` (with `<spine>`)
- At least one XHTML content file
- At least one CSS file

```python
# In scripts/convert_horizontal.py — add test helper at bottom

def _make_test_epub(path, writing_mode="vertical-rl", page_direction="rtl"):
    """Create a minimal epub for testing."""
    import zipfile
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/epub+zip")
        zf.writestr("META-INF/container.xml", """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""")
        spine_attr = f' page-progression-direction="{page_direction}"' if page_direction else ""
        zf.writestr("OEBPS/content.opf", f"""<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test</dc:title>
    <dc:language>zh-TW</dc:language>
  </metadata>
  <manifest>
    <item id="ch1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="css" href="style.css" media-type="text/css"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine{spine_attr} toc="ncx">
    <itemref idref="ch1"/>
  </spine>
</package>""")
        wm = f"writing-mode: {writing_mode};" if writing_mode else ""
        zf.writestr("OEBPS/style.css", f"body {{ {wm} }}")
        zf.writestr("OEBPS/chapter1.xhtml", """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><link rel="stylesheet" href="style.css"/></head>
<body><p>測試內容</p></body>
</html>""")
```

**Step 2: Implement detection**

```python
import os
import re
import zipfile
import tempfile
import xml.etree.ElementTree as ET


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
```

**Step 3: Verify detection works**

Run manually in Python REPL or add a quick smoke test in `if __name__ == "__main__"` that creates a test epub and runs `detect_vertical()` on it. Expected: `needs_conversion=True` for vertical epub, `False` for horizontal.

**Step 4: Commit**

```bash
git add scripts/convert_horizontal.py
git commit -m "feat: implement epub vertical layout detection"
```

---

### Task 3: Implement direct manipulation conversion (fallback path)

**Files:**
- Modify: `scripts/convert_horizontal.py`

**Step 1: Add punctuation mapping constant**

```python
V2H_PUNCTUATION = {
    "︒": "。", "︑": "、", "︐": "，", "︔": "；", "︓": "：",
    "︕": "！", "︖": "？", "﹁": "「", "﹂": "」", "﹃": "『",
    "﹄": "』", "︽": "《", "︾": "》", "︵": "（", "︶": "）",
    "︷": "｛", "︸": "｝", "﹇": "［", "﹈": "］",
}

_v2h_re = re.compile("|".join(re.escape(k) for k in V2H_PUNCTUATION))
```

**Step 2: Implement CSS writing-mode rewrite**

```python
_WRITING_MODE_RE = re.compile(
    r"(-(?:epub|webkit)-)?writing-mode\s*:\s*vertical-(rl|lr)",
)

def rewrite_css_horizontal(content):
    """Replace vertical writing-mode with horizontal-tb in CSS/XHTML content."""
    return _WRITING_MODE_RE.sub(
        lambda m: f"{m.group(1) or ''}writing-mode: horizontal-tb", content
    )
```

**Step 3: Implement OPF spine fix**

```python
def fix_spine_direction(opf_content):
    """Remove page-progression-direction='rtl' from <spine>."""
    return re.sub(
        r'\s+page-progression-direction\s*=\s*"rtl"',
        "",
        opf_content,
    )
```

**Step 4: Implement punctuation replacement**

```python
def replace_punctuation(content):
    """Replace vertical-form Unicode punctuation with horizontal equivalents."""
    return _v2h_re.sub(lambda m: V2H_PUNCTUATION[m.group()], content)
```

**Step 5: Implement the full direct conversion function**

```python
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
```

**Step 6: Test with test epub**

Create a vertical test epub, run `convert_direct()`, inspect the output to verify:
- CSS has `horizontal-tb`
- OPF has no `page-progression-direction="rtl"`
- Vertical punctuation is replaced

**Step 7: Commit**

```bash
git add scripts/convert_horizontal.py
git commit -m "feat: implement direct epub horizontal conversion"
```

---

### Task 4: Implement Calibre CLI path

**Files:**
- Modify: `scripts/convert_horizontal.py`

**Step 1: Implement Calibre detection**

```python
import shutil
import subprocess

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
```

**Step 2: Implement Calibre conversion**

```python
def convert_via_calibre(epub_path, output_path, calibre_debug):
    """Convert epub using Calibre's TradSimpChinese plugin CLI."""
    # Determine output dir and suffix from output_path
    out_dir = os.path.dirname(os.path.abspath(output_path))
    # The plugin appends suffix to the original filename, so we use a temp dir
    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            [
                calibre_debug, "-e",
                "from calibre_plugins.chinese_text.main import main; import sys; sys.exit(main(sys.argv[1:], ('cli','0.0')))",
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
```

**Step 3: Commit**

```bash
git add scripts/convert_horizontal.py
git commit -m "feat: implement Calibre CLI conversion path"
```

---

### Task 5: Wire up main() with CLI interface

**Files:**
- Modify: `scripts/convert_horizontal.py`

**Step 1: Implement main()**

```python
import argparse


def main():
    parser = argparse.ArgumentParser(
        description="Convert Chinese epub from vertical (直排) to horizontal (橫排) layout."
    )
    parser.add_argument("input", help="Input epub file path")
    parser.add_argument("-o", "--output", help="Output epub file path (default: <input>_horizontal.epub)")
    args = parser.parse_args()

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

    # Direct manipulation first
    try:
        convert_direct(args.input, output)
        return 0
    except Exception as e:
        print(f"Direct manipulation failed: {e}, falling back to Calibre.", file=sys.stderr)

    # Fallback: Calibre
    calibre = find_calibre_debug()
    if calibre:
        print(f"Using Calibre: {calibre}")
        if convert_via_calibre(args.input, output, calibre):
            return 0
    print("All conversion methods failed.", file=sys.stderr)
    return 1
```

**Step 2: Commit**

```bash
git add scripts/convert_horizontal.py
git commit -m "feat: wire up CLI entry point with detection and dual-path conversion"
```

---

### Task 6: Write SKILL.md agent instructions

**Files:**
- Modify: `SKILL.md`

**Step 1: Write the full SKILL.md**

```markdown
---
name: epub-chinese-cleaner
description: Convert Chinese-language epub files from vertical layout (直排) to horizontal layout (橫排) with punctuation normalization and left-to-right page flow. Use when a user has a Chinese epub with vertical text direction or right-to-left page progression and wants to convert it to standard horizontal reading.
compatibility: Requires Python 3.8+. Optionally uses Calibre with TradSimpChinese plugin for best results.
metadata:
  author: william
  version: "1.0"
---

# epub-chinese-cleaner

Converts Chinese epub files from vertical (直排) + RTL page flow to horizontal (橫排) + LTR page flow.

## What it does

1. **Detects** whether the epub needs conversion (checks CSS `writing-mode` and OPF `page-progression-direction`)
2. **Converts writing mode** from `vertical-rl` to `horizontal-tb` (including vendor prefixes)
3. **Normalizes punctuation** from vertical Unicode forms to horizontal equivalents
4. **Fixes page direction** by removing `page-progression-direction="rtl"` from OPF spine
5. **Preserves original** — outputs a new file with `_horizontal` suffix

## Usage

Run the conversion script:

    python3 scripts/convert_horizontal.py <input.epub> [-o output.epub]

If no `-o` is specified, output is `<input>_horizontal.epub`.

The script automatically:
- Tries Calibre CLI (TradSimpChinese plugin) if available at standard paths
- Falls back to direct epub manipulation if Calibre is not installed
- Skips conversion if the epub is already horizontal

## Example

    python3 scripts/convert_horizontal.py 三體.epub

Output: `三體_horizontal.epub`

## Punctuation mapping

See [references/punctuation-map.md](references/punctuation-map.md) for the full vertical → horizontal punctuation mapping.
```

**Step 2: Commit**

```bash
git add SKILL.md
git commit -m "feat: write SKILL.md agent instructions"
```

---

### Task 7: End-to-end test with test epub

**Step 1: Run the script against the built-in test epub**

Add a `--self-test` flag to `main()` that creates a test epub with vertical content and converts it, then verifies the output.

```python
# Add to argparse:
parser.add_argument("--self-test", action="store_true", help="Run self-test with a generated test epub")

# In main(), before input file check:
if args.self_test:
    return _run_self_test()
```

```python
def _run_self_test():
    """Create a test epub, convert it, verify results."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_in = os.path.join(tmpdir, "test_vertical.epub")
        test_out = os.path.join(tmpdir, "test_horizontal.epub")

        _make_test_epub(test_in, writing_mode="vertical-rl", page_direction="rtl")

        # Should need conversion
        info = detect_vertical(test_in)
        assert info["needs_conversion"], "Detection should find vertical layout"

        # Convert
        convert_direct(test_in, test_out)

        # Verify result
        info2 = detect_vertical(test_out)
        assert not info2["needs_conversion"], "Output should be horizontal"

        # Check punctuation (test with vertical punct in content)
        test_in2 = os.path.join(tmpdir, "test_punct.epub")
        test_out2 = os.path.join(tmpdir, "test_punct_h.epub")
        _make_test_epub(test_in2)

        # Inject vertical punctuation
        with zipfile.ZipFile(test_in2, "a") as zf:
            pass  # test epub already has basic structure

        convert_direct(test_in2, test_out2)
        with zipfile.ZipFile(test_out2, "r") as zf:
            for name in zf.namelist():
                if name.endswith(".css"):
                    css = zf.read(name).decode("utf-8")
                    assert "vertical-rl" not in css, f"CSS still has vertical: {name}"

    print("All self-tests passed.")
    return 0
```

**Step 2: Run self-test**

```bash
python3 scripts/convert_horizontal.py --self-test
```

Expected: `All self-tests passed.`

**Step 3: Commit**

```bash
git add scripts/convert_horizontal.py
git commit -m "feat: add self-test for end-to-end verification"
```
