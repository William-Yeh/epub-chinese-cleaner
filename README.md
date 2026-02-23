# epub-chinese-cleaner

[![CI](https://github.com/William-Yeh/epub-chinese-cleaner/actions/workflows/ci.yml/badge.svg)](https://github.com/William-Yeh/epub-chinese-cleaner/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/William-Yeh/epub-chinese-cleaner)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-blue)](https://agentskills.io)

Convert Chinese-language epub files from vertical layout (直排) to horizontal layout (橫排) with punctuation normalization and left-to-right page flow.

## Installation

### Recommended: `npx skills`

```bash
npx skills add William-Yeh/epub-chinese-cleaner
```

### Manual installation

Copy the skill directory to your agent's skill folder:

| Agent | Directory |
|-------|-----------|
| Claude Code | `~/.claude/skills/` |
| Cursor | `.cursor/skills/` |
| Gemini CLI | `.gemini/skills/` |
| Amp | `.amp/skills/` |
| Roo Code | `.roo/skills/` |
| Copilot | `.github/skills/` |

Optionally install [Calibre](https://calibre-ebook.com/) with the [TradSimpChinese plugin](https://github.com/Hopkins1/TradSimpChinese) for best results. The script falls back to direct epub manipulation if Calibre is not available.

## Usage

After installing, try these prompts with your agent:

- "Convert `三體.epub` to horizontal layout"
- "This epub has vertical text, can you make it horizontal?"
- "Check if `book.epub` needs conversion to horizontal reading flow"

The agent will run the conversion script automatically, detecting whether the epub needs conversion and choosing the best method (Calibre if available, direct manipulation otherwise).

### CLI usage

You can also run the script directly:

```bash
python3 scripts/convert_horizontal.py <input.epub> [-o output.epub]
```

If no `-o` is specified, output is `<input>_horizontal.epub`.

```bash
# Example
python3 scripts/convert_horizontal.py 三體.epub
# Output: 三體_horizontal.epub

# Self-test
python3 scripts/convert_horizontal.py --self-test
```

## License

[MIT](LICENSE)
