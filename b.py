#!/usr/bin/python3
"""Drive Chrome/Brave from the CLI as text (no screenshots). BROWSER=brave to use Brave."""
import json
import os
import re
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
  if c is "open" then
    set u to item 2 of argv
    set i to 0
    repeat with t in tabs of w
      set i to i + 1
      if (URL of t) is u or (URL of t) is (u & "/") then
        set active tab index of w to i
        return "existing " & (id of t)
      end if
    end repeat
    set t to make new tab at end of tabs of w with properties {URL:u}
    return "new " & (id of t)
  end if
  if c is "tabid" then return ((id of active tab of w) as text) & " " & (URL of active tab of w)
  if c is "closeids" then
    set ids to rest of argv
    set n to 0
    repeat with x in windows
      repeat with i from (count of tabs of x) to 1 by -1
        if ids contains {((id of tab i of x) as text)} then
          close tab i of x
          set n to n + 1
        end if
      end repeat
    end repeat
    return "closed " & n
  end if
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
const isBoxy=e=>isBox(e)||/^(radio|checkbox)$/.test(e.getAttribute&&e.getAttribute('role')||'')||(e.tagName.includes('-')&&/(^|-)(radio|checkbox)(-|$)/i.test(e.tagName)&&!e.parentElement.closest('[role=radio],[role=checkbox]'));
function opt(e){if(e.labels&&e.labels[0]&&T(e.labels[0].innerText))return T(e.labels[0].innerText);
const l=e.closest('label');if(l&&T(l.innerText))return T(l.innerText);
for(let s=e.nextElementSibling;s;s=s.nextElementSibling)if(T(s.innerText))return T(s.innerText);
for(let p=e.parentElement,i=0;p&&i<4;i++,p=p.parentElement){if(p.querySelectorAll('input[type=radio],input[type=checkbox],[role=radio],[role=checkbox]').length>1)break;if(T(p.innerText))return T(p.innerText)}
return e.value&&e.value!='on'?e.value:''}
const grp=e=>{const r=e.getRootNode();return e.name?[...(r.querySelectorAll?r:document).querySelectorAll('input[name="'+CSS.escape(e.name)+'"]')]:[e]};
function aq(e){const a=isBox(e)&&e.getAttribute('aria-label');if(!a)return '';const g=grp(e);return (g.length>1&&g.every(x=>x.getAttribute('aria-label')===a))||(T(opt(e))&&T(opt(e))!==T(a))?T(a):''}
const on=e=>e.tagName=='INPUT'?opt(e):T(e.getAttribute('aria-label')||e.innerText);
function ques(e){const a=aq(e);if(a)return a;const f=e.closest('fieldset');if(f){const l=f.querySelector('legend');if(l&&T(l.innerText))return T(l.innerText)}
const g=e.closest('[role=radiogroup],[role=group]');if(g){const t=g.getAttribute('aria-label')||T((byId(g,g.getAttribute('aria-labelledby')||'')||{}).innerText);if(t)return T(t)}
let p=e.parentElement,c=e;for(let i=0;p&&i<8;i++,c=p,p=p.parentElement){if([...p.querySelectorAll(FIELD)].some(x=>!isBoxy(x))){for(let s=c.previousElementSibling;s;s=s.previousElementSibling){if(s.matches('label')||s.querySelector(FIELD))continue;const x=T(s.innerText);if(x)return x}return ''}
const own=[...p.querySelectorAll('input[type=radio],input[type=checkbox],[role=radio],[role=checkbox]')].map(on).filter(Boolean).sort((a,b)=>b.length-a.length);
const L=(p.innerText||'').split('\n').map(s=>T(own.reduce((s,o)=>s.split(o).join(' '),s))).filter(Boolean);if(L.length)return L[0]}return ''}
function lab(e){if(!e.getAttribute)return '';let t=e.getAttribute('aria-label');const lb=e.getAttribute('aria-labelledby');
if(!t&&lb)t=lb.split(' ').map(i=>(byId(e,i)||{}).innerText||'').join(' ');if(isBox(e)&&(!t||aq(e)))return opt(e);
if(!t&&e.labels&&e.labels[0])t=e.labels[0].innerText;return T(t||e.innerText||e.placeholder||e.value||e.title||e.name||'')}
function flab(e){if(isBoxy(e))return ques(e);let t=e.getAttribute('aria-label');const lb=e.getAttribute('aria-labelledby');
if(!t&&lb)t=lb.split(' ').map(i=>(byId(e,i)||{}).innerText||'').join(' ');if(!t&&e.labels&&e.labels[0])t=e.labels[0].innerText;
if(!t&&e.placeholder)t=e.placeholder;
for(let p=e.parentElement,i=0;!T(t)&&p&&i<4;i++,p=p.parentElement){const H=new Set([...p.querySelectorAll('h1,h2,h3')].map(h=>T(h.innerText)));t=(p.innerText||'').split('\n').map(T).filter(x=>x&&x!==T(e.value)&&!H.has(x))[0]}
return T(t||e.name||e.id||'')}
const vis0=e=>{const r=e.getBoundingClientRect();return r.width&&r.height&&getComputedStyle(e).visibility!='hidden'&&e.type!='hidden'};
const vis=e=>{if(vis0(e))return true;if(!isBox(e)||e.closest('[hidden],[aria-hidden=true]'))return false;if(e.checkVisibility)return e.checkVisibility();if(e.labels&&e.labels[0]&&vis0(e.labels[0]))return true;for(let p=e.parentElement,i=0;p&&i<4;i++,p=p.parentElement){if(vis0(p))return true}return false};
function itext(r){const sl=[...r.querySelectorAll('select')].map(s=>{const sp=document.createElement('span');sp.textContent='['+(s.selectedIndex>=0?T(s.options[s.selectedIndex].text):'')+' ▾]';s.__d=s.style.display;s.style.display='none';s.after(sp);return [s,sp]});
try{return r.innerText}finally{sl.forEach(([s,sp])=>{s.style.display=s.__d;sp.remove()})}}
const STATUS=/^(application (was )?(submitted|sent)|your application was sent.{0,40}|applied|applied (on .{1,20}|\d+ \w+ ago)|you applied.{0,40})$/i;
const stat=r=>[...(r||document).querySelectorAll('h1,h2,h3,h4,h5,span,p,div,strong,li')].some(x=>x.childElementCount<=3&&T(x.innerText).length<80&&STATUS.test(T(x.innerText))&&!x.closest('label,legend,fieldset,[role=radiogroup],[role=group],form')&&vis(x));
const dsig=R=>R?T((R.querySelector('h1,h2,h3')||R).innerText).slice(0,80)+'|'+R.querySelectorAll(FIELD).length:'';
function scope(){if(window.__gtAll)return null;const d=[...document.querySelectorAll('[role=dialog],[aria-modal=true],dialog[open]')].filter(e=>{const r=e.getBoundingClientRect();return r.width>80&&r.height>80&&getComputedStyle(e).visibility!='hidden'&&!/^\d+ notifications?\b/i.test(T(e.getAttribute('aria-label')||(e.querySelector('h1,h2,h3')||{}).innerText||''))});
const m=d.filter(e=>e.matches('[aria-modal=true],dialog[open]'));return m.length?m[m.length-1]:d.length?d[d.length-1]:null}
function ctlOf(e){if(e.matches(FIELD))return e;if(e.tagName=='LABEL'){if(e.control)return e.control;const x=e.querySelector(FIELD);if(x)return x}
for(let p=e,i=0;p&&i<4;i++,p=p.parentElement){const x=[...p.querySelectorAll(FIELD)].filter(x=>vis(x)||x.type=='file');if(x.length==1)return x[0];if(x.length>1)break}return null}
function cx(q,form){window.__cxerr='';if(/^\d+$/.test(q))return (window.__cx||[])[+q];const root=scope()||document;
{const bi=document.getElementById(q);if(bi)return bi}if(/^[#.\[]/.test(q)){try{const e=root.querySelector(q)||document.querySelector(q);if(e)return e}catch(_){}}
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
function MW(code){if(window.__gtMain){try{const r=(0,eval)('(()=>{'+code+'})()');return r===undefined?null:r}catch(e){if(!(e instanceof EvalError))return 'ERR: '+e.message}}const d=document.documentElement,s=document.createElement('script');const n=[...document.querySelectorAll('script')].find(x=>x.nonce);if(n)s.nonce=n.nonce;
d.removeAttribute('data-gtr');try{s.textContent='(()=>{let r;try{r=(()=>{'+code+'})()}catch(e){r="ERR: "+e.message}document.documentElement.setAttribute("data-gtr",JSON.stringify(r===undefined?null:r))})()';(document.head||d).appendChild(s);s.remove()}catch(_){}
const r=d.getAttribute('data-gtr');d.removeAttribute('data-gtr');return r===null?'CSP':JSON.parse(r)}
function inst(n){if(!n)return null;const k=Object.keys(n).find(k=>k.startsWith('__reactFiber$')||k.startsWith('__reactInternalInstance$'));let f=k&&n[k];
for(let i=0;f&&i<60;i++,f=f.return){const s=f.stateNode;if(s&&typeof s.selectOption=='function'&&s.props)return s}return null}'''

ELEMENTS = r'''const R=scope();const a=deep(R||document,0,0,[]).filter(x=>x[0].matches&&x[0].matches(SEL)&&vis(x[0]));window.__cx=a.map(x=>x[0]);window.__cxa=a;window.__gtForm=dsig(R);
const h=R?'[dialog: '+T(R.getAttribute('aria-label')||(R.querySelector('h1,h2,h3')||R).innerText).slice(0,60)+'] (b el all = whole page)\n':'';
return h+(a.map((x,i)=>{const e=x[0];let t=e.tagName.toLowerCase()+(e.tagName=='INPUT'?':'+e.type:'');
let v=(e.tagName=='INPUT'||e.tagName=='TEXTAREA')&&e.value&&!/^(password|checkbox|radio)$/.test(e.type)?' = '+JSON.stringify(e.value.slice(0,40)):'';
if(e.checked||e.getAttribute('aria-checked')=='true')v+=' [x]';if(e.disabled)v+=' (disabled)';
return i+' '+t+' '+(isBoxy(e)?ques(e).slice(0,60)+' → '+on(e).slice(0,40):lab(e).slice(0,80))+v}).join('\n')||'no elements')'''

# One scan of the active form/dialog: kind, label, required, value, options. Sets window.__cx for numbers.
SCAN = r'''function scan(){const R=scope();let root=R;if(!root){const af=document.activeElement&&document.activeElement.closest&&document.activeElement.closest('form');
root=af||[...document.forms].filter(vis).sort((a,b)=>b.elements.length-a.elements.length)[0]||document}
const a=deep(root,0,0,[]).filter(x=>{const e=x[0];if(e.matches&&e.tagName!='INPUT'&&e.matches('[role=combobox]')&&e.querySelector('input:not([type=hidden])'))return false;return e.matches&&(e.matches(FIELD)||e.matches('[role=radio],[role=checkbox]')||isBoxy(e)||(root!==document&&e.matches('button,[role=button]')))&&(vis(e)||e.type=='file')});
window.__cx=a.map(x=>x[0]);window.__cxa=a;window.__root=root;
return a.map(x=>{const e=x[0],role=e.getAttribute('role')||'';
const k=e.tagName=='SELECT'?'select':e.tagName=='TEXTAREA'?'textarea':isBox(e)?e.type:/^(radio|checkbox)$/.test(role)?role:isBoxy(e)?(/radio/i.test(e.tagName)?'radio':'checkbox'):e.type=='file'?'file':
(e.tagName=='BUTTON'||role=='button'||/^(submit|button|reset|image)$/.test(e.type))?'button':(role=='combobox'||inst(e))?'combo':e.isContentEditable?'editor':'text';
const l0=k=='button'?lab(e):flab(e),l=l0.replace(/\s*\*$/,'');let v='',o='';
if(k=='select'){v=e.selectedIndex>=0?T(e.options[e.selectedIndex].text):'';o=[...e.options].map(o=>T(o.text)).filter(Boolean);o=o.length>30?o.length+' options':o.slice(0,12).join(', ')+(o.length>12?' +'+(o.length-12):'')}
else if(k=='combo'){let s=null;for(let p=e.parentElement,j=0;p&&!s&&j<5;j++,p=p.parentElement)s=p.querySelector('[class*=singleValue],[class*=single-value],[class*=multiValue],[class*=multi-value]');v=s?T(s.innerText):e.value}
else if(k=='file')v=e.files&&e.files.length?e.files[0].name:'';else if(k=='editor')v=T(e.innerText);
else if(k=='radio'||k=='checkbox')v=e.tagName=='INPUT'||typeof e.checked=='boolean'?!!e.checked:e.getAttribute('aria-checked')=='true';else if(k!='button')v=e.value;
return {k,l,q:(k=='radio'||k=='checkbox')?ques(e):'',o:(k=='radio'||k=='checkbox')?on(e):o,v,r:!!(e.required||e.getAttribute('aria-required')=='true'||/\*\s*$/.test(l0)),d:!!e.disabled}})}'''

FORM = r'''const it=scan();const out=[];let g=null;const R=window.__root;window.__gtForm=dsig(scope());
it.forEach((f,i)=>{if(f.k=='radio'||f.k=='checkbox'){const s=i+' '+f.o.slice(0,40)+(f.v?' [x]':'');if(g&&g.key==f.k+f.q){g.s.push(s);return}
g={key:f.k+f.q,s:[s],line:f.k+' "'+f.q.slice(0,70)+'"'+(f.r?'*':'')};out.push(g);return}g=null;
out.push({line:i+' '+f.k+' "'+f.l.slice(0,60)+'"'+(f.r?'*':'')+(f.k=='button'?'':' = '+JSON.stringify(String(f.v).slice(0,40)))+(f.o?' {'+f.o+'}':'')+(f.d?' (disabled)':'')})});
const h=R===document?'[no form/dialog found; whole page]\n':R.matches('form')?'':'[dialog: '+T(R.getAttribute('aria-label')||(R.querySelector('h1,h2,h3')||R).innerText).slice(0,60)+']\n';
return h+(out.map(x=>x.s?x.line+': '+x.s.join(' | '):x.line).join('\n')||'no fields')'''

FORMMAP = r'''const it=scan();const res={};const N=s=>s.toLowerCase().replace(/\s*\*$/,'').trim();
K.forEach(k=>{const lo=N(k);const c=it.map((f,i)=>({f,i})).filter(x=>x.f.k!='button');const L=x=>N(x.f.q||x.f.l);
let m=c.filter(x=>L(x)==lo);if(!m.length)m=c.filter(x=>L(x).startsWith(lo));if(!m.length)m=c.filter(x=>L(x).includes(lo));
if(!m.length){res[k]={k:'missing'};return}
const gk=x=>x.f.q||('#'+x.i);const U=[...new Map(m.map(x=>[gk(x),x])).values()];
if(U.length>1){const ps=x=>L(x).indexOf(lo);U.sort((a,b)=>ps(a)-ps(b));if(ps(U[0])<ps(U[1]))m=m.filter(x=>gk(x)===gk(U[0]))}const f=m[0].f;
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
const st=()=>e.tagName=='INPUT'||(e.tagName.includes('-')&&typeof e.checked=='boolean')?e.checked:e.getAttribute('aria-checked')=='true'||e.hasAttribute('checked');e.scrollIntoView({block:'center'});const lb=e.labels&&e.labels[0];
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


SOCK = os.path.expanduser('~/.ghosttab/%s.sock' % ('brave' if 'Brave' in APP else 'chrome'))


# one set of agent tabs per Claude session, so parallel sessions never share a tab
SID = os.environ.get('B_SESSION') or os.environ.get('CLAUDE_CODE_SESSION_ID') or os.environ.get('CLAUDE_PID') or 'default'
_cwd = os.path.basename(os.getcwd())
SNAME = os.environ.get('B_NAME') or ('GhostTab ' + _cwd if _cwd not in ('', os.path.basename(os.path.expanduser('~'))) else 'GhostTab')


class ExtDown(Exception):
    pass


def ext(op, timeout=None, **kw):
    """One request to the GhostTab extension (CDP in the hidden tab) via the native host's socket."""
    import socket
    t = timeout or TIMEOUT
    s = socket.socket(socket.AF_UNIX)
    s.settimeout(t + 3)
    try:
        s.connect(SOCK)
    except OSError:
        raise ExtDown()
    kw.update(op=op, bg=bool(bgwin()), timeout=t, s=SID, name=SNAME)
    s.sendall((json.dumps(kw) + '\n').encode())
    buf = b''
    try:
        while not buf.endswith(b'\n'):
            chunk = s.recv(1 << 20)
            if not chunk:
                break
            buf += chunk
    except OSError:
        buf = b''
    s.close()
    r = json.loads(buf) if buf else {'ok': False, 'e': 'timeout'}
    if not r['ok']:
        raise RuntimeError(r['e'])
    return r['r']


def xbg():
    return bgwin() == 'ext'


def xin():
    """Send clicks/keys through the extension (never the user's real mouse) whenever it is connected."""
    return xbg() or (not bgwin() and not os.environ.get('B_NOEXT') and os.path.exists(SOCK))


def js(code, soft=False):
    if xbg():
        try:
            return ext('eval', code=code)
        except ExtDown:
            sys.exit('GhostTab extension not connected (is %s running with the extension on? b ext status)' % APP)
        except RuntimeError as e:
            if str(e) != 'timeout':
                sys.exit('extension: %s' % e)
            if soft:
                return 'timeout'
            sys.exit('page did not answer in %ds; it may still have acted, check b url / b t 300. Longer wait: B_TIMEOUT=90 b ...' % TIMEOUT)
    return osa('js', code, soft=soft)


def x_click(x, y, n=1):
    ext('click', x=x, y=y, n=n)


XKEYS = {'enter': ('Enter', 13, '\r'), 'return': ('Enter', 13, '\r'), 'tab': ('Tab', 9, ''), 'esc': ('Escape', 27, ''),
         'escape': ('Escape', 27, ''), 'backspace': ('Backspace', 8, ''), 'delete': ('Delete', 46, ''), 'space': (' ', 32, ' '),
         'up': ('ArrowUp', 38, ''), 'down': ('ArrowDown', 40, ''), 'left': ('ArrowLeft', 37, ''), 'right': ('ArrowRight', 39, ''),
         'pageup': ('PageUp', 33, ''), 'pagedown': ('PageDown', 34, ''), 'home': ('Home', 36, ''), 'end': ('End', 35, '')}


def x_key(combo):
    parts = combo.lower().split('+')
    k = parts[-1]
    mod = sum({'alt': 1, 'opt': 1, 'ctrl': 2, 'cmd': 4, 'meta': 4, 'shift': 8}[p] for p in parts[:-1])
    if k in XKEYS:
        key, kc, text = XKEYS[k]
        code = 'Space' if k == 'space' else key
    else:
        key, kc, text = k, ord(k.upper()), k
        code = 'Key' + k.upper() if k.isalpha() else 'Digit' + k if k.isdigit() else ''
    if mod & 8 and len(key) == 1:
        key = text = key.upper()
    if mod & 6:
        text = ''
    cmd = {'a': 'selectAll', 'c': 'copy', 'v': 'paste', 'x': 'cut', 'z': 'undo'}.get(k) if mod & 4 else None
    ext('key', key=key, code=code, kc=kc, mod=mod, text=text or None, commands=[cmd] if cmd else None)


# find the file input for a target (or the page); else return the target's centre for a trusted click
XFILE = r'''let f=e&&e.tagName=='INPUT'&&e.type=='file'?e:null;
if(!f&&e){f=e.querySelector('input[type=file]');const c=e.closest('form,section,[role=dialog],div');if(!f&&c)f=c.querySelector('input[type=file]')}
if(!f&&!e)f=deep(scope()||document,0,0,[]).map(x=>x[0]).find(x=>x.tagName=='INPUT'&&x.type=='file');
window.__gtEl=f||null;if(f)return 'INPUT';if(!e)return 'NONE';e.scrollIntoView({block:'center'});const r=e.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])'''


def x_upload(q, path):
    out = target(q, XFILE) if q else page('let e=null;' + XFILE)
    name = os.path.basename(path)
    if out == 'INPUT':
        ext('files', expr='window.__gtEl', files=[path])
        return 'attached %s' % name
    ext('arm', files=[path])
    if out == 'NONE':
        return 'file chooser armed with %s: now click the upload button (b click / b rclick)' % name
    if not out.startswith('['):
        return out
    x_click(*json.loads(out))
    for _ in range(25):
        time.sleep(0.2)
        if ext('armed') == 'used':
            return 'attached %s via the file chooser' % name
    return 'clicked, but no file chooser opened yet (armed: the next one gets %s)' % name


VPOS = 'const f=(window.__cxa||[]).find(x=>x[0]===e)||[e,0,0];e.scrollIntoView({block:"center"});const r=e.getBoundingClientRect();return JSON.stringify([f[1]+r.x+r.width/2,f[2]+r.y+r.height/2])'


DLG = 'var $dlg=(()=>{const BACKING=2;%s;return scope()||document})();' % DEEP


def user_js(code):
    out = js('(()=>{%slet r;try{r=(\n%s\n)}catch(e){return "ERR: "+e.message}if(r instanceof Promise)return "Promise (not awaited; store the result in window.x and read it)";'
             'const el=x=>x.tagName.toLowerCase()+(x.type?":"+x.type:"")+(x.id?"#"+x.id:"")+" "+String(x.getAttribute("aria-label")||x.innerText||x.value||"").replace(/\\s+/g," ").trim().slice(0,60);'
             'if(r instanceof NodeList||r instanceof HTMLCollection||(Array.isArray(r)&&r.length&&r.every(x=>x instanceof Element)))return r.length+" elements"+[...r].slice(0,50).map((x,i)=>"\\n"+i+" "+el(x)).join("");'
             'if(r instanceof Element)return r.outerHTML.slice(0,300);return r===undefined?"undefined":r===null?"null":typeof r=="object"?(()=>{try{return JSON.stringify(r)}catch(_){return String(r)}})():String(r)})()' % (DLG, code))
    if out == 'missing value':
        # statements, not an expression: run as a script, its completion value is the result
        out = js('%stry{\n%s\n}catch(e){"ERR: "+e.message}' % (DLG, code))
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
    if xbg():
        return js(code)
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


SECRET_DIRS = ('.ssh', '.aws', '.gnupg', '.config', '.kube', '.docker', '.azure', '.gcloud', '.netrc', 'Library', '.ghosttab', '.claude')
SECRET_FILES = re.compile(r'(^\.env|^id_(rsa|ed25519|ecdsa|dsa)|\.(pem|key|p12|pfx|kdbx|keychain(-db)?|ovpn)$|^credentials|^\.?(bash|zsh)_history$|^\.(npmrc|pypirc|git-credentials)$)', re.I)


def safe_path(p):
    """Uploads are a data-exfiltration path if an agent gets prompt-injected: block secrets, optionally confine to B_UPLOAD_DIRS."""
    path = os.path.realpath(os.path.expanduser(p))
    home = os.path.realpath(os.path.expanduser('~'))
    rel = os.path.relpath(path, home).split(os.sep) if path.startswith(home + os.sep) else []
    if (rel and (rel[0] in SECRET_DIRS or any(x.startswith('.') for x in rel[:-1]))) or SECRET_FILES.search(os.path.basename(path)):
        sys.exit('refused: %s looks like a secret or config file. GhostTab never uploads keys, .env, dotfolders or ~/Library' % path)
    allow = [os.path.realpath(os.path.expanduser(d)) for d in os.environ.get('B_UPLOAD_DIRS', '').split(':') if d]
    if allow and not any(path == d or path.startswith(d + os.sep) for d in allow):
        sys.exit('refused: %s is outside B_UPLOAD_DIRS (%s)' % (path, ':'.join(allow)))
    return path


def send_file(path):
    """Stream a local file into the page as window.__up (Uint8Array chunks)."""
    js('window.__up=[];0')
    with open(path, 'rb') as fh:
        while True:
            chunk = fh.read(700 * 1024 if xbg() else 6 * 1024 * 1024)  # native messaging caps host->browser at 1MB
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

# Submit/Send/Pay-like buttons: no fuzzy matches, no stale or already-submitted state. Sets FIN (url | title | label) when final.
FINAL = r'''const L=lab(e),fin=/^(submit|send|pay|post|place order|purchase|apply( now)?$|confirm and pay)|submit application/i.test(L);let FIN='';
if(fin){if(!/^\d+$/.test(Q)&&!FIN_OK&&L.toLowerCase().replace(/\s*\*$/,'')!==Q.toLowerCase())return 'REFUSED: "'+Q+'" fuzzily matched the final button "'+L.slice(0,50)+'". Use its exact text, its number from b el, or add --final';
const R=scope();if(!FORCE&&/apply|submit/i.test(L)&&stat(R||document.querySelector('main')||document.body))return 'REFUSED: the page already says it was submitted/applied. Check b t 400 (--force to override)';
if(!FORCE&&R&&window.__gtForm!==undefined&&window.__gtForm!==dsig(R))return 'REFUSED: the dialog changed since your last b form / b el / b li review. Look again, then click (--force to override)';
FIN=location.href+' | '+document.title+' | '+L.slice(0,60)}'''
SUBMITS = os.path.join(HERE, 'submits.log')


def fin_log(out):
    if ' |FIN|' not in out:
        return out
    out, info = out.split(' |FIN|', 1)
    info = info.strip()
    if not info:
        return out
    if not out.startswith('REFUSED'):
        with open(SUBMITS, 'a') as fh:
            fh.write('%s %s %s\n' % (time.strftime('%Y-%m-%d %H:%M:%S'), 'brave' if 'Brave' in APP else 'chrome', info))
    return out


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
    if xbg():
        import base64
        path = '/tmp/b-shot-raw.png'
        open(path, 'wb').write(base64.b64decode(ext('shot', timeout=20)))
        return path, None
    if bgwin():
        sys.exit('ocr/shot need a visible window; the bg window is minimized. Use text/el, or b bg off for ocr')
    n, x, y, w, h = cg_window()
    path = '/tmp/b-shot-raw.png'
    subprocess.run(['screencapture', '-x', '-o', '-l', str(n), path])
    return path, (x, y, w, h)


def no_bg(cmd):
    if bgwin():
        sys.exit('%s uses the real mouse/keyboard; in bg mode use click/fill/clickat instead, or run: b bg off' % cmd)


def point(q, final=False):
    if not xbg():
        no_bg('real input')
        front_check()
    P = ('const vp=()=>{%s};' % VPOS, 'vp()') if xin() else ('', 'JSON.stringify(pos(e))')
    out = target(q, P[0] + (FINAL + ';return ' + P[1] + '+" |FIN| "+FIN' if final else 'return ' + P[1]), real=True, **FLAGS)
    if final and ' |FIN|' in out:
        out, info = out.split(' |FIN|', 1)
        PENDING[0] = info.strip()
    if not out.startswith('['):
        sys.exit(out)
    if not xin():
        osa('front')
        time.sleep(0.3)
    return json.loads(out)


FLAGS = {'FIN_OK': False, 'FORCE': False}
PENDING = ['']
STATE = os.path.join(HERE, '.front-' + APP.split()[0].lower())


def front_check():
    # the user may be working in the front window: refuse real input if the tab/site changed since b last looked
    if FLAGS['FORCE'] or os.environ.get('B_FORCE'):
        return
    try:
        old = open(STATE).read().split(' ', 1)
    except OSError:
        return
    now = osa('tabid').split(' ', 1)
    host = lambda u: u.split('/')[2] if u.count('/') >= 2 else u
    if len(now) == 2 and len(old) == 2 and (now[0] != old[0] or host(now[1]) != host(old[1])):
        sys.exit('front tab changed since b last looked (now %s). The user may be using it. Run b url to accept, or add --force' % now[1][:100])


def front_mark():
    if not bgwin():
        r = osa('tabid', soft=True)
        if r[:1].isdigit():
            open(STATE, 'w').write(r)


def settle(msg):
    """After a click: report whether the page navigated or changed."""
    if not msg.startswith(('clicked', 'chosen')):
        return msg
    for _ in range(4):
        time.sleep(0.25)
        s = js('window.__gtSig===undefined?"navigated":(location.href+"|"+document.getElementsByTagName("*").length)==window.__gtSig?"":"page changed"')
        if s:
            time.sleep(0.6)
            code = js('/(security|verification|confirmation) code|enter the (\\d+[- ]digit )?code|code (we|was) sent/i.test(document.body.innerText)', soft=True) == 'true'
            return '%s → %s%s' % (msg, 'navigating' if s == 'missing value' else s, '\n== EMAIL/SMS CODE NEEDED: ask the user for the code' if code else '')
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
    href0 = js('location.href')
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
        st = js('window.__gtOld?(location.href!=%s&&document.readyState=="complete"&&performance.now()>0?"spa":"old"):document.readyState' % json.dumps(href0), soft=True)
        if st == 'spa' and time.time() - t0 > 1.5:
            st = 'complete'
        if st in ('interactive', 'complete') or (st in ('old', 'spa') and url and time.time() - t0 > 12):
            break
        time.sleep(0.25)
    if st not in ('old', 'spa'):
        print('ok')
    elif st == 'spa':
        print('ok (in-app navigation)')
    elif url and retry and not xbg() and js('location.href') != url:
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
 bg on [hidden]|off|close|status  agent tab in your window, never active (hidden = minimized window); close removes
 until 'JS' [sec] | until url~PART [sec] | until text TEXT [sec] | until gone TEXT [sec]
 fill N|LABEL @file  fill from a file; newlines become paragraphs in rich editors (LinkedIn, Gmail...)
 li jobs QUERY [PLACE|geo=ID] [days=30] [all] [any]   Easy Apply jobs (any = all jobs; all = show Applied too)
 li job ID | li apply ID [CVNAME] | li review      job summary / start Easy Apply to the questions / compact review
 close mine          close the tabs b opened in your window (front mode)
 save N|TEXT|URL OUT download an image/link/canvas (with your login) to a file
 gpt image @prompt.txt OUT.png   ChatGPT: send prompt, wait, save the generated image full size
 yt pin VIDEO_ID COMMENT_ID      pin a comment on your video
 fb "note" | stats   report a GhostTab problem/idea | per-command speed and errors
 safety: Submit/Send/Pay/Apply clicks need exact text or a number (--final to allow fuzzy); refused if the page
         already says submitted or the dialog changed since b form/el (--force); every final click goes to submits.log
         rclick/type/key/rupload refuse if you switched tab/site since b's last command (b url to accept, or --force)
 log [N]             last N actions (what the agent did, when, where)
 wait TEXT [sec] | js CODE | shot   (window screenshot, last resort)
 env: B_TIMEOUT=60 for slow pages (default 30s)'''


LOG = os.path.join(HERE, 'activity.log')
MINE = os.path.join(HERE, '.mine-' + APP.split()[0].lower())
ACTS = {'go', 'open', 'back', 'reload', 'close', 'tab', 'click', 'rclick', 'fill', 'type', 'select', 'check', 'enter',
        'key', 'upload', 'drop', 'rupload', 'clickat', 'rclickat', 'scroll', 'hover', 'js', 'bg', 'pick', 'choose', 'fillform'}
ALIAS = {'t': 'tail', 'x': 'text', 'e': 'el', 'c': 'click', 'f': 'fill', 'g': 'go', 'o': 'open', 'u': 'url',
         'k': 'key', 's': 'scroll', 'w': 'wait', 'up': 'upload'}
REST = ('fill', 'type', 'select', 'pick', 'choose', 'hover', 'check')


GEO = {'worldwide': 92000000, 'eu': 91000000, 'europe': 91000000, 'cyprus': 106774002, 'poland': 105072130,
       'uae': 104305776, 'united arab emirates': 104305776, 'dubai': 104305776, 'uk': 101165590, 'united kingdom': 101165590,
       'us': 103644278, 'usa': 103644278, 'united states': 103644278, 'germany': 101282230, 'netherlands': 102890719,
       'ireland': 104738515, 'ie': 104738515, 'nl': 102890719, 'holland': 102890719, 'ksa': 100459316, 'saudi': 100459316,
       'de': 101282230, 'pl': 105072130, 'cy': 106774002, 'gb': 101165590, 'england': 101165590, 'pk': 101022442, 'canada': 101174742, 'saudi arabia': 100459316, 'pakistan': 101022442}

# one Easy Apply step: where we are, what is unanswered, which button moves on
LISTEP = r"""const R=scope();const t=R?R.innerText:'';const it=R?scan():[];const pb=R&&R.querySelector('[role=progressbar],progress');
const pr=(t.match(/(\d+)\s*%/)||[])[1]||((t.match(/\b(\d+)\s*\/\s*(\d+)\b/)||[]).slice(1).join('/'))||(pb&&(pb.getAttribute('aria-valuenow')||pb.value))||'';
const h=R?T((R.querySelector('h3,h2')||{}).innerText||''):'';const req=[];const seen={};
it.forEach(f=>{if(f.k=='button')return;if(f.k=='radio'||f.k=='checkbox'){const k=f.q;if(!(k in seen))seen[k]=f.r?0:1;if(f.v)seen[k]=1;return}if(f.r&&(f.v===''||f.v===false||/^select an option$/i.test(f.v)))req.push(f.l)});
Object.keys(seen).forEach(k=>{if(!seen[k])req.push(k)});
const btn=[...R?R.querySelectorAll('button'):[]].filter(b=>vis(b)&&!b.disabled);const NX='[data-easy-apply-next-button],[data-live-test-easy-apply-next-button],[data-live-test-easy-apply-review-button]';
const nx=btn.find(b=>b.matches(NX))||btn.find(b=>/^(next|review|continue)$/i.test(T(b.innerText))||/next step|review your application/i.test(b.getAttribute('aria-label')||''));
document.querySelectorAll('[data-gtnext]').forEach(x=>x.removeAttribute('data-gtnext'));if(nx)nx.setAttribute('data-gtnext','1');
const sub=btn.find(b=>b.matches('[data-live-test-easy-apply-submit-button],[data-easy-apply-submit-button]')||/submit application/i.test(T(b.innerText)+' '+(b.getAttribute('aria-label')||'')));
const err=R?[...R.querySelectorAll('[role=alert],.artdeco-inline-feedback--error,[class*=error]')].map(x=>T(x.innerText)).filter(Boolean).slice(0,5):[];
const fl=it.filter(f=>f.k!='button');const fn=/\.(pdf|docx?)\b/i;
const qf=fl.filter(f=>{if(f.k=='file')return false;if(f.k=='radio'||f.k=='checkbox')return !fn.test(f.o)&&!fn.test(f.q);
if(f.k=='select')return !/^\d+ options$/.test(f.o)&&!/@/.test(f.v);if(f.k=='textarea')return true;
const v=String(f.v);return v===''||/\?/.test(f.l)||/^\d{1,2}$/.test(v)});
const ct=fl.some(f=>f.k=='select'&&(/^\d+ options$/.test(f.o)||/@/.test(f.v)));const kind=ct?'contact':qf.length?'questions':fl.some(f=>f.k=='file'||fn.test(f.o||''))||[...R?R.querySelectorAll('*'):[]].some(x=>!x.children.length&&fn.test(x.textContent||''))?'resume':fl.length?'contact':'profile';
const cl=!fl.length&&[...R?R.querySelectorAll('a,button'):[]].find(b=>vis(b)&&/continue|weiter|dalej|continuer|continuar/i.test(T(b.innerText)));
if(cl)cl.setAttribute('data-gtcont','1');return JSON.stringify({limit:/easy apply limit|reached today.{0,20}limit/i.test(t),dlg:!!R,h,pr,req,kind,cont:!!cl,next:nx?T(nx.innerText):'',submit:!!sub,done:R?stat(R):false,
review:!!sub||/^(100|(\d+)\/\2)$/.test(pr)||/review your application/i.test(t),resume:/upload resume|^resume$/im.test(t)||[...R?R.querySelectorAll('*'):[]].some(x=>!x.children.length&&/\.(pdf|docx?)\b/i.test(x.textContent||'')),sig:dsig(R),err})"""

LIREVIEW = r"""const R=scope();if(!R)return 'no Easy Apply dialog open';window.__gtForm=dsig(R);const fn=/\.(pdf|docx?)\b/i;
const cv=[...new Set([...R.querySelectorAll('*')].filter(x=>!x.children.length&&fn.test(x.textContent||'')).map(x=>T(x.textContent)))];
const txt=x=>T(x.innerText||'');const ok=x=>txt(x)&&txt(x).length<300&&!x.querySelector('button,input,select,textarea');
const pairs=[...R.querySelectorAll('*')].filter(x=>{const c=[...x.children].filter(y=>txt(y));return c.length==2&&c.every(ok)&&!c.some(y=>y.matches('button,a,[role=button]'))&&!c[0].matches('h1,h2,h3,h4')&&!/^(button|a|label)$/i.test(x.tagName)});
const inner=pairs.filter(x=>!pairs.some(y=>y!==x&&x.contains(y)));const seen=new Set(),out=[];
const contact=a=>/@|^\+?[\d\s()-]{7,}$|\(\+\d+\)/.test(a)||fn.test(a);
inner.forEach(x=>{const [q,a]=[...x.children].filter(y=>txt(y)).map(txt);if(contact(a)||contact(q)||seen.has(q))return;seen.add(q);out.push(q.slice(0,90)+' → '+a.slice(0,80))});
return 'CV: '+(cv.join(', ')||'none shown')+'\n'+(out.slice(0,60).join('\n')||'(no Q→A pairs found; b t 1500)')"""


def li(a):
    if a[1] == 'job':
        main(['go', 'https://www.linkedin.com/jobs/view/%s/' % a[2]])
        js_until('document.querySelector("h1")', 15)
        print(js(r'''(()=>{const T=s=>(s||'').replace(/\n{2,}/g,'\n').trim();const t=(document.querySelector('main')||document.body).innerText;const h=document.querySelector('h1');
const i=Math.max(0,h?t.indexOf(h.innerText.trim()):0);const j=t.search(/About the job/i);
const ea=[...document.querySelectorAll('button,a')].some(b=>/easy apply/i.test(b.innerText||b.getAttribute('aria-label')||''));
return T(t.slice(i,j>i?Math.min(j,i+500):i+500))+'\nEasy Apply: '+(ea?'yes':'no')+'\n'+(j>=0?T(t.slice(j,j+1500)):'')})()'''))
        return
    if a[1] == 'review':
        print(page(SCAN + ';' + LIREVIEW))
        return
    if a[1] == 'limit':
        print('DAILY LIMIT reached (dialog on this page)' if js('/easy apply limit|reached today.{0,20}limit/i.test(document.body.innerText)') == 'true' else 'no Easy Apply limit message on this page')
        return
    if a[1] == 'apply':
        return li_apply(a[2], ' '.join(a[3:]))
    from urllib.parse import quote
    opts = [x for x in a[3:] if '=' in x or x in ('all', 'any')]
    kv = dict(x.split('=', 1) for x in opts if '=' in x)
    place = ' '.join(x for x in a[3:] if x not in opts)
    url = 'https://www.linkedin.com/jobs/search-results/?keywords=%s' % quote(a[2])
    geo = kv.get('geo') or GEO.get(place.lower())
    if geo:
        url += '&geoId=%s' % geo
    elif place:
        sys.exit('no geoId known for "%s" (LinkedIn would ignore it and use your saved location). Known: %s. Or pass geo=ID' % (place, ', '.join(sorted(GEO))))
    if 'any' not in opts:
        url += '&f_AL=true'
    url += '&f_TPR=r%d' % (int(kv.get('days', 30)) * 86400)
    main(['go', url])
    js_until('location.href.includes(%s)&&document.querySelectorAll(' % json.dumps('geoId=%s' % geo if geo else 'keywords=') + '"[componentkey^=\'job-card-component-ref-\'],[data-job-id],[data-occludable-job-id]").length', 15)
    print(js(r'''(()=>{const seen=new Set(),out=[];let ap=0;document.querySelectorAll("[componentkey^='job-card-component-ref-'],[data-job-id],[data-occludable-job-id]").forEach(c=>{
const id=(c.getAttribute('componentkey')||'').replace('job-card-component-ref-','')||c.getAttribute('data-job-id')||c.getAttribute('data-occludable-job-id');
if(!id||seen.has(id))return;seen.add(id);const L=[...new Set((c.innerText||'').split('\n').map(s=>s.trim()).filter(s=>s&&!/^(Promoted|Viewed|Saved|·)$/.test(s)))];
if(!SHOWALL&&L.some(l=>/^Applied\b/.test(l))){ap++;return}
out.push(id+' | '+L.slice(0,6).join(' | ').slice(0,220))});return (out.join('\n')||'no jobs found (b t 1500 to see the page)')+(ap?'\n('+ap+' already applied hidden; add all to show)':'')})()'''.replace('SHOWALL', 'true' if 'all' in opts else 'false')))


def li_apply(jid, cv):
    """Open the job, start/continue Easy Apply, pick the saved CV, press Next through the plain pages; stop at questions or review."""
    main(['go', 'https://www.linkedin.com/jobs/view/%s/' % jid])
    js_until('document.querySelector("h1")', 15)
    st = page(r"""const m=document.querySelector('main')||document.body;
let top=document.querySelector('h1');for(let i=0;top&&i<5;i++)top=top.parentElement;if(stat(top||m))return 'ALREADY';
const b=deep(document,0,0,[]).map(x=>x[0]).filter(e=>e.matches&&e.matches('button,a,[role=button]')&&vis(e)&&/^(easy apply|continue)\b/i.test(lab(e))&&!e.closest('[role=dialog],nav,header'));
if(!b.length)return 'NOBUTTON';b[0].click();return lab(b[0])""")
    if st in ('ALREADY', 'NOBUTTON'):
        print({'ALREADY': 'already applied to %s' % jid, 'NOBUTTON': 'no Easy Apply / Continue button on %s' % jid}[st])
        return
    if st.lower().startswith('continue'):
        print('(resumed a draft: LinkedIn drops uploaded cover letters on drafts, re-upload if one is needed)')
    js_until('(()=>{%s;return scope()})()' % DEEP.replace('BACKING', '2'), 10)
    picked, last, retried = False, '', False
    for _ in range(10):
        end = time.time() + 5
        while True:
            time.sleep(0.5)
            s = json.loads(page(SCAN + ';' + LISTEP))
            if s['next'] or s['pr'] or s['review'] or s['cont'] or s['done'] or s['limit'] or time.time() > end:
                break
        if not s['dlg']:
            print('Easy Apply dialog did not open (b t 600)')
            return
        if s['limit']:
            print('== DAILY LIMIT: LinkedIn says today\'s Easy Apply limit is reached. Save jobs and continue tomorrow')
            return
        if s['done']:
            print('application already sent (dialog says so)')
            return
        if s['review']:
            print('== AT REVIEW. Check, then click the submit button by its exact text')
            print(page(SCAN + ';' + LIREVIEW))
            return
        if s['cont']:
            print('(passed "%s")' % s['h'][:50])
            js('document.querySelector("[data-gtcont]").click();1')
            time.sleep(1.5)
            continue
        if s['resume'] and cv and not picked:
            picked = True
            sys.stdout.write('CV: ')
            main(['upload', cv])
            time.sleep(1)
            continue
        plain = s['kind'] != 'questions'
        if s['sig'] == last and s['next'] and not retried:
            retried = True
            js('document.querySelector("[data-gtnext]").click();1')
            time.sleep(1.5)
            continue
        if s['sig'] == last or not s['next'] or s['req'] or not plain:
            print('== %s (page "%s", %s)%s' % ('STUCK' if s['sig'] == last else 'QUESTIONS', s['h'], (s['pr'] + ('' if '/' in s['pr'] else '%')) if s['pr'] else '?',
                                                ('\nunanswered: ' + ' | '.join(r[:60] for r in s['req'])) if s['req'] else ''))
            if s['err']:
                print('errors: ' + ' | '.join(s['err']))
            print('\n'.join(l for l in page(SCAN + ';' + FORM).splitlines() if ' button "' not in l))
            print('next button: %s' % (s['next'] or 'none'))
            return
        last, retried = s['sig'], False
        js('document.querySelector("[data-gtnext]").click();1')
    print('gave up after 10 pages (b form)')


SAVE_START = r"""const u=U;window.__sv=null;fetch(u,{credentials:'include'}).then(r=>{if(!r.ok)throw new Error('HTTP '+r.status);return r.blob()})
.then(b=>new Promise(res=>{const f=new FileReader();f.onload=()=>res(f.result);f.readAsDataURL(b)})).then(d=>window.__sv=d).catch(e=>{window.__sv='ERR '+e.message});return 1"""


def save(src, out):
    """Download a URL or the image/link/canvas at a target with the page's cookies into a local file."""
    import base64
    if '://' not in src:
        src = page(r"""let e=cx(Q,false);if(!e)return 'ERR not found: '+Q;if(e.tagName!='IMG'&&e.tagName!='CANVAS'&&e.tagName!='A'){const i=e.querySelector('img,canvas');if(i)e=i}
if(e.tagName=='CANVAS')return e.toDataURL('image/png');return e.currentSrc||e.src||e.href||'ERR no image or link at '+Q""", Q=src)
        if src.startswith('ERR'):
            sys.exit(src[4:])
    if not src.startswith('data:'):
        page(SAVE_START, U=src)
        end = time.time() + 60
        while time.time() < end and js('window.__sv?1:0') != '1':
            time.sleep(0.3)
        n = int(js('window.__sv?window.__sv.length:0'))
        head = js('window.__sv?window.__sv.slice(0,200):""')
        if (not n or head.startswith('ERR')) and xin():
            # cross-origin without CORS: take it from the browser's own cache
            try:
                data = b''.join(__import__('base64').b64decode(x) for x in json.loads(ext('resource', url=src, timeout=60)))
                out = os.path.abspath(os.path.expanduser(out))
                open(out, 'wb').write(data)
                return 'saved %s (%d KB)' % (out, len(data) // 1024)
            except (ExtDown, RuntimeError):
                pass
        if not n or head.startswith('ERR'):
            try:
                data = subprocess.run(['curl', '-sfL', '--max-time', '30', '-A', 'Mozilla/5.0', src], capture_output=True, check=True).stdout
                out = os.path.abspath(os.path.expanduser(out))
                open(out, 'wb').write(data)
                return 'saved %s (%d KB, public download)' % (out, len(data) // 1024)
            except Exception:
                pass
            # last resort: draw the loaded image on a canvas
            src = page(r"""const i=[...document.images].find(x=>(x.currentSrc||x.src)==U);if(!i)return 'ERR '+H;try{const c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;c.getContext('2d').drawImage(i,0,0);return c.toDataURL('image/png')}catch(e){return 'ERR '+H+' / '+e.message}""", U=src, H=head or 'timeout')
            if src.startswith('ERR'):
                sys.exit('could not download: ' + src[4:])
        else:
            src = ''.join(js('window.__sv.slice(%d,%d)' % (i, i + 600000)) for i in range(0, n, 600000))
            js('window.__sv=null;1')
    data = base64.b64decode(src.split(',', 1)[1])
    out = os.path.abspath(os.path.expanduser(out))
    open(out, 'wb').write(data)
    return 'saved %s (%d KB)' % (out, len(data) // 1024)


GPT_IMGS = 'JSON.stringify([...document.querySelectorAll("main img")].filter(i=>i.naturalWidth>=256&&/generated|image/i.test(i.alt||"image")).map(i=>i.currentSrc||i.src))'


def gpt(a):
    """b gpt image @prompt.txt|TEXT OUT.png : new ChatGPT chat, send the prompt, wait for the image, save it full size."""
    if len(a) < 4 or a[1] != 'image':
        sys.exit('usage: b gpt image @prompt.txt|"prompt" OUT.png')
    prompt = open(os.path.expanduser(a[2][1:])).read().strip() if a[2].startswith('@') else a[2]
    main(['go', 'https://chatgpt.com/'])
    if not js_until('document.querySelector("#prompt-textarea")', 25):
        sys.exit('ChatGPT composer not found (logged out? b t 400)')
    before = set(json.loads(js(GPT_IMGS)))
    print(page(r"""const e=document.querySelector('#prompt-textarea');e.focus();document.execCommand('selectAll');const L=V.split('\n');
L.forEach((l,i)=>{if(l)document.execCommand('insertText',false,l);if(i<L.length-1)document.execCommand('insertParagraph')});return 'prompt: '+V.length+' chars'""", V=prompt))
    if not js_until('(b=>b&&!b.disabled)(document.querySelector("[data-testid=send-button],#composer-submit-button"))', 15):
        sys.exit('send button never enabled')
    js('document.querySelector("[data-testid=send-button],#composer-submit-button").click();1')
    t0 = time.time()
    js_until('document.querySelector("[data-testid=stop-button]")', 20)
    new = []
    while time.time() - t0 < 300:
        time.sleep(3)
        pump()
        busy = js('!!document.querySelector("[data-testid=stop-button]")') == 'true'
        new = [u for u in json.loads(js(GPT_IMGS)) if u not in before]
        if new and not busy:
            break
    if not new:
        sys.exit('no image after %ds; last reply: %s' % (time.time() - t0, js('(()=>{const m=[...document.querySelectorAll("[data-message-author-role=assistant]")].pop();return m?m.innerText.slice(0,300):"none"})()')))
    time.sleep(2)
    new = [u for u in json.loads(js(GPT_IMGS)) if u not in before] or new
    print('%s after %ds' % (save(new[-1], a[3]), time.time() - t0))


YT_THREAD = r"""const t=[...document.querySelectorAll('ytd-comment-thread-renderer')];const m=t.find(x=>[...x.querySelectorAll('a[href*="lc="]')].some(a=>a.href.includes('lc='+C)))||t.find(x=>/highlighted/i.test(x.innerText));"""


def tclick(find, **v):
    """find = JS returning the element (or a string error); real (trusted) click via the extension, else JS click."""
    out = page('const e=(()=>{%s})();if(!e||typeof e=="string")return "ERR "+(e||"not found");e.scrollIntoView({block:"center"});'
               'if(!XIN){e.click();return "JS"}const r=e.getBoundingClientRect();return JSON.stringify([r.x+r.width/2,r.y+r.height/2])' % find, XIN=xin(), **v)
    if out.startswith('['):
        pump()
        x_click(*json.loads(out))
        return 'ok'
    return 'ok' if out == 'JS' else out


def yt(a):
    """b yt pin VIDEO_ID COMMENT_ID : open the video with the comment highlighted and pin it."""
    if len(a) < 4 or a[1] != 'pin':
        sys.exit('usage: b yt pin VIDEO_ID COMMENT_ID')
    vid, cid = a[2], a[3]
    main(['go', 'https://www.youtube.com/watch?v=%s&lc=%s' % (vid, cid)])
    end = time.time() + 40
    while time.time() < end:
        js('(()=>{const c=document.querySelector("ytd-comments#comments,#comments");if(c)c.scrollIntoView();return 1})()')
        pump()
        if page(YT_THREAD + 'return m?1:0', C=cid) == '1':
            break
        time.sleep(1)
    else:
        sys.exit('comment %s did not load (comments off, wrong id, or not your channel)' % cid)
    if page(YT_THREAD + 'return /pinned by/i.test(m.innerText)?1:0', C=cid) == '1':
        print('already pinned')
        return
    r = tclick(YT_THREAD + "return m&&(m.querySelector('#action-menu button,button[aria-label=\"Action menu\"]')||'no action menu (only the channel owner can pin)')", C=cid)
    if r != 'ok':
        sys.exit(r)
    item = None
    for _ in range(12):
        pump()
        time.sleep(0.4)
        r = tclick("""const i=[...document.querySelectorAll('tp-yt-paper-item,[role=menuitem],ytd-menu-service-item-renderer')].filter(x=>vis(x)&&/^pin$/i.test(T(x.innerText)));return i.sort((a,b)=>a.contains(b)?1:b.contains(a)?-1:0)[0]""")
        if r == 'ok':
            item = True
            break
    if not item:
        sys.exit('menu opened but no "Pin" item (b t 400)')
    for _ in range(16):
        pump()
        time.sleep(0.5)
        r = tclick("""const d=[...document.querySelectorAll('yt-confirm-dialog-renderer,tp-yt-paper-dialog,[role=dialog]')].filter(vis).pop();if(!d)return '';
return [...d.querySelectorAll('button,[role=button]')].filter(x=>vis(x)&&/^pin$/i.test(T(x.innerText||x.getAttribute('aria-label')))).pop()||''""")
        if r == 'ok':
            break
    else:
        sys.exit('clicked Pin in the menu but no confirm dialog showed up')
    for _ in range(20):
        pump()
        time.sleep(0.6)
        if js('/pinned by/i.test(document.querySelector("ytd-comments")?.innerText||"")') == 'true':
            print('pinned %s on %s' % (cid, vid))
            return
    print('confirmed Pin; "Pinned by" not visible yet (reload the video to check)')


def ext_cmd(m):
    if m == 'install':
        xid = open(os.path.join(HERE, 'ext', 'ID')).read().strip()
        for name, d in (('chrome', '~/Library/Application Support/Google/Chrome'), ('brave', '~/Library/Application Support/BraveSoftware/Brave-Browser')):
            d = os.path.expanduser(d)
            if not os.path.isdir(d):
                continue
            sh = os.path.join(HERE, 'host-%s.sh' % name)
            open(sh, 'w').write('#!/bin/sh\nexec /usr/bin/python3 "%s" %s "$@"\n' % (os.path.join(HERE, 'host.py'), name))
            os.chmod(sh, 0o755)
            os.makedirs(os.path.join(d, 'NativeMessagingHosts'), exist_ok=True)
            json.dump({'name': 'com.ghosttab.bridge', 'description': 'GhostTab bridge', 'path': sh, 'type': 'stdio',
                       'allowed_origins': ['chrome-extension://%s/' % xid]},
                      open(os.path.join(d, 'NativeMessagingHosts', 'com.ghosttab.bridge.json'), 'w'), indent=1)
            print('%s: native host registered' % name)
        print('Now in each browser: open chrome://extensions (brave://extensions), turn on Developer mode, Load unpacked -> %s\n'
              'Then: b ext status, b bg close, b bg on' % os.path.join(HERE, 'ext'))
        return
    if m == 'reload':
        print(ext('reload', timeout=3))
        return
    try:
        print('extension connected (%s)' % ext('ping', timeout=3))
    except (ExtDown, RuntimeError) as e:
        print('extension not connected: %s' % (e or 'no socket at ' + SOCK))


def pump():
    """Force one rendered frame in the hidden tab (screenshot) so lazy-loaded content appears."""
    if xbg():
        try:
            ext('shot', timeout=10)
        except (ExtDown, RuntimeError):
            pass


def js_until(cond, sec):
    end = time.time() + sec
    while time.time() < end:
        pump()
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
    global TIMEOUT
    if c in ('click', 'rclick') and 'B_TIMEOUT' not in os.environ:
        TIMEOUT = 90
    FLAGS['FIN_OK'] = '--final' in a
    FLAGS['FORCE'] = '--force' in a
    front = '--front' in a or os.environ.get('B_FRONT')
    a = [x for x in a if x not in ('--final', '--force', '--front')]
    if not bgwin() and not front and c in ACTS - {'bg', 'js'} | {'li', 'gpt', 'yt', 'save'} and a[1:2] != ['mine']:
        sys.exit('bg mode is off, so this would act on the tab the user is looking at. Run b bg on first '
                 '(or add --front only if the user asked you to use their visible tab)')
    run(c, a)
    if c not in ('log', 'bg', 'tabs', 'li', 'close') and not bgwin():
        front_mark()


def run(c, a):
    if c in REST and len(a) > 3:
        a = a[:2] + [' '.join(a[2:])]
    if c == 'fb':
        with open(FEEDBACK, 'a') as fh:
            fh.write('%s | %s | %s\n' % (time.strftime('%Y-%m-%d %H:%M'), os.path.basename(os.getcwd()), ' '.join(a[1:])))
        print('thanks, noted for the GhostTab maintainer')
        return
    if c == 'stats':
        try:
            L = [l.rstrip('\n').split('\t') for l in open(STATS)][-2000:]
        except OSError:
            L = []
        agg = {}
        for l in L:
            if len(l) < 5:
                continue
            k = l[3].split(' ')[0]
            d = agg.setdefault(k, [0, 0, 0])
            d[0] += 1
            d[1] += int(l[2])
            d[2] += bool(l[4])
        print('cmd calls avg_ms errors')
        for k, (n, ms, e) in sorted(agg.items(), key=lambda x: -x[1][1]):
            print('%s %d %d %d' % (k, n, ms // n, e))
        errs = [l for l in L if len(l) > 4 and l[4]][-15:]
        if errs:
            print('\nrecent errors:\n' + '\n'.join('%s %s: %s' % (l[0], l[3][:50], l[4][:100]) for l in errs))
        return
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
    if xbg() and c in ('tabs', 'tab', 'open', 'close'):
        if c == 'open':
            ext('newtab', url=a[1] if '://' in a[1] else 'https://' + a[1])
            time.sleep(0.5)
            js_until('document.readyState!="loading"&&location.href!="about:blank"', 20)
        try:
            out = ext({'tabs': 'tabs', 'tab': 'tab', 'open': 'tabs', 'close': 'closetab'}[c], **({'i': int(a[1])} if c == 'tab' else {})) if c != 'open' else 'ok'
        except RuntimeError as e:
            out = str(e)
        print(out)
    elif bgwin() and c in ('open', 'go', 'back', 'reload'):
        bg_nav(c, a[1] if len(a) > 1 else '')
    elif bgwin() and c in ('tab', 'close', 'front'):
        sys.exit('%s not available in bg mode (single hidden tab); use go' % c)
    elif c == 'close' and a[1:2] == ['mine']:
        try:
            ids = open(MINE).read().split()
        except OSError:
            ids = []
        print(osa('closeids', *ids, wid='') if ids else 'no tabs opened by b')
        if os.path.exists(MINE):
            os.remove(MINE)
    elif c in ('tabs', 'tab', 'open', 'go', 'back', 'reload', 'close', 'front'):
        out = osa(*a)
        if c == 'open':
            kind, _, tid = out.partition(' ')
            if kind == 'new':
                open(MINE, 'a').write(tid + '\n')
            out = 'ok (already open: switched to it)' if kind == 'existing' else 'ok'
        if c in ('open', 'go') and not out.startswith('ok (already'):
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
let t;try{t=itext(r)}finally{hid.forEach(e=>e.style.display=e.__d)}return (R?'[dialog only; b %s all = page]\n':'')+t.replace(/\n{3,}/g,"\n\n").slice(%s)''' % (c, sl),
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
            'click': FINAL + ';' + SIG + 'e.scrollIntoView({block:"center"});e.click();return "clicked: "+lab(e).slice(0,60)+(FIN?" |FIN| "+FIN:"")',
            'hover': 'e.scrollIntoView({block:"center"});["pointerover","mouseover","mouseenter","pointermove","mousemove"].forEach(t=>e.dispatchEvent(new MouseEvent(t,{bubbles:true})));return "hovered: "+lab(e).slice(0,60)',
            'fill': '''const v=%s;if(!e.matches(FIELD)&&!e.isContentEditable){const c=ctlOf(e);if(c)e=c}if(!(e.matches('input,textarea')&&!isBox(e)&&e.type!='file')&&!e.isContentEditable)return "not a text field: "+e.tagName.toLowerCase()+" "+lab(e).slice(0,50)+" (use b form for field numbers)";if(e.readOnly||e.disabled)return "field is read-only/disabled: "+flab(e).slice(0,50);if(e.matches('input[aria-autocomplete=list],[class*=select__input] input,input[class*=select__input]'))return "USEPICK";e.focus();
if(e.isContentEditable){document.execCommand("selectAll");
const dt=new DataTransfer();dt.setData("text/plain",v);dt.setData("text/html",v.split("\\n").map(l=>"<p>"+(l.replace(/&/g,"&amp;").replace(/</g,"&lt;")||"<br>")+"</p>").join(""));
const pe=new ClipboardEvent("paste",{clipboardData:dt,bubbles:true,cancelable:true,composed:true});e.dispatchEvent(pe);
if(!pe.defaultPrevented){const L=v.split("\\n");L.forEach((l,i)=>{if(l)document.execCommand("insertText",false,l);if(i<L.length-1)document.execCommand("insertParagraph")})}}
else{const p=e.tagName=="TEXTAREA"?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;Object.getOwnPropertyDescriptor(p,"value").set.call(e,v);
e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}))}
const fv=e.isContentEditable?null:e.value;return "filled "+e.tagName.toLowerCase()+" \\""+flab(e).slice(0,40)+"\\" ("+v.length+" chars)"+(fv!==null&&fv!==v?" → now "+JSON.stringify(fv.slice(0,60)):"")''' % v,
            'select': '''const v=%s;if(e.tagName=="LABEL"&&e.control)e=e.control;if(!e.options)return "not a <select>; for comboboxes use pick, else click to open then click the option";
const o=[...e.options].find(o=>o.text.trim().toLowerCase()==v.toLowerCase())||[...e.options].find(o=>o.text.trim().toLowerCase().includes(v.toLowerCase()));
if(!o)return "no option; have: "+[...e.options].map(o=>o.text.trim()).join(", ");e.value=o.value;e.dispatchEvent(new Event("input",{bubbles:true}));e.dispatchEvent(new Event("change",{bubbles:true}));return "selected "+o.text.trim()+" in \\""+flab(e).slice(0,40)+"\\""''' % v,
            'check': '''const v=%s;if(!isBoxy(e)){const l=e.closest('label');e=(l&&l.control)||(e.tagName=="LABEL"&&e.control)||ctlOf(e)||e.closest('[role=checkbox]')||e}
if(!isBoxy(e))return "not a checkbox: "+lab(e).slice(0,50);const st=()=>e.tagName=="INPUT"?e.checked:e.getAttribute("aria-checked")=="true";
const want=v?/^(on|true|yes|1|x)$/i.test(v):!st();if(st()!==want)e.click();
if(st()!==want&&e.tagName=="INPUT"){Object.getOwnPropertyDescriptor(HTMLInputElement.prototype,"checked").set.call(e,want);["click","input","change"].forEach(t=>e.dispatchEvent(new Event(t,{bubbles:true})))}
return (st()===want?"checked=":"NOT changed, checked=")+st()+" ("+(ques(e)||lab(e)).slice(0,50)+")"''' % v,
            'enter': '''e.focus();["keydown","keypress","keyup"].forEach(t=>e.dispatchEvent(new KeyboardEvent(t,{key:"Enter",code:"Enter",keyCode:13,which:13,bubbles:true})));
if(e.form&&e.form.requestSubmit)e.form.requestSubmit();return "enter pressed"''',
        }[c]
        out = fin_log(target(a[1], body, **(FLAGS if c == 'click' else {})))
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
        x, y = point(a[1], final=True)
        (x_click if xin() else real_click)(x, y, int(a[2]) if len(a) > 2 else 1)
        fin_log(' |FIN| ' + PENDING[0] if PENDING[0] else '')
        print('real click at %d,%d' % (x, y))
    elif c == 'type':
        x, y = point(a[1])
        if xin():
            x_click(x, y)
            x_key('cmd+a')
            ext('type', text=a[2])
        else:
            real_click(x, y)
            time.sleep(0.2)
            key('cmd+a')
            paste(a[2])
        print('typed %d chars' % len(a[2]))
    elif c == 'key' and xin():
        if not xbg():
            front_check()
        for combo in a[1:]:
            x_key(combo)
        print('keys sent')
    elif c == 'key':
        no_bg('key')
        front_check()
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
            pump()
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
const t=D.filter(e=>!e.children.length&&T(e.innerText).toLowerCase().includes(n))[0];if(!t)return 'no saved file named "'+N+'" here (not at the resume/file step?) and no local file '+N;
const c=t.closest('label,button,[role=radio],[role=button],[role=option],li,[tabindex]')||t;c.click();return 'clicked '+T(c.innerText).slice(0,60)''', N=a[1]))
                return
        path = safe_path(a[2])
        if not os.path.exists(path):
            sys.exit('no such file: ' + path)
        t0 = time.time()
        if c == 'upload' and xbg():
            print('%s in %.1fs' % (x_upload('' if a[1] == '-' else a[1], path), time.time() - t0))
            return
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
    elif c == 'rupload' and xbg():
        path = safe_path(a[2])
        print(x_upload(a[1], path) if os.path.exists(path) else 'no such file: ' + path)
    elif c == 'rupload':
        no_bg('rupload')
        front_check()
        path = safe_path(a[2])
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
    elif c == 'save':
        print(save(a[1], a[2]))
    elif c == 'gpt':
        gpt(a)
    elif c == 'yt':
        yt(a)
    elif c == 'ext':
        ext_cmd(a[1] if len(a) > 1 else 'status')
    elif c == 'shot':
        path, _ = capture()
        subprocess.run(['sips', '-Z', '1200', path, '--out', '/tmp/b-shot.png'], capture_output=True)
        print('/tmp/b-shot.png')
    elif c == 'ocr':
        path, box = capture()
        geo = json.loads(js('JSON.stringify([outerWidth,outerHeight,innerWidth,innerHeight,devicePixelRatio])'))
        ow, oh, iw, ih, dpr = geo
        sc = float(backing())
        z = dpr / sc
        ox, oy = (ow - iw * z) / 2, oh - ih * z
        if box is None:
            # CDP screenshot: viewport only, in device pixels
            sc, z, ox, oy = dpr, 1, 0, 0
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
    elif c == 'rclickat' and xin():
        if not xbg():
            front_check()
        x_click(float(a[1]), float(a[2]))
        print('real click done')
    elif c == 'rclickat':
        no_bg('rclickat')
        front_check()
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
            where = 'win' if a[2:3] == ['hidden'] else 'tab'
            if bgwin() and not xbg():
                print('bg already on (window %s)' % bgwin())
                return
            if not os.environ.get('B_NOEXT') and os.path.exists(SOCK):
                try:
                    ext('ping', timeout=3)
                    try:
                        ext('place', where=where)
                    except RuntimeError:
                        where = 'win'  # extension older than 1.4
                    open(BGFILE, 'w').write('ext')
                    if os.path.exists(BGFILE + '.parked') and open(BGFILE + '.parked').read().strip() == 'ext':
                        os.remove(BGFILE + '.parked')
                    print('bg on: ' + ('agent tab in your window ("GhostTab" group, never made active; watch it any time)' if where == 'tab'
                                       else 'extension hidden minimized window') + '; real clicks, keys and uploads work')
                    return
                except (ExtDown, RuntimeError):
                    pass
            parked = BGFILE + '.parked'
            if os.path.exists(parked) and open(parked).read().strip() == 'ext':
                os.remove(parked)
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
                    w = open(f).read().strip()
                    try:
                        ext('closeghost') if w == 'ext' else osa('closewin', wid=w)
                    except (ExtDown, RuntimeError):
                        pass
                    if w != 'ext':  # ext mode is shared by all sessions; close only removed this session's tabs
                        os.remove(f)
            print('agent tabs closed' if xbg() else 'hidden window closed')
        else:
            if xbg():
                try:
                    w = ext('place', timeout=3)
                except (ExtDown, RuntimeError):
                    w = 'win'
                print('bg on (' + ('agent tab in your window' if w == 'tab' else 'extension hidden window') + ')')
                return
            print((''if xbg() else 'bg on (window %s)' % bgwin()) if bgwin() else 'bg off')
    else:
        sys.exit('unknown command ' + c + '\n' + USAGE)


STATS = os.path.join(HERE, 'stats.log')
FEEDBACK = os.path.join(HERE, 'feedback.log')


def top():
    # every top-level call: duration and outcome, so slow or failing commands show up without anyone reporting them
    t0, err = time.time(), ''
    out = []
    w = sys.stdout.write
    sys.stdout.write = lambda x: (out.append(x) if len(out) < 50 else None, w(x))[1]
    try:
        main()
    except SystemExit as e:
        err = '' if e.code in (None, 0) else str(e.code)
        raise
    except Exception as e:
        err = '%s: %s' % (type(e).__name__, e)
        raise
    finally:
        o = ''.join(out)
        if not err and re.search(r'(?m)^(not found|REFUSED|ERR|no such|ambiguous|timeout|page did not|not a |NOT |no (Easy|saved|file|form|jobs|dialog)|== STUCK)', o):
            err = re.search(r'(?m)^(not found|REFUSED|ERR|no such|ambiguous|timeout|page did not|not a |NOT |no (Easy|saved|file|form|jobs|dialog)|== STUCK).*', o).group(0)
        try:
            a = sys.argv[1:]
            with open(STATS, 'a') as fh:
                fh.write('%s\t%s\t%d\t%s\t%s\n' % (time.strftime('%m-%d %H:%M:%S'), 'brave' if 'Brave' in APP else 'chrome',
                                                     (time.time() - t0) * 1000, ' '.join(x[:40] for x in a)[:120], err.replace('\n', ' ')[:160]))
        except OSError:
            pass


if __name__ == '__main__':
    top()
