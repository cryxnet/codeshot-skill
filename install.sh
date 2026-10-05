#!/usr/bin/env bash
# Install the code-screenshot skill into an AI agent harness (or package it as a .skill zip).
#
#   ./install.sh                  -> ~/.claude/skills/code-screenshot        (user-level)
#   ./install.sh --project        -> ./.claude/skills/code-screenshot        (current project)
#   ./install.sh --dest DIR       -> DIR/code-screenshot                     (any harness)
#   ./install.sh --package        -> ./dist/code-screenshot.skill            (zip for upload)
#   add --deps to also `pip install -r requirements.txt`
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/skills/code-screenshot"
DEST="${HOME}/.claude/skills"
PACKAGE=0
DEPS=0

usage() { sed -n '2,8p' "$0" | sed 's/^# \{0,1\}//'; }

while [ $# -gt 0 ]; do
  case "$1" in
    --project) DEST="$PWD/.claude/skills" ;;
    --dest)    [ $# -ge 2 ] || { echo "--dest needs a directory" >&2; exit 2; }; DEST="$2"; shift ;;
    --package) PACKAGE=1 ;;
    --deps)    DEPS=1 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; usage; exit 2 ;;
  esac
  shift
done

command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
[ -f "$SRC/SKILL.md" ] || { echo "Cannot find $SRC/SKILL.md" >&2; exit 1; }

if [ "$DEPS" -eq 1 ]; then
  python3 -m pip install -r "$HERE/requirements.txt" || {
    echo "pip failed. If your Python is externally managed, use a venv or add --break-system-packages." >&2; exit 1; }
fi

if [ "$PACKAGE" -eq 1 ]; then
  mkdir -p "$HERE/dist"
  python3 - "$SRC" "$HERE/dist/code-screenshot.skill" <<'PY'
import os, sys, zipfile
src, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            if f.endswith((".pyc", ".DS_Store")):
                continue
            p = os.path.join(root, f)
            z.write(p, os.path.join("code-screenshot", os.path.relpath(p, src)))
print("Packaged", out)
PY
  exit 0
fi

mkdir -p "$DEST"
rm -rf "$DEST/code-screenshot"
cp -R "$SRC" "$DEST/code-screenshot"
find "$DEST/code-screenshot" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
echo "Installed to: $DEST/code-screenshot"
python3 "$DEST/code-screenshot/scripts/codeshot.py" --doctor || \
  echo "Tip: run ./install.sh --deps (or: pip install pillow pygments) for PNG output and syntax colours."
