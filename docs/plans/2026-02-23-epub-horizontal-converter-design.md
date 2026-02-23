# epub-chinese-cleaner Design

## Goal

Agent Skill (agentskills.io spec) that converts a Chinese-language epub from vertical layout (直排) + RTL page flow to horizontal layout (橫排) + LTR page flow, with punctuation normalization.

## Requirements

- **Step 1**: Convert writing-mode from `vertical-rl` to `horizontal-tb` (+ vendor prefixes)
- **Step 2**: Update vertical-form punctuation to horizontal equivalents
- **Step 3**: Remove `page-progression-direction="rtl"` from `<spine>` in `content.opf`
- **Detection**: Skip conversion if epub is already horizontal
- **Output**: New file with `_horizontal` suffix (preserves original)
- **Calibre first**: Use TradSimpChinese plugin CLI if available, direct epub manipulation as fallback
- **Scope**: Layout + punctuation only (no 繁簡轉換)

## Directory Structure

```
epub-chinese-cleaner/
├── SKILL.md
├── scripts/
│   └── convert_horizontal.py
└── references/
    └── punctuation-map.md
```

## Conversion Strategy

### Calibre Path (preferred)

Use TradSimpChinese plugin CLI with flags:
- `-td horizontal` (text direction)
- `-up` (update punctuation)
- `-d t2t` (no character conversion)

Then post-process `content.opf` to remove `page-progression-direction="rtl"`.

### Direct Manipulation Fallback

1. Unzip epub to temp directory
2. Scan all CSS/XHTML files for `writing-mode: vertical-rl` / `vertical-lr`
3. Replace with `horizontal-tb` (also `-epub-writing-mode`, `-webkit-writing-mode`)
4. Replace vertical-form Unicode punctuation with horizontal equivalents
5. Parse `content.opf`, remove `page-progression-direction="rtl"` from `<spine>`
6. Re-zip as new epub

### Punctuation Mapping (vertical → horizontal)

```
︒ → 。    ︑ → 、    ︐ → ，    ︔ → ；    ︓ → ：
︕ → ！    ︖ → ？    ﹁ → 「    ﹂ → 」    ﹃ → 『
﹄ → 』    ︽ → 《    ︾ → 》    ︵ → （    ︶ → ）
︷ → ｛    ︸ → ｝    ﹇ → ［    ﹈ → ］
```

### Detection Logic

Before converting, check:
- Any CSS/XHTML contains `writing-mode: vertical-rl` or `vertical-lr`
- `content.opf` contains `page-progression-direction="rtl"`

If neither → skip, report "already horizontal".
