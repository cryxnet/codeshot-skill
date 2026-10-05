# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-10-05

### Added
- `codeshot.py` renderer: code and terminal output to **PNG** (Pillow) or **SVG** (zero dependencies).
- **Code mode** with Pygments syntax highlighting, line numbers, `--highlight`, `--lines`, `--focus`, tab expansion and dedent.
- **Terminal mode** with a full ANSI parser (16 / 256 / truecolor, bold, dim, italic, underline, reverse, `\r` progress-bar overwrites), `--command`, `--run`, `--end-prompt`.
- **9 design styles**: `macos`, `windows`, `editor`, `minimal`, `closeup`, `card`, `glass`, `neon`, `flat`.
- **16 gradient backdrops** (linear, multi-stop, and mesh) plus custom `#hex` stops and `--gradient-angle`.
- **8 colour themes**: dracula, monokai, nord, one-dark, github-dark, solarized-dark, github-light, solarized-light.
- **Close-up and focus** for both code and terminal: `--lines`, `--tail`, `--focus`, `--focus-match`, `--highlight-match`.
- `--gallery styles|gradients|themes` contact sheets.
- `SKILL.md` so any AI agent harness can use the tool, with a decision guide, recipes, safety rules and troubleshooting.
- One-command install: `npx skills add <owner>/codeshot` (layout `skills/code-screenshot/`), plus a Claude Code plugin marketplace (`.claude-plugin/`) and `install.sh`.
- Test suite (stdlib `unittest`), CI workflow, and reproducible README images (`docs/make_images.py`).
