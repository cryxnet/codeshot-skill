"""Tests for codeshot. Stdlib only:  python3 -m unittest discover -s tests -v

PNG tests are skipped automatically when Pillow is not installed.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "code-screenshot" / "scripts" / "codeshot.py"
SAMPLE = ROOT / "examples" / "sample.py"
PYTEST_ANSI = ROOT / "examples" / "pytest-session.ansi"

spec = importlib.util.spec_from_file_location("codeshot", SCRIPT)
cs = importlib.util.module_from_spec(spec)
sys.modules["codeshot"] = cs  # needed for dataclasses with postponed annotations
spec.loader.exec_module(cs)

try:
    import PIL  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False

TH = cs.THEMES["dracula"]
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def run_cli(*args, stdin=None):
    return subprocess.run([sys.executable, str(SCRIPT), *[str(a) for a in args]],
                          input=stdin, capture_output=True, text=True, cwd=str(ROOT))


def parse(*argv):
    return cs.build_parser().parse_args(list(argv))


def prepared_lines(argv, text=None, mode="code"):
    """Run the same selection pipeline the CLI uses and return plain strings."""
    a = parse(*argv)
    spans = cs.parse_ansi(text, TH) if mode == "terminal" else cs.highlight_code(text, "python", None, TH)
    while spans and not spans[-1]:          # same trimming the CLI does
        spans.pop()
    raw = [cs.Line(s, False, a.start_line + i) for i, s in enumerate(spans)]
    if mode == "terminal":
        raw.insert(0, cs.Line([cs.Span("$ cmd", TH["fg"])]))          # context line, num=None
    cfg = cs.make_cfg(a)
    return cs.finalize(raw, a, cfg, TH, mode)


class TestAnsi(unittest.TestCase):
    def test_basic_colors_and_reset(self):
        lines = cs.parse_ansi("\x1b[31mred\x1b[0m plain", TH)
        self.assertEqual([s.text for s in lines[0]], ["red", " plain"])
        self.assertEqual(lines[0][0].fg, cs.DARK_ANSI[1])
        self.assertEqual(lines[0][1].fg, TH["fg"])

    def test_bold_underline_and_bright(self):
        sp = cs.parse_ansi("\x1b[1;4;92mx\x1b[0m", TH)[0][0]
        self.assertTrue(sp.bold and sp.underline)
        self.assertEqual(sp.fg, cs.DARK_ANSI[10])

    def test_256_and_truecolor(self):
        a, b = cs.parse_ansi("\x1b[38;5;208ma\x1b[38;2;1;2;3mb", TH)[0]
        self.assertEqual(a.fg, "#ff8700")
        self.assertEqual(b.fg, "#010203")

    def test_carriage_return_overwrites_line(self):
        lines = cs.parse_ansi("progress 10%\rprogress 100%\ndone", TH)
        self.assertEqual(["".join(s.text for s in l) for l in lines], ["progress 100%", "done"])

    def test_other_escape_sequences_are_dropped(self):
        lines = cs.parse_ansi("\x1b[2K\x1b]0;title\x07hello\x1b[1A", TH)
        self.assertEqual("".join(s.text for s in lines[0]), "hello")

    def test_reverse_video_swaps_colors(self):
        sp = cs.parse_ansi("\x1b[7mx", TH)[0][0]
        self.assertEqual(sp.bg, TH["fg"])
        self.assertEqual(sp.fg, TH["bg"])


class TestHelpers(unittest.TestCase):
    def test_cell_width(self):
        self.assertEqual(cs.tw("abc"), 3)
        self.assertEqual(cs.tw("\u4e16\u754c"), 4)   # wide CJK
        self.assertEqual(cs.tw("e\u0301"), 1)        # combining accent

    def test_parse_ranges(self):
        self.assertEqual(cs.parse_ranges("1,3-5"), {1, 3, 4, 5})
        self.assertEqual(cs.parse_ranges(None), set())

    def test_mix_and_hex(self):
        self.assertEqual(cs.mix("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(cs.hex_rgb("#abc"), (170, 187, 204))

    def test_resolve_backdrop(self):
        self.assertIsNone(cs.resolve_backdrop("none", TH, None))
        self.assertEqual(cs.resolve_backdrop("#112233,#445566", TH, 90)["colors"], ["#112233", "#445566"])
        self.assertTrue(cs.resolve_backdrop("mesh-aurora", TH, None)["mesh"])
        self.assertEqual(cs.resolve_backdrop("not-a-gradient", TH, None)["colors"], list(TH["grad"]))  # falls back
        self.assertEqual(cs.resolve_backdrop(None, TH, None)["angle"], 135)

    def test_wrap_lines(self):
        wrapped = cs.wrap_lines([cs.Line([cs.Span("x" * 25, "#fff")], num=7)], 10)
        self.assertEqual([l.width() for l in wrapped], [10, 10, 5])
        self.assertEqual([l.num for l in wrapped], [7, None, None])


class TestSelection(unittest.TestCase):
    CODE = "\n".join(f"line{i}" for i in range(1, 11))

    def texts(self, lines):
        return ["".join(sp.text for sp in l.spans) for l in lines]

    def test_lines_range_keeps_true_numbers(self):
        lines = prepared_lines(["--lines", "3-5", "--line-numbers"], self.CODE)
        self.assertEqual([l.num for l in lines], [3, 4, 5])
        self.assertTrue(self.texts(lines)[0].strip().startswith("3"))

    def test_focus_dims_everything_else(self):
        lines = prepared_lines(["--focus", "4-5"], self.CODE)
        self.assertEqual([l.dim for l in lines], [n not in (4, 5) for n in range(1, 11)])

    def test_focus_match_and_highlight_match(self):
        lines = prepared_lines(["--focus-match", "line[19]$", "--highlight-match", "line2$"], self.CODE)
        self.assertEqual([l.num for l in lines if not l.dim], [1, 9])
        self.assertTrue(next(l for l in lines if l.num == 2).hl)

    def test_tail(self):
        lines = prepared_lines(["--tail", "3"], self.CODE)
        self.assertEqual([l.num for l in lines], [8, 9, 10])

    def test_max_lines_adds_marker(self):
        lines = prepared_lines(["--max-lines", "4"], self.CODE)
        self.assertEqual(len(lines), 5)
        self.assertIn("6 more lines", self.texts(lines)[-1])

    def test_terminal_context_line_survives_crop_and_focus(self):
        out = "\n".join(f"out{i}" for i in range(1, 9))
        lines = prepared_lines(["--lines", "2-3", "--focus", "3"], out, mode="terminal")
        self.assertEqual(self.texts(lines)[0], "$ cmd")           # command header kept
        self.assertFalse(lines[0].dim)                           # ...and never dimmed
        self.assertEqual([l.num for l in lines[1:]], [2, 3])
        self.assertEqual([l.dim for l in lines[1:]], [True, False])

    def test_terminal_focus_match_ignores_ansi_codes(self):
        out = "ok\n\x1b[31mFAILED\x1b[0m thing\nok"
        lines = prepared_lines(["--focus-match", "^FAILED"], out, mode="terminal")
        self.assertEqual([l.dim for l in lines[1:]], [True, False, True])

    def test_terminal_line_numbers_only_when_requested(self):
        out = "a\nb"
        self.assertNotIn("1", self.texts(prepared_lines([], out, mode="terminal"))[1])
        numbered = self.texts(prepared_lines(["--line-numbers"], out, mode="terminal"))
        self.assertTrue(numbered[1].lstrip().startswith("1"))


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestRendering(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def out(self, name):
        return str(Path(self.tmp.name) / name)

    def test_every_style_renders_png(self):
        from PIL import Image
        for style in cs.STYLES:
            with self.subTest(style=style):
                path = self.out(f"{style}.png")
                r = run_cli(SAMPLE, "--style", style, "-o", path)
                self.assertEqual(r.returncode, 0, r.stderr)
                self.assertEqual(Path(path).read_bytes()[:8], PNG_MAGIC)
                with Image.open(path) as im:
                    w, h = im.size
                self.assertGreater(w, 200)
                self.assertGreater(h, 100)

    def test_every_style_renders_valid_svg(self):
        for style in cs.STYLES:
            with self.subTest(style=style):
                path = self.out(f"{style}.svg")
                r = run_cli(SAMPLE, "--style", style, "--gradient", "mesh-sunrise", "-o", path)
                self.assertEqual(r.returncode, 0, r.stderr)
                dom = xml.dom.minidom.parse(path)
                self.assertGreater(len(dom.getElementsByTagName("text")), 5)

    def test_every_gradient_and_theme_renders(self):
        for name in list(cs.GRADIENTS)[:3] + ["mesh-nebula"]:
            r = run_cli("--code", "x = 1", "--lang", "python", "--gradient", name, "-o", self.out("g.png"))
            self.assertEqual(r.returncode, 0, r.stderr)
        for theme in cs.THEMES:
            r = run_cli("--code", "x = 1", "--lang", "python", "--theme", theme, "-o", self.out("t.png"))
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_gradient_angle_direction(self):
        # 180deg = top -> bottom;  90deg = left -> right
        top_bottom = cs.make_gradient_image(100, 100, ["#000000", "#ffffff"], 180)
        self.assertLess(top_bottom.getpixel((50, 2))[0], 20)
        self.assertGreater(top_bottom.getpixel((50, 97))[0], 235)
        left_right = cs.make_gradient_image(100, 100, ["#000000", "#ffffff"], 90)
        self.assertLess(left_right.getpixel((2, 50))[0], 20)
        self.assertGreater(left_right.getpixel((97, 50))[0], 235)

    def test_diagonal_gradient_hits_end_colors_at_corners(self):
        g = cs.make_gradient_image(200, 120, ["#000000", "#ffffff"], 135)
        self.assertLess(g.getpixel((1, 1))[0], 12)
        self.assertGreater(g.getpixel((198, 118))[0], 243)

    def test_closeup_and_transparent_backdrop_have_clear_corners(self):
        from PIL import Image
        path = self.out("c.png")
        self.assertEqual(run_cli(SAMPLE, "--style", "closeup", "-o", path).returncode, 0)
        with Image.open(path) as im:
            self.assertEqual(im.getpixel((0, 0))[3], 0)

    def test_scale_changes_pixel_size(self):
        from PIL import Image
        a, b = self.out("s1.png"), self.out("s2.png")
        run_cli(SAMPLE, "--scale", "1", "-o", a)
        run_cli(SAMPLE, "--scale", "2", "-o", b)
        with Image.open(a) as ia, Image.open(b) as ib:
            self.assertAlmostEqual(ib.width / ia.width, 2, delta=0.1)

    def test_terminal_run_and_stdin(self):
        r = run_cli("--run", "echo hello", "-o", self.out("run.png"))
        self.assertEqual(r.returncode, 0, r.stderr)
        r = run_cli("--mode", "terminal", "--command", "cat x", "-o", self.out("stdin.png"), stdin="\x1b[32mok\x1b[0m\n")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_example_terminal_session_with_focus(self):
        r = run_cli(PYTEST_ANSI, "--command", "pytest -q", "--style", "closeup", "--focus-match", r"FAILED|^E ",
                    "--line-numbers", "-o", self.out("p.png"))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("mode=terminal", r.stdout)

    def test_galleries(self):
        for kind in ("styles", "gradients", "themes"):
            r = run_cli(SAMPLE, "--gallery", kind, "-o", self.out(f"{kind}.png"))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(Path(self.out(f"{kind}.png")).read_bytes()[:8], PNG_MAGIC)


class TestCli(unittest.TestCase):
    def test_version_and_lists(self):
        self.assertIn(cs.__version__, run_cli("--version").stdout)
        self.assertIn("closeup", run_cli("--list-styles").stdout)
        self.assertIn("mesh-aurora", run_cli("--list-gradients").stdout)
        self.assertIn("dracula", run_cli("--list-themes").stdout)

    def test_empty_input_is_an_error(self):
        r = run_cli("--code", "", "-o", os.path.join(tempfile.gettempdir(), "never.png"))
        self.assertNotEqual(r.returncode, 0)

    def test_falls_back_to_svg_extension_logic(self):
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "x.svg")
            r = run_cli("--code", "print(1)", "--lang", "python", "-o", out)
            self.assertEqual(r.returncode, 0, r.stderr)
            xml.dom.minidom.parse(out)

    def test_run_timeout_is_reported(self):
        r = run_cli("--run", "sleep 5", "--timeout", "1", "-o", os.path.join(tempfile.gettempdir(), "t.png"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("timed out", r.stderr)


class TestDistribution(unittest.TestCase):
    """Guards the metadata that `npx skills add` and Claude Code's /plugin marketplace rely on."""

    @staticmethod
    def frontmatter(path):
        import re
        text = Path(path).read_text(encoding="utf-8")
        m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
        assert m, f"{path}: missing YAML frontmatter"
        return dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line)

    def test_every_skill_is_discoverable_by_the_skills_cli(self):
        skills = sorted((ROOT / "skills").glob("*/SKILL.md"))
        self.assertTrue(skills, "expected skills/<name>/SKILL.md")
        for path in skills:
            with self.subTest(skill=path.parent.name):
                fm = self.frontmatter(path)
                self.assertEqual(fm["name"], path.parent.name)          # folder name == skill name
                self.assertRegex(fm["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
                self.assertLessEqual(len(fm["name"]), 64)
                self.assertTrue(fm["description"].strip())
                self.assertLessEqual(len(fm["description"]), 1024)
                self.assertNotRegex(fm["description"], r": | #")     # would break strict YAML parsers

    def test_skill_ships_its_script(self):
        self.assertTrue((ROOT / "skills" / "code-screenshot" / "scripts" / "codeshot.py").is_file())

    def test_plugin_manifests(self):
        import json
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        self.assertTrue(market["owner"]["name"])
        entry = market["plugins"][0]
        self.assertEqual(entry["name"], plugin["name"])                # entry name must equal manifest name
        self.assertEqual(entry["source"], "./")
        self.assertNotIn(market["name"], {"claude-plugins-official", "anthropic-marketplace", "agent-skills"})

    def test_versions_agree_everywhere(self):
        import json, re
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        top = re.search(r"^## \[(\d+\.\d+\.\d+)\]", (ROOT / "CHANGELOG.md").read_text(), re.M).group(1)
        self.assertEqual({cs.__version__, plugin["version"], market["plugins"][0]["version"], top}, {cs.__version__})


if __name__ == "__main__":
    unittest.main()
