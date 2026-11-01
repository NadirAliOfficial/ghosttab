#!/usr/bin/python3
"""Drive Chrome/Brave from the CLI as text (no screenshots). BROWSER=brave to use Brave."""
import json
import os
import subprocess
import sys
import time

APP = 'Brave Browser' if os.environ.get('BROWSER', 'chrome').lower().startswith('brave') else 'Google Chrome'

SCRIPT = '''on run argv
tell application "%s"
  set wid to item 1 of argv
  set argv to rest of argv
  set c to item 1 of argv
  if c is "findghost" then
    repeat with x in windows
      if (given name of x) is "ghosttab" then return id of x
    end repeat
    return ""
  end if
  if c is "newwin" then
    -- created already minimized and named: no window animation, nothing on screen
    set n to make new window with properties {minimized:true}
    set given name of n to "ghosttab"
    return id of n
  end if
  if wid is "0" then
    set w to window 1
  else
    set w to window id (wid as integer)
  end if
  if c is "exists" then return "yes"
  if c is "bounds" then return bounds of w
  if c is "js" then return execute active tab of w javascript (item 2 of argv)
  if c is "closewin" then close w
  if c is "tabs" then
    set out to ""
    set i to 0
    repeat with t in tabs of w
      set i to i + 1
      set out to out & i & " | " & (title of t) & " | " & (URL of t) & linefeed
    end repeat
    return out & "active: " & (active tab index of w)
  end if
  if c is "tab" then set active tab index of w to ((item 2 of argv) as integer)
  if c is "open" then make new tab at end of tabs of w with properties {URL:(item 2 of argv)}
  if c is "go" then set URL of active tab of w to (item 2 of argv)
  if c is "back" then go back active tab of w
  if c is "reload" then reload active tab of w
  if c is "close" then close active tab of w
  if c is "front" then
    set index of w to 1
    activate
  end if
  return "ok"
end tell
end run''' % APP

# Walks shadow DOM and same-origin iframes; keeps refs in window.__cx, frame offsets in window.__cxo.
DEEP = r'''function deep(root,ox,oy,out){root.querySelectorAll('*').forEach(e=>{out.push([e,ox,oy]);
if(e.shadowRoot)deep(e.shadowRoot,ox,oy,out);
if(e.tagName=='IFRAME'){try{const r=e.getBoundingClientRect();deep(e.contentDocument,ox+r.x,oy+r.y,out)}catch(_){}}});return out}
const SEL='a,button,input,textarea,select,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=option],[role=checkbox],[role=radio],[role=combobox],[role=switch],[contenteditable=true],[onclick]';
const lab=e=>(e.getAttribute('aria-label')||(e.labels&&e.labels[0]?e.labels[0].innerText:'')||e.innerText||e.placeholder||e.value||e.title||e.name||'').replace(/\s+/g,' ').trim();
const vis=e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&getComputedStyle(e).visibility!='hidden'&&e.type!='hidden'};
function cx(q){if(/^\d+$/.test(q))return (window.__cx||[])[+q];
const all=deep(document,0,0,[]).map(x=>x[0]).filter(e=>e.matches&&(e.matches(SEL)||e.matches('label,span,div,li,p,h1,h2,h3,td'))&&vis(e));
let m=all.filter(e=>lab(e)===q);if(!m.length)m=all.filter(e=>lab(e).toLowerCase().includes(q.toLowerCase()));
m.sort((a,b)=>(b.matches(SEL)-a.matches(SEL))||(lab(a).length-lab(b).length));return m[0]}
function pos(e){const all=window.__cxa||[];const f=all.find(x=>x[0]===e)||[e,0,0];e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();
const z=devicePixelRatio/BACKING;return [screenX+(outerWidth-innerWidth*z)/2+(f[1]+r.x+r.width/2)*z, screenY+(outerHeight-innerHeight*z)+(f[2]+r.y+r.height/2)*z]}'''

ELEMENTS = r'''(()=>{const a=deep(document,0,0,[]).filter(x=>x[0].matches&&x[0].matches(SEL)&&vis(x[0]));window.__cx=a.map(x=>x[0]);window.__cxa=a;
return a.map((x,i)=>{const e=x[0];let t=e.tagName.toLowerCase()+(e.tagName=='INPUT'?':'+e.type:'');
let v=(e.tagName=='INPUT'||e.tagName=='TEXTAREA')&&e.value&&e.type!='password'&&e.type!='checkbox'&&e.type!='radio'?' = '+JSON.stringify(e.value.slice(0,40)):'';
if(e.checked)v+=' [x]';if(e.disabled)v+=' (disabled)';return i+' '+t+' '+lab(e).slice(0,80)+v}).join('\n')||'no elements'})()'''

KEYS = {'enter': 36, 'return': 36, 'tab': 48, 'esc': 53, 'escape': 53, 'delete': 51, 'backspace': 51, 'space': 49,
        'up': 126, 'down': 125, 'left': 123, 'right': 124, 'pageup': 116, 'pagedown': 121, 'home': 115, 'end': 119,
        **{ch: code for ch, code in zip('asdfhgzxcvbqweryt123465=97-80]ou[ip', [
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
            31, 32, 33, 34, 35])}, 'l': 37, 'j': 38, 'k': 40, 'n': 45, 'm': 46}
MODS = {'cmd': 0x100000, 'shift': 0x20000, 'alt': 0x80000, 'opt': 0x80000, 'ctrl': 0x40000}


HERE = os.path.dirname(os.path.realpath(__file__))
BGFILE = os.path.join(HERE, '.bgwin-' + APP.split()[0].lower())


def bgwin():
    try:
        return open(BGFILE).read().strip()
    except OSError:
        return ''


def osa(*args, wid=None):
    wid = bgwin() if wid is None else wid
    r = subprocess.run(['osascript', '-', wid or '0', *args], input=SCRIPT, capture_output=True, text=True)
    if wid and r.returncode and 'get window' in r.stderr and args[0] not in ('closewin', 'exists'):
        sys.exit('background window is gone (closed?). Nothing was done. Run: b bg off, then b bg on')
    out = (r.stdout or r.stderr).strip()
    if 'Executing JavaScript through AppleScript is turned off' in out:
        sys.exit('Turn on: %s menu bar > View > Developer > Allow JavaScript from Apple Events' % APP)
    return out


def js(code):
    return osa('js', code)


_BACKING = []


def backing():
    if not _BACKING:
        _BACKING.append(subprocess.run(['osascript', '-l', 'JavaScript', '-e',
                                        'ObjC.import("AppKit");$.NSScreen.mainScreen.backingScaleFactor'],
                                       capture_output=True, text=True).stdout.strip() or '2')
    return _BACKING[0]


def js_big(code):
    """Run JS too large for argv (file chunks) by embedding it in the script via stdin."""
    w = 'window id %s' % bgwin() if bgwin() else 'window 1'
    lit = code.replace('\\', '\\\\').replace('"', '\\"')
    r = subprocess.run(['osascript', '-'], input='tell application "%s" to execute active tab of %s javascript "%s"' % (APP, w, lit),
                       capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


FILE_TARGET = r'''let f=e&&e.tagName=='INPUT'&&e.type=='file'?e:null;
if(!f&&e)f=e.querySelector('input[type=file]')||(e.closest('form,section,div')||document).querySelector('input[type=file]');
if(!f){const all=deep(document,0,0,[]).map(x=>x[0]).filter(x=>x.tagName=='INPUT'&&x.type=='file');f=all[0]}'''


def send_file(path):
    """Stream a local file into the page as window.__up (Uint8Array chunks)."""
    js('window.__up=[];0')
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(6 * 1024 * 1024)
            if not chunk:
                break
            b64 = __import__('base64').b64encode(chunk).decode()
            out = js_big('(()=>{const s=atob("%s");const u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);window.__up.push(u);return window.__up.length})()' % b64)
            if not out.isdigit():
                sys.exit('upload failed: ' + out[:200])
    import mimetypes
    return json.dumps(os.path.basename(path)), json.dumps(mimetypes.guess_type(path)[0] or 'application/octet-stream')


def cg(body):
    r = subprocess.run(['osascript', '-l', 'JavaScript', '-e', 'ObjC.import("CoreGraphics");' + body],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit('macOS input blocked: allow Terminal in System Settings > Privacy & Security > Accessibility\n' + r.stderr)


def real_click(x, y, n=1):
    cg('''function ev(t,c){var e=$.CGEventCreateMouseEvent($(),t,{x:%f,y:%f},0);$.CGEventSetIntegerValueField(e,1,c);$.CGEventPost(0,e)}
ev(5,1);delay(0.05);for(var c=1;c<=%d;c++){ev(1,c);delay(0.04);ev(2,c);delay(0.06)}''' % (x, y, n))


def key(combo):
    parts = combo.lower().split('+')
    flags = sum(MODS[p] for p in parts[:-1])
    code = KEYS[parts[-1]]
    cg('''[true,false].forEach(function(d){var e=$.CGEventCreateKeyboardEvent($(),%d,d);$.CGEventSetFlags(e,%d);$.CGEventPost(0,e);delay(0.03)})''' % (code, flags))


def paste(text):
    old = subprocess.run(['pbpaste'], capture_output=True).stdout
    subprocess.run(['pbcopy'], input=text.encode())
    key('cmd+v')
    time.sleep(0.3)
    subprocess.run(['pbcopy'], input=old)


def target(q, body):
    return js('(()=>{const BACKING=%s;%s;let e=cx(%s);if(!e)return "not found: "+%s;%s})()' % (
        backing(), DEEP, json.dumps(q), json.dumps(q), body))


def front_app():
    return subprocess.run(['osascript', '-l', 'JavaScript', '-e',
                           'ObjC.import("AppKit");$.NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier.js'],
                          capture_output=True, text=True).stdout.strip()


def cg_window():
    """CoreGraphics window number + bounds (points) of the target browser window, matched by bounds."""
    l, t, r, b = [int(v) for v in osa('bounds').split(', ')]
    out = subprocess.run(['osascript', '-l', 'JavaScript', '-e', '''ObjC.import("CoreGraphics");
var l=ObjC.castRefToObject($.CGWindowListCopyWindowInfo(0,0));var o=[];
for(var i=0;i<l.count;i++){var w=l.objectAtIndex(i);if(w.objectForKey("kCGWindowOwnerName").js!="%s"||w.objectForKey("kCGWindowLayer").js!=0)continue;
var b=w.objectForKey("kCGWindowBounds");o.push([w.objectForKey("kCGWindowNumber").js,b.objectForKey("X").js,b.objectForKey("Y").js,b.objectForKey("Width").js,b.objectForKey("Height").js].join(" "))}o.join("\\n")''' % APP],
                         capture_output=True, text=True).stdout.split('\n')
    for line in out:
        n, x, y, w, h = [int(float(v)) for v in line.split()]
        if abs(x - l) < 3 and abs(y - t) < 3 and abs(w - (r - l)) < 3:
            return n, x, y, w, h
    sys.exit('browser window not found on screen (minimized or on another Space?)')


def capture():
    if bgwin():
        sys.exit('ocr/shot need a visible window; the bg window is minimized. Use text/el, or b bg off for ocr')
    n, x, y, w, h = cg_window()
    path = '/tmp/b-shot-raw.png'
    subprocess.run(['screencapture', '-x', '-o', '-l', str(n), path])
    return path, (x, y, w, h)


def no_bg(cmd):
    if bgwin():
        sys.exit('%s uses the real mouse/keyboard; in bg mode use click/fill/clickat instead, or run: b bg off' % cmd)


def point(q):
    no_bg('real input')
    out = target(q, 'return JSON.stringify(pos(e))')
    if out.startswith('not found'):
        sys.exit(out)
    osa('front')
    time.sleep(0.3)
    return json.loads(out)


USAGE = '''commands:
 tabs | tab N | open URL | go URL | back | reload | close | url | front
 text [start] [len] | tail [len] | el | find TEXT
 click N|TEXT        js click            rclick N|TEXT [2]   real mouse click (double with 2)
 fill N|LABEL VALUE  set value           type N|LABEL VALUE  real keyboard (focus + paste)
 select N|LABEL OPT | check N|LABEL | hover N|TEXT | enter N|LABEL
 key COMBO           real keys: enter, esc, tab, cmd+a, cmd+shift+t, down...
 scroll down|up|top|bottom|N|TEXT
 upload N|LABEL|- /path   attach file/video via JS (bg-safe; '-' = first file input)
 drop N|TEXT /path        drag-and-drop a file onto a drop zone (bg-safe)
 rupload N|LABEL /path    real click + macOS file dialog (front window only)
 do 'cmd ; cmd ; cmd'     batch several steps in one call (auto 0.8s pause after click/go)
 aliases: t=tail x=text e=el c=click f=fill g=go o=open u=url k=key s=scroll w=wait up=upload
 console             recent console errors/logs (hook installs on first call)
 ocr [FILTER]        read the window's pixels as text on-device (no image tokens) -> "x,y text" page coords
 clickat X Y         click page point (from ocr), works in bg   rclickat X Y  real mouse click there
 bg on|off|close|status  hidden minimized window; never steals focus (off parks it, close removes)
 log [N]             last N actions (what the agent did, when, where)
 wait TEXT [sec] | js CODE | shot   (window screenshot, last resort)'''


LOG = os.path.join(HERE, 'activity.log')
ACTS = {'go', 'open', 'back', 'reload', 'close', 'tab', 'click', 'rclick', 'fill', 'type', 'select', 'check', 'enter',
        'key', 'upload', 'drop', 'rupload', 'clickat', 'rclickat', 'scroll', 'hover', 'js', 'bg'}
ALIAS = {'t': 'tail', 'x': 'text', 'e': 'el', 'c': 'click', 'f': 'fill', 'g': 'go', 'o': 'open', 'u': 'url',
         'k': 'key', 's': 'scroll', 'w': 'wait', 'up': 'upload'}


def main(a=None):
    a = sys.argv[1:] if a is None else a
    if not a:
        sys.exit(__doc__ + '\n' + USAGE)
    if a[0] == 'do':
        import shlex
        lex = shlex.shlex(' '.join(a[1:]), posix=True, punctuation_chars=';')
        lex.whitespace_split = True
        step = []
        for tok in list(lex) + [';']:
            if tok == ';':
                if step:
                    main(step)
                    if step[0] in ('click', 'c', 'go', 'g', 'open', 'o', 'enter', 'clickat'):
                        time.sleep(0.8)
                step = []
            else:
                step.append(tok)
        return
    c = a[0] = ALIAS.get(a[0], a[0])
    if c == 'log':
        try:
            lines = open(LOG).read().splitlines()
        except OSError:
            lines = []
        print('\n'.join(lines[-(int(a[1]) if len(a) > 1 else 20):]) or 'no activity yet')
        return
    if c in ACTS:
        args = ' '.join(x if len(x) < 70 else x[:67] + '...' for x in a[1:])
        with open(LOG, 'a') as fh:
            fh.write('%s %s%s %s %s\n' % (time.strftime('%m-%d %H:%M:%S'), ('brave' if 'Brave' in APP else 'chrome'), ' bg' if bgwin() else '', c, args))
    if bgwin() and c in ('open', 'go', 'back', 'reload'):
        # AppleScript navigation un-minimizes and activates the browser; navigate from inside the page instead
        js('window.__gtOld=1;1')
        if c in ('open', 'go'):
            url = a[1] if '://' in a[1] or a[1].startswith(('data:', 'about:')) else 'https://' + a[1]
            if url.startswith('data:text/html,'):
                from urllib.parse import unquote
                # about:blank would inherit the current site's CSP; use a neutral origin
                if not js('location.href').startswith('https://example.com'):
                    js('location.href="https://example.com/";1')
                    for _ in range(80):
                        if js('location.host+document.readyState') == 'example.comcomplete':
                            break
                        time.sleep(0.1)
                js('document.open();document.write(%s);document.close();delete window.__gtOld;1' % json.dumps(unquote(url[15:])))
            else:
                js('location.href=%s;1' % json.dumps(url))
        else:
            js({'back': 'history.back();1', 'reload': 'location.reload();1'}[c])
        end = time.time() + 20
        while time.time() < end and js('window.__gtOld?"old":document.readyState') != 'complete':
            time.sleep(0.25)
        print('ok')
    elif bgwin() and c in ('tab', 'close', 'front'):
        sys.exit('%s not available in bg mode (single hidden tab); use go' % c)
    elif c in ('tabs', 'tab', 'open', 'go', 'back', 'reload', 'close', 'front'):
        out = osa(*a)
        if c in ('open', 'go'):
            time.sleep(2.5)
        print(out)
    elif c == 'url':
        print(js('location.href+" | "+document.title'))
    elif c == 'text':
        start, n = (int(a[1]) if len(a) > 1 else 0), (int(a[2]) if len(a) > 2 else 3000)
        print(js('(document.querySelector("main")||document.body).innerText.replace(/\\n{3,}/g,"\\n\\n").slice(%d,%d)' % (start, start + n)))
    elif c == 'tail':
        n = int(a[1]) if len(a) > 1 else 2500
        print(js('(document.querySelector("main")||document.body).innerText.replace(/\\n{3,}/g,"\\n\\n").slice(-%d)' % n))
    elif c == 'el':
        print(js('(()=>{const BACKING=2;%s;return %s})()' % (DEEP, ELEMENTS)))
    elif c == 'find':
        q = json.dumps(a[1].lower())
        print(js(r'''(()=>{const q=%s;return (window.__cx||[]).map((e,i)=>i+' '+(e.getAttribute('aria-label')||e.innerText||e.placeholder||e.value||'').replace(/\s+/g,' ').trim().slice(0,80)).filter(s=>s.toLowerCase().includes(q)).join('\n')||'none (run el first)'})()''' % q))
    elif c in ('click', 'fill', 'select', 'check', 'enter', 'hover'):
        v = json.dumps(a[2] if len(a) > 2 else '')
        body = {
            'click': 'e.scrollIntoView({block:"center"});e.click();return "clicked: "+lab(e).slice(0,60)',
            'hover': 'e.scrollIntoView({block:"center"});["pointerover","mouseover","mouseenter","pointermove","mousemove"].forEach(t=>e.dispatchEvent(new MouseEvent(t,{bubbles:true})));return "hovered: "+lab(e).slice(0,60)',
            'fill': '''const v=%s;if(e.tagName=="LABEL"&&e.control)e=e.control;e.focus();
if(e.isContentEditable){document.execCommand("selectAll");document.execCommand("insertText",false,v)}
else{const p=e.tagName=="TEXTAREA"?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,"value").set.call(e,v);
e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))}
return "filled "+e.tagName.toLowerCase()+" ("+v.length+" chars)"''' % v,
            'select': '''const v=%s;if(e.tagName=="LABEL"&&e.control)e=e.control;if(!e.options)return "not a <select>; use click to open it then click the option";
const o=[...e.options].find(o=>o.text.trim().toLowerCase().includes(v.toLowerCase()));
if(!o)return "no option; have: "+[...e.options].map(o=>o.text.trim()).join(", ");e.value=o.value;e.dispatchEvent(new Event("change",{bubbles:true}));return "selected "+o.text.trim()''' % v,
            'check': 'if(e.tagName=="LABEL"&&e.control)e=e.control;e.click();return "checked="+e.checked',
            'enter': '''e.focus();["keydown","keypress","keyup"].forEach(t=>e.dispatchEvent(new KeyboardEvent(t,{key:"Enter",code:"Enter",keyCode:13,which:13,bubbles:true})));
if(e.form&&e.form.requestSubmit)e.form.requestSubmit();return "enter pressed"''',
        }[c]
        print(target(a[1], body))
    elif c == 'rclick':
        x, y = point(a[1])
        real_click(x, y, int(a[2]) if len(a) > 2 else 1)
        print('real click at %d,%d' % (x, y))
    elif c == 'type':
        x, y = point(a[1])
        real_click(x, y)
        time.sleep(0.2)
        key('cmd+a')
        paste(a[2])
        print('typed %d chars' % len(a[2]))
    elif c == 'key':
        no_bg('key')
        osa('front')
        time.sleep(0.2)
        for combo in a[1:]:
            key(combo)
            time.sleep(0.1)
        print('keys sent')
    elif c == 'scroll':
        w = a[1] if len(a) > 1 else 'down'
        code = {'down': 'scrollBy(0,innerHeight*.8)', 'up': 'scrollBy(0,-innerHeight*.8)', 'top': 'scrollTo(0,0)',
                'bottom': 'scrollTo(0,document.body.scrollHeight)'}.get(w)
        if code is None and w.lstrip('-').isdigit():
            code = 'scrollBy(0,%s)' % w
        if code:
            # also scroll the biggest scrollable panel (chat lists etc.)
            print(js('''(()=>{%s;const p=[...document.querySelectorAll("*")].filter(e=>e.scrollHeight>e.clientHeight+50&&/(auto|scroll)/.test(getComputedStyle(e).overflowY)).sort((a,b)=>b.clientHeight-a.clientHeight)[0];
if(p){const d={down:p.clientHeight*.8,up:-p.clientHeight*.8,top:-1e9,bottom:1e9}[%s];p.scrollBy(0,d!==undefined?d:%s)}return "scrolled"})()''' % (
                code, json.dumps(w), w if w.lstrip('-').isdigit() else 0)))
        else:
            print(target(w, 'e.scrollIntoView({block:"center"});return "scrolled to: "+lab(e).slice(0,60)'))
    elif c in ('upload', 'drop'):
        path = os.path.abspath(os.path.expanduser(a[2]))
        if not os.path.exists(path):
            sys.exit('no such file: ' + path)
        t0 = time.time()
        name, mime = send_file(path)
        mk = 'const file=new File(window.__up,%s,{type:%s});window.__up=null;const dt=new DataTransfer();dt.items.add(file);' % (name, mime)
        if c == 'upload':
            body = mk + FILE_TARGET + '''if(!f)return "no file input on page; try: b drop TARGET file";
f.files=dt.files;f.dispatchEvent(new Event("input",{bubbles:true}));f.dispatchEvent(new Event("change",{bubbles:true}));
return "attached "+file.name+" ("+(file.size/1048576).toFixed(1)+" MB)"'''
        else:
            body = mk + '''const r=e.getBoundingClientRect(),o={bubbles:true,cancelable:true,dataTransfer:dt,clientX:r.x+r.width/2,clientY:r.y+r.height/2};
["dragenter","dragover","drop"].forEach(t=>e.dispatchEvent(new DragEvent(t,o)));return "dropped "+file.name+" ("+(file.size/1048576).toFixed(1)+" MB)"'''
        q = a[1] if c == 'drop' or a[1] != '-' else ''
        out = target(q, body) if q else js('(()=>{const BACKING=2;%s;let e=null;%s})()' % (DEEP, body))
        print('%s in %.1fs' % (out, time.time() - t0))
    elif c == 'rupload':
        no_bg('rupload')
        path = os.path.abspath(os.path.expanduser(a[2]))
        if not os.path.exists(path):
            sys.exit('no such file: ' + path)
        x, y = point(a[1])
        real_click(x, y)
        time.sleep(1.2)
        key('cmd+shift+g')
        time.sleep(0.6)
        paste(path)
        time.sleep(0.4)
        key('enter')
        time.sleep(0.8)
        key('enter')
        print('upload dialog: chose %s (verify with el / tail)' % path)
    elif c == 'console':
        print(js('''(()=>{if(!window.__cxlog){window.__cxlog=[];["error","warn","log"].forEach(k=>{const o=console[k];console[k]=function(...x){window.__cxlog.push(k+": "+x.map(String).join(" ").slice(0,300));o.apply(console,x)}});
addEventListener("error",e=>window.__cxlog.push("uncaught: "+e.message));return "console hook installed; reproduce, then run console again"}
return window.__cxlog.slice(-30).join("\\n")||"no logs yet"})()'''))
    elif c == 'wait':
        q, end = a[1].lower(), time.time() + (float(a[2]) if len(a) > 2 else 15)
        while time.time() < end:
            if q in js('document.body.innerText').lower():
                print('found')
                return
            time.sleep(1)
        print('timeout')
    elif c == 'js':
        print(js(a[1]))
    elif c == 'shot':
        path, _ = capture()
        subprocess.run(['sips', '-Z', '1200', path, '--out', '/tmp/b-shot.png'], capture_output=True)
        print('/tmp/b-shot.png')
    elif c == 'ocr':
        path, (x, y, w, h) = capture()
        geo = json.loads(js('JSON.stringify([outerWidth,outerHeight,innerWidth,innerHeight,devicePixelRatio])'))
        ow, oh, iw, ih, dpr = geo
        sc = float(backing())
        z = dpr / sc
        ox, oy = (ow - iw * z) / 2, oh - ih * z
        flt = ' '.join(a[1:]).lower()
        lines = subprocess.run([os.path.join(HERE, 'ocr'), path], capture_output=True, text=True).stdout.splitlines()
        for ln in lines:
            box, text = ln.split('\t', 1)
            bx, by, bw, bh = [float(v) for v in box.split()]
            px, py = (bx + bw / 2) / sc, (by + bh / 2) / sc
            if py < oy or (flt and flt not in text.lower()):
                continue
            print('%d,%d %s' % ((px - ox) / z, (py - oy) / z, text))
    elif c == 'clickat':
        X, Y = float(a[1]), float(a[2])
        print(js('''(()=>{const e=document.elementFromPoint(%f,%f);if(!e)return "nothing there";
["pointerdown","mousedown","pointerup","mouseup"].forEach(t=>e.dispatchEvent(new MouseEvent(t,{bubbles:true,clientX:%f,clientY:%f})));e.click();
return "clicked: "+(e.innerText||e.getAttribute("aria-label")||e.tagName).replace(/\\s+/g," ").trim().slice(0,60)})()''' % (X, Y, X, Y)))
    elif c == 'rclickat':
        no_bg('rclickat')
        geo = json.loads(js('JSON.stringify([screenX,screenY,outerWidth,outerHeight,innerWidth,innerHeight,devicePixelRatio])'))
        sx, sy, ow, oh, iw, ih, dpr = geo
        z = dpr / float(backing())
        osa('front')
        time.sleep(0.3)
        real_click(sx + (ow - iw * z) / 2 + float(a[1]) * z, sy + oh - ih * z + float(a[2]) * z)
        print('real click done')
    elif c == 'bg':
        m = a[1] if len(a) > 1 else 'status'
        if m == 'on':
            if bgwin():
                print('bg already on (window %s)' % bgwin())
                return
            parked = BGFILE + '.parked'
            if os.path.exists(parked):
                wid = open(parked).read().strip()
                if osa('exists', wid=wid) == 'yes':
                    os.rename(parked, BGFILE)
                    print('bg on: reusing hidden window %s' % wid)
                    return
                os.remove(parked)
            found = osa('findghost', wid='')
            if found.isdigit():
                open(BGFILE, 'w').write(found)
                print('bg on: reusing hidden window %s' % found)
                return
            app = front_app()
            wid = osa('newwin', wid='')
            if app and front_app() != app:
                # give focus back without un-minimizing anything (unlike `open -b`)
                subprocess.run(['osascript', '-l', 'JavaScript', '-e', 'ObjC.import("AppKit");var a=$.NSRunningApplication.runningApplicationsWithBundleIdentifier("%s");if(a.count)a.objectAtIndex(0).activateWithOptions(0)' % app],
                               capture_output=True)
            open(BGFILE, 'w').write(wid)
            print('bg on: hidden minimized window %s; never comes to front' % wid)
        elif m == 'off':
            if bgwin():
                os.rename(BGFILE, BGFILE + '.parked')
            print('bg off: back to your front window (hidden window parked for reuse; b bg close removes it)')
        elif m == 'close':
            for f in (BGFILE, BGFILE + '.parked'):
                if os.path.exists(f):
                    osa('closewin', wid=open(f).read().strip())
                    os.remove(f)
            print('hidden window closed')
        else:
            print('bg on (window %s)' % bgwin() if bgwin() else 'bg off')
    else:
        sys.exit('unknown command ' + c + '\n' + USAGE)


if __name__ == '__main__':
    main()
