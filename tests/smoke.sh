#!/bin/bash
# End-to-end check in a background window. BROWSER=brave to test Brave. Needs Apple Events JS enabled.
set -e
T=$(mktemp -d); echo hello > "$T/a.txt"; mkfile -n 5m "$T/v.mp4"
ok() { grep -q "$2" <<<"$1" && echo "PASS $3" || { echo "FAIL $3: $1"; FAIL=1; }; }
b bg on >/dev/null
b go 'data:text/html,<input id=n placeholder=Name><select id=s><option>Red</option><option>Blue</option></select><input type=file id=f hidden><button onclick="o.textContent+=`clicked `">Go</button><div id=z style="width:200px;height:80px">Drop</div><fieldset><legend>Authorized?</legend><input type=radio name=a id=r1><label for=r1></label><span>Yes</span><input type=radio name=a id=r2><label for=r2></label><span>No</span></fieldset><canvas id=c width=400 height=60></canvas><p id=o></p><script>f.onchange=()=>o.textContent+="file:"+f.files[0].name+" ";z.ondragover=e=>e.preventDefault();z.ondrop=e=>{e.preventDefault();o.textContent+="drop:"+e.dataTransfer.files[0].size+" "};c.getContext("2d").font="28px Arial";c.getContext("2d").fillText("Canvas 4250",10,40)</script>' >/dev/null
ok "$(b el)" "input:text Name" el
ok "$(b fill Name Nadir)" "filled" fill
ok "$(b select 1 blue)" "selected Blue" select
ok "$(b c Go)" "clicked" click
ok "$(b up - "$T/a.txt")" "attached a.txt" upload
ok "$(b drop Drop "$T/v.mp4")" "dropped v.mp4" drop
ok "$(b x 0 400)" "clicked file:a.txt drop:5242880" page-state
ok "$(b ocr 2>&1)" "minimized\|Canvas 4250" ocr-in-bg
ok "$(b do 'f Name Nadir Ali ; e')" 'Name = "Nadir Ali"' batch
ok "$(b choose Authorized Yes)" "chosen: Authorized? → Yes" choose
ok "$(b form)" 'radio "Authorized?": .* Yes \[x\]' form
ok "$(b js 'throw new Error("x")')" "ERR: x" js-errors
ok "$(b until text clicked 3)" "ok" until
b go 'data:text/html,<div role=dialog aria-modal=true style="width:400px;height:300px"><h3>Questions</h3><div><p>Asset classes?</p><div><div><div><input type=radio name=q id=r_1 aria-label="Asset classes?" style="opacity:0;width:0;height:0"></div></div><p>Yes</p></div><div><div><div><input type=radio name=q id=r_2 aria-label="Asset classes?" style="opacity:0;width:0;height:0"></div></div><p>No</p></div></div><select id=cc><option>Pakistan (+92)</option><option>Poland (+48)</option></select><button>Submit application</button></div>' >/dev/null
ok "$(b choose "asset classes" No)" "chosen: Asset classes? → No" li-radio
ok "$(b form)" 'radio "Asset classes?": 0 Yes | 1 No \[x\]' li-radio-form
ok "$(b x)" "\[Pakistan (+92) ▾\]" select-collapsed
ok "$(b js '$dlg.querySelectorAll("input")')" "2 elements" js-dlg
ok "$(b c Submit)" "REFUSED" final-fuzzy
b js 'document.querySelector("h3").textContent="Other";1' >/dev/null
ok "$(b c 'Submit application')" "dialog changed" final-stale
b go 'data:text/html,<dialog open style="width:300px;height:150px"><h2 style="position:absolute;width:1px;height:1px;overflow:hidden">0 notifications</h2>You reached today limit<button>Got it</button></dialog>' >/dev/null
ok "$(b el)" "Got it" dlg-srheading
b go 'data:text/html,<input id=t placeholder=Tags><p id=o></p><script>t.onkeydown=e=>{if(e.key=="Enter"){o.textContent+="["+t.value+"]";t.value=""}}</script>' >/dev/null
ok "$(b tags Tags 'ai, python,go' >/dev/null; b x 0 100)" "\[ai\]\[python\]\[go\]" tags
b go 'data:text/html,<p>You applied for one seat only per family.</p><form><input name=a placeholder=Name></form><button onclick="o.textContent=`sent`">Submit</button><p id=o></p>' >/dev/null
ok "$(b c Submit --final)" "clicked" status-intro-text
b go 'data:text/html,<div role=dialog id=d style="width:300px;height:200px"><h2>Apply</h2><input id=dt placeholder=Date onclick="cal.hidden=false" onfocus="cal.hidden=false"><div id=cal class=datepicker hidden>calendar</div></div><p id=o></p><script>document.addEventListener("keydown",e=>{if(e.key=="Escape")d.remove()});document.addEventListener("mousedown",e=>{if(!cal.contains(e.target)&&e.target!=dt)cal.hidden=true})</script>' >/dev/null
b c Date >/dev/null
ok "$(b key esc; b js 'document.getElementById("d")?(cal.hidden?"kept-closed":"kept-open"):"gone"')" "kept-closed" esc-popup-in-dialog
b go 'data:text/html,<div role=dialog style="width:400px;height:300px"><h3>Review your application</h3><div><input type=file id=f1 hidden><label for=f1>Upload cover letter</label><input type=file id=f2 hidden><label for=f2>Upload resume</label></div><div><input type=radio name=cv id=a><label for=a><span>Old_CV.pdf</span></label></div><div><input type=radio name=cv id=b2 checked><label for=b2><span>Python_CV.pdf</span></label></div><p id=o></p><script>f1.onchange=()=>o.textContent+="cover ";f2.onchange=()=>o.textContent+="resume "</script></div>' >/dev/null
ok "$(b li review)" "CV: Python_CV.pdf$" li-review-selected-cv
ok "$(b up 'Upload resume' "$T/a.txt" >/dev/null; b js 'o.textContent')" "^resume $" upload-label-for
rm -rf "$T"; exit ${FAIL:-0}
