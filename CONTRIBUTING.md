# Contributing to codeshot

Thanks for helping! This is a small project; the goal is to keep it **dependency-light, offline-friendly and easy for AI agents to drive**.

## Dev setup

```bash
git clone https://github.com/cryxnet/codeshot.git && cd codeshot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 skills/code-screenshot/scripts/codeshot.py --doctor
```

## Run the tests

```bash
python3 -m unittest discover -s tests -v
```

Tests use only the standard library. PNG tests are skipped automatically if Pillow is missing, so please also run the suite once **without** Pillow/Pygments installed to make sure the SVG-only path still works.

## Regenerate the README images

All README images are produced by codeshot itself (they double as a visual regression check):

```bash
python3 docs/make_images.py     # needs Pillow, Pygments and git
```

Commit the changed images together with the code change that caused them, and look at them before committing.

## Project layout

```
skills/code-screenshot/   the skill: what `npx skills add` installs
  SKILL.md                instructions the agent reads
  scripts/codeshot.py     the renderer (single file, stdlib + optional Pillow/Pygments)
.claude-plugin/           Claude Code plugin + marketplace manifests (source: ./)
examples/                 inputs used by tests and README images
docs/                     image generator + generated images
tests/                    unittest suite
```

## Common contributions

**Add a design style:** add an entry to `STYLES` in `codeshot.py` (it only needs the keys that differ from `DEFAULTS`). If it needs new drawing code, implement it in **both** `render_image` (PNG) and `render_svg`. Add it to the table in `SKILL.md` (including a row in the decision guide) and the README, then regenerate images.

**Add a gradient:** add it to `GRADIENTS` (`G([...colors], angle, mesh=False)`); mesh gradients are `[base, blob, blob, blob]`.

**Add a colour theme:** add it to `THEMES`. `pyg` must be a Pygments style name (see `pygmentize -L styles`); unknown names fall back to `monokai`.

## Releasing

Bump the version in **four** places (a test fails if they disagree): `__version__` in `codeshot.py`, `.claude-plugin/plugin.json`, the plugin entry in `.claude-plugin/marketplace.json`, and a new heading in `CHANGELOG.md`. Then tag it (`git tag v1.1.0 && git push --tags`). Claude Code users receive updates when the version changes; `npx skills update` re-pulls from the repo.

## Guidelines

- Keep `codeshot.py` a **single file** that runs on Python 3.9+ with no required third-party packages.
- Never make the renderer touch the network.
- Anything that executes commands (`--run`) must stay opt-in and documented in `SKILL.md`'s safety rules.
- Update `SKILL.md` whenever flags change: it is the interface AI agents actually read.
- Add or update tests for behaviour changes and add a line to `CHANGELOG.md`.

## Reporting bugs

Please include `python3 skills/code-screenshot/scripts/codeshot.py --doctor` output, the exact command, and the input (or a minimal piece of it).
