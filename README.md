# GhostTab 👻

**Browser hands for AI agents — your real, logged-in browser, driven invisibly as text.**

GhostTab is built for **AI agents**, not humans: Claude Code, Codex, or any agent with a shell. Install it once, and your agent can browse, read, click, fill forms and upload files in a hidden tab while you keep using your Mac.

- **~5–10× fewer tokens** than screenshot-based browser agents — pages come back as compact text (a few hundred tokens vs ~1,500 per screenshot)
- **Never steals your screen** — background mode runs in a hidden minimized window: no focus stealing, nothing on screen
- **~0.2s per step**, batching for multi-step actions in one tool call
- Ships with an agent skill (`SKILL.md`) that teaches the agent the commands and the safety rules

What your agent runs:

```bash
b bg on                          # agent tab in your window (GhostTab group), never made active; `bg on hidden` = minimized window
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
- **Background mode** — a hidden, minimized Brave/Chrome window that never comes to the front; shares your logins.
- **Uploads without dialogs** — files streamed into the page (`upload`) or dropped on drop zones (`drop`); 50 MB ≈ 3s.
- **Whole forms in one call** — `form` dumps every field (label, required, value, options); `fillform answers.json` fills the page: text, selects, radios, react-select comboboxes, files.
- **On-device OCR** — Apple Vision reads what the DOM can't (canvas, images, charts) with click coordinates.
- **Real input when needed** — trusted mouse clicks, typing, key combos, native file dialog (front window).
- **Batching + short aliases** — fewer tool calls, fewer tokens.
- **Safety rails** — the bundled agent skill forbids final actions (send/pay/submit/delete) without the user's OK, and typing passwords/2FA. If the background window disappears, `b` opens a new hidden one instead of touching your window.

## Install
```bash
git clone https://github.com/NadirAliOfficial/ghosttab && cd ghosttab && ./install.sh
```
Requirements: macOS, Chrome or Brave (`BROWSER=brave b ...`), Xcode Command Line Tools (for OCR).

One-time: browser menu bar → **View → Developer → Allow JavaScript from Apple Events**.
Optional for real mouse/keyboard: System Settings → Privacy & Security → **Accessibility** → allow your terminal.

`install.sh` also installs `SKILL.md` as a Claude Code skill (`~/.claude/skills/ghosttab`), so the agent picks it up automatically.

## Commands
| | |
|---|---|
| `tabs` `tab N` `open URL` `go URL` `back` `reload` `close` `url` `front` | navigation |
| `text [start] [len]` · `tail [len]` | read page text |
| `el` · `find TEXT` | list / filter interactive elements (dialog-scoped when a modal is open) |
| `form` · `fillform @answers.json` | dump / fill a whole form or dialog in one call |
| `pick N\|LABEL TEXT` · `choose QUESTION OPTION` | react-select comboboxes · radio/checkbox questions |
| `click N\|TEXT` · `fill N\|LABEL VALUE` · `select` · `check` · `hover` · `enter` | act (JS, background-safe) |
| `scroll down\|up\|top\|bottom\|PX\|TEXT` | page + main scroll panel |
| `upload N\|LABEL\|- FILE` · `drop N\|TEXT FILE` | files/videos without dialogs |
| `ocr [FILTER]` · `clickat X Y` | on-device OCR + click by coordinates |
| `rclick` `type` `key COMBO` `rupload` `rclickat` | real input (front window) |
| `log [N]` | what the agent did, when |
| `until url~X\|text X\|gone X\|'JS'` | wait without writing JS |
| `li jobs QUERY [PLACE\|geo=ID]` · `li job ID` | LinkedIn Easy Apply search by geoId (hides Applied) / summary |
| `li apply ID [CV]` · `li review` | Easy Apply up to the questions or review page (never submits) / compact review |
| `close mine` | close tabs `b open` made; `open` reuses a tab with the same URL |
| `console` · `wait TEXT [sec]` · `js CODE` · `shot` | debug, waits, raw JS, last-resort screenshot |
| `bg on [hidden]\|off\|close\|status` | background mode: agent tab in your window, or a hidden window |
| `do 'cmd ; cmd'` | batch |

Aliases: `t`=tail `x`=text `e`=el `c`=click `f`=fill `g`=go `o`=open `u`=url `k`=key `s`=scroll `w`=wait `up`=upload.

## Extension bridge (recommended)
`b ext install`, then in Chrome/Brave: Extensions > Developer mode > Load unpacked > the `ext` folder, then `b bg close; b bg on`.
The hidden tab then gets real clicks, keys, file-chooser uploads and screenshots through the browser's debugger API, without ever touching your screen. Commands are also faster than AppleScript. Without it, GhostTab falls back to AppleScript.

## Safety
- **Prompt injection:** page text is untrusted. The skill tells the agent never to follow instructions found on pages and to stay on the task's site. Use `bg` mode so the agent works in its own hidden window, not your tabs.
- **Uploads are sandboxed:** keys (`id_*`, `.pem`, `.key`, `.p12`), `.env`, credentials, shell history, every dotfolder in your home (`~/.ssh`, `~/.aws`...) and `~/Library` are always refused. `B_UPLOAD_DIRS=~/Downloads:~/cv` confines uploads to those folders.
- **Apple Events:** "Allow JavaScript from Apple Events" lets any local process that can send Apple Events run JS in the browser. Turn it off when you aren't using GhostTab (View > Developer). The optional extension bridge (`ext/`, `b ext install`) talks over a user-only socket instead (experimental).
Submit/Send/Pay-like clicks need exact text or a number, are refused on stale or already-submitted state, and are logged to `submits.log`. Real-input commands refuse if you switched tab while an agent was working.

## Limits
Cross-origin iframes (payment fields, third-party sign-in) aren't readable — by design. CAPTCHAs and 2FA are left to you. Off-screen windows throttle video/animation; reading and clicking are unaffected. Sites with a strict CSP (LinkedIn) block the file-picker stub; use a saved file (`upload NAME`), `drop`, or `rupload`. A few sites accept only trusted input — use the real-input commands in the front window.

## Test
```bash
tests/smoke.sh   # end-to-end in a background window
```

MIT © Nadir Ali
