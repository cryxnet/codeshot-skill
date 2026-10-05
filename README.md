<p align="center">
  <img src="docs/images/hero.png" alt="codeshot: a Python snippet and a pytest run rendered as polished screenshots over a mesh gradient" width="100%">
</p>

<h1 align="center">codeshot</h1>

<p align="center">
  <b>Beautiful screenshots of code and terminal output, for humans and AI agents.</b><br>
  One file. No browser. No network. PNG or SVG.
</p>

<p align="center">
  <a href="LICENSE"><img alt="License: MIT" src="https://img.shields.io/badge/license-MIT-blue.svg"></a>
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-3776AB.svg?logo=python&logoColor=white">
  <img alt="Agent skill" src="https://img.shields.io/badge/AI%20agent-skill%20included-8A2BE2.svg">
  <a href="https://github.com/cryxnet/codeshot/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/cryxnet/codeshot/actions/workflows/ci.yml/badge.svg"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="#use-it-as-an-ai-agent-skill">Agent skill</a> ·
  <a href="#gallery">Gallery</a> ·
  <a href="#close-up--focus">Close-up & focus</a> ·
  <a href="#cli-reference">CLI reference</a> ·
  <a href="#faq">FAQ</a>
</p>

---

**codeshot** turns a code snippet, a diff, a stack trace, or a real terminal session into a clean, shareable image, with the polish of Carbon or ray.so, but as a single Python script that runs anywhere, **including inside sandboxed AI-agent environments** that have no browser and no internet.

It ships in two parts that work together:

| Part | What it is |
|---|---|
| [`codeshot.py`](skills/code-screenshot/scripts/codeshot.py) | The renderer: a single-file CLI (Python 3.9+, Pillow and Pygments optional). |
| [`SKILL.md`](skills/code-screenshot/SKILL.md) | Instructions that teach any AI agent *when* and *how* to use it: picking a style, redacting secrets, verifying the result. |

**Install it as an agent skill with one command:**

```bash
npx skills add cryxnet/codeshot
```

Works with Claude Code, Codex, Cursor, GitHub Copilot, Gemini CLI, OpenCode and more. [Details below](#use-it-as-an-ai-agent-skill), including the Claude Code plugin-marketplace route.

## Features

- 🖼️ **Code and terminal** in one tool. Syntax highlighting via Pygments, a full ANSI parser for terminals (16 / 256 / truecolor, bold, dim, italic, underline, reverse, `\r` progress bars).
- 🎨 **9 design styles**: macOS, Windows, editor tab, minimal, **close-up**, social card, frosted **glass**, **neon**, flat.
- 🌈 **16 gradient backdrops** (linear, multi-stop, and **mesh**), custom `#hex` stops, adjustable angle. Or fully transparent.
- 🔍 **Close-up & focus** for code *and* terminals: crop to a line range, spotlight lines (or lines matching a regex) and dim the rest.
- 🌓 **8 colour themes**: Dracula, Monokai, Nord, One Dark, GitHub Dark/Light, Solarized Dark/Light.
- ▶️ **Run-and-capture**: `--run "pytest -q"` executes a command and renders its real output (opt-in, with safety rules for agents).
- 📦 **PNG or SVG**. PNG needs Pillow; **SVG needs nothing**. Retina (2×) by default, 3× for close-ups.
- 🤖 **Agent-ready**: harness-agnostic `SKILL.md` with a decision guide, recipes, secret-redaction rules, and troubleshooting.
- 🧪 Tested, with CI on Python 3.9 to 3.13 and a stdlib-only job.

## Quick start

```bash
git clone https://github.com/cryxnet/codeshot.git
cd codeshot
pip install -r requirements.txt            # pillow + pygments (optional but recommended)

python3 skills/code-screenshot/scripts/codeshot.py examples/sample.py -o shot.png
```

Check your environment any time:

```bash
python3 skills/code-screenshot/scripts/codeshot.py --doctor
```

### A few things to try

```bash
S=skills/code-screenshot/scripts/codeshot.py

# Code, with line numbers and a highlighted band
python3 $S examples/sample.py --line-numbers --highlight 15-16 -o code.png

# A real command, captured and rendered
python3 $S --run "git log --graph --oneline --decorate --color=always" --style card --gradient mesh-sunrise -o log.png

# Zoom in on a few lines of a file and spotlight two of them
python3 $S examples/sample.py --style closeup --lines 10-17 --focus 14-16 -o closeup.png

# Terminal: spotlight only the failures
python3 $S examples/pytest-session.ansi --command "pytest -q" --style closeup --focus-match "FAILED|^E " -o fail.png

# Frosted glass over a mesh gradient
python3 $S examples/sample.py --style glass --gradient mesh-aurora -o glass.png

# See every variant using YOUR snippet
python3 $S examples/sample.py --gallery styles -o styles.png
```

## Use it as an AI agent skill

The folder [`skills/code-screenshot/`](skills/code-screenshot) **is** the skill. Install it once; from then on you can just *ask*:

> “Make a close-up screenshot of lines 10 to 17 of `retry.py` and spotlight the `raise`.”
> “Run the tests and give me an image of just the failures, dark theme, neon style.”
> “Turn this stack trace into a screenshot I can paste in the bug report.”

The agent reads `SKILL.md`, picks a style that fits the destination, redacts secrets, renders the image with `codeshot.py`, and checks the result.

### Option 1: `npx skills add` (any agent)

The open [skills CLI](https://github.com/vercel-labs/skills) installs skills straight from a GitHub repo. It detects which agents you have (Claude Code, Codex, Cursor, GitHub Copilot, Gemini CLI, OpenCode, …) and puts the skill in the right folder for each. Needs Node.js.

```bash
npx skills add cryxnet/codeshot                       # interactive: pick agents and scope
npx skills add cryxnet/codeshot --list                # just show what the repo contains
npx skills add cryxnet/codeshot --skill code-screenshot
npx skills add cryxnet/codeshot -a claude-code        # target one agent
npx skills add cryxnet/codeshot -g                    # global: available in every project
npx skills add cryxnet/codeshot -g -a claude-code -y  # global, one agent, no prompts

npx skills list                                             # what's installed
npx skills update                                           # pull the latest version
npx skills remove code-screenshot
```

A full URL (`https://github.com/cryxnet/codeshot`) or any git URL also works, and `npx skills add .` installs from a local checkout, handy while developing.

> The skills CLI is a separate, third-party tool (not part of this repo). Check its documentation for current options and for its telemetry opt-out (`DISABLE_TELEMETRY=1`).

### Option 2: Claude Code plugin marketplace

This repo is also a one-plugin Claude Code marketplace (see [`.claude-plugin/`](.claude-plugin)):

```bash
# inside Claude Code
/plugin marketplace add cryxnet/codeshot
/plugin install codeshot@codeshot

# or from your shell
claude plugin marketplace add cryxnet/codeshot
claude plugin install codeshot@codeshot
```

Plugin skills are namespaced by the plugin name, so you can also call it explicitly with `/codeshot:code-screenshot`.

### Option 3: manual

```bash
git clone https://github.com/cryxnet/codeshot.git && cd codeshot
./install.sh                    # ~/.claude/skills/code-screenshot     (user-level)
./install.sh --project          # ./.claude/skills/code-screenshot     (this project only)
./install.sh --dest ~/my/skills # any folder: <DIR>/code-screenshot
./install.sh --deps             # also pip-install Pillow + Pygments
./install.sh --package          # dist/code-screenshot.skill (zip for apps that accept a skill upload)
```

For a harness with no skills support, put the folder anywhere reachable and point its instructions file (`AGENTS.md`, `.cursor/rules/`, `GEMINI.md`, `CONVENTIONS.md`, system prompt…) at it:

```markdown
## Screenshots of code or terminal output
When asked for a screenshot / image of code, a diff, a stack trace or a command's output,
follow `tools/code-screenshot/SKILL.md`. `SKILL_DIR` there means `tools/code-screenshot/`.
```

> **Requirements for agents:** a shell / code-execution tool and Python 3.9+. Without Pillow the skill falls back to SVG automatically; `pip install pillow pygments` gives PNG and syntax colours.

## Gallery

### Design styles (`--style`)

<table>
  <tr>
    <td align="center"><img src="docs/images/styles/macos.png" width="320"><br><sub><code>macos</code> (default)</sub></td>
    <td align="center"><img src="docs/images/styles/windows.png" width="320"><br><sub><code>windows</code></sub></td>
    <td align="center"><img src="docs/images/styles/editor.png" width="320"><br><sub><code>editor</code></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/styles/minimal.png" width="320"><br><sub><code>minimal</code></sub></td>
    <td align="center"><img src="docs/images/styles/closeup.png" width="320"><br><sub><code>closeup</code>: code only</sub></td>
    <td align="center"><img src="docs/images/styles/card.png" width="320"><br><sub><code>card</code></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/styles/glass.png" width="320"><br><sub><code>glass</code> + <code>mesh-aurora</code></sub></td>
    <td align="center"><img src="docs/images/styles/neon.png" width="320"><br><sub><code>neon</code></sub></td>
    <td align="center"><img src="docs/images/styles/flat.png" width="320"><br><sub><code>flat</code> (docs / READMEs)</sub></td>
  </tr>
</table>

| Style | Best for |
|---|---|
| `macos` *(default)* | General purpose: READMEs, blogs |
| `windows` | PowerShell / WSL / Windows-terminal content |
| `editor` | “Here's the file”: IDE tab strip, line numbers on |
| `minimal` | Clean article images: no title bar, soft shadow |
| `closeup` | **Code only**: no frame or backdrop, big type, 3× resolution. Slides, inline docs, zoom-ins |
| `card` | Tweets, LinkedIn, slide covers: big padding and type |
| `glass` | Hero images: frosted window blurring the gradient behind it |
| `neon` | Dark-mode posts: glowing gradient outline on near-black |
| `flat` | Docs sites, wikis, print: 1px outline, transparent surround |

<details>
<summary><b>Contact sheet of all styles</b></summary>
<img src="docs/images/gallery-styles.png" alt="All nine styles side by side">
</details>

### Gradients (`--gradient`)

Presets (`--list-gradients`) or your own: `--gradient "#0ea5e9,#6366f1" --gradient-angle 160`. Use `none` for a transparent background.

<img src="docs/images/gallery-gradients.png" alt="All 16 gradient presets" width="100%">

<table>
  <tr>
    <td><img src="docs/images/custom-gradient.png" alt="Custom two-colour gradient at 160 degrees" width="480"></td>
    <td valign="middle">
      <b>Custom brand colours</b>
      <pre>codeshot.py sample.py \
  --style card \
  --gradient "#0ea5e9,#6366f1" \
  --gradient-angle 160</pre>
      <sub>Angles follow CSS: 0 = up, 90 = right, 135 = diagonal (default), 180 = down.</sub>
    </td>
  </tr>
</table>

### Themes (`--theme`)

`dracula` · `monokai` · `nord` · `one-dark` · `github-dark` · `solarized-dark` · `github-light` · `solarized-light`

<details>
<summary><b>Contact sheet of all themes</b></summary>
<img src="docs/images/gallery-themes.png" alt="All eight colour themes side by side">
</details>

## Close-up & focus

Show **only what matters**. These options work for **both code and terminal output**:

<img src="docs/images/focus-before-after.png" alt="Left: a full pytest session. Right: the same session cropped to the traceback with the two key lines spotlighted" width="100%">

| Option | What it does |
|---|---|
| `--lines 8-13` | Crop to a range, **keeping the true line numbers** |
| `--tail 10` | Only the last N lines (long build / test logs) |
| `--focus 12-13` | Spotlight lines, **dim everything else** |
| `--focus-match "FAILED\|^E "` | Spotlight every line matching a regex (ANSI colours ignored) |
| `--highlight 15-16` / `--highlight-match REGEX` | Keep full colour, add a tinted band and accent bar |
| `--line-numbers` | Show the gutter (terminals number the *output* lines) |

For terminals, the shown command (`--command` / `--run`) is a *context line*: it is never cropped and never dimmed, so the image always shows what was run.

<table>
  <tr>
    <td align="center"><img src="docs/images/code-closeup-focus.png" alt="Code close-up with focus"><br><sub><b>Code:</b> <code>--style closeup --lines 10-17 --focus 14-16</code></sub></td>
  </tr>
  <tr>
    <td align="center"><img src="docs/images/terminal-focus-match.png" alt="Terminal close-up with regex focus"><br><sub><b>Terminal:</b> <code>--style closeup --focus-match "FAILED|^E " --line-numbers</code></sub></td>
  </tr>
</table>

## More examples

<table>
  <tr>
    <td width="50%"><img src="docs/images/terminal-git-log.png" alt="Real git log output rendered as a card over a mesh gradient"><br><sub><b>Real command output</b>: <code>--run "git log --graph --oneline --decorate --color=always" --style card --gradient mesh-sunrise</code></sub></td>
    <td width="50%"><img src="docs/images/terminal-windows.png" alt="Windows terminal style"><br><sub><b>Windows style</b>: <code>--style windows --theme github-dark --tail 7 --end-prompt</code></sub></td>
  </tr>
  <tr>
    <td colspan="2"><img src="docs/images/code-diff-neon.png" alt="A diff in the neon style" width="60%"><br><sub><b>Diffs</b>: <code>git diff | codeshot.py --lang diff --style neon</code></sub></td>
  </tr>
</table>

## CLI reference

```
codeshot.py [input] [options]       input = file, "-" for stdin, or use --code / --run
```

<details open>
<summary><b>Input & output</b></summary>

| Option | Description | Default |
|---|---|---|
| `input` / `--code TEXT` / stdin | Source to render | – |
| `-o, --output` | `.png`, `.jpg` or `.svg` (PNG falls back to SVG without Pillow) | `screenshot.png` |
| `--mode auto\|code\|terminal` | Auto-detects terminal when ANSI codes or `--command` are present | `auto` |
| `-l, --lang` | Pygments language (`python`, `ts`, `bash`, `json`, `diff`, …). **Always set it for snippets** | by extension |
| `-t, --title` | Title-bar text | filename / `Terminal` |
</details>

<details open>
<summary><b>Look & feel</b></summary>

| Option | Description | Default |
|---|---|---|
| `--style` | `macos` `windows` `editor` `minimal` `closeup` `card` `glass` `neon` `flat` | `macos` |
| `--gradient`, `--backdrop` | Preset, `none`, `#hex`, or `#hex1,#hex2[,…]` | theme gradient |
| `--gradient-angle` | CSS angle in degrees | `135` |
| `--theme` | Syntax / terminal colours | `dracula` |
| `--chrome macos\|windows\|tab\|none` (`--no-chrome`) | Title-bar type | per style |
| `--font PATH`, `--font-size`, `--line-height` | Typography (PNG) | per style |
| `--scale N` | Pixel density | `2` (`closeup`: `3`) |
| `--padding` `--margin` `--radius` `--min-width` | Geometry | per style |
| `--no-shadow` | Disable the drop shadow | – |
| `--gallery styles\|gradients\|themes` | Render a contact sheet of all variants | – |
</details>

<details open>
<summary><b>Selecting lines</b></summary>

| Option | Description |
|---|---|
| `--line-numbers` / `--no-line-numbers`, `--start-line N` | Gutter on/off, first number |
| `--lines A-B`, `--tail N` | Crop to a range / last N lines |
| `--focus A-B`, `--focus-match REGEX` | Spotlight, dim the rest |
| `--highlight A-B`, `--highlight-match REGEX` | Tinted band |
| `--wrap N`, `--max-lines N` | Hard-wrap at N columns / truncate with “… N more lines” |
</details>

<details open>
<summary><b>Terminal</b></summary>

| Option | Description | Default |
|---|---|---|
| `--run CMD` | Execute `CMD` in a shell, capture stdout + stderr (colours forced on) | – |
| `--command CMD` | Show `CMD` after a prompt *without* running it (pair with piped output) | – |
| `--prompt STR` | Prompt text, e.g. `"~/repo $"` or `"PS C:\proj>"` | `$` |
| `--end-prompt` | Trailing prompt with a cursor block | off |
| `--timeout N` | Kill `--run` after N seconds | `30` |
</details>

Discovery: `--doctor` · `--version` · `--list-styles` · `--list-gradients` · `--list-themes`.

## How it works

```mermaid
flowchart LR
  A["file · stdin · --code · --run"] --> B{mode}
  B -->|code| C["Pygments lexer<br/>→ colour spans"]
  B -->|terminal| D["ANSI parser<br/>→ colour spans"]
  C --> E["select<br/>--lines · --tail · --focus · --highlight"]
  D --> E
  E --> F["layout<br/>wrap · gutter · dim"]
  F --> G{format}
  G -->|.png| H["Pillow renderer<br/>window · gradient · glass · glow"]
  G -->|.svg| I["SVG writer<br/>zero dependencies"]
```

Both renderers share the same line model, so every style, gradient and selection option behaves identically in PNG and SVG (with two PNG-only details: the real background blur in `glass`, and custom fonts via `--font`).

## Requirements, fonts & limitations

- **Python 3.9+.** `pip install -r requirements.txt` adds Pillow (PNG) and Pygments (highlighting). Both are optional.
- **Fonts.** PNG output auto-detects a monospace TTF (JetBrains Mono, Fira Code, Menlo, Consolas, DejaVu Sans Mono, Liberation Mono, …). Use `--font /path/to/Font.ttf` to pick your own.
- **Glyph coverage.** The fallback fonts lack CJK, emoji and Nerd-Font icons; those show as boxes in PNG. Pass a font that has them with `--font`, or output SVG so the viewer's fonts are used.
- **SVG** is text-based and scales perfectly, but fonts and the `glass` blur depend on the viewer. Use PNG for pixel-exact results.
- **Not a screen grabber.** codeshot renders text you give it; it doesn't capture GUI windows or websites.
- Tested locally on Python 3.12 with Pillow 12 / Pygments 2.20; CI covers Python 3.9 to 3.13 on Linux.

## FAQ

<details>
<summary><b><code>npx skills add</code> says it found no skills.</b></summary>
Check that the repo is public (or that you have git access), that Node.js is installed, and run <code>npx skills add cryxnet/codeshot --list</code>. The CLI looks for <code>skills/&lt;name&gt;/SKILL.md</code>, and skips skills whose frontmatter is invalid.
</details>

<details>
<summary><b>How do I get a PNG if Pillow isn't installed?</b></summary>
Run <code>pip install pillow</code> (use a virtualenv or <code>--break-system-packages</code> on externally-managed Pythons). Or convert the SVG: <code>rsvg-convert -o out.png in.svg</code>, <code>inkscape in.svg -o out.png</code> or <code>magick in.svg out.png</code>.
</details>

<details>
<summary><b>Can I get a transparent background?</b></summary>
Yes: <code>--gradient none</code>. For a frameless, transparent result use <code>--style closeup --gradient none</code>; the rounded corners stay transparent.
</details>

<details>
<summary><b>My command output has no colours.</b></summary>
Many tools disable colour when not attached to a TTY. Add the tool's flag inside the <code>--run</code> string: <code>--color=always</code>, <code>-c color.ui=always</code>, or <code>FORCE_COLOR=1 npm test</code>.
</details>

<details>
<summary><b>I see <code>\x1b[31m</code> literally in my image.</b></summary>
The text contains the four characters <code>\x1b</code> instead of a real ESC byte (typical with <code>echo "\x1b[31m…"</code>). Generate real escapes with <code>printf '\033[31m'</code> or capture the actual program output.
</details>

<details>
<summary><b>Is <code>--run</code> safe?</b></summary>
It runs the command you give it in a shell on your machine, exactly like typing it yourself. The agent instructions in <code>SKILL.md</code> restrict agents to commands you asked for or that are clearly read-only, and tell them to redact secrets before sharing an image. Review commands before approving them.
</details>

<details>
<summary><b>Why not just use a headless browser?</b></summary>
Sandboxed agent environments often have no browser, no network, or no way to install one. codeshot needs only Python, and falls back to dependency-free SVG when even Pillow is missing.
</details>

## Development

```bash
python3 -m unittest discover -s tests -v     # stdlib only, no pytest needed
python3 docs/make_images.py                  # regenerate every image in this README
```

```
skills/code-screenshot/  the skill (SKILL.md + scripts/codeshot.py)
.claude-plugin/          Claude Code plugin + marketplace manifests
examples/              inputs used by tests and README images
docs/                  image generator + generated images
tests/                 unittest suite
install.sh             installer / packager
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add styles, gradients and themes, and [CHANGELOG.md](CHANGELOG.md) for release notes.

## License

[MIT](LICENSE)

---

<sub>Inspired by the great screenshot tools Carbon, ray.so and freeze. Built on <a href="https://pygments.org/">Pygments</a> and <a href="https://python-pillow.org/">Pillow</a>.</sub>
