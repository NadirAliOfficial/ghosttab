#!/usr/bin/python3
"""Drive Chrome/Brave from the CLI as text (no screenshots). BROWSER=brave to use Brave."""
import json
import os
import subprocess
import sys
import time

APP = 'Brave Browser' if os.environ.get('BROWSER', 'chrome').lower().startswith('brave') else 'Google Chrome'
TIMEOUT = float(os.environ.get('B_TIMEOUT', 30))

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

# Walks shadow DOM and same-origin iframes; keeps refs in window.__cx, frame offsets in window.__cxa.
DEEP = r'''function deep(root,ox,oy,out){root.querySelectorAll('*').forEach(e=>{out.push([e,ox,oy]);
if(e.shadowRoot)deep(e.shadowRoot,ox,oy,out);
if(e.tagName=='IFRAME'){try{const r=e.getBoundingClientRect();deep(e.contentDocument,ox+r.x,oy+r.y,out)}catch(_){}}});return out}
const SEL='a,button,input,textarea,select,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=option],[role=checkbox],[role=radio],[role=combobox],[role=switch],[contenteditable=true],[onclick]';
const FIELD='input:not([type=hidden]),textarea,select,[contenteditable=true],[role=combobox],[role=textbox]';
const T=s=>(s||'').replace(/\s+/g,' ').trim();
const byId=(e,i)=>{const r=e.getRootNode();return (r.getElementById&&r.getElementById(i))||document.getElementById(i)};
const isBox=e=>e.tagName=='INPUT'&&(e.type=='radio'||e.type=='checkbox');
const isBoxy=e=>isBox(e)||/^(radio|checkbox)$/.test(e.getAttribute&&e.getAttribute('role')||'');
function opt(e){if(e.labels&&e.labels[0]&&T(e.labels[0].innerText))return T(e.labels[0].innerText);
const l=e.closest('label');if(l&&T(l.innerText))return T(l.innerText);
for(let s=e.nextElementSibling;s;s=s.nextElementSibling)if(T(s.innerText))return T(s.innerText);
if(e.value&&e.value!='on')return e.value;return T(e.parentElement&&e.parentElement.innerText)}
const on=e=>e.tagName=='INPUT'?opt(e):T(e.getAttribute('aria-label')||e.innerText);
function ques(e){const f=e.closest('fieldset');if(f){const l=f.querySelector('legend');if(l&&T(l.innerText))return T(l.innerText)}
const g=e.closest('[role=radiogroup],[role=group]');if(g){const t=g.getAttribute('aria-label')||T((byId(g,g.getAttribute('aria-labelledby')||'')||{}).innerText);if(t)return T(t)}
let p=e.parentElement;for(let i=0;p&&i<8;i++,p=p.parentElement){if([...p.querySelectorAll(FIELD)].some(x=>!isBoxy(x)))return '';
const own=[...p.querySelectorAll('input[type=radio],input[type=checkbox],[role=radio],[role=checkbox]')].map(on).filter(Boolean).sort((a,b)=>b.length-a.length);
const L=(p.innerText||'').split('\n').map(s=>T(own.reduce((s,o)=>s.split(o).join(' '),s))).filter(Boolean);if(L.length)return L[0]}return ''}
function lab(e){if(!e.getAttribute)return '';let t=e.getAttribute('aria-label');const lb=e.getAttribute('aria-labelledby');
if(!t&&lb)t=lb.split(' ').map(i=>(byId(e,i)||{}).innerText||'').join(' ');if(!t&&isBox(e))return opt(e);
if(!t&&e.labels&&e.labels[0])t=e.labels[0].innerText;return T(t||e.innerText||e.placeholder||e.value||e.title||e.name||'')}
function flab(e){if(isBoxy(e))return ques(e);let t=e.getAttribute('aria-label');const lb=e.getAttribute('aria-labelledby');
if(!t&&lb)t=lb.split(' ').map(i=>(byId(e,i)||{}).innerText||'').join(' ');if(!t&&e.labels&&e.labels[0])t=e.labels[0].innerText;
if(!t&&e.placeholder)t=e.placeholder;
for(let p=e.parentElement,i=0;!T(t)&&p&&i<4;i++,p=p.parentElement)t=(p.innerText||'').split('\n').map(T).filter(x=>x&&x!==T(e.value))[0];
return T(t||e.name||e.id||'')}
const vis=e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&getComputedStyle(e).visibility!='hidden'&&e.type!='hidden'};
function scope(){if(window.__gtAll)return null;const d=[...document.querySelectorAll('[role=dialog],[aria-modal=true],dialog[open]')].filter(e=>{const r=e.getBoundingClientRect();return r.width>80&&r.height>80&&getComputedStyle(e).visibility!='hidden'});return d.length?d[d.length-1]:null}
function ctlOf(e){if(e.matches(FIELD))return e;if(e.tagName=='LABEL'){if(e.control)return e.control;const x=e.querySelector(FIELD);if(x)return x}
for(let p=e,i=0;p&&i<4;i++,p=p.parentElement){const x=[...p.querySelectorAll(FIELD)].filter(x=>vis(x)||x.type=='file');if(x.length==1)return x[0];if(x.length>1)break}return null}
function cx(q,form){window.__cxerr='';if(/^\d+$/.test(q))return (window.__cx||[])[+q];const root=scope()||document;
if(/^[#.\[]/.test(q)){try{const e=root.querySelector(q)||document.querySelector(q);if(e)return e}catch(_){}}
const lo=q.toLowerCase(),L=e=>lab(e).toLowerCase().replace(/\s*\*$/,'');const D=deep(root,0,0,[]).map(x=>x[0]).filter(e=>e.matches);
const all=D.filter(e=>(e.matches(SEL)||e.matches('label,span,div,li,p,h1,h2,h3,h4,td,legend'))&&vis(e));
if(form){const F=e=>flab(e).toLowerCase().replace(/\s*\*$/,'');const fs=D.filter(e=>e.matches(FIELD)&&!isBox(e)&&(vis(e)||e.type=='file'));
let m=fs.filter(e=>F(e)===lo);if(!m.length)m=fs.filter(e=>e.id===q||e.name===q);
if(!m.length)m=fs.filter(e=>F(e).startsWith(lo));if(!m.length)m=fs.filter(e=>F(e).includes(lo));
if(!m.length)m=all.filter(e=>!e.matches(SEL)&&L(e).includes(lo)).sort((a,b)=>L(a).length-L(b).length).map(ctlOf).filter(Boolean).slice(0,1);
m=[...new Set(m)];if(m.length>1){window.__cxerr='ambiguous "'+q+'": '+m.slice(0,6).map(e=>'"'+flab(e).slice(0,40)+'"').join(', ')+' (use numbers from b form / b el)';return null}
if(m.length)return m[0]}
let m=all.filter(e=>L(e)===lo);if(!m.length)m=all.filter(e=>L(e).includes(lo));
m.sort((a,b)=>(b.matches(SEL)-a.matches(SEL))||(L(a).length-L(b).length));return m[0]}
function pos(e){const all=window.__cxa||[];const f=all.find(x=>x[0]===e)||[e,0,0];e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();
const z=devicePixelRatio/BACKING;return [screenX+(outerWidth-innerWidth*z)/2+(f[1]+r.x+r.width/2)*z, screenY+(outerHeight-innerHeight*z)+(f[2]+r.y+r.height/2)*z]}
function MW(code){const d=document.documentElement,s=document.createElement('script');const n=[...document.querySelectorAll('script')].find(x=>x.nonce);if(n)s.nonce=n.nonce;
d.removeAttribute('data-gtr');try{s.textContent='(()=>{let r;try{r=(()=>{'+code+'})()}catch(e){r="ERR: "+e.message}document.documentElement.setAttribute("data-gtr",JSON.stringify(r===undefined?null:r))})()';(document.head||d).appendChild(s);s.remove()}catch(_){}
const r=d.getAttribute('data-gtr');d.removeAttribute('data-gtr');return r===null?'CSP':JSON.parse(r)}
function inst(n){if(!n)return null;const k=Object.keys(n).find(k=>k.startsWith('__reactFiber$')||k.startsWith('__reactInternalInstance$'));let f=k&&n[k];
for(let i=0;f&&i<60;i++,f=f.return){const s=f.stateNode;if(s&&typeof s.selectOption=='function'&&s.props)return s}return null}'''

ELEMENTS = r'''const R=scope();const a=deep(R||document,0,0,[]).filter(x=>x[0].matches&&x[0].matches(SEL)&&vis(x[0]));window.__cx=a.map(x=>x[0]);window.__cxa=a;
const h=R?'[dialog: '+T(R.getAttribute('aria-label')||(R.querySelector('h1,h2,h3')||R).innerText).slice(0,60)+'] (b el all = whole page)\n':'';
return h+(a.map((x,i)=>{const e=x[0];let t=e.tagName.toLowerCase()+(e.tagName=='INPUT'?':'+e.type:'');
let v=(e.tagName=='INPUT'||e.tagName=='TEXTAREA')&&e.value&&!/^(password|checkbox|radio)$/.test(e.type)?' = '+JSON.stringify(e.value.slice(0,40)):'';
if(e.checked||e.getAttribute('aria-checked')=='true')v+=' [x]';if(e.disabled)v+=' (disabled)';
return i+' '+t+' '+(isBoxy(e)?ques(e).slice(0,60)+' → '+on(e).slice(0,40):lab(e).slice(0,80))+v}).join('\n')||'no elements')'''

# One scan of the active form/dialog: kind, label, required, value, options. Sets window.__cx for numbers.
SCAN = r'''function scan(){const R=scope();let root=R;if(!root){const af=document.activeElement&&document.activeElement.closest&&document.activeElement.closest('form');
root=af||[...document.forms].filter(vis).sort((a,b)=>b.elements.length-a.elements.length)[0]||document}
const a=deep(root,0,0,[]).filter(x=>{const e=x[0];return e.matches&&(e.matches(FIELD)||e.matches('[role=radio],[role=checkbox]')||(root!==document&&e.matches('button,[role=button]')))&&(vis(e)||e.type=='file')});
window.__cx=a.map(x=>x[0]);window.__cxa=a;window.__root=root;
return a.map(x=>{const e=x[0],role=e.getAttribute('role')||'';
const k=e.tagName=='SELECT'?'select':e.tagName=='TEXTAREA'?'textarea':isBox(e)?e.type:/^(radio|checkbox)$/.test(role)?role:e.type=='file'?'file':
(e.tagName=='BUTTON'||role=='button'||/^(submit|button|reset|image)$/.test(e.type))?'button':(role=='combobox'||inst(e))?'combo':e.isContentEditable?'editor':'text';
const l0=k=='button'?lab(e):flab(e),l=l0.replace(/\s*\*$/,'');let v='',o='';
if(k=='select'){v=e.selectedIndex>=0?T(e.options[e.selectedIndex].text):'';o=[...e.options].map(o=>T(o.text)).filter(Boolean);o=o.slice(0,12).join(', ')+(o.length>12?' +'+(o.length-12):'')}
else if(k=='combo'){let s=null;for(let p=e.parentElement,j=0;p&&!s&&j<5;j++,p=p.parentElement)s=p.querySelector('[class*=singleValue],[class*=single-value],[class*=multiValue],[class*=multi-value]');v=s?T(s.innerText):e.value}
else if(k=='file')v=e.files&&e.files.length?e.files[0].name:'';else if(k=='editor')v=T(e.innerText);
else if(k=='radio'||k=='checkbox')v=e.tagName=='INPUT'?e.checked:e.getAttribute('aria-checked')=='true';else if(k!='button')v=e.value;
return {k,l,q:(k=='radio'||k=='checkbox')?ques(e):'',o:(k=='radio'||k=='checkbox')?on(e):o,v,r:!!(e.required||e.getAttribute('aria-required')=='true'||/\*\s*$/.test(l0)),d:!!e.disabled}})}'''

FORM = r'''const it=scan();const out=[];let g=null;const R=window.__root;
it.forEach((f,i)=>{if(f.k=='radio'||f.k=='checkbox'){const s=i+' '+f.o.slice(0,40)+(f.v?' [x]':'');if(g&&g.key==f.k+f.q){g.s.push(s);return}
g={key:f.k+f.q,s:[s],line:f.k+' "'+f.q.slice(0,70)+'"'+(f.r?'*':'')};out.push(g);return}g=null;
out.push({line:i+' '+f.k+' "'+f.l.slice(0,60)+'"'+(f.r?'*':'')+(f.k=='button'?'':' = '+JSON.stringify(String(f.v).slice(0,40)))+(f.o?' {'+f.o+'}':'')+(f.d?' (disabled)':'')})});
const h=R===document?'[no form/dialog found; whole page]\n':R.matches('form')?'':'[dialog: '+T(R.getAttribute('aria-label')||(R.querySelector('h1,h2,h3')||R).innerText).slice(0,60)+']\n';
return h+(out.map(x=>x.s?x.line+': '+x.s.join(' | '):x.line).join('\n')||'no fields')'''

FORMMAP = r'''const it=scan();const res={};const N=s=>s.toLowerCase().replace(/\s*\*$/,'').trim();
K.forEach(k=>{const lo=N(k);const c=it.map((f,i)=>({f,i})).filter(x=>x.f.k!='button');const L=x=>N(x.f.q||x.f.l);
let m=c.filter(x=>L(x)==lo);if(!m.length)m=c.filter(x=>L(x).startsWith(lo));if(!m.length)m=c.filter(x=>L(x).includes(lo));
if(!m.length){res[k]={k:'missing'};return}const f=m[0].f;
if(m.every(x=>(x.f.k=='radio'||x.f.k=='checkbox')&&x.f.q==f.q))res[k]=m.length==1&&f.k=='checkbox'?{k:'check',i:m[0].i}:{k:'choose',q:f.q};
else if(m.length==1)res[k]={k:f.k,i:m[0].i};else res[k]={k:'ambiguous',l:m.slice(0,5).map(x=>x.f.q||x.f.l).join(' | ')}});return JSON.stringify(res)'''

# runs in the page's main world (b js runs in an isolated world that can't see React internals)
PKM = r'''function inst(n){if(!n)return null;const k=Object.keys(n).find(k=>k.startsWith('__reactFiber$')||k.startsWith('__reactInternalInstance$'));let f=k&&n[k];
for(let i=0;f&&i<60;i++,f=f.return){const s=f.stateNode;if(s&&typeof s.selectOption=='function'&&s.props)return s}return null}
function rsel(e){const c=[e,e.control,e.htmlFor&&document.getElementById(e.htmlFor),e.querySelector&&e.querySelector('input')];
for(let p=e,i=0;p&&i<5;i++,p=p.parentElement)c.push(p.querySelector('input[role=combobox],[class*=select__input] input,input'));for(const x of c){const s=inst(x);if(s)return s}return null}
function pk(t){const S=window.__pk;const gl=o=>String(S.getOptionLabel?S.getOptionLabel(o):o.label);const opts=(S.props.options||[]).flatMap(o=>o&&o.options?o.options:[o]);
const lo=t.toLowerCase();const o=opts.find(o=>gl(o).toLowerCase()==lo)||opts.find(o=>gl(o).toLowerCase().startsWith(lo))||opts.find(o=>gl(o).toLowerCase().includes(lo));
if(o){S.selectOption(o);return "picked: "+gl(o)}return "NOMATCH "+opts.length+" options: "+opts.slice(0,8).map(gl).join(", ")}'''

PICK = r'''let e=cx(Q,true);if(!e)return window.__cxerr||"not found: "+Q;e.setAttribute('data-gtpk','1');
const r=MW(PKM+';const e=document.querySelector("[data-gtpk]");e.removeAttribute("data-gtpk");const S=rsel(e);if(!S)return "NOSEL";window.__pk=S;'+
'document.querySelectorAll("[data-gtpki]").forEach(x=>x.removeAttribute("data-gtpki"));S.inputRef&&S.inputRef.setAttribute("data-gtpki","1");return pk('+JSON.stringify(V)+')');
e.removeAttribute('data-gtpk');if(r!='CSP'&&r!='NOSEL')return r;const i=e.matches('input')?e:ctlOf(e);if(!i||!i.matches('input'))return 'not a combobox; click it, el, then click the option';
document.querySelectorAll("[data-gtpki]").forEach(x=>x.removeAttribute("data-gtpki"));i.setAttribute('data-gtpki','1');return 'EVENTS' '''

# type into the combobox from the isolated world (React sees it as user input), then wait for options
PKTYPE = r'''const i=document.querySelector('[data-gtpki]');if(!i)return 0;i.focus();Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"value").set.call(i,V);
i.dispatchEvent(new Event("input",{bubbles:true}));return 1'''
PKOPT = r'''const lo=V.toLowerCase();const o=[...document.querySelectorAll('[id*="-option-"],[role=option]')].filter(x=>vis(x)&&T(x.innerText));
const m=o.find(x=>T(x.innerText).toLowerCase()==lo)||o.find(x=>T(x.innerText).toLowerCase().startsWith(lo))||o.find(x=>T(x.innerText).toLowerCase().includes(lo));
if(!m)return 'NOMATCH '+o.length+' options: '+o.slice(0,8).map(x=>T(x.innerText)).join(', ');m.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));m.click();return 'picked: '+T(m.innerText)'''

CHOOSE = r'''const q=Q.toLowerCase(),o=O.toLowerCase();const bx=deep(scope()||document,0,0,[]).map(x=>x[0]).filter(e=>e.matches&&isBoxy(e));
const c=bx.filter(e=>ques(e).toLowerCase().includes(q));
if(!c.length)return 'no question like "'+Q+'"; have: '+[...new Set(bx.map(ques))].slice(0,8).join(' | ');
const e=c.find(e=>on(e).toLowerCase()==o)||c.find(e=>on(e).toLowerCase().startsWith(o))||c.find(e=>on(e).toLowerCase().includes(o));
if(!e)return 'no option "'+O+'"; have: '+c.map(on).join(', ');
const st=()=>e.tagName=='INPUT'?e.checked:e.getAttribute('aria-checked')=='true';e.scrollIntoView({block:'center'});const lb=e.labels&&e.labels[0];
const fire=x=>{['pointerdown','mousedown','pointerup','mouseup'].forEach(t=>x.dispatchEvent(new MouseEvent(t,{bubbles:true})));x.click()};
if(!st())fire(e);if(!st()&&lb)fire(lb);
if(!st()&&e.tagName=='INPUT'){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,'checked').set.call(e,true);['click','input','change'].forEach(t=>e.dispatchEvent(new Event(t,{bubbles:true})))}
window.__ch=e;return (st()?'chosen: ':'clicked, NOT checked (try b bg off + rclick): ')+ques(e).slice(0,50)+' → '+on(e)'''

KEYS = {'enter': 36, 'return': 36, 'tab': 48, 'esc': 53, 'escape': 53, 'delete': 51, 'backspace': 51, 'space': 49,
        'up': 126, 'down': 125, 'left': 123, 'right': 124, 'pageup': 116, 'pagedown': 121, 'home': 115, 'end': 119,
        **{ch: code for ch, code in zip('asdfhgzxcvbqweryt123465=97-80]ou[ip', [
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30,
            31, 32, 33, 34, 35])}, 'l': 37, 'j': 38, 'k': 40, 'n': 45, 'm': 46}
MODS = {'cmd': 0x100000, 'shift': 0x20000, 'alt': 0x80000, 'opt': 0x80000, 'ctrl': 0x40000}


HERE = os.path.dirname(os.path.realpath(__file__))
BGFILE = os.path.join(HERE, '.bgwin-' + APP.split()[0].lower())
CMD = ['']


def bgwin():
    try:
        return open(BGFILE).read().strip()
    except OSError:
        return ''


def osa(*args, wid=None, soft=False):
    wid = bgwin() if wid is None else wid
    try:
        r = subprocess.run(['osascript', '-', wid or '0', *args], input=SCRIPT, capture_output=True, text=True, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        if soft:
            return 'timeout'
        sys.exit('page did not answer in %ds (busy page or a dialog like "Leave site?"); it may still have acted, check b url / b t 300. '
                 'Longer wait: B_TIMEOUT=90 b ...' % TIMEOUT)
    if wid and r.returncode and 'get window' in r.stderr and args[0] not in ('closewin', 'exists'):
        # the hidden window was closed: make a fresh one, never fall back to the user's window
        if os.path.exists(BGFILE):
            os.remove(BGFILE)
        new = bg_new()
        if CMD[0] in ('go', 'open'):
            print('(hidden window was gone; opened a new one %s)' % new, file=sys.stderr)
            return osa(*args)
        sys.exit('hidden window was gone; opened a new blank one (%s). Nothing was done: b go URL, then retry' % new)
    out = (r.stdout or r.stderr).strip()
    if 'Executing JavaScript through AppleScript is turned off' in out:
        sys.exit('Turn on: %s menu bar > View > Developer > Allow JavaScript from Apple Events' % APP)
    return out


def js(code, soft=False):
    return osa('js', code, soft=soft)


def user_js(code):
    out = js('(()=>{let r;try{r=(\n%s\n)}catch(e){return "ERR: "+e.message}if(r instanceof Promise)return "Promise (not awaited; store the result in window.x and read it)";'
             'if(r instanceof Element)return r.outerHTML.slice(0,300);return r===undefined?"undefined":r===null?"null":typeof r=="object"?(()=>{try{return JSON.stringify(r)}catch(_){return String(r)}})():String(r)})()' % code)
    if out == 'missing value':
        # statements, not an expression: run as a script, its completion value is the result
        out = js('try{\n%s\n}catch(e){"ERR: "+e.message}' % code)
        if out == 'missing value':
            out = 'undefined (or a JS syntax error)'
    return out


_BACKING = []


def backing():
    if not _BACKING:
        _BACKING.append(subprocess.run(['osascript', '-l', 'JavaScript', '-e',
                                        'ObjC.import("AppKit");$.NSScreen.mainScreen.backingScaleFactor'],
                                       capture_output=True, text=True).stdout.strip() or '2')
    return _BACKING[0]


def page(body, real=False, **v):
    """Run body with the DEEP helpers in scope; keyword args become JS consts."""
    consts = ''.join('const %s=%s;' % (k, json.dumps(x)) for k, x in v.items())
    return js('(()=>{const BACKING=%s;%s;%s%s})()' % (backing() if real else 2, DEEP, consts, body))


def js_big(code):
    """Run JS too large for argv (file chunks) by embedding it in the script via stdin."""
    w = 'window id %s' % bgwin() if bgwin() else 'window 1'
    lit = code.replace('\\', '\\\\').replace('"', '\\"')
    r = subprocess.run(['osascript', '-'], input='tell application "%s" to execute active tab of %s javascript "%s"' % (APP, w, lit),
                       capture_output=True, text=True)
    return (r.stdout or r.stderr).strip()


# file input near the target; if none, stub showOpenFilePicker (LinkedIn etc.) and click the target
FILE_TARGET = r'''let f=e&&e.tagName=='INPUT'&&e.type=='file'?e:null;
if(!f&&e){f=e.querySelector('input[type=file]');const c=e.closest('form,section,[role=dialog],div');if(!f&&c)f=c.querySelector('input[type=file]')}
if(!f&&!e){const all=deep(scope()||document,0,0,[]).map(x=>x[0]).filter(x=>x.tagName=='INPUT'&&x.type=='file');f=all[0]}
if(!f){let h=document.getElementById('__gtfile');if(!h){h=document.createElement('input');h.type='file';h.id='__gtfile';h.style.display='none';document.documentElement.appendChild(h)}h.files=dt.files;
if(MW(STUB)=='CSP')return 'no file input, and this page blocks the file-picker stub (CSP). Try: b drop on the upload area, b upload NAME for a file already on the site, or b bg off + b rupload';
if(e){e.scrollIntoView({block:'center'});e.click();return 'no file input; file-picker stub armed and clicked "'+lab(e).slice(0,40)+'" ('+file.name+'). Verify with b form / b t 300'}
return 'no file input; file-picker stub armed with '+file.name+': now click the upload button'}'''


# main world: answer the next showOpenFilePicker() or file-input click() with the staged file
STUB = r'''const h=document.getElementById('__gtfile');const op=window.showOpenFilePicker,ck=HTMLInputElement.prototype.click;
const done=()=>{window.showOpenFilePicker=op;HTMLInputElement.prototype.click=ck;h.remove()};
window.showOpenFilePicker=async()=>{const f=h.files[0];done();return [{kind:'file',name:f.name,getFile:async()=>f,queryPermission:async()=>'granted',requestPermission:async()=>'granted',isSameEntry:async()=>false}]};
HTMLInputElement.prototype.click=function(){if(this.type!='file')return ck.call(this);this.files=h.files;done();this.dispatchEvent(new Event('input',{bubbles:true}));this.dispatchEvent(new Event('change',{bubbles:true}))};return 'ok' '''


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


FORM_CMDS = ('fill', 'type', 'select', 'check', 'pick', 'upload')


def target(q, body, real=False, **v):
    return page('let e=cx(Q,%s);if(!e)return window.__cxerr||"not found: "+Q;%s' % (
        'true' if CMD[0] in FORM_CMDS else 'false', body), real, Q=q, **v)


def front_app():
    return subprocess.run(['osascript', '-l', 'JavaScript', '-e',
                           'ObjC.import("AppKit");$.NSWorkspace.sharedWorkspace.frontmostApplication.bundleIdentifier.js'],
                          capture_output=True, text=True).stdout.strip()


def cg_window():
    """CoreGraphics window number + bounds (points) of the target browser window: on-screen windows only, front first."""
    l, t, r, b = [int(v) for v in osa('bounds').split(', ')]
    out = subprocess.run(['osascript', '-l', 'JavaScript', '-e', '''ObjC.import("CoreGraphics");
var l=ObjC.castRefToObject($.CGWindowListCopyWindowInfo(17,0));var o=[];
for(var i=0;i<l.count;i++){var w=l.objectAtIndex(i);if(w.objectForKey("kCGWindowOwnerName").js!="%s"||w.objectForKey("kCGWindowLayer").js!=0)continue;
var b=w.objectForKey("kCGWindowBounds");o.push([w.objectForKey("kCGWindowNumber").js,b.objectForKey("X").js,b.objectForKey("Y").js,b.objectForKey("Width").js,b.objectForKey("Height").js].join(" "))}o.join("\\n")''' % APP],
                         capture_output=True, text=True).stdout.split('\n')
    for line in out:
        if not line.strip():
            continue
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
    out = target(q, 'return JSON.stringify(pos(e))', real=True)
    if not out.startswith('['):
        sys.exit(out)
    osa('front')
    time.sleep(0.3)
    return json.loads(out)


def settle(msg):
    """After a click: report whether the page navigated or changed."""
    if not msg.startswith(('clicked', 'chosen')):
        return msg
    for _ in range(4):
        time.sleep(0.25)
        s = js('window.__gtSig===undefined?"navigated":(location.href+"|"+document.getElementsByTagName("*").length)==window.__gtSig?"":"page changed"')
        if s:
            return '%s → %s' % (msg, 'navigating' if s == 'missing value' else s)
    return msg + ' → no change yet'


SIG = 'window.__gtSig=location.href+"|"+document.getElementsByTagName("*").length;'


def bg_new():
    app = front_app()
    wid = osa('newwin', wid='')
    if app and front_app() != app:
        # give focus back without un-minimizing anything (unlike `open -b`)
        subprocess.run(['osascript', '-l', 'JavaScript', '-e', 'ObjC.import("AppKit");var a=$.NSRunningApplication.runningApplicationsWithBundleIdentifier("%s");if(a.count)a.objectAtIndex(0).activateWithOptions(0)' % app],
                       capture_output=True)
    open(BGFILE, 'w').write(wid)
    return wid


def bg_nav(c, arg, retry=True):
    # AppleScript navigation un-minimizes and activates the browser; navigate from inside the page instead
    js('window.__gtOld=1;1')
    url = ''
    if c in ('open', 'go'):
        url = arg if '://' in arg or arg.startswith(('data:', 'about:')) else 'https://' + arg
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
    t0, st = time.time(), 'old'
    while time.time() - t0 < 20:
        st = js('window.__gtOld?"old":document.readyState', soft=True)
        if st in ('interactive', 'complete') or (st == 'old' and url and time.time() - t0 > 12):
            break
        time.sleep(0.25)
    if st != 'old':
        print('ok')
    elif url and retry and js('location.href') != url:
        # navigation ignored (tab wedged): replace the hidden window and try once more
        osa('closewin')
        os.remove(BGFILE)
        bg_new()
        print('(hidden tab ignored navigation; recreated it)', file=sys.stderr)
        bg_nav(c, arg, retry=False)
    else:
        print('page did not change (a download, or the site blocked it)')


USAGE = '''commands:
 tabs | tab N | open URL | go URL | back | reload | close | url | front
 text [all|-m] [start] [len] | tail [all|-m] [len] | el [all] | find TEXT
 form                one-call dump of the open dialog/form: kind, label, required*, value, options
 fillform @answers.json   fill a whole page {label: value}; radios, selects, comboboxes, files
 click N|TEXT        js click            rclick N|TEXT [2]   real mouse click (double with 2)
 fill N|LABEL VALUE  set value           type N|LABEL VALUE  real keyboard (focus + paste)
 select N|LABEL OPT | check N|LABEL [on|off] | hover N|TEXT | enter N|LABEL
 pick N|LABEL TEXT   choose in a react-select combobox (Greenhouse/Lever/Ashby), bg-safe
 choose QUESTION OPTION   tick the radio/checkbox OPTION under QUESTION, verifies it stuck
 key COMBO           real keys: enter, esc, tab, cmd+a, cmd+shift+t, down...
 scroll down|up|top|bottom|N|TEXT
 upload N|LABEL|- /path   attach file via JS (bg-safe; '-' = first file input; no input = file-picker stub)
 upload NAME              select an already-uploaded file on the page (e.g. a saved resume)
 drop N|TEXT /path        drag-and-drop a file onto a drop zone (bg-safe)
 rupload N|LABEL /path    real click + macOS file dialog (front window only)
 do 'cmd ; cmd ; cmd'     batch several steps in one call
 aliases: t=tail x=text e=el c=click f=fill g=go o=open u=url k=key s=scroll w=wait up=upload
 console             recent console errors/logs (hook installs on first call)
 ocr [FILTER]        read the window's pixels as text on-device (no image tokens) -> "x,y text" page coords
 clickat X Y         click page point (from ocr), works in bg   rclickat X Y  real mouse click there
 bg on|off|close|status  hidden minimized window; never steals focus (off parks it, close removes)
 until 'JS' [sec] | until url~PART [sec] | until text TEXT [sec] | until gone TEXT [sec]
 fill N|LABEL @file  fill from a file; newlines become paragraphs in rich editors (LinkedIn, Gmail...)
 li jobs QUERY [LOCATION] | li job ID   LinkedIn job search / job summary
 log [N]             last N actions (what the agent did, when, where)
 wait TEXT [sec] | js CODE | shot   (window screenshot, last resort)
 env: B_TIMEOUT=60 for slow pages (default 30s)'''


LOG = os.path.join(HERE, 'activity.log')
ACTS = {'go', 'open', 'back', 'reload', 'close', 'tab', 'click', 'rclick', 'fill', 'type', 'select', 'check', 'enter',
        'key', 'upload', 'drop', 'rupload', 'clickat', 'rclickat', 'scroll', 'hover', 'js', 'bg', 'pick', 'choose', 'fillform'}
ALIAS = {'t': 'tail', 'x': 'text', 'e': 'el', 'c': 'click', 'f': 'fill', 'g': 'go', 'o': 'open', 'u': 'url',
         'k': 'key', 's': 'scroll', 'w': 'wait', 'up': 'upload'}
REST = ('fill', 'type', 'select', 'pick', 'choose', 'hover', 'check')


def li(a):
    if a[1] == 'job':
        main(['go', 'https://www.linkedin.com/jobs/view/%s/' % a[2]])
        js_until('document.querySelector("h1")', 15)
        print(js(r'''(()=>{const T=s=>(s||'').replace(/\n{2,}/g,'\n').trim();const t=(document.querySelector('main')||document.body).innerText;const h=document.querySelector('h1');
const i=Math.max(0,h?t.indexOf(h.innerText.trim()):0);const j=t.search(/About the job/i);
const ea=[...document.querySelectorAll('button,a')].some(b=>/easy apply/i.test(b.innerText||b.getAttribute('aria-label')||''));
return T(t.slice(i,j>i?Math.min(j,i+500):i+500))+'\nEasy Apply: '+(ea?'yes':'no')+'\n'+(j>=0?T(t.slice(j,j+1500)):'')})()'''))
        return
    from urllib.parse import quote
    url = 'https://www.linkedin.com/jobs/search/?keywords=%s' % quote(a[2])
    if len(a) > 3:
        url += '&location=' + quote(' '.join(a[3:]))
    main(['go', url])
    js_until('document.querySelectorAll("[componentkey^=\'job-card-component-ref-\'],[data-job-id],[data-occludable-job-id]").length', 15)
    print(js(r'''(()=>{const seen=new Set(),out=[];document.querySelectorAll("[componentkey^='job-card-component-ref-'],[data-job-id],[data-occludable-job-id]").forEach(c=>{
const id=(c.getAttribute('componentkey')||'').replace('job-card-component-ref-','')||c.getAttribute('data-job-id')||c.getAttribute('data-occludable-job-id');
if(!id||seen.has(id))return;seen.add(id);const L=[...new Set((c.innerText||'').split('\n').map(s=>s.trim()).filter(s=>s&&!/^(Promoted|Viewed|Saved|·)$/.test(s)))];
out.push(id+' | '+L.slice(0,6).join(' | ').slice(0,220))});return out.join('\n')||'no jobs found (b t 1500 to see the page)'})()'''))


def js_until(cond, sec):
    end = time.time() + sec
    while time.time() < end:
        if js('!!(%s)' % cond, soft=True) == 'true':
            return True
        time.sleep(0.5)
    return False


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
                    if step[0] in ('go', 'g', 'open', 'o', 'enter'):
                        time.sleep(0.8)
                step = []
            else:
                step.append(tok)
        return
    c = a[0] = ALIAS.get(a[0], a[0])
    CMD[0] = c
    if c in REST and len(a) > 3:
        a = a[:2] + [' '.join(a[2:])]
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
        bg_nav(c, a[1] if len(a) > 1 else '')
    elif bgwin() and c in ('tab', 'close', 'front'):
        sys.exit('%s not available in bg mode (single hidden tab); use go' % c)
    elif c in ('tabs', 'tab', 'open', 'go', 'back', 'reload', 'close', 'front'):
        out = osa(*a)
        if c in ('open', 'go'):
            time.sleep(2.5)
        print(out)
    elif c == 'url':
        print(js('location.href+" | "+document.title'))
    elif c in ('text', 'tail'):
        flags = {x for x in a[1:] if not x.lstrip('-').isdigit()}
        nums = [int(x) for x in a[1:] if x.lstrip('-').isdigit()]
        if c == 'text':
            sl = '%d,%d' % ((nums[0] if nums else 0), (nums[0] if nums else 0) + (nums[1] if len(nums) > 1 else 3000))
        else:
            sl = '-%d' % (nums[0] if nums else 2500)
        print(page(r'''window.__gtAll=ALL;const R=scope();window.__gtAll=false;let r=R||document.querySelector("main")||document.body,hid=[];
if(MAIN&&!R){hid=[...r.querySelectorAll('header,nav,footer,aside,[role=navigation],[role=banner],[role=contentinfo],[role=complementary]')];hid.forEach(e=>{e.__d=e.style.display;e.style.display='none'})}
const t=r.innerText;hid.forEach(e=>e.style.display=e.__d);return (R?'[dialog only; b %s all = page]\n':'')+t.replace(/\n{3,}/g,"\n\n").slice(%s)''' % (c, sl),
                   ALL='all' in flags, MAIN=bool(flags & {'-m', '--main', 'main'})))
    elif c == 'el':
        print(page('window.__gtAll=%s;try{%s}finally{window.__gtAll=false}' % ('true' if 'all' in a[1:] else 'false', ELEMENTS)))
    elif c == 'form':
        print(page(SCAN + ';' + FORM))
    elif c == 'fillform':
        path = os.path.expanduser(a[1].lstrip('@'))
        ans = json.load(open(path))
        plan = page(SCAN + ';' + FORMMAP, K=list(ans))
        try:
            plan = json.loads(plan)
        except ValueError:
            sys.exit('form scan failed: ' + plan[:200])
        bad = []
        for k, v in ans.items():
            p = plan.get(k, {'k': 'missing'})
            kind = p['k']
            if kind == 'missing' and isinstance(v, str) and os.path.isfile(os.path.expanduser(v)):
                kind, p = 'button', None
                sys.stdout.write(k + ': ')
                main(['upload', k, v])
                continue
            if kind in ('missing', 'ambiguous'):
                bad.append('%s (%s%s)' % (k, kind, ': ' + p['l'] if kind == 'ambiguous' else ''))
                continue
            vals = v if isinstance(v, list) else [v]
            for x in vals:
                x = str(x).lower() if isinstance(x, bool) else str(x)
                step = {'select': ['select', str(p.get('i')), x], 'combo': ['pick', str(p.get('i')), x],
                        'choose': ['choose', p.get('q', ''), x], 'check': ['check', str(p.get('i')), 'on' if x in ('true', 'yes', 'on', '1') else 'off'],
                        'file': ['upload', str(p.get('i')), x]}.get(kind, ['fill', str(p.get('i')), x])
                sys.stdout.write(k + ': ')
                try:
                    main(step)
                except SystemExit as ex:
                    print(ex)
        print('not matched: ' + '; '.join(bad) if bad else 'all fields matched')
    elif c == 'find':
        q = json.dumps(a[1].lower())
        print(js(r'''(()=>{const q=%s;return (window.__cx||[]).map((e,i)=>i+' '+(e.getAttribute('aria-label')||e.innerText||e.placeholder||e.value||'').replace(/\s+/g,' ').trim().slice(0,80)).filter(s=>s.toLowerCase().includes(q)).join('\n')||'none (run el first)'})()''' % q))
    elif c in ('click', 'fill', 'select', 'check', 'enter', 'hover'):
        if len(a) > 2 and a[2].startswith('@') and os.path.isfile(os.path.expanduser(a[2][1:])):
            a[2] = open(os.path.expanduser(a[2][1:])).read().strip()
        v = json.dumps(a[2] if len(a) > 2 else '')
        body = {
            'click': SIG + 'e.scrollIntoView({block:"center"});e.click();return "clicked: "+lab(e).slice(0,60)',
            'hover': 'e.scrollIntoView({block:"center"});["pointerover","mouseover","mouseenter","pointermove","mousemove"].forEach(t=>e.dispatchEvent(new MouseEvent(t,{bubbles:true})));return "hovered: "+lab(e).slice(0,60)',
            'fill': '''const v=%s;if(!e.matches(FIELD)&&!e.isContentEditable){const c=ctlOf(e);if(c)e=c}if(e.matches('input[aria-autocomplete=list],[class*=select__input] input,input[class*=select__input]'))return "USEPICK";e.focus();
if(e.isContentEditable){document.execCommand("selectAll");const L=v.split("\\n");L.forEach((l,i)=>{if(l)document.execCommand("insertText",false,l);if(i<L.length-1)document.execCommand("insertParagraph")})}
else{const p=e.tagName=="TEXTAREA"?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,"value").set.call(e,v);
e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))}
return "filled "+e.tagName.toLowerCase()+" \\""+flab(e).slice(0,40)+"\\" ("+v.length+" chars)"''' % v,
            'select': '''const v=%s;if(e.tagName=="LABEL"&&e.control)e=e.control;if(!e.options)return "not a <select>; for comboboxes use pick, else click to open then click the option";
const o=[...e.options].find(o=>o.text.trim().toLowerCase()==v.toLowerCase())||[...e.options].find(o=>o.text.trim().toLowerCase().includes(v.toLowerCase()));
if(!o)return "no option; have: "+[...e.options].map(o=>o.text.trim()).join(", ");e.value=o.value;e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));return "selected "+o.text.trim()+" in \\""+flab(e).slice(0,40)+"\\""''' % v,
            'check': '''const v=%s;if(e.tagName=="LABEL"&&e.control)e=e.control;const want=v?/^(on|true|yes|1|x)$/i.test(v):null;
if(want===null||e.checked!==want)e.click();return "checked="+e.checked+" ("+lab(e).slice(0,40)+")"''' % v,
            'enter': '''e.focus();["keydown","keypress","keyup"].forEach(t=>e.dispatchEvent(new KeyboardEvent(t,{key:"Enter",code:"Enter",keyCode:13,which:13,bubbles:true})));
if(e.form&&e.form.requestSubmit)e.form.requestSubmit();return "enter pressed"''',
        }[c]
        out = target(a[1], body)
        if out == 'USEPICK':
            return main(['pick', a[1], a[2]])
        print(settle(out) if c == 'click' else out)
    elif c == 'pick':
        out = page(PICK, Q=a[1], V=a[2], PKM=PKM)
        if out.startswith('NOMATCH') or out == 'EVENTS':
            # options load as you type (async): type the text, then select once a match shows up
            ev = out == 'EVENTS'
            page(PKTYPE, V=a[2])
            end = time.time() + 8
            out = 'NOMATCH'
            while out.startswith('NOMATCH') and time.time() < end:
                time.sleep(0.4)
                out = page(PKOPT if ev else 'return MW(PKM+";return pk("+JSON.stringify(V)+")")', V=a[2], PKM=PKM)
        print(out)
    elif c == 'choose':
        out = page(CHOOSE, Q=a[1], O=a[2] if len(a) > 2 else '')
        if out.startswith('chosen'):
            time.sleep(0.3)
            if js('(()=>{const e=window.__ch;return e.tagName=="INPUT"?e.checked:e.getAttribute("aria-checked")=="true"})()') != 'true':
                out = out.replace('chosen', 'chosen but it un-checked itself (try b bg off + rclick)', 1)
        print(out)
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
        if c == 'upload' and len(a) == 2:
            if os.path.isfile(os.path.expanduser(a[1])):
                a = [c, '-', a[1]]
            else:
                # a file already on the page (e.g. a saved resume): tick or click it by name
                print(page(r'''const n=N.toLowerCase();const D=deep(scope()||document,0,0,[]).map(x=>x[0]).filter(e=>e.matches&&vis(e));
const b=D.filter(e=>isBoxy(e)&&on(e).toLowerCase().includes(n))[0];if(b){const lb=b.labels&&b.labels[0];(lb||b).click();if(isBox(b)&&!b.checked)b.click();return 'selected '+on(b).slice(0,60)+(isBox(b)?' checked='+b.checked:'')}
const t=D.filter(e=>!e.children.length&&T(e.innerText).toLowerCase().includes(n))[0];if(!t)return 'no file named "'+N+'" on the page and no such local file';
const c=t.closest('label,button,[role=radio],[role=button],[role=option],li,[tabindex]')||t;c.click();return 'clicked '+T(c.innerText).slice(0,60)''', N=a[1]))
                return
        path = os.path.abspath(os.path.expanduser(a[2]))
        if not os.path.exists(path):
            sys.exit('no such file: ' + path)
        t0 = time.time()
        name, mime = send_file(path)
        mk = 'const file=new File(window.__up,%s,{type:%s});window.__up=null;const dt=new DataTransfer();dt.items.add(file);' % (name, mime)
        if c == 'upload':
            body = mk + FILE_TARGET + '''f.files=dt.files;f.dispatchEvent(new Event("input",{bubbles:true,composed:true}));f.dispatchEvent(new Event("change",{bubbles:true,composed:true}));
return "attached "+file.name+" ("+(file.size/1048576).toFixed(1)+" MB)"'''
        else:
            body = mk + '''const r=e.getBoundingClientRect(),o={bubbles:true,cancelable:true,dataTransfer:dt,clientX:r.x+r.width/2,clientY:r.y+r.height/2};
["dragenter","dragover","drop"].forEach(t=>e.dispatchEvent(new DragEvent(t,o)));return "dropped "+file.name+" ("+(file.size/1048576).toFixed(1)+" MB)"'''
        q = a[1] if c == 'drop' or a[1] != '-' else ''
        out = target(q, body, STUB=STUB) if q else page('let e=null;' + body, STUB=STUB)
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
    elif c == 'until':
        cond, rest = a[1], a[2:]
        if cond.startswith('url~'):
            cond = 'location.href.includes(%s)' % json.dumps(cond[4:])
        elif cond in ('text', 'gone') and rest:
            cond = '%sdocument.body.innerText.toLowerCase().includes(%s)' % ('!' if cond == 'gone' else '', json.dumps(rest[0].lower()))
            rest = rest[1:]
        if js_until(cond, float(rest[0]) if rest else 30):
            print('ok')
        else:
            sys.exit('timeout')
    elif c == 'wait':
        q, end = a[1].lower(), time.time() + (float(a[2]) if len(a) > 2 else 15)
        while time.time() < end:
            if q in js('document.body.innerText').lower():
                print('found')
                return
            time.sleep(1)
        print('timeout')
    elif c == 'js':
        print(user_js(a[1]))
    elif c == 'li':
        li(a)
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
        print(settle(js('''(()=>{const e=document.elementFromPoint(%f,%f);if(!e)return "nothing there";%s
["pointerdown","mousedown","pointerup","mouseup"].forEach(t=>e.dispatchEvent(new MouseEvent(t,{bubbles:true,clientX:%f,clientY:%f})));e.click();
return "clicked: "+(e.innerText||e.getAttribute("aria-label")||e.tagName).replace(/\\s+/g," ").trim().slice(0,60)})()''' % (X, Y, SIG, X, Y))))
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
            print('bg on: hidden minimized window %s; never comes to front' % bg_new())
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
