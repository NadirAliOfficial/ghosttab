# GhostTab 👻

**Your real browser, driven invisibly from the terminal.**

Drive your real, logged-in browser on macOS from the terminal — as **text**, not screenshots.

Built for AI coding agents (Claude Code, Codex, any shell-capable agent): reading a page costs a few hundred tokens instead of ~1,500 per screenshot, steps run in ~0.2s, and **background mode** works in an off-screen window so you keep using your Mac.

```bash
b bg on                          # work in a hidden window, your focus untouched
b go https://news.ycombinator.com
b t 800                          # last 800 chars of page text
b e                              # numbered clickable / fillable elements
b c 12                           # click element 12
b do 'f Email me@x.com ; c "Next" ; t 300'   # batch steps in one call
b up - ~/Movies/demo.mp4         # attach a file/video to the page, no dialog
b ocr total                      # read canvas/images/PDF on-device, no image tokens
b bg off
```

## Features
- **Text first** — page text, element lists, values; shadow DOM + same-origin iframes included.
- **Background mode** — separate Brave/Chrome window parked off-screen; shares your logins.
- **Uploads without dialogs** — files streamed into the page (`upload`) or dropped on drop zones (`drop`); 50 MB ≈ 3s.
- **On-device OCR** — Apple Vision reads what the DOM can't (canvas, images, charts) with click coordinates.
- **Real input when needed** — trusted mouse clicks, typing, key combos, native file dialog (front window).
- **Batching + short aliases** — fewer tool calls, fewer tokens.
- **Safety rails** — the bundled agent skill forbids final actions (send/pay/submit/delete) without the user's OK, and typing passwords/2FA. If the background window disappears, `b` stops instead of touching your window.

## Install
```bash
git clone https://github.com/NadirAliOfficial/ghosttab && cd ghosttab && ./install.sh
```
Requirements: macOS, Brave or Chrome (`BROWSER=chrome b ...`), Xcode Command Line Tools (for OCR).

One-time: browser menu bar → **View → Developer → Allow JavaScript from Apple Events**.
Optional for real mouse/keyboard: System Settings → Privacy & Security → **Accessibility** → allow your terminal.

`install.sh` also installs `SKILL.md` as a Claude Code skill (`~/.claude/skills/ghosttab`), so the agent picks it up automatically.

## Commands
| | |
|---|---|
| `tabs` `tab N` `open URL` `go URL` `back` `reload` `close` `url` `front` | navigation |
| `text [start] [len]` · `tail [len]` | read page text |
| `el` · `find TEXT` | list / filter interactive elements |
| `click N\|TEXT` · `fill N\|LABEL VALUE` · `select` · `check` · `hover` · `enter` | act (JS, background-safe) |
| `scroll down\|up\|top\|bottom\|PX\|TEXT` | page + main scroll panel |
| `upload N\|LABEL\|- FILE` · `drop N\|TEXT FILE` | files/videos without dialogs |
| `ocr [FILTER]` · `clickat X Y` | on-device OCR + click by coordinates |
| `rclick` `type` `key COMBO` `rupload` `rclickat` | real input (front window) |
| `console` · `wait TEXT [sec]` · `js CODE` · `shot` | debug, waits, raw JS, last-resort screenshot |
| `bg on\|off\|status` | background mode |
| `do 'cmd ; cmd'` | batch |

Aliases: `t`=tail `x`=text `e`=el `c`=click `f`=fill `g`=go `o`=open `u`=url `k`=key `s`=scroll `w`=wait `up`=upload.

## Limits
Cross-origin iframes (payment fields, third-party sign-in) aren't readable — by design. CAPTCHAs and 2FA are left to you. Off-screen windows throttle video/animation; reading and clicking are unaffected. A few sites accept only trusted input — use the real-input commands in the front window.

## Test
```bash
tests/smoke.sh   # end-to-end in a background window
```

MIT © Nadir Ali
