#!/usr/bin/env python3
"""
codeshot.py - render code snippets and terminal output as polished screenshots.

Harness-agnostic: needs only Python 3.9+. Optional libs:
  Pillow    -> PNG output          (pip install pillow)
  Pygments  -> syntax highlighting (pip install pygments)
Without Pillow the script falls back to SVG (no dependencies at all).

Examples
  python3 codeshot.py app.py -o shot.png --line-numbers --highlight 3-5
  cat out.txt | python3 codeshot.py --mode terminal --command "npm test" -o term.png
  python3 codeshot.py --run "ls -la" -o ls.png
  python3 codeshot.py --code 'print("hi")' --lang python -o hi.png
  python3 codeshot.py app.py --style closeup --lines 4-8 --focus 5-6
  python3 codeshot.py --run "pytest -q" --style closeup --focus-match "FAIL|Error"
  python3 codeshot.py app.py --style glass --gradient mesh-aurora
  python3 codeshot.py app.py --gallery styles -o styles.png
  python3 codeshot.py --doctor
"""
from __future__ import annotations

__version__ = "1.0.0"

import argparse
import copy
import math
import os
import re
import subprocess
import sys
import textwrap
import unicodedata
from dataclasses import dataclass, field, replace
from types import SimpleNamespace
from typing import List, Optional


def warn(msg: str) -> None:
    print(f"[codeshot] {msg}", file=sys.stderr)


# --------------------------------------------------------------------------- #
# Themes
# --------------------------------------------------------------------------- #
DARK_ANSI = ["#4b5263", "#e06c75", "#98c379", "#e5c07b", "#61afef", "#c678dd", "#56b6c2", "#abb2bf",
             "#5c6370", "#ff7b86", "#b5e890", "#f0d28a", "#82c4ff", "#d994ee", "#73d0dc", "#ffffff"]
LIGHT_ANSI = ["#383a42", "#e45649", "#50a14f", "#c18401", "#4078f2", "#a626a4", "#0184bc", "#a0a1a7",
              "#4f525e", "#e06c75", "#6bb76a", "#d9a441", "#5c92ff", "#c05cc0", "#2aa1c0", "#696c77"]

THEMES = {
    "dracula":        dict(pyg="dracula",        bg="#282a36", fg="#f8f8f2", bar="#21222c", muted="#6272a4", grad=("#bd93f9", "#ff79c6"), light=False),
    "monokai":        dict(pyg="monokai",        bg="#272822", fg="#f8f8f2", bar="#1e1f1c", muted="#75715e", grad=("#a6e22e", "#66d9ef"), light=False),
    "nord":           dict(pyg="nord",           bg="#2e3440", fg="#d8dee9", bar="#272c36", muted="#616e88", grad=("#88c0d0", "#5e81ac"), light=False),
    "one-dark":       dict(pyg="one-dark",       bg="#282c34", fg="#abb2bf", bar="#21252b", muted="#5c6370", grad=("#61afef", "#c678dd"), light=False),
    "github-dark":    dict(pyg="github-dark",    bg="#0d1117", fg="#e6edf3", bar="#161b22", muted="#7d8590", grad=("#1f6feb", "#8957e5"), light=False),
    "solarized-dark": dict(pyg="solarized-dark", bg="#002b36", fg="#93a1a1", bar="#00212b", muted="#586e75", grad=("#2aa198", "#268bd2"), light=False),
    "github-light":   dict(pyg="default",        bg="#ffffff", fg="#24292f", bar="#f0f2f5", muted="#8c959f", grad=("#c7d2fe", "#fbcfe8"), light=True),
    "solarized-light":dict(pyg="solarized-light",bg="#fdf6e3", fg="#586e75", bar="#eee8d5", muted="#93a1a1", grad=("#fde68a", "#fbcfe8"), light=True),
}
DEFAULT_THEME = "dracula"


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def hex_rgb(c: str):
    c = c.lstrip("#")
    if len(c) == 3:
        c = "".join(ch * 2 for ch in c)
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(a: str, b: str, t: float) -> str:
    """Blend colour a toward b by t (0..1)."""
    ra, rb = hex_rgb(a), hex_rgb(b)
    return "#%02x%02x%02x" % tuple(round(x + (y - x) * t) for x, y in zip(ra, rb))


def cw(ch: str) -> int:
    """Terminal cell width of a character."""
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def tw(s: str) -> int:
    return sum(cw(c) for c in s)


@dataclass
class Span:
    text: str
    fg: str
    bg: Optional[str] = None
    bold: bool = False
    italic: bool = False
    underline: bool = False


@dataclass
class Line:
    spans: List[Span] = field(default_factory=list)
    hl: bool = False
    num: Optional[int] = None
    dim: bool = False

    def width(self) -> int:
        return sum(tw(s.text) for s in self.spans)


# --------------------------------------------------------------------------- #
# Code -> spans (Pygments)
# --------------------------------------------------------------------------- #
def highlight_code(src: str, lang: Optional[str], filename: Optional[str], th: dict) -> List[List[Span]]:
    try:
        from pygments import lex
        from pygments.lexers import TextLexer, get_lexer_by_name, guess_lexer, guess_lexer_for_filename
        from pygments.styles import get_style_by_name
        from pygments.util import ClassNotFound
    except ImportError:
        warn("Pygments not installed - rendering without syntax colours (pip install pygments).")
        return [[Span(l, th["fg"])] if l else [] for l in src.split("\n")]

    lexer = None
    if lang:
        try:
            lexer = get_lexer_by_name(lang)
        except ClassNotFound:
            warn(f"Unknown language '{lang}', guessing instead.")
    if lexer is None and filename:
        try:
            lexer = guess_lexer_for_filename(filename, src)
        except ClassNotFound:
            pass
    if lexer is None:
        try:
            lexer = guess_lexer(src)
        except ClassNotFound:
            lexer = TextLexer()
    try:
        style = get_style_by_name(th["pyg"])
    except ClassNotFound:
        style = get_style_by_name("monokai")

    lines: List[List[Span]] = [[]]
    for ttype, value in lex(src, lexer):
        st = style.style_for_token(ttype)
        color = "#" + st["color"] if st["color"] else th["fg"]
        for i, part in enumerate(value.split("\n")):
            if i > 0:
                lines.append([])
            if part:
                lines[-1].append(Span(part, color, None, bool(st["bold"]), bool(st["italic"]), bool(st["underline"])))
    return lines


# --------------------------------------------------------------------------- #
# ANSI text -> spans
# --------------------------------------------------------------------------- #
ANSI_RE = re.compile(
    r"\x1b\[([0-9;:]*)m"                      # SGR (colours / styles)
    r"|\x1b\[[0-9;?<=>]*[ -/]*[@-ln-~]"       # any other CSI sequence (cursor moves etc.) -> dropped
    r"|\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)"     # OSC (titles, hyperlinks) -> dropped
    r"|\x1b[()][0-9A-Za-z]|\x1b[=>78]"        # misc escapes -> dropped
)


def xterm256(n: int, pal: List[str]) -> str:
    if n < 16:
        return pal[n]
    if n < 232:
        n -= 16
        lv = [0, 95, 135, 175, 215, 255]
        return "#%02x%02x%02x" % (lv[n // 36], lv[(n // 6) % 6], lv[n % 6])
    g = 8 + 10 * (n - 232)
    return "#%02x%02x%02x" % (g, g, g)


def _apply_sgr(params: str, st: dict, pal: List[str]) -> None:
    codes = [int(p) if p.isdigit() else 0 for p in re.split(r"[;:]", params)] if params else [0]
    i = 0
    while i < len(codes):
        c = codes[i]
        if c == 0:
            st.update(fg=None, bg=None, bold=False, dim=False, italic=False, ul=False, rev=False)
        elif c == 1: st["bold"] = True
        elif c == 2: st["dim"] = True
        elif c == 3: st["italic"] = True
        elif c == 4: st["ul"] = True
        elif c == 7: st["rev"] = True
        elif c == 22: st["bold"] = st["dim"] = False
        elif c == 23: st["italic"] = False
        elif c == 24: st["ul"] = False
        elif c == 27: st["rev"] = False
        elif 30 <= c <= 37: st["fg"] = pal[c - 30]
        elif c == 39: st["fg"] = None
        elif 40 <= c <= 47: st["bg"] = pal[c - 40]
        elif c == 49: st["bg"] = None
        elif 90 <= c <= 97: st["fg"] = pal[c - 90 + 8]
        elif 100 <= c <= 107: st["bg"] = pal[c - 100 + 8]
        elif c in (38, 48):
            key = "fg" if c == 38 else "bg"
            if i + 2 < len(codes) and codes[i + 1] == 5:
                st[key] = xterm256(codes[i + 2], pal)
                i += 2
            elif i + 4 < len(codes) and codes[i + 1] == 2:
                st[key] = "#%02x%02x%02x" % tuple(min(255, v) for v in codes[i + 2:i + 5])
                i += 4
        i += 1


def parse_ansi(text: str, th: dict) -> List[List[Span]]:
    pal = LIGHT_ANSI if th["light"] else DARK_ANSI
    st = dict(fg=None, bg=None, bold=False, dim=False, italic=False, ul=False, rev=False)
    lines: List[List[Span]] = [[]]
    text = text.replace("\r\n", "\n")

    def emit(t: str) -> None:
        if not t:
            return
        fg, bg = st["fg"], st["bg"]
        if st["rev"]:
            fg, bg = (bg or th["bg"]), (fg or th["fg"])
        fg = fg or th["fg"]
        if st["dim"]:
            fg = mix(fg, th["bg"], 0.5)
        lines[-1].append(Span(t, fg, bg, st["bold"], st["italic"], st["ul"]))

    def feed(chunk: str) -> None:
        for piece in re.split(r"(\n|\r)", chunk):
            if piece == "\n":
                lines.append([])
            elif piece == "\r":      # carriage return: progress bars overwrite the line
                lines[-1] = []
            else:
                emit(piece)

    pos = 0
    for m in ANSI_RE.finditer(text):
        feed(text[pos:m.start()])
        if m.group(1) is not None:
            _apply_sgr(m.group(1), st, pal)
        pos = m.end()
    feed(text[pos:])
    return lines


# --------------------------------------------------------------------------- #
# Layout transforms
# --------------------------------------------------------------------------- #
def wrap_lines(lines: List[Line], cols: int) -> List[Line]:
    out: List[Line] = []
    for ln in lines:
        if ln.width() <= cols:
            out.append(ln)
            continue
        segs: List[List[Span]] = [[]]
        w = 0
        for sp in ln.spans:
            buf = ""
            for ch in sp.text:
                c = cw(ch)
                if w + c > cols and w > 0:
                    if buf:
                        segs[-1].append(replace(sp, text=buf))
                        buf = ""
                    segs.append([])
                    w = 0
                buf += ch
                w += c
            if buf:
                segs[-1].append(replace(sp, text=buf))
        for k, seg in enumerate(segs):
            out.append(Line(seg, ln.hl, ln.num if k == 0 else None, ln.dim))
    return out


def parse_ranges(spec: Optional[str]) -> set:
    nums = set()
    if not spec:
        return nums
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            nums.update(range(int(a), int(b) + 1))
        else:
            nums.add(int(part))
    return nums


# --------------------------------------------------------------------------- #
# Fonts (PNG)
# --------------------------------------------------------------------------- #
FONT_TRIPLES = [
    ("JetBrainsMono-Regular.ttf", "JetBrainsMono-Bold.ttf", "JetBrainsMono-Italic.ttf"),
    ("FiraCode-Regular.ttf", "FiraCode-Bold.ttf", None),
    ("/System/Library/Fonts/Menlo.ttc#0", "/System/Library/Fonts/Menlo.ttc#1", "/System/Library/Fonts/Menlo.ttc#2"),
    ("consola.ttf", "consolab.ttf", "consolai.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
     "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Oblique.ttf"),
    ("DejaVuSansMono.ttf", "DejaVuSansMono-Bold.ttf", "DejaVuSansMono-Oblique.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationMono-Italic.ttf"),
    ("LiberationMono-Regular.ttf", "LiberationMono-Bold.ttf", "LiberationMono-Italic.ttf"),
    ("UbuntuMono-R.ttf", "UbuntuMono-B.ttf", "UbuntuMono-RI.ttf"),
    ("cour.ttf", "courbd.ttf", "couri.ttf"),
    ("FreeMono.ttf", "FreeMonoBold.ttf", "FreeMonoOblique.ttf"),
]


def _try_font(name: Optional[str], size: int):
    from PIL import ImageFont
    if not name:
        return None
    index = 0
    if "#" in name:
        name, idx = name.rsplit("#", 1)
        index = int(idx)
    try:
        return ImageFont.truetype(name, size, index=index)
    except (OSError, ValueError):
        return None


def load_fonts(user_font: Optional[str], size: int) -> dict:
    from PIL import ImageFont
    if user_font:
        reg = _try_font(user_font, size)
        if reg:
            return dict(regular=reg, bold=None, italic=None, name=user_font)
        warn(f"Could not load font '{user_font}', falling back.")
    for r, b, i in FONT_TRIPLES:
        reg = _try_font(r, size)
        if reg:
            return dict(regular=reg, bold=_try_font(b, size), italic=_try_font(i, size), name=r)
    try:
        warn("No monospace TTF found - using Pillow's built-in font. Pass --font /path/to/Mono.ttf for best results.")
        return dict(regular=ImageFont.load_default(size), bold=None, italic=None, name="builtin")
    except TypeError:
        return dict(regular=ImageFont.load_default(), bold=None, italic=None, name="builtin")


def doctor() -> int:
    ok = True
    print(f"python  : {sys.version.split()[0]}")
    try:
        import PIL
        print(f"Pillow  : {PIL.__version__}  (PNG output available)")
        f = load_fonts(None, 16)
        print(f"font    : {f['name']}  bold={'yes' if f['bold'] else 'faux'}  italic={'yes' if f['italic'] else 'no'}")
    except ImportError:
        print("Pillow  : MISSING  -> PNG unavailable, SVG fallback only (pip install pillow)")
        ok = False
    try:
        import pygments
        print(f"Pygments: {pygments.__version__}  (syntax highlighting available)")
    except ImportError:
        print("Pygments: MISSING  -> no syntax colours (pip install pygments)")
        ok = False
    return 0 if ok else 1


# --------------------------------------------------------------------------- #
# Design styles (frame / layout variants)  -  override with explicit flags
# --------------------------------------------------------------------------- #
DEFAULTS = dict(chrome="macos", font_size=15, line_height=1.5, padding=28, margin=56, radius=14,
                min_width=480, shadow=True, backdrop=None, glass=False, glow=False, border=False,
                line_numbers=False, scale=2)

STYLES = {
    # classic floating window with traffic lights
    "macos":   dict(),
    # Windows-terminal look: icon + title left, window controls right
    "windows": dict(chrome="windows"),
    # IDE look: file tab strip, line numbers on
    "editor":  dict(chrome="tab", line_numbers=True),
    # no title bar, soft shadow - clean for blogs
    "minimal": dict(chrome="none", margin=40, padding=24, radius=12),
    # CLOSE-UP: only the code. No frame, no backdrop, big type, tight padding
    "closeup": dict(chrome="none", margin=0, padding=20, radius=10, font_size=18, shadow=False, backdrop="none", scale=3),
    # social/slide card: big padding, big type, big shadow
    "card":    dict(chrome="none", margin=72, padding=38, radius=22, font_size=17, line_height=1.6),
    # frosted-glass window over the gradient
    "glass":   dict(glass=True, border=True, radius=18),
    # glowing gradient outline on a near-black backdrop
    "neon":    dict(chrome="none", glow=True, border=True, shadow=False, margin=64, radius=16, backdrop="#07070d"),
    # flat 1px-outlined box, transparent surround - for docs / READMEs
    "flat":    dict(chrome="none", margin=0, shadow=False, backdrop="none", border=True, radius=6, padding=22),
}
BAR_H = {"macos": 44, "windows": 40, "tab": 40, "none": 0}

# --------------------------------------------------------------------------- #
# Gradient backdrops
# --------------------------------------------------------------------------- #
def G(colors, angle=135, mesh=False):
    return dict(colors=colors, angle=angle, mesh=mesh)


GRADIENTS = {
    "sunset":      G(["#ff512f", "#dd2476"]),
    "fire":        G(["#f12711", "#f5af19"]),
    "peach":       G(["#ffecd2", "#fcb69f"]),
    "candy":       G(["#f093fb", "#f5576c"]),
    "lavender":    G(["#a18cd1", "#fbc2eb"]),
    "vaporwave":   G(["#ff6ec7", "#7873f5", "#00e5ff"]),
    "ocean":       G(["#2193b0", "#6dd5ed"]),
    "aurora":      G(["#00c9ff", "#92fe9d"]),
    "forest":      G(["#134e5e", "#71b280"]),
    "midnight":    G(["#0f2027", "#203a43", "#2c5364"]),
    "ice":         G(["#e0eafc", "#cfdef3"]),
    "paper":       G(["#fdfbfb", "#e2e5ea"]),
    "mono":        G(["#232526", "#414345"]),
    # mesh gradients: [base, blob, blob, blob]
    "mesh-aurora":  G(["#0b1020", "#7c3aed", "#06b6d4", "#22c55e"], mesh=True),
    "mesh-sunrise": G(["#1b1035", "#ff6b6b", "#feca57", "#ff9ff3"], mesh=True),
    "mesh-nebula":  G(["#0a0a23", "#8e2de2", "#4a00e0", "#ff0080"], mesh=True),
}
BLOB_POS = [(0.10, 0.12), (0.92, 0.30), (0.45, 1.02), (0.96, 0.98)]
_HEX = re.compile(r"^#?([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def resolve_backdrop(spec: Optional[str], th: dict, angle: Optional[float]):
    """spec: None/'theme' | 'none' | preset name | '#hex' | '#hex1,#hex2,...' -> dict or None"""
    if spec is None or str(spec).strip().lower() == "theme":
        return G(list(th["grad"]), angle if angle is not None else 135)
    s = str(spec).strip()
    if s.lower() == "none":
        return None
    if s.lower() in GRADIENTS:
        g = dict(GRADIENTS[s.lower()])
        if angle is not None:
            g["angle"] = angle
        return g
    cols = [c.strip() for c in s.split(",") if c.strip()]
    if cols and all(_HEX.match(c) for c in cols):
        return G(["#" + c.lstrip("#") for c in cols], angle if angle is not None else 135)
    warn(f"Unknown gradient '{spec}' - using theme gradient. See --list-gradients.")
    return G(list(th["grad"]), angle if angle is not None else 135)


def make_gradient_image(W: int, H: int, colors: List[str], angle: float):
    """CSS-style linear gradient (0deg = up, 90 = right, 180 = down, 135 = down-right)."""
    from PIL import Image
    n = 256
    rgb = [hex_rgb(c) for c in colors]
    strip = Image.new("RGB", (1, n))
    seg = len(rgb) - 1
    for i in range(n):
        if seg == 0:
            c = rgb[0]
        else:
            t = i / (n - 1) * seg
            k = min(int(t), seg - 1)
            f = t - k
            c = tuple(round(a + (b - a) * f) for a, b in zip(rgb[k], rgb[k + 1]))
        strip.putpixel((0, i), c)
    ang = math.radians(angle)
    L = max(2, int(round(abs(W * math.sin(ang)) + abs(H * math.cos(ang)))))   # CSS gradient-line length
    D = int(math.hypot(W, H) * 1.06) + 4
    y0 = (D - L) // 2
    g = Image.new("RGB", (D, D), rgb[0])
    g.paste(Image.new("RGB", (D, D - (y0 + L)), rgb[-1]), (0, y0 + L))
    g.paste(strip.resize((D, L), Image.BILINEAR), (0, y0))
    g = g.rotate(180 - angle, resample=Image.BICUBIC)
    left, top = (D - W) // 2, (D - H) // 2
    return g.crop((left, top, left + W, top + H)).convert("RGBA")


def make_mesh_image(W: int, H: int, colors: List[str]):
    from PIL import Image, ImageDraw, ImageFilter
    sw, sh = max(8, W // 4), max(8, H // 4)
    img = Image.new("RGB", (sw, sh), colors[0])
    d = ImageDraw.Draw(img)
    r = max(sw, sh) * 0.42
    for (px, py), c in zip(BLOB_POS, colors[1:]):
        d.ellipse([px * sw - r, py * sh - r, px * sw + r, py * sh + r], fill=c)
    img = img.filter(ImageFilter.GaussianBlur(max(sw, sh) * 0.16))
    return img.resize((W, H), Image.BICUBIC).convert("RGBA")


def make_backdrop_image(W: int, H: int, bd: dict):
    from PIL import Image
    if bd["mesh"]:
        return make_mesh_image(W, H, bd["colors"])
    if len(bd["colors"]) == 1:
        return Image.new("RGBA", (W, H), bd["colors"][0])
    return make_gradient_image(W, H, bd["colors"], bd["angle"])


def make_cfg(a, style: Optional[str] = None, backdrop: Optional[str] = None, scale: Optional[int] = None):
    c = dict(DEFAULTS)
    c.update(STYLES[style or a.style])
    for k in ("font_size", "line_height", "padding", "margin", "radius", "min_width", "chrome", "backdrop", "scale"):
        v = getattr(a, k, None)
        if v is not None:
            c[k] = v
    if a.no_chrome:
        c["chrome"] = "none"
    if a.no_shadow:
        c["shadow"] = False
    if a.line_numbers:
        c["line_numbers"] = True
    if a.no_line_numbers:
        c["line_numbers"] = False
    if backdrop is not None:
        c["backdrop"] = backdrop
    if scale is not None:
        c["scale"] = scale
    c.update(font=a.font, title=a.title, angle=a.gradient_angle)
    return SimpleNamespace(**c)


# --------------------------------------------------------------------------- #
# PNG renderer
# --------------------------------------------------------------------------- #
def _ring_mask(w: int, h: int, radius: int, width: int):
    from PIL import Image, ImageChops, ImageDraw
    big = Image.new("L", (w * 4, h * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, w * 4 - 1, h * 4 - 1], radius=radius * 4, fill=255)
    inner = Image.new("L", (w * 4, h * 4), 0)
    b = width * 4
    ImageDraw.Draw(inner).rounded_rectangle([b, b, w * 4 - 1 - b, h * 4 - 1 - b], radius=max(0, radius - width) * 4, fill=255)
    return ImageChops.subtract(big, inner).resize((w, h), Image.LANCZOS)


def render_image(lines: List[Line], th: dict, cfg):
    from PIL import Image, ImageChops, ImageDraw, ImageFilter

    S = cfg.scale
    fs = max(8, int(round(cfg.font_size * S)))
    fonts = load_fonts(cfg.font, fs)
    reg = fonts["regular"]
    cell = reg.getlength("M")
    line_h = int(round(fs * cfg.line_height))
    pad_x = int(cfg.padding * S)
    pad_y = int(cfg.padding * S * 0.8)
    bar_h = int(BAR_H[cfg.chrome] * S)
    margin = int(cfg.margin * S)
    radius = int(cfg.radius * S)

    maxcols = max([ln.width() for ln in lines] + [1])
    win_w = max(int(math.ceil(maxcols * cell)) + 2 * pad_x, int(cfg.min_width * S))
    win_h = bar_h + 2 * pad_y + line_h * len(lines)
    W, H = win_w + 2 * margin, win_h + 2 * margin

    # ---- backdrop canvas
    bd = resolve_backdrop(cfg.backdrop, th, cfg.angle) if margin > 0 else None
    canvas = make_backdrop_image(W, H, bd) if bd else Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # ---- window base (solid, or blurred-backdrop "glass")
    if cfg.glass and bd:
        region = canvas.crop((margin, margin, margin + win_w, margin + win_h)).filter(ImageFilter.GaussianBlur(int(18 * S)))
        win = Image.alpha_composite(region, Image.new("RGBA", (win_w, win_h), hex_rgb(th["bg"]) + (150,)))
    else:
        win = Image.new("RGBA", (win_w, win_h), th["bg"])
    d = ImageDraw.Draw(win)

    def draw_text(xy, text, font, fill, anchor="lm"):
        try:
            d.text(xy, text, font=font, fill=fill, anchor=anchor)
        except (ValueError, TypeError):      # bitmap fonts have no anchors
            d.text((xy[0], xy[1] - fs / 2), text, font=font, fill=fill)

    # ---- chrome
    if bar_h:
        bar = th["bar"]
        if cfg.glass:
            win.alpha_composite(Image.new("RGBA", (win_w, bar_h), hex_rgb(bar) + (110,)), (0, 0))
            d = ImageDraw.Draw(win)
        else:
            d.rectangle([0, 0, win_w, bar_h], fill=bar)
        sep = mix(bar, th["fg"], 0.10)
        tf = load_fonts(cfg.font, max(8, int(fs * 0.85)))["regular"]
        lw = max(1, S // 2 if S > 1 else 1)
        if cfg.chrome == "macos":
            d.line([0, bar_h, win_w, bar_h], fill=sep, width=lw)
            r = int(6.5 * S)
            for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
                cx, cy = int(24 * S) + i * int(22 * S), bar_h // 2
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=c)
            if cfg.title:
                draw_text((win_w / 2, bar_h / 2), cfg.title, tf, th["muted"], "mm")
        elif cfg.chrome == "windows":
            d.line([0, bar_h, win_w, bar_h], fill=sep, width=lw)
            cy, ic = bar_h // 2, int(7 * S)
            d.rounded_rectangle([int(16 * S), cy - ic, int(16 * S) + 2 * ic, cy + ic], radius=int(3 * S), fill=th["grad"][0])
            draw_text((int(16 * S) + 3 * ic, cy), cfg.title or "Terminal", tf, mix(th["fg"], th["bg"], 0.30))
            bw, col, k = int(46 * S), mix(th["fg"], th["bg"], 0.25), int(5 * S)
            x0 = win_w - 3 * bw
            cx = x0 + bw // 2
            d.line([cx - k, cy, cx + k, cy], fill=col, width=lw)
            cx += bw
            d.rectangle([cx - k, cy - k, cx + k, cy + k], outline=col, width=lw)
            cx += bw
            d.line([cx - k, cy - k, cx + k, cy + k], fill=col, width=lw)
            d.line([cx - k, cy + k, cx + k, cy - k], fill=col, width=lw)
        elif cfg.chrome == "tab":
            title = cfg.title or "untitled"
            tab_w = min(win_w, int(tf.getlength(title)) + int(56 * S))
            d.rectangle([0, 0, tab_w, bar_h], fill=th["bg"] if not cfg.glass else mix(th["bg"], th["bar"], 0.0))
            d.rectangle([0, 0, tab_w, max(2, int(2 * S))], fill=th["grad"][0])
            d.ellipse([int(14 * S), bar_h // 2 - int(4 * S), int(22 * S), bar_h // 2 + int(4 * S)], fill=th["grad"][1])
            draw_text((int(30 * S), bar_h // 2 + 1), title, tf, th["fg"])
            d.line([tab_w, bar_h, win_w, bar_h], fill=sep, width=lw)

    # ---- text
    top = bar_h + pad_y
    for i, ln in enumerate(lines):
        y = top + i * line_h
        if ln.hl:
            d.rectangle([0, y, win_w, y + line_h], fill=mix(th["bg"], th["fg"], 0.10))
            d.rectangle([0, y, max(2, int(3 * S)), y + line_h], fill=th["grad"][0])
        col = 0
        for sp in ln.spans:
            x = pad_x + col * cell
            w = tw(sp.text) * cell
            if sp.bg:
                d.rectangle([x, y, x + w, y + line_h], fill=sp.bg)
            font, faux = reg, False
            if sp.bold:
                if fonts["bold"]:
                    font = fonts["bold"]
                else:
                    faux = True
            elif sp.italic and fonts["italic"]:
                font = fonts["italic"]
            cy = y + line_h / 2
            if sp.text.isascii():
                draw_text((x, cy), sp.text, font, sp.fg)
                if faux:
                    draw_text((x + S * 0.6, cy), sp.text, font, sp.fg)
            else:  # keep wide / non-ASCII glyphs locked to the cell grid
                c0 = col
                for ch in sp.text:
                    cx = pad_x + c0 * cell
                    draw_text((cx, cy), ch, font, sp.fg)
                    if faux:
                        draw_text((cx + S * 0.6, cy), ch, font, sp.fg)
                    c0 += cw(ch)
            if sp.underline:
                uy = y + line_h * 0.86
                d.line([x, uy, x + w, uy], fill=sp.fg, width=max(1, S // 2))
            col += tw(sp.text)

    # ---- rounded mask
    big = Image.new("L", (win_w * 4, win_h * 4), 0)
    ImageDraw.Draw(big).rounded_rectangle([0, 0, win_w * 4 - 1, win_h * 4 - 1], radius=radius * 4, fill=255)
    mask = big.resize((win_w, win_h), Image.LANCZOS)

    # ---- shadow
    if margin > 0 and cfg.shadow:
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        off = int(14 * S)
        ImageDraw.Draw(sh).rounded_rectangle(
            [margin, margin + off, margin + win_w, margin + win_h + off], radius=radius, fill=(0, 0, 0, 150))
        canvas = Image.alpha_composite(canvas, sh.filter(ImageFilter.GaussianBlur(int(16 * S))))

    # ---- neon glow (behind the window edge)
    ring_colors = list(th["grad"])
    if cfg.glow and margin > 0:
        ringcol = make_gradient_image(win_w, win_h, ring_colors, 135)
        glow = Image.new("RGBA", (win_w, win_h), (0, 0, 0, 0))
        glow.paste(ringcol, (0, 0), _ring_mask(win_w, win_h, radius, max(4, int(9 * S))))
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        layer.paste(glow, (margin, margin))
        layer = layer.filter(ImageFilter.GaussianBlur(int(16 * S)))
        for _ in range(5):
            canvas = Image.alpha_composite(canvas, layer)

    # ---- composite window
    win.putalpha(mask)
    canvas.alpha_composite(win, (margin, margin))

    # ---- border
    if cfg.border:
        bw_ = max(1, int(round(1.2 * S)))
        ring = _ring_mask(win_w, win_h, radius, bw_)
        if cfg.glow:
            b = make_gradient_image(win_w, win_h, ring_colors, 135)
        elif cfg.glass:
            b = Image.new("RGBA", (win_w, win_h), (255, 255, 255, 255))
            ring = ring.point(lambda v: int(v * 0.35))
        else:
            b = Image.new("RGBA", (win_w, win_h), hex_rgb(mix(th["bg"], th["fg"], 0.22 if not th["light"] else 0.18)) + (255,))
        b.putalpha(ring)
        canvas.alpha_composite(b, (margin, margin))
    return canvas


def render_png(lines: List[Line], th: dict, cfg, out: str):
    img = render_image(lines, th, cfg)
    if out.lower().endswith((".jpg", ".jpeg")):
        img = img.convert("RGB")
    img.save(out)
    return img.size


# --------------------------------------------------------------------------- #
# SVG renderer (zero dependencies)
# --------------------------------------------------------------------------- #
def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def render_svg(lines: List[Line], th: dict, cfg, out: str):
    fs = cfg.font_size
    cell = fs * 0.602
    line_h = fs * cfg.line_height
    pad_x, pad_y = cfg.padding, cfg.padding * 0.8
    bar_h = BAR_H[cfg.chrome]
    margin, radius = cfg.margin, cfg.radius
    maxcols = max([ln.width() for ln in lines] + [1])
    win_w = max(maxcols * cell + 2 * pad_x, cfg.min_width)
    win_h = bar_h + 2 * pad_y + line_h * len(lines)
    W, H = win_w + 2 * margin, win_h + 2 * margin
    fam = "'JetBrains Mono','Fira Code','SF Mono',Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"
    bd = resolve_backdrop(cfg.backdrop, th, cfg.angle) if margin > 0 else None
    scale = cfg.scale

    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W * scale:.0f}" height="{H * scale:.0f}" viewBox="0 0 {W:.1f} {H:.1f}">', "<defs>"]
    if bd and not bd["mesh"] and len(bd["colors"]) > 1:
        ang = math.radians(bd["angle"])
        dx, dy = math.sin(ang), -math.cos(ang)
        stops = "".join(f'<stop offset="{i / (len(bd["colors"]) - 1):.3f}" stop-color="{c}"/>' for i, c in enumerate(bd["colors"]))
        p.append(f'<linearGradient id="bd" x1="{0.5 - dx / 2:.3f}" y1="{0.5 - dy / 2:.3f}" x2="{0.5 + dx / 2:.3f}" y2="{0.5 + dy / 2:.3f}">{stops}</linearGradient>')
    if bd and bd["mesh"]:
        for i, c in enumerate(bd["colors"][1:]):
            p.append(f'<radialGradient id="m{i}"><stop offset="0" stop-color="{c}" stop-opacity="0.95"/><stop offset="1" stop-color="{c}" stop-opacity="0"/></radialGradient>')
    ring_stops = f'<stop offset="0" stop-color="{th["grad"][0]}"/><stop offset="1" stop-color="{th["grad"][1]}"/>'
    p.append(f'<linearGradient id="ring" x1="0" y1="0" x2="1" y2="1">{ring_stops}</linearGradient>')
    p.append('<filter id="sh" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="14" stdDeviation="16" flood-color="#000" flood-opacity="0.55"/></filter>')
    p.append('<filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="10"/></filter>')
    p.append(f'<clipPath id="win"><rect width="{win_w:.1f}" height="{win_h:.1f}" rx="{radius}"/></clipPath>')
    p.append("</defs>")

    if bd:
        if bd["mesh"]:
            p.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="{bd["colors"][0]}"/>')
            r = max(W, H) * 0.6
            for i, (px, py) in enumerate(BLOB_POS[:len(bd["colors"]) - 1]):
                p.append(f'<circle cx="{px * W:.1f}" cy="{py * H:.1f}" r="{r:.1f}" fill="url(#m{i})"/>')
        elif len(bd["colors"]) == 1:
            p.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="{bd["colors"][0]}"/>')
        else:
            p.append(f'<rect width="{W:.1f}" height="{H:.1f}" fill="url(#bd)"/>')

    p.append(f'<g transform="translate({margin},{margin})">')
    if cfg.glow and margin > 0:
        p.append(f'<rect width="{win_w:.1f}" height="{win_h:.1f}" rx="{radius}" fill="none" stroke="url(#ring)" stroke-width="6" filter="url(#glow)" opacity="0.9"/>')
    shadow = ' filter="url(#sh)"' if (cfg.shadow and margin > 0) else ""
    base_op = ' fill-opacity="0.58"' if cfg.glass else ""
    p.append(f'<rect width="{win_w:.1f}" height="{win_h:.1f}" rx="{radius}" fill="{th["bg"]}"{base_op}{shadow}/>')
    p.append('<g clip-path="url(#win)">')

    if bar_h:
        bar_op = ' fill-opacity="0.45"' if cfg.glass else ""
        sep = mix(th["bar"], th["fg"], 0.10)
        if cfg.chrome == "tab":
            title = cfg.title or "untitled"
            tab_w = min(win_w, len(title) * fs * 0.85 * 0.602 + 56)
            p.append(f'<rect width="{win_w:.1f}" height="{bar_h}" fill="{th["bar"]}"{bar_op}/>')
            p.append(f'<rect width="{tab_w:.1f}" height="{bar_h}" fill="{th["bg"]}"/><rect width="{tab_w:.1f}" height="2" fill="{th["grad"][0]}"/>')
            p.append(f'<circle cx="18" cy="{bar_h / 2}" r="4" fill="{th["grad"][1]}"/>')
            p.append(f'<text x="30" y="{bar_h / 2 + 1}" fill="{th["fg"]}" font-family="{fam}" font-size="{fs * 0.85:.1f}" dominant-baseline="central">{_esc(title)}</text>')
        else:
            p.append(f'<rect width="{win_w:.1f}" height="{bar_h}" fill="{th["bar"]}"{bar_op}/>')
            p.append(f'<rect y="{bar_h}" width="{win_w:.1f}" height="1" fill="{sep}"/>')
        if cfg.chrome == "macos":
            for i, c in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
                p.append(f'<circle cx="{24 + i * 22}" cy="{bar_h / 2}" r="6.5" fill="{c}"/>')
            if cfg.title:
                p.append(f'<text x="{win_w / 2:.1f}" y="{bar_h / 2}" fill="{th["muted"]}" font-family="{fam}" font-size="{fs * 0.85:.1f}" text-anchor="middle" dominant-baseline="central">{_esc(cfg.title)}</text>')
        elif cfg.chrome == "windows":
            cy = bar_h / 2
            col = mix(th["fg"], th["bg"], 0.25)
            p.append(f'<rect x="16" y="{cy - 7}" width="14" height="14" rx="3" fill="{th["grad"][0]}"/>')
            p.append(f'<text x="40" y="{cy}" fill="{mix(th["fg"], th["bg"], 0.30)}" font-family="{fam}" font-size="{fs * 0.85:.1f}" dominant-baseline="central">{_esc(cfg.title or "Terminal")}</text>')
            x0 = win_w - 138
            p.append(f'<g stroke="{col}" stroke-width="1" fill="none"><line x1="{x0 + 18}" y1="{cy}" x2="{x0 + 28}" y2="{cy}"/>'
                     f'<rect x="{x0 + 64}" y="{cy - 5}" width="10" height="10"/>'
                     f'<line x1="{x0 + 110}" y1="{cy - 5}" x2="{x0 + 120}" y2="{cy + 5}"/><line x1="{x0 + 110}" y1="{cy + 5}" x2="{x0 + 120}" y2="{cy - 5}"/></g>')

    top = bar_h + pad_y
    for i, ln in enumerate(lines):
        y = top + i * line_h
        if ln.hl:
            p.append(f'<rect x="0" y="{y:.1f}" width="{win_w:.1f}" height="{line_h:.1f}" fill="{mix(th["bg"], th["fg"], 0.10)}"/>')
            p.append(f'<rect x="0" y="{y:.1f}" width="3" height="{line_h:.1f}" fill="{th["grad"][0]}"/>')
        col = 0
        for sp in ln.spans:
            x = pad_x + col * cell
            n = tw(sp.text)
            if sp.bg:
                p.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{n * cell:.1f}" height="{line_h:.1f}" fill="{sp.bg}"/>')
            if sp.text.strip():
                attrs = f'x="{x:.2f}" y="{y + line_h / 2:.2f}" fill="{sp.fg}" font-family="{fam}" font-size="{fs}" dominant-baseline="central" xml:space="preserve" style="white-space:pre"'
                if sp.bold: attrs += ' font-weight="700"'
                if sp.italic: attrs += ' font-style="italic"'
                if sp.underline: attrs += ' text-decoration="underline"'
                if n > 1: attrs += f' textLength="{n * cell:.2f}" lengthAdjust="spacing"'
                p.append(f"<text {attrs}>{_esc(sp.text)}</text>")
            col += n
    p.append("</g>")
    if cfg.border or cfg.glow:
        stroke = "url(#ring)" if cfg.glow else ("#ffffff" if cfg.glass else mix(th["bg"], th["fg"], 0.2))
        op = ' stroke-opacity="0.35"' if (cfg.glass and not cfg.glow) else ""
        p.append(f'<rect x="0.6" y="0.6" width="{win_w - 1.2:.1f}" height="{win_h - 1.2:.1f}" rx="{radius}" fill="none" stroke="{stroke}" stroke-width="1.2"{op}/>')
    p.append("</g></svg>")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(p))
    return int(W * scale), int(H * scale)


# --------------------------------------------------------------------------- #
# Line preparation (shared by all variants)
# --------------------------------------------------------------------------- #
def _plain(l: Line) -> str:
    return "".join(sp.text for sp in l.spans)


def finalize(lines: List[Line], a, cfg, th: dict, mode: str) -> List[Line]:
    """Selection (--lines/--tail/--focus/--highlight[-match]), wrapping, gutter, dimming.

    Works for code AND terminal. Lines with num=None (the shown command, the end prompt)
    are context: they are never cropped away and never dimmed.
    """
    lines = copy.deepcopy(lines)
    numbered = [l.num for l in lines if l.num is not None]
    if a.lines:
        lo, hi = (a.lines.split("-", 1) if "-" in a.lines else (a.lines, a.lines))
        lo, hi = int(lo), int(hi)
        lines = [l for l in lines if l.num is None or lo <= l.num <= hi]
    if a.tail and numbered:
        cut = max(numbered) - a.tail
        lines = [l for l in lines if l.num is None or l.num > cut]
    if a.highlight_match:
        rx = re.compile(a.highlight_match)
        for l in lines:
            if l.num is not None and rx.search(_plain(l)):
                l.hl = True
    if a.focus or a.focus_match:
        keep = parse_ranges(a.focus)
        rx = re.compile(a.focus_match) if a.focus_match else None
        for l in lines:
            if l.num is None:
                continue
            hit = l.num in keep or bool(rx and rx.search(_plain(l)))
            l.hl = False if hit else l.hl
            l.dim = not hit
    if a.wrap:
        lines = wrap_lines(lines, a.wrap)
    want_gutter = (cfg.line_numbers and mode == "code") or (mode == "terminal" and a.line_numbers)
    if want_gutter:
        nums = [l.num for l in lines if l.num is not None]
        w = len(str(max(nums))) if nums else 1
        for l in lines:
            gutter = (f"{l.num:>{w}}" if l.num is not None else " " * w) + "  "
            l.spans.insert(0, Span(gutter, th["muted"]))
    for l in lines:
        if l.dim:
            for sp in l.spans:
                sp.fg = mix(sp.fg, th["bg"], 0.62)
    if a.max_lines and len(lines) > a.max_lines:
        extra = len(lines) - a.max_lines
        lines = lines[:a.max_lines] + [Line([Span(f"\u2026 {extra} more line{'s' if extra != 1 else ''}", th["muted"], italic=True)])]
    return lines


SAMPLE = '''def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers."""
    seq = [0, 1]
    while len(seq) < n:
        seq.append(seq[-1] + seq[-2])
    return seq[:n]

print(fibonacci(10))'''


# --------------------------------------------------------------------------- #
# Gallery (contact sheet of variants)
# --------------------------------------------------------------------------- #
def make_gallery(kind: str, raw: List[Line], a, th: dict, mode: str, out: str):
    from PIL import Image, ImageDraw
    if kind == "styles":
        items = [(n, dict(style=n)) for n in STYLES]
    elif kind == "gradients":
        items = [(n, dict(style="macos", backdrop=n, margin=40)) for n in GRADIENTS]
    else:
        items = [(t, dict(theme=t)) for t in THEMES]
    thumbs = []
    for name, kw in items:
        t_th = THEMES[kw["theme"]] if "theme" in kw else th
        cfg = make_cfg(a, style=kw.get("style"), backdrop=kw.get("backdrop"), scale=1)
        if "margin" in kw and a.margin is None:
            cfg.margin = kw["margin"]
        cfg.title = a.title if a.title else ("sample.py" if mode == "code" else "Terminal")
        lines = finalize(raw, a, cfg, t_th, mode)[:10]
        img = render_image(lines, t_th, cfg)
        thumbs.append((name, img))
    cols, tw_, gap, label_h = 3, 560, 28, 40
    scaled = []
    for name, img in thumbs:
        r = tw_ / img.width
        scaled.append((name, img.resize((tw_, max(1, int(img.height * r))), Image.LANCZOS)))
    rows = [scaled[i:i + cols] for i in range(0, len(scaled), cols)]
    row_h = [max(i.height for _, i in r) + label_h for r in rows]
    W = cols * tw_ + (cols + 1) * gap
    H = sum(row_h) + (len(rows) + 1) * gap
    sheet = Image.new("RGBA", (W, H), "#eef0f4")
    d = ImageDraw.Draw(sheet)
    lf = load_fonts(None, 20)["regular"]
    y = gap
    for r, rh in zip(rows, row_h):
        for k, (name, img) in enumerate(r):
            x = gap + k * (tw_ + gap)
            d.text((x, y + 4), name, font=lf, fill="#333844")
            sheet.alpha_composite(img, (x, y + label_h))
        y += rh + gap
    sheet.convert("RGB").save(out)
    return sheet.size


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Render code or terminal output as a screenshot (PNG/SVG).",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--version", action="version", version=f"codeshot {__version__}")
    p.add_argument("input", nargs="?", help="File to render, or '-' for stdin")
    p.add_argument("--code", help="Inline text to render instead of a file")
    p.add_argument("-o", "--output", default="screenshot.png", help="Output path (.png/.jpg/.svg). Default screenshot.png")
    p.add_argument("--mode", choices=["auto", "code", "terminal"], default="auto")
    p.add_argument("-l", "--lang", help="Pygments language name (python, js, bash, json, diff, ...)")
    p.add_argument("-t", "--title", help="Window title (default: filename or 'Terminal')")
    p.add_argument("--theme", default=DEFAULT_THEME, choices=sorted(THEMES), help="Syntax/colour theme")
    # design variants
    p.add_argument("--style", default="macos", choices=sorted(STYLES), help="Design variant (frame/layout)")
    p.add_argument("--gradient", "--backdrop", dest="backdrop",
                   help="Backdrop: preset name, 'none', '#hex', or '#hex1,#hex2[,#hex3]'")
    p.add_argument("--gradient-angle", type=float, default=None, help="CSS angle in degrees (0=up, 90=right, 135=diag)")
    p.add_argument("--gallery", choices=["styles", "gradients", "themes"], help="Render a contact sheet of all variants")
    p.add_argument("--list-themes", action="store_true")
    p.add_argument("--list-styles", action="store_true")
    p.add_argument("--list-gradients", action="store_true")
    p.add_argument("--doctor", action="store_true", help="Check dependencies and fonts, then exit")
    # code options
    p.add_argument("--line-numbers", action="store_true")
    p.add_argument("--no-line-numbers", action="store_true")
    p.add_argument("--start-line", type=int, default=1, help="First line number shown (default 1)")
    p.add_argument("--lines", help="Show only this range, e.g. '5-9' (code lines or terminal OUTPUT lines)")
    p.add_argument("--tail", type=int, help="Show only the last N lines (keeps true numbers)")
    p.add_argument("--highlight", help="Lines to emphasise with a band, e.g. '3,7-9'")
    p.add_argument("--highlight-match", metavar="REGEX", help="Band every line matching this regex")
    p.add_argument("--focus", help="Spotlight these lines and dim all others, e.g. '4-6'")
    p.add_argument("--focus-match", metavar="REGEX", help="Spotlight lines matching this regex, dim the rest")
    p.add_argument("--tab-size", type=int, default=4)
    p.add_argument("--no-dedent", action="store_true")
    # terminal options
    p.add_argument("--command", help="Show this command after a prompt above the output")
    p.add_argument("--run", help="Run this shell command, capture stdout+stderr, and render it")
    p.add_argument("--timeout", type=int, default=30, help="Seconds before --run is killed")
    p.add_argument("--prompt", default="$", help="Prompt string, e.g. '$' or 'user@host:~/proj$'")
    p.add_argument("--end-prompt", action="store_true", help="Add a trailing prompt with a cursor block")
    # layout overrides (None = use the style's value)
    p.add_argument("--wrap", type=int, help="Hard-wrap lines at N columns")
    p.add_argument("--max-lines", type=int, help="Truncate after N lines")
    p.add_argument("--font", help="Path to a monospace .ttf/.otf (PNG only)")
    p.add_argument("--font-size", type=float)
    p.add_argument("--line-height", type=float)
    p.add_argument("--scale", type=int, help="Pixel density multiplier (2 = retina)")
    p.add_argument("--padding", type=float)
    p.add_argument("--margin", type=float, help="Space around the window; 0 = no backdrop/shadow")
    p.add_argument("--radius", type=float)
    p.add_argument("--min-width", type=float)
    p.add_argument("--chrome", choices=["macos", "windows", "tab", "none"], help="Title-bar type")
    p.add_argument("--no-chrome", action="store_true", help="Same as --chrome none")
    p.add_argument("--no-shadow", action="store_true")
    return p


def main() -> int:
    a = build_parser().parse_args()
    if a.doctor:
        return doctor()
    if a.list_themes:
        print("\n".join(sorted(THEMES)))
        return 0
    if a.list_styles:
        for n, v in STYLES.items():
            print(f"{n:8s} {v if v else '(default)'}")
        return 0
    if a.list_gradients:
        for n, g in GRADIENTS.items():
            print(f"{n:13s} {'mesh ' if g['mesh'] else ''}{' -> '.join(g['colors'])}")
        return 0
    th = THEMES[a.theme]

    # ---- gather source text
    filename = None
    src = None
    if a.run:
        env = dict(os.environ, FORCE_COLOR="1", CLICOLOR_FORCE="1", TERM="xterm-256color")
        try:
            r = subprocess.run(a.run, shell=True, capture_output=True, timeout=a.timeout, env=env)
            src = (r.stdout + r.stderr).decode("utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            warn(f"Command timed out after {a.timeout}s.")
            return 2
        a.command = a.command or a.run
        mode = "terminal"
    else:
        if a.code is not None:
            src = a.code
        elif a.input and a.input != "-":
            filename = os.path.basename(a.input)
            with open(a.input, "rb") as fh:      # raw bytes: keep lone \r (progress bars)
                src = fh.read().decode("utf-8", errors="replace")
        elif not sys.stdin.isatty():
            src = sys.stdin.buffer.read().decode("utf-8", errors="replace")
        elif a.gallery:
            src, a.lang = SAMPLE, a.lang or "python"
        else:
            warn("No input. Provide a file, --code, --run, or pipe text on stdin.")
            return 2
        mode = a.mode
        if mode == "auto":
            mode = "terminal" if (a.command or "\x1b[" in src) else "code"

    # ---- build raw lines (style-independent)
    if mode == "code":
        src = src.replace("\r\n", "\n").expandtabs(a.tab_size)
    if mode == "terminal":
        spans = parse_ansi(src, th)
        while spans and not spans[-1]:
            spans.pop()
        raw = [Line(s, False, a.start_line + i) for i, s in enumerate(spans)]
        pal = LIGHT_ANSI if th["light"] else DARK_ANSI
        header = []
        if a.command:
            for k, cmd_line in enumerate(a.command.split("\n")):
                lead = (a.prompt + " ") if k == 0 else "> "
                header.append(Line([Span(lead, pal[2], bold=True), Span(cmd_line, th["fg"], bold=True)]))
        raw = header + raw
        if a.end_prompt:
            raw.append(Line([Span(a.prompt + " ", pal[2], bold=True), Span("\u2588", th["fg"])]))
        title = a.title or "Terminal"
    else:
        src = src.strip("\n")
        if not a.no_dedent:
            src = textwrap.dedent(src)
        spans = highlight_code(src, a.lang, filename, th)
        while spans and not spans[-1]:
            spans.pop()
        hl = parse_ranges(a.highlight)
        raw = [Line(s, (a.start_line + i) in hl, a.start_line + i) for i, s in enumerate(spans)]
        title = a.title if a.title is not None else (filename or "")
    if not raw:
        warn("Nothing to render (empty input).")
        return 2
    a.title = title

    try:
        import PIL  # noqa: F401
        have_pil = True
    except ImportError:
        have_pil = False

    # ---- gallery
    if a.gallery:
        if not have_pil:
            warn("--gallery needs Pillow (pip install pillow).")
            return 2
        out = a.output if a.output != "screenshot.png" else f"gallery-{a.gallery}.png"
        size = make_gallery(a.gallery, raw, a, th, mode, out)
        print(f"Wrote {out} ({size[0]}x{size[1]}px, gallery={a.gallery})")
        return 0

    # ---- render one image
    cfg = make_cfg(a)
    lines = finalize(raw, a, cfg, th, mode)
    if not lines:
        warn("Nothing left to render after --lines / --max-lines.")
        return 2
    out = a.output
    want_svg = out.lower().endswith(".svg")
    if not want_svg and not have_pil:
        warn("Pillow not installed - writing SVG instead (pip install pillow for PNG).")
        out = os.path.splitext(out)[0] + ".svg"
        want_svg = True
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    size = render_svg(lines, th, cfg, out) if want_svg else render_png(lines, th, cfg, out)
    print(f"Wrote {out} ({size[0]}x{size[1]}px, {len(lines)} lines, mode={mode}, style={a.style}, theme={a.theme})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
