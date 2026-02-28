---
name: epub-chinese-cleaner
description: Use when a user has a Chinese epub with vertical text direction or right-to-left page progression and wants to convert it to standard horizontal reading. Converts from vertical layout (直排) to horizontal layout (橫排) with punctuation normalization and left-to-right page flow.
license: MIT
compatibility: Requires Python 3.8+. Optionally uses Calibre with TradSimpChinese plugin for best results.
metadata:
  author: William Yeh <william.pjyeh@gmail.com>
  version: "1.5"
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

Ask the agent to convert an epub by name or description:

- "Convert `三體.epub` to horizontal layout"
- "This epub has vertical text, can you make it horizontal?"
- "Check if `book.epub` needs conversion"

The agent runs:

    python3 scripts/convert_horizontal.py <input.epub>

Output is `<input>_horizontal.epub`. The script auto-detects whether conversion is needed and uses direct manipulation by default, falling back to Calibre if direct manipulation fails.

## Punctuation mapping

See [references/punctuation-map.md](references/punctuation-map.md) for the full vertical → horizontal punctuation mapping.
