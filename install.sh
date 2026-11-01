#!/bin/bash
# Installs `b` + the Claude Code skill into ~/.claude/skills/ghosttab
set -e
cd "$(dirname "$0")"
D="$HOME/.claude/skills/ghosttab"
mkdir -p "$D"
cp b.py SKILL.md ocr.swift "$D/"
chmod +x "$D/b.py"
xcrun swiftc -O "$D/ocr.swift" -o "$D/ocr"
BIN=/opt/homebrew/bin; [ -d "$BIN" ] || BIN=/usr/local/bin
ln -sf "$D/b.py" "$BIN/b"
echo "Installed: $BIN/b"
echo "One-time: Brave/Chrome menu bar > View > Developer > Allow JavaScript from Apple Events"
echo "Optional (real mouse/keyboard): System Settings > Privacy & Security > Accessibility > allow your terminal"
