#!/bin/bash
# Round 23 restore-proof for ONE product in a group, per CLAUDE.md's hard rule.
#   bash scripts/apply/r23-proof.sh <handle>
# apply one -> read the RENDERED page -> restore and compare md5 -> restore again (no-op)
# -> tamper so live matches NEITHER recorded state -> the restore must REFUSE.
# A refusal is three things: a non-zero exit, the guard's own message, and live unchanged.
set -euo pipefail
H="$1"; S="$(node -e "console.log(process.env.TMPDIR||'/tmp')")"
A=scripts/apply/r23-accordion.mjs
R=/private/tmp/claude-501/-Users-convertcoldmedia-Desktop-Claude-Master-InHouseWellness-inh-seo/558694a6-2cd1-4a58-b983-ebc2bb925214/scratchpad
fail() { echo "PROOF FAILED: $1"; exit 1; }

echo "=== $H ==="
echo "--- 0. the injections must LAND and be REFUSED, each by its own guard ---"
set +e
O=$(node $A --only "$H" --inject-stray 2>&1); E=$?; set -e
[ $E -ne 0 ] || fail "stray injection was ACCEPTED"
echo "$O" | grep -q "TEXT OUTSIDE THE EDITED REGION CHANGED" || fail "stray injection refused for the wrong reason"
set +e
O=$(node $A --only "$H" --inject-link 2>&1); E=$?; set -e
[ $E -ne 0 ] || fail "empty-anchor injection was ACCEPTED"
echo "$O" | grep -q "LINK SET CHANGED" || fail "link injection refused for the wrong reason"
echo "$O" | grep -q "TEXT OUTSIDE" && fail "the link proof is not isolated — the text guard caught it too"
echo "  both injections landed and were refused, each by its own guard"

echo "--- 1. RENDERED before ---"
node $R/rendered.mjs "$H" > "$R/$H.before.txt" || fail "could not read the rendered page BEFORE"

echo "--- 2. apply to this one product ---"
node $A --only "$H" --apply || fail "apply failed"
B=$(ls -t data/backups/*/r23-accordion-"$H"*.json 2>/dev/null | head -1)
[ -n "$B" ] || fail "no backup written"
echo "  backup $B"

echo "--- 3. RENDERED after ---"
sleep 4
node $R/rendered.mjs "$H" > "$R/$H.after.txt" || fail "could not read the rendered page AFTER"
diff -q "$R/$H.before.txt" "$R/$H.after.txt" >/dev/null && fail "the RENDERED page did not change — the write did not reach the customer"
echo "  rendered output changed"

echo "--- 4. restore, comparing the read-back md5 to the recorded before-state ---"
node $A --restore "$B" --only "$H" --apply | tee "$R/$H.restore.txt"
grep -q "RESTORED" "$R/$H.restore.txt" || fail "restore did not confirm against the before-state"

echo "--- 5. restore again: must be a no-op ---"
node $A --restore "$B" --only "$H" --apply | grep -q "already restored" || fail "the second restore was not a no-op"
echo "  idempotent"

echo "--- 6. tamper: live now matches NEITHER recorded state. The restore must REFUSE ---"
node -e '
 const fs=require("fs"); const f=process.argv[1]; const j=JSON.parse(fs.readFileSync(f,"utf8"));
 j.forEach(s=>{ s.md5="0".repeat(32); s.storedMd5="1".repeat(32); });
 fs.writeFileSync(f.replace(/\.json$/,".TAMPERED.json"), JSON.stringify(j,null,2));' "$B"
T="${B%.json}.TAMPERED.json"
LIVE_BEFORE=$(node -e '
 import("./scripts/lib/shopify.js").then(async({gql})=>{const d=await gql(`query($h:String!){productByHandle(handle:$h){metafield(namespace:"custom",key:"shipping_details"){value}}}`,{h:process.argv[1]});
 console.log(require("crypto").createHash("md5").update(d.productByHandle.metafield.value).digest("hex"));})' "$H")
[ "$LIVE_BEFORE" != "00000000000000000000000000000000" ] || fail "tamper premise not asserted"
set +e
O=$(node $A --restore "$T" --only "$H" --apply 2>&1); E=$?; set -e
[ $E -ne 0 ] || fail "the tampered restore exited 0"
echo "$O" | grep -q "REFUSE" || fail "the tampered restore did not print its own refusal"
LIVE_AFTER=$(node -e '
 import("./scripts/lib/shopify.js").then(async({gql})=>{const d=await gql(`query($h:String!){productByHandle(handle:$h){metafield(namespace:"custom",key:"shipping_details"){value}}}`,{h:process.argv[1]});
 console.log(require("crypto").createHash("md5").update(d.productByHandle.metafield.value).digest("hex"));})' "$H")
[ "$LIVE_AFTER" = "$LIVE_BEFORE" ] || fail "live CHANGED during the refused restore"
rm "$T"
echo "  refused: exit $E, its own message, live unchanged ($LIVE_AFTER)"
echo "=== $H: PROVEN. Live is back at the before-state. ==="
