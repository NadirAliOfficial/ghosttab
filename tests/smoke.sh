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
ok "$(b ocr 2>&1)" "minimized" ocr-blocked-in-bg
ok "$(b do 'f Name Nadir Ali ; e')" 'Name = "Nadir Ali"' batch
ok "$(b choose Authorized Yes)" "chosen: Authorized? → Yes" choose
ok "$(b form)" 'radio "Authorized?": .* Yes \[x\]' form
ok "$(b js 'throw new Error("x")')" "ERR: x" js-errors
ok "$(b until text clicked 3)" "ok" until
b bg off >/dev/null
rm -rf "$T"; exit ${FAIL:-0}
