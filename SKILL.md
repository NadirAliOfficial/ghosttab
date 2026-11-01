---
name: ghosttab
description: Use for ANY task in the user's browser on this Mac — open a site, read a page, check inboxes/dashboards, click, fill forms, upload files, draft messages. Drives Chrome (default) or Brave as TEXT via the `b` command, no screenshots. Prefer this over Claude in Chrome / screenshot tools; it does the same jobs for far fewer tokens.
---

# GhostTab — browser via CLI (`b`)

Drive the user's real, logged-in Chrome from Bash. Everything is text. `BROWSER=brave b ...` targets Brave. Without bg mode it works on window 1, active tab.

## Commands
| Command | Does |
|---|---|
| `b tabs` / `b tab N` / `b front` | list tabs / switch tab / bring browser to front |
| `b open URL` / `b go URL` | new tab / navigate current tab (waits 2.5s) |
| `b back`, `b reload`, `b close`, `b url` | basic nav, current URL + title |
| `b text [start] [len]` | page text (default first 3000 chars) |
| `b tail [len]` | last N chars — chats/inboxes, latest messages |
| `b el` | numbered visible clickable/fillable elements, incl. shadow DOM + same-origin iframes |
| `b find TEXT` | filter the last `el` list |
| `b click N\|TEXT` | JS click (fast, invisible) |
| `b rclick N\|TEXT [2]` | REAL mouse click (trusted event; 2 = double) — use when JS click is ignored |
| `b fill N\|LABEL VALUE` | set value of input/textarea/contenteditable (React-safe) |
| `b type N\|LABEL VALUE` | REAL keyboard: click field, select all, paste value — when fill doesn't stick |
| `b key COMBO...` | real keys: `enter esc tab down cmd+a cmd+shift+t cmd+l ...` |
| `b select N\|LABEL OPT`, `b check N\|LABEL`, `b hover N\|TEXT` | native dropdowns, checkboxes, hover menus |
| `b scroll down\|up\|top\|bottom\|PX\|TEXT` | scroll page + main scroll panel, or to an element |
| `b upload N\|LABEL\|- /path` | attach file/video via JS, no dialog, bg-safe (`-` = first file input; 50 MB ≈ 3s) |
| `b drop N\|TEXT /path` | drag-and-drop a file onto a drop zone, bg-safe |
| `b rupload N\|LABEL /path` | real click + macOS file dialog (front window; only if `upload` is rejected) |
| `b do 'cmd ; cmd ; cmd'` | batch steps in ONE call (auto 0.8s pause after click/go) — use it to save tool calls |
| `b console` | first call installs hook; next call prints recent errors/logs |
| `b log [N]` | last N actions taken (time, browser, command) — show the user what was done |
| `b wait TEXT [sec]` | wait until text appears |
| `b js 'CODE'` | any JS, prints result |
| `b ocr [FILTER]` | read the window's pixels as text ON-DEVICE (Apple Vision, ~0.7s, zero image tokens) → `x,y text` in page coords. For canvas, images, PDFs, charts, anything `text` misses |
| `b clickat X Y` | click a page point from `ocr` (works in bg) · `b rclickat X Y` real mouse there |
| `b bg on\|off\|close\|status` | BACKGROUND MODE: a hidden minimized window; never comes to front, nothing visible on screen. `off` parks it for instant reuse, `close` removes it |
| `b shot` | LAST RESORT: browser-window screenshot at 1200px → /tmp/b-shot.png |

Aliases: `t`=tail `x`=text `e`=el `c`=click `f`=fill `g`=go `o`=open `u`=url `k`=key `s`=scroll `w`=wait `up`=upload.

Custom dropdowns (div-based): `click` to open, `el`, then `click` the option.

## Background mode (default for multi-step jobs)
Run `b bg on` first so the user isn't disturbed, then `b go URL` etc. It shares the user's logins.
In bg mode real-input commands (`rclick`, `type`, `key`, `rupload`, `rclickat`) are refused — use `click`, `fill`, `clickat`, `enter`.
`ocr`/`shot`/`tab`/`close` don't work in bg mode (the window is minimized); `go`/`back`/`reload` navigate from inside the page so the browser never activates.
If a site truly needs real input or OCR, tell the user, `b bg off`, and do it in the front window. `b bg off` when done (parks the hidden window for reuse).
The user can watch live: right-click the browser's Dock icon → window named "ghosttab". bg mode uses ONE hidden tab (adding tabs would pop the window up).
If `b` says the background window is gone, stop — never fall back to the user's window silently.

## Workflow (cheap first)
1. `b tabs` / `b url` to know where you are.
2. Read small slices: `b tail 1500`, `b text 0 2000`. Never dump whole pages.
3. `b el` only when acting; act by number; re-run `el` after the page changes.
4. Try JS `click`/`fill` first; switch to `rclick`/`type`/`key` if the site ignores it.
5. Verify with a short `b tail 300` or `b el | grep ...`.
6. Repeat jobs on one site: one `b js` that extracts exactly the fields needed.
7. Visual-only content: `b ocr` (text + coordinates, no image tokens) → `b clickat X Y`. `b shot` only if OCR can't answer, and say why.

## Rules
- **Never do the final action without the user's explicit OK in this conversation**: Send, Submit, Post, Pay, Buy, Order, Delete, Accept, Confirm, or Enter on a submitting form. Fill the draft, tell the user it's ready, wait for "send".
- Never type passwords, 2FA codes or card numbers; ask the user to log in.
- Real input (`rclick`/`type`/`key`/`rupload`) moves the user's actual mouse/keyboard focus — tell the user briefly before a long sequence.
- If JavaScript from Apple Events is off: browser menu bar → View → Developer → Allow JavaScript from Apple Events (one-time per browser). If real input fails: System Settings → Privacy & Security → Accessibility → allow Terminal.
- Don't close or switch tabs you didn't open unless the task needs it.
