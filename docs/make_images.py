#!/usr/bin/env python3
"""Regenerate every image used in README.md (and the GitHub social preview).

Everything is rendered by codeshot itself, so the images double as a regression check.
Requires: Pillow, Pygments, git.   Usage:  python3 docs/make_images.py
"""
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "skills" / "code-screenshot" / "scripts" / "codeshot.py"
IMG = ROOT / "docs" / "images"
SAMPLE = ROOT / "examples" / "sample.py"
PYTEST = ROOT / "examples" / "pytest-session.ansi"

spec = importlib.util.spec_from_file_location("codeshot", CLI)
cs = importlib.util.module_from_spec(spec)
sys.modules["codeshot"] = cs  # required for dataclasses under `from __future__ import annotations`
spec.loader.exec_module(cs)


def cli(*args, cwd=ROOT):
    cmd = [sys.executable, str(CLI), *[str(a) for a in args]]
    subprocess.run(cmd, check=True, cwd=str(cwd), stdout=subprocess.DEVNULL)


def font(size, bold=False):
    names = (["DejaVuSans-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"] if bold else ["DejaVuSans.ttf", "Arial.ttf", "arial.ttf"])
    for n in names:
        try:
            return ImageFont.truetype(n, size)
        except OSError:
            continue
    return ImageFont.load_default(size)


def paste_with_shadow(base, win, xy, blur=30, dy=28, opacity=0.6):
    x, y = xy
    blk = Image.new("RGBA", win.size, (0, 0, 0, 255))
    blk.putalpha(win.getchannel("A").point(lambda v: int(v * opacity)))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    sh.alpha_composite(blk, (x, y + dy))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(blur)))
    base.alpha_composite(win, (x, y))


def fit_width(img, w):
    return img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)


def make_git_repo(path: Path):
    env = dict(os.environ, GIT_AUTHOR_NAME="Ada", GIT_AUTHOR_EMAIL="ada@example.com",
               GIT_COMMITTER_NAME="Ada", GIT_COMMITTER_EMAIL="ada@example.com")
    n = [0]

    def git(*a, msg=None):
        n[0] += 1
        e = dict(env, GIT_AUTHOR_DATE=f"2026-01-{n[0]:02d}T12:00:00", GIT_COMMITTER_DATE=f"2026-01-{n[0]:02d}T12:00:00")
        subprocess.run(["git", *a], cwd=path, env=e, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def commit(fname, text, msg):
        (path / fname).write_text(text)
        git("add", ".")
        git("commit", "-q", "-m", msg)

    git("init", "-q", "-b", "main")
    commit("app.py", "print('hello')\n", "feat: initial commit")
    commit("app.py", "print('hello')\nprint('world')\n", "feat: add world")
    git("checkout", "-q", "-b", "feature/glass-style")
    commit("glass.py", "GLASS = True\n", "feat: add glass style")
    commit("glass.py", "GLASS = True\nBLUR = 18\n", "fix: blur radius on glass")
    git("checkout", "-q", "main")
    commit("app.py", "print('hello')\nprint('world')\nprint('!')\n", "docs: update README")
    git("merge", "-q", "--no-ff", "feature/glass-style", "-m", "Merge feature/glass-style")
    git("tag", "v1.0.0")
    (path / "app.py").write_text("print('hello')\nprint('world')\nprint('!')\nprint('done')\n")
    git("add", ".")
    git("commit", "-q", "-m", "feat: finish line")


def main():
    IMG.mkdir(parents=True, exist_ok=True)
    (IMG / "styles").mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="codeshot-img-"))
    S, P = SAMPLE, PYTEST
    snippet = ["--lines", "5-18", "--highlight", "15-16", "--title", "retry.py"]

    # ---------------------------------------------------------------- per-style images
    for style in cs.STYLES:
        extra = ["--theme", "github-light", "--gradient", "paper"] if style == "flat" else []
        cli(S, *snippet, "--style", style, "-o", IMG / "styles" / f"{style}.png", *extra)
    cli(S, *snippet, "--style", "glass", "--gradient", "mesh-aurora", "-o", IMG / "styles" / "glass.png")

    # ---------------------------------------------------------------- galleries
    for kind in ("styles", "gradients", "themes"):
        cli(S, "--lines", "5-14", "--gallery", kind, "--title", "retry.py", "-o", IMG / f"gallery-{kind}.png")

    # ---------------------------------------------------------------- close-up & focus
    cli(S, "--style", "closeup", "--lines", "10-17", "--focus", "14-16", "--line-numbers", "--theme", "one-dark",
        "-o", IMG / "code-closeup-focus.png")
    cli(P, "--command", "pytest -q", "--style", "closeup", "--lines", "8-13", "--focus", "12-13", "--theme", "one-dark",
        "-o", IMG / "terminal-closeup-focus.png")
    cli(P, "--command", "pytest -q", "--style", "closeup", "--focus-match", r"FAILED|^E ", "--line-numbers", "--theme", "one-dark",
        "-o", IMG / "terminal-focus-match.png")

    # before / after composite
    cli(P, "--command", "pytest -q", "--style", "macos", "--margin", "0", "--no-shadow", "--gradient", "none", "--scale", "2",
        "--theme", "one-dark", "-o", tmp / "full.png")
    cli(P, "--command", "pytest -q", "--style", "closeup", "--lines", "8-13", "--focus", "12-13", "--theme", "one-dark",
        "--scale", "2", "-o", tmp / "close.png")
    full, close = Image.open(tmp / "full.png"), Image.open(tmp / "close.png")
    lw, rw = 760, 760
    full, close = fit_width(full, lw), fit_width(close, rw)
    pad, head = 48, 84
    W, H = pad * 3 + lw + rw, head + pad + max(full.height, close.height) + pad
    sheet = Image.new("RGBA", (W, H), "#f3f4f8")
    d = ImageDraw.Draw(sheet)
    d.text((pad, 40), "Full output", font=font(26, True), fill="#1f2430", anchor="lm")
    d.text((pad * 2 + lw, 40), "--style closeup --lines 8-13 --focus 12-13", font=font(24, True), fill="#1f2430", anchor="lm")
    paste_with_shadow(sheet, full, (pad, head), blur=14, dy=10, opacity=0.35)
    paste_with_shadow(sheet, close, (pad * 2 + lw, head + (full.height - close.height) // 2), blur=14, dy=10, opacity=0.35)
    sheet.convert("RGB").save(IMG / "focus-before-after.png")

    # ---------------------------------------------------------------- terminal examples
    cli(P, "--command", "pytest -q", "--style", "windows", "--theme", "github-dark", "--tail", "7", "--end-prompt",
        "--prompt", "PS C:\\proj>", "-o", IMG / "terminal-windows.png")
    repo = tmp / "demo-repo"
    repo.mkdir()
    make_git_repo(repo)
    cli("--run", "git log --graph --oneline --decorate --color=always", "--style", "card", "--gradient", "mesh-sunrise",
        "--prompt", "~/demo-repo $", "--end-prompt", "-o", IMG / "terminal-git-log.png", cwd=repo)
    diff = subprocess.run(["git", "diff", "HEAD~1", "HEAD"], cwd=repo, capture_output=True, text=True, check=True).stdout
    (tmp / "change.diff").write_text(diff)
    cli(tmp / "change.diff", "--lang", "diff", "--style", "neon", "--theme", "github-dark", "--title", "git diff", "-o", IMG / "code-diff-neon.png")
    cli(S, "--style", "card", "--gradient", "#0ea5e9,#6366f1", "--gradient-angle", "160", "--lines", "5-13", "--theme", "one-dark",
        "-o", IMG / "custom-gradient.png")

    # ---------------------------------------------------------------- hero banner
    cli(S, "--lines", "5-18", "--highlight", "15-16", "--title", "retry.py", "--style", "macos", "--margin", "0", "--no-shadow",
        "--gradient", "none", "--theme", "dracula", "-o", tmp / "h_code.png")
    cli(P, "--command", "pytest -q", "--lines", "5-17", "--focus-match", r"FAILED|^E |passed|failed", "--style", "macos", "--margin", "0",
        "--no-shadow", "--gradient", "none", "--theme", "one-dark", "-o", tmp / "h_term.png")
    code, term = fit_width(Image.open(tmp / "h_code.png"), 900), fit_width(Image.open(tmp / "h_term.png"), 920)
    W, H = 1760, 940
    hero = cs.make_backdrop_image(W, H, cs.GRADIENTS["mesh-aurora"])
    paste_with_shadow(hero, code, (70, 70))
    paste_with_shadow(hero, term, (W - 920 - 70, H - term.height - 70))
    hero.convert("RGB").save(IMG / "hero.png", optimize=True)

    # ---------------------------------------------------------------- social preview (1280x640)
    cli(S, "--lines", "8-17", "--title", "retry.py", "--style", "macos", "--margin", "0", "--no-shadow", "--gradient", "none",
        "--theme", "github-dark", "--font-size", "15", "--min-width", "420", "-o", tmp / "s_code.png")
    sw, sh = 1280, 640
    soc = cs.make_backdrop_image(sw, sh, cs.GRADIENTS["mesh-nebula"])
    d = ImageDraw.Draw(soc)
    d.text((72, 190), "codeshot", font=font(104, True), fill="#ffffff", anchor="ls")
    d.text((76, 262), "Beautiful screenshots of code", font=font(36), fill="#f3e8ff", anchor="ls")
    d.text((76, 308), "and terminal output.", font=font(36), fill="#f3e8ff", anchor="ls")
    d.text((76, 380), "For humans and AI agents.", font=font(30, True), fill="#ffffff", anchor="ls")
    chips = ["PNG + SVG", "9 styles", "16 gradients", "close-up & focus"]
    overlay = Image.new("RGBA", soc.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    f = font(22, True)
    x, cy = 76, 566
    for c in chips:
        w = int(od.textlength(c, font=f)) + 36
        od.rounded_rectangle([x, cy - 24, x + w, cy + 24], radius=24, fill=(255, 255, 255, 46), outline=(255, 255, 255, 150), width=2)
        od.text((x + w / 2, cy), c, font=f, fill="#ffffff", anchor="mm")
        x += w + 14
    soc.alpha_composite(overlay)
    win = fit_width(Image.open(tmp / "s_code.png"), 560)
    paste_with_shadow(soc, win, (sw - 560 - 48, 150), blur=26, dy=22)
    soc.convert("RGB").save(IMG / "social-preview.png", optimize=True)

    shutil.rmtree(tmp, ignore_errors=True)
    total = sum(p.stat().st_size for p in IMG.rglob("*.png"))
    print(f"Done: {len(list(IMG.rglob('*.png')))} images, {total / 1e6:.1f} MB -> {IMG}")


if __name__ == "__main__":
    main()
