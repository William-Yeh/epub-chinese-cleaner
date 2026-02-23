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

## Testing

Run the test suite (no global install needed):

```bash
uv run --with pytest pytest tests/ -v
```

Or use the built-in self-test (no dependencies):

```bash
python3 scripts/convert_horizontal.py --self-test
```

### Test strategy

The suite has **46 tests** organized in three tiers:

**Unit tests** — pure functions, no I/O:
- `rewrite_css_horizontal`: standard, vendor-prefixed (`-epub-`, `-webkit-`), `vertical-lr`, no-match
- `fix_spine_direction`: double/single quotes, extra whitespace, no-match
- `replace_punctuation`: parametrized across all 19 V2H mappings, mixed content, passthrough
- `V2H_PUNCTUATION` completeness: confirms all 19 entries are present

**Integration tests** — epub I/O via in-memory zip fixtures:
- `find_opf_path`: resolves `OEBPS/content.opf` from `container.xml`
- `detect_vertical`: five scenarios (both signals, CSS-only, spine-only, vendor prefix, already horizontal)
- `convert_direct`: full conversion pipeline (CSS + OPF + punctuation), mimetype positioning/compression, single-quote spine attributes

**CLI tests** — `main()` entry point:
- `--self-test` exits 0
- No args prints help, exits 1
- Missing file exits 1 with error
- Already-horizontal epub exits 0 with skip message

### Design notes

- **No real epub fixtures checked in.** Tests use `_make_test_epub()` to build minimal valid epubs in `tmp_path`. This keeps the repo small and makes each test's input explicit.
- **`tmp_epub` fixture is a factory.** It returns a callable that accepts `writing_mode` and `page_direction` kwargs, so each test can create exactly the epub variant it needs while pytest handles cleanup.
- **Parametrize for punctuation.** Each of the 19 vertical→horizontal character mappings is an individual test case via `@pytest.mark.parametrize`, so a failure pinpoints the exact broken pair.
- **Calibre path is mocked.** `find_calibre_debug` is tested with `shutil.which` and `os.path.isfile` patched to return `None`/`False`, avoiding a hard dependency on Calibre being installed.

## License

[MIT](LICENSE)
