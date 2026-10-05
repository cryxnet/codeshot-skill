---
name: code-screenshot
description: Create polished screenshots (PNG or SVG) of code snippets and terminal sessions in many design variants - macOS/Windows/editor-tab windows, close-up code-only crops, social cards, frosted glass, neon, flat doc style - with swappable gradient backdrops (linear, multi-colour, mesh), syntax highlighting, line numbers, highlighted/spotlighted lines, ANSI colours and colour themes. Use this skill whenever the user asks for a screenshot, image, picture, snapshot, "carbon-style" or "ray.so-style" render of code, a diff, a stack trace, a CLI command, terminal output, a test run, a git log, or a shell session - for docs, READMEs, blog posts, slides, tweets, bug reports, or tutorials. Also use it when the user wants to "make this code look nice", "turn this output into an image", or "show what running X looks like", even if they never say "screenshot".
compatibility: Needs a shell/code-execution tool and Python 3.9+. Pillow (PNG) and Pygments (highlighting) recommended; SVG output works with zero dependencies.
---

# Code & Terminal Screenshots

Turn code or terminal output into a clean, shareable image by running the bundled renderer, `scripts/codeshot.py`. It needs no browser, no network, and no GUI. It works the same in any agent harness that can run a shell command and write files.

Three independent knobs control the look: **`--style`** (frame/layout design), **`--gradient`** (backdrop colours) and **`--theme`** (syntax colours). Any combination works.

`SKILL_DIR` below means the directory that contains this SKILL.md.

## Use / don't use

| Use this skill | Don't use it |
|---|---|
| "Screenshot this function", "make an image of this snippet" | The user wants a screenshot of a **GUI app, website, or their actual screen** (use a browser/OS screenshot tool instead) |
| "Show me what `git log` looks like as an image" | The user only wants the code **explained or fixed** (no image requested) |
| Docs/README/blog/slide visuals of code or CLI output | A chart, diagram, or UI mockup |
| Bug-report images of a stack trace or failing test | The user wants a **copy-pasteable** snippet (give text, optionally plus the image) |

## Quick start

```bash
# 1. Check the environment (1 second)
python3 SKILL_DIR/scripts/codeshot.py --doctor

# 2. Code file -> PNG
python3 SKILL_DIR/scripts/codeshot.py path/to/app.py -o shot.png --line-numbers

# 3. Terminal: run a real command and capture it
python3 SKILL_DIR/scripts/codeshot.py --run "pytest -q" -o tests.png
```

If `--doctor` reports a missing library, install it (`pip install pillow pygments`; on externally-managed Pythons add `--break-system-packages` or use a venv). If installing is impossible, carry on: without Pillow the script writes SVG, and without Pygments it renders uncoloured code.

## Variants: style × gradient × theme

### `--style` (design / layout)
| Style | Look | Best for |
|---|---|---|
| `macos` *(default)* | Floating window, traffic lights, centered title | General purpose, READMEs, blogs |
| `windows` | Windows-Terminal bar: icon + title left, ─ □ ✕ right | Windows/PowerShell/WSL content |
| `editor` | IDE file-tab strip, line numbers on | "Show this file" snippets, code reviews |
| `minimal` | No title bar, soft shadow | Clean blog/article images |
| `closeup` | **Code only**: no frame, no backdrop, big type, tight padding, 3× resolution | Zoomed-in highlight of a few lines, slides, inline docs |
| `card` | No title bar, large padding and type, big shadow | Tweets, LinkedIn, slide covers |
| `glass` | Frosted translucent window blurring the gradient behind it | Marketing, hero images (shines on `mesh-*` gradients) |
| `neon` | Near-black backdrop, glowing gradient outline | Dark-mode posts, "cyber" aesthetic |
| `flat` | 1px outline, transparent surround, no shadow | Docs sites, wikis, print |

Any style can be tweaked with explicit flags (`--chrome`, `--margin`, `--padding`, `--font-size`, `--radius`, `--no-shadow`, `--line-numbers`…); explicit flags always win over the style.

### `--gradient` (backdrop)
Accepts a **preset name**, `none` (transparent), one `#hex` (solid), or `#hex1,#hex2[,#hex3…]` (custom multi-stop). `--gradient-angle` sets the CSS angle (0 = up, 90 = right, 135 = diagonal default, 180 = down).

| Family | Presets |
|---|---|
| Warm | `sunset`, `fire`, `peach`, `candy`, `lavender`, `vaporwave` |
| Cool | `ocean`, `aurora`, `forest`, `midnight`, `ice` |
| Neutral | `paper`, `mono` |
| Mesh (organic multi-colour blobs) | `mesh-aurora`, `mesh-sunrise`, `mesh-nebula` |

Without `--gradient`, the colour theme's own gradient is used. List them with `--list-gradients`.

### `--theme` (syntax / terminal colours)
Dark: `dracula` *(default)*, `monokai`, `nord`, `one-dark`, `github-dark`, `solarized-dark` · Light: `github-light`, `solarized-light`.

### Zoom and focus (code **and** terminal)
These work the same for source code and for terminal output.
- `--lines 8-12`: crop to just those lines, **keeping the true numbers**.
- `--tail 10`: only the last N lines (great for long build/test logs).
- `--focus 9-10`: spotlight lines and dim all the rest (strongest "look here" effect).
- `--focus-match "FAIL|Error"`: spotlight every line matching a regex (matched against the plain text, ANSI colours ignored). Combine with `--focus` to add specific lines.
- `--highlight 9-10` / `--highlight-match REGEX`: keep full colour but add a tinted band + accent bar.
- `--line-numbers`: show the gutter. In terminal mode it numbers the **output** lines (1 = first line of output).

For terminals, the shown command (`--command` / `--run`) and the `--end-prompt` are *context lines*: they are never cropped by `--lines`/`--tail` and never dimmed, so the image always shows what was run. Numbers refer to output lines only.

### Preview all variants
```bash
python3 SKILL_DIR/scripts/codeshot.py snippet.py --gallery styles    -o styles.png     # every --style
python3 SKILL_DIR/scripts/codeshot.py snippet.py --gallery gradients -o gradients.png  # every --gradient
python3 SKILL_DIR/scripts/codeshot.py snippet.py --gallery themes    -o themes.png     # every --theme
```
Use a gallery when the user says "show me options", "which looks best?", or "different variants". Present the sheet, then ask which to render at full size.

### Choosing a variant (decision guide)
| User says / destination | Use |
|---|---|
| "close-up", "just the code", "zoom in on lines 5-8", slide, inline in docs | `--style closeup --lines A-B [--focus X-Y]` |
| Terminal: "show just the error", "highlight the failing tests", "last few lines of the log" | `--style closeup --focus-match "FAIL\|Error"`, or `--tail N`, or `--lines A-B --focus X-Y` |
| Tweet / LinkedIn / cover image | `--style card --gradient sunset` (or `mesh-*`) |
| Fancy / modern / hero | `--style glass --gradient mesh-aurora` |
| Dark / cyber / dev-twitter | `--style neon` |
| GitHub README (light page) | `--style flat --theme github-light` |
| Windows / PowerShell | `--style windows` (add `--theme github-dark` or `nord`) |
| "As in VS Code" / file view | `--style editor` |
| No preference | default `macos` with the theme gradient |
| Company/brand colours | `--gradient "#hex1,#hex2"` |
| Needs transparent background | `--gradient none` (+ `--style closeup` or `--margin 0`) |

Contrast rule: on a **light** gradient (`peach`, `ice`, `paper`, `lavender`) the dark window pops; on a **dark** gradient (`midnight`, `mono`, `mesh-nebula`) keep the shadow on or prefer `glass`/`neon`.

## Workflow

Follow these steps in order.

### 1. Get the exact content
- **Code from the conversation or a file**: use the user's text verbatim. Never "improve" it unless asked.
- **Terminal output**: prefer a **real capture** (`--run`, or pipe the real output). If the user supplied the output, use it as given.
- If the output is **illustrative or invented** (user says "mock up what it would look like"), that is fine, but tell the user it is a mock-up and not a real run.
- Trim to what matters. Aim for **≤ 30 lines and ≤ 90 columns**; larger images get unreadable once scaled down. Use `--max-lines`, `--wrap`, or pick the relevant slice and set `--start-line` so line numbers stay truthful.

### 2. Sanitize before rendering
Screenshots get shared publicly. Scan the content and **redact** (replace with `***`, `<redacted>`, or `example.com`) anything like API keys, tokens, passwords, private keys, `.env` values, internal hostnames/IPs, emails, and home-directory paths, unless the user explicitly says it is safe. Mention what you redacted.

### 3. Pick the mode
| Situation | Mode | How |
|---|---|---|
| Source code, config, JSON, SQL, a diff | `code` | file path, `--code`, or stdin; set `--lang` |
| A command and its output | `terminal` | `--run "cmd"` (execute) or `--command "cmd"` + piped/ file output (don't execute) |
| Output containing ANSI colours | `terminal` | auto-detected from `\x1b[` sequences |

Always pass `--lang` for code that comes from a snippet or stdin (e.g. `python`, `typescript`, `bash`, `json`, `diff`, `rust`, `sql`, `yaml`). Auto-guessing short snippets is unreliable. For a file path, the extension is used.

### 4. Render
Write images to the working directory, or to whatever output folder your harness exposes for user-visible files.

Choose a variant that serves the purpose (see the decision guide above). If the user gave no styling preference, use the default; if they asked for variety, make a `--gallery` first or render 2-3 different variants side by side as separate files.

Other options worth knowing:
- **Referencing specific lines in prose** → `--line-numbers --highlight 4-6` (or `--focus`)
- **A snippet from the middle of a file** → `--line-numbers --start-line 42`
- **Scalable / editable / tiny file** → `-o shot.svg`

### 5. Verify
- If your harness can view images, **open the result** and check: nothing clipped, text legible, colours correct, no `\x1b[` junk or `?` boxes.
- If it cannot, rely on the printed summary (`Wrote … WxHpx, N lines`) and sanity-check that N matches expectations.
- If something looks off, see Troubleshooting, adjust, and re-render. Don't ship the first attempt blindly when a fix is cheap.

### 6. Deliver
- Give the user the **file path** (or attach/present it using your harness's file-sharing mechanism if it has one).
- State briefly what was rendered (theme, lines, any redactions, mock-up vs real). Keep it short.
- Offer one relevant tweak (e.g. "light theme?", "highlight the failing line?") only if natural.

## Recipes

```bash
S=SKILL_DIR/scripts/codeshot.py

# Code file with line numbers and two highlighted lines
python3 $S src/server.ts -o server.png --line-numbers --highlight 12-13 --theme one-dark

# Inline snippet
python3 $S --code 'const x = [1,2,3].map(n => n * 2);' --lang javascript -o x.png

# Heredoc (safest for multi-line snippets with quotes)
python3 $S --lang python -o snippet.png --title "utils.py" <<'EOF'
def add(a, b):
    return a + b
EOF

# Real command, real output (stderr included, colours forced on)
python3 $S --run "git log --oneline --graph -n 8" -o log.png --prompt "~/repo $"

# Show a command but do NOT execute it (use captured output from a file/pipe)
cat output.txt | python3 $S --command "npm run build" --end-prompt -o build.png

# Close-up on two lines of a bigger file, rest dimmed
python3 $S src/server.ts --style closeup --lines 40-52 --focus 46-47 --start-line 1 -o closeup.png

# Terminal close-up: spotlight only the failures in a long test run (command stays visible)
python3 $S --run "pytest -q" --style closeup --focus-match "FAILED|^E " -o fail.png

# Terminal: crop to the traceback and spotlight two lines of it
cat pytest.log | python3 $S --command "pytest -q" --style closeup --lines 8-13 --focus 12-13 -o trace.png

# Terminal: only the last 6 lines of a long build, failing line banded
python3 $S build.log --command "npm run build" --tail 6 --highlight-match "error" --end-prompt -o build.png

# Social card with a custom brand gradient
python3 $S snippet.py --style card --gradient "#0ea5e9,#6366f1" --gradient-angle 160 -o card.png

# Frosted glass over a mesh gradient
python3 $S snippet.py --style glass --gradient mesh-aurora --line-numbers -o glass.png

# Windows terminal look
python3 $S --run "dir" --style windows --theme github-dark -o win.png

# Neon on dark
python3 $S snippet.py --style neon --theme github-dark -o neon.png

# Transparent, frameless (for compositing)
python3 $S snippet.py --style closeup --gradient none -o transparent.png

# Diff
git diff HEAD~1 | python3 $S --lang diff -o diff.png --no-chrome

# Stack trace, wrapped, light theme
python3 $S trace.txt --mode terminal --wrap 100 --theme github-light -o trace.png

# Multi-line command header (plain single quotes with a real newline: works in any POSIX shell)
python3 $S out.txt --command 'docker run --rm \
  -p 8080:80 nginx' -o docker.png
```

For a **multi-step terminal session** (several commands), render each step as its own image, or concatenate the commands and outputs into one text file with ANSI prompts and render it with `--mode terminal`.

## Option reference

| Option | Meaning | Default |
|---|---|---|
| `input` / `--code` / stdin | Source: file, inline text, or pipe | – |
| `-o, --output` | `.png`, `.jpg`, or `.svg` | `screenshot.png` |
| `--mode` | `auto` / `code` / `terminal` | `auto` |
| `-l, --lang` | Pygments language name | guess |
| `-t, --title` | Title-bar text | filename / `Terminal` |
| `--theme` | Syntax/terminal colour theme | `dracula` |
| `--style` | Design variant (see Variants) | `macos` |
| `--gradient` / `--backdrop` | Preset, `none`, `#hex`, or `#hex1,#hex2…` | theme gradient |
| `--gradient-angle` | CSS angle in degrees | 135 |
| `--gallery styles\|gradients\|themes` | Contact sheet of all variants | – |
| `--lines A-B`, `--tail N` | Crop to a range / last N lines (code + terminal) | – |
| `--focus A-B`, `--focus-match REGEX` | Spotlight lines, dim the rest (code + terminal) | – |
| `--highlight A-B`, `--highlight-match REGEX` | Band lines (code + terminal) | – |
| `--chrome macos\|windows\|tab\|none` | Title-bar type (`--no-chrome` = none) | per style |
| `--no-line-numbers` | Force numbers off | per style |
| `--line-numbers`, `--start-line N` | Gutter numbers | off, 1 |
| `--command "cmd"` | Prompt + command shown above output | – |
| `--run "cmd"` | Execute command, capture stdout+stderr | – |
| `--prompt "$"` | Prompt text | `$` |
| `--end-prompt` | Trailing prompt with block cursor | off |
| `--wrap N` / `--max-lines N` | Hard-wrap columns / truncate | off |
| `--font PATH` | Custom monospace `.ttf`/`.otf` (PNG) | auto-detect |
| `--font-size`, `--line-height` | Typography | per style (15, 1.5) |
| `--scale N` | Pixel density (2 = retina) | 2 (`closeup`: 3) |
| `--padding`, `--margin`, `--radius`, `--min-width` | Geometry | per style (28, 56, 14, 480) |
| `--no-shadow` | Drop shadow off | off |
| `--timeout N` | Kill `--run` after N seconds | 30 |
| `--doctor`, `--list-themes`, `--list-styles`, `--list-gradients` | Diagnostics / discovery | – |

## Safety rules for `--run`
`--run` executes a shell command on the user's machine.
- Only run commands the user asked for, or that are clearly read-only and harmless (`ls`, `git log`, `--version`, test runners the user requested).
- Never run destructive, privileged, or network-mutating commands (`rm`, `sudo`, `curl | sh`, deploys, `git push`, DB writes) just to make a nicer screenshot. Ask first, or use `--command` with output the user provides.
- Output may contain secrets (env dumps, config prints). Apply step 2 before sharing.

## Design guidance (what makes a good one)
- **Legibility first**: 14-16 px font, ≤ 90 columns, a few lines to ~30. If it's long, show the relevant slice with `--start-line` and `--max-lines`.
- **One idea per image**: highlight the lines the surrounding text talks about.
- **Match the destination**: light theme for white docs, dark for slides/social; `--style closeup` (or `flat`) for tight inline use.
- **Honest terminals**: real output beats fabricated output. Don't edit output to look nicer (remove noise by truncating or choosing a better command, not by rewriting results).
- **Titles help**: use the filename for code (`--title "src/auth.ts"`), the project or host for terminals.
- **Accessibility**: when posting an image, also give the underlying text or alt-text so it's searchable and screen-reader friendly.

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `Pillow not installed - writing SVG instead` | `pip install pillow` for PNG, or convert the SVG: `rsvg-convert -o out.png in.svg`, `inkscape in.svg -o out.png`, `magick in.svg out.png`, or `cairosvg in.svg -o out.png` |
| No colours in code | Pygments missing → `pip install pygments`; or wrong `--lang` |
| Wrong colours/guessed language | Pass `--lang` explicitly (`python`, `bash`, `ts`, `json`, `diff`…) |
| Literal `\x1b[31m` shown | The text contains the characters `\x1b` instead of real ESC bytes (e.g. produced by `echo "\x1b..."`). Regenerate with real escapes (`printf '\033[31m'` in bash, or Python `"\x1b[31m"`) |
| Command output has no colours | Many tools disable colour when not on a TTY. Add the tool's flag (`--color=always`, `-c color.ui=always`, `FORCE_COLOR=1`) in the `--run` string |
| Boxes (□) for CJK, emoji, or icons | The chosen font lacks those glyphs. Pass `--font` pointing to a font that has them (e.g. a Nerd Font or Noto Sans Mono CJK), or use SVG so the viewer's fonts are used |
| Ugly/tiny fallback font warning | No monospace TTF found. Pass `--font /path/to/Mono.ttf` |
| `Unknown gradient` warning | Use a preset from `--list-gradients`, `none`, or comma-separated hex colours like `"#ff0080,#7928ca"` |
| Terminal `--lines`/`--focus` hit the wrong lines | Numbers count **output** lines only (the command header isn't numbered). Add `--line-numbers` to see them, or use `--focus-match` instead |
| `--focus-match` matches nothing | The regex runs on plain text (no ANSI codes). Use `^E ` for line starts, `\|` for alternation, and test with `grep -E` first |
| `glass` looks like a plain tint | Glass needs a colourful backdrop - try `--gradient mesh-aurora` or `vaporwave` |
| SVG shows no blur/glow | SVG viewers vary; `glass` blur is PNG-only (SVG gets translucency), neon glow works in browsers. Prefer PNG for these styles |
| Image too wide | `--wrap 80`, lower `--font-size`, or trim the content |
| Progress bars show many lines | The script collapses `\r` overwrites; ensure the raw output was captured, not a re-flowed copy |
| `--run` timed out | Increase `--timeout`, or capture output separately and pipe it in |
| Cannot execute code in this harness | See the fallback below |

## Fallback: no code execution available
If the harness cannot run commands, hand-write a **self-contained SVG** (or HTML) and save it as the deliverable. Keep to this skeleton, using one `<text>` per line, `xml:space="preserve"`, a monospace font stack, and one `<tspan fill="…">` per coloured token:

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="720" height="260" viewBox="0 0 720 260">
  <rect width="720" height="260" rx="14" fill="#282a36"/>
  <rect width="720" height="40" rx="14" fill="#21222c"/>
  <circle cx="24" cy="20" r="6.5" fill="#ff5f56"/><circle cx="46" cy="20" r="6.5" fill="#ffbd2e"/><circle cx="68" cy="20" r="6.5" fill="#27c93f"/>
  <g font-family="'JetBrains Mono',Menlo,Consolas,'DejaVu Sans Mono',monospace" font-size="15" xml:space="preserve">
    <text x="28" y="82"><tspan fill="#ff79c6">def</tspan> <tspan fill="#50fa7b">add</tspan><tspan fill="#f8f8f2">(a, b):</tspan></text>
    <text x="28" y="108"><tspan fill="#f8f8f2">    </tspan><tspan fill="#ff79c6">return</tspan> <tspan fill="#f8f8f2">a + b</tspan></text>
  </g>
</svg>
```
Line pitch ≈ 1.5 × font-size; character width ≈ 0.6 × font-size. Tell the user it was hand-built.

## Installing this skill in a harness
The skill is just a folder: `code-screenshot/SKILL.md` + `code-screenshot/scripts/codeshot.py`. From the repository root, `./install.sh` copies it to `~/.claude/skills/` (`--project` for the current project, `--dest DIR` for any harness, `--package` for a `.skill` zip, `--deps` to also pip-install Pillow + Pygments).
- **Harnesses with native skills** (e.g. Claude Code and compatible agents): copy the folder into the skills directory, such as `~/.claude/skills/code-screenshot/` or `<project>/.claude/skills/code-screenshot/`.
- **Harnesses without native skills** (Cursor, Codex CLI, Gemini CLI, Aider, custom agents): put the folder anywhere in the repo or home dir, and add a rule to the harness's instruction file (`AGENTS.md`, `.cursor/rules/`, `GEMINI.md`, `CONVENTIONS.md`, system prompt): *"For screenshots of code or terminal output, follow `<path>/code-screenshot/SKILL.md`."* Keep `SKILL_DIR` pointing at that folder.
- **Chat UIs with a sandbox**: upload the folder (or the `.skill` zip) or paste SKILL.md and the script into the conversation, then ask for the screenshot.
