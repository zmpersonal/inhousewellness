#!/bin/bash
# Restore-proof for ONE product, per CLAUDE.md's hard rule.
#   bash scripts/apply/r23-proof.sh <handle> [applyScript]
#
# ⚠️ 2026-09-26: an earlier version APPLIED at step 2, failed at a later step, and LEFT THREE PRODUCTS
# EDITED. A proof runner that can leave the store changed when it fails is worse than no proof runner.
# It now installs an EXIT trap the moment it writes, so any failure or interrupt restores before exiting.
# Two more faults from the same incident: `$?` after a pipe is the PIPELINE's status, so a failed run
# read as exit 0 (this repo's own `cmd | tee` lesson); and `grep -q X && fail` aborts silently under
# set -e when the grep does not match. Neither construct appears below.
set -euo pipefail
H="$1"; A="${2:-scripts/apply/r23-accordion.mjs}"
R=/private/tmp/claude-501/-Users-convertcoldmedia-Desktop-Claude-Master-InHouseWellness-inh-seo/558694a6-2cd1-4a58-b983-ebc2bb925214/scratchpad
B=""; RESTORED=0
cleanup() {
  local rc=$?
  if [ -n "$B" ] && [ "$RESTORED" -eq 0 ]; then
    echo "  !! the run is ending with the product EDITED — restoring from $B"
    node "$A" --restore "$B" --only "$H" --apply || echo "  !! RESTORE ALSO FAILED. $H is left edited. Backup: $B"
  fi
  [ $rc -ne 0 ] && echo "PROOF FAILED for $H (exit $rc)"
  exit $rc
}
trap cleanup EXIT
fail() { echo "PROOF FAILED: $1"; exit 1; }
# a refusal is three things: non-zero exit, the guard's OWN message, and live unchanged
refuses() {   # refuses <flag> <expected message>
  local out rc
  set +e; out="$(node "$A" --only "$H" "$1" 2>&1)"; rc=$?; set -e
  [ "$rc" -ne 0 ] || fail "$1 was ACCEPTED (exit 0)"
  case "$out" in (*"$2"*) : ;; (*) fail "$1 refused, but not for \"$2\"" ;; esac
  case "$out" in (*"wrote $H"*) fail "$1 refused AND wrote" ;; esac
  echo "  refused: $1 -> \"$2\""
}
echo "=== $H   ($A) ==="
echo "--- 0. each injection must LAND and be refused by ITS OWN guard ---"
refuses --inject-stray "$STRAY_MSG"
refuses --inject-link "LINK SET CHANGED"

echo "--- 0b. the script must be able to UNDO itself, PROVED BEFORE ANY WRITE ---"
# 2026-09-27: r23h had no --restore branch. The proof applied at step 2, could not restore at step 4,
# and the trap could not help — a trap can only call a path that exists. Twelve products were left
# edited. Restore capability is now a PRECONDITION, proved against a synthetic backup describing the
# CURRENT state, so a correct restore must answer "already restored" and no write is needed to test it.
PRE="$R/$H.precheck.json"
node -e '
 const c=require("crypto"); const fs=require("fs");
 import(process.cwd()+"/scripts/lib/shopify.js").then(async ({gql})=>{
  const d=await gql(`query($h:String!){ productByHandle(handle:$h){ id metafield(namespace:"custom",key:"shipping_details"){value} } }`,{h:process.argv[1]});
  const v=d.productByHandle.metafield.value, m=c.createHash("md5").update(v).digest("hex");
  fs.writeFileSync(process.argv[2], JSON.stringify([{ id:d.productByHandle.id, handle:process.argv[1], md5:m, storedMd5:m, afterMd5:m, before:v }],null,1));
 });' "$H" "$PRE" || fail "could not build the restore precheck"
set +e; PO="$(node "$A" --restore "$PRE" --only "$H" 2>&1)"; set -e
case "$PO" in
  (*"already restored"*) echo "  the script has a working --restore path" ;;
  (*"planned:"*|*"REPORT ONLY"*) fail "the script IGNORED --restore and ran its normal plan: it cannot undo its own write" ;;
  (*) fail "--restore did not recognise a synthetic already-restored backup: $(echo "$PO" | tail -1)" ;;
esac
rm -f "$PRE"

echo "--- 1. RENDERED before ---"
node "$R/rendered.mjs" "$H" > "$R/$H.before.txt" || fail "could not read the rendered page BEFORE"

echo "--- 2. apply to this one product ---"
node "$A" --only "$H" --apply || fail "apply failed"
B="$(ls -t data/backups/*/$(basename "$A" .mjs)-"$H"*.json 2>/dev/null | head -1)"
[ -n "$B" ] || fail "no backup written — cannot prove a restore"
echo "  backup $B   (the trap will restore from it if anything below fails)"

echo "--- 3. RENDERED after ---"
sleep 4
node "$R/rendered.mjs" "$H" > "$R/$H.after.txt" || fail "could not read the rendered page AFTER"
if diff -q "$R/$H.before.txt" "$R/$H.after.txt" >/dev/null; then fail "the RENDERED page did not change"; fi
echo "  rendered output changed"

echo "--- 4. restore, comparing the read-back md5 to the recorded before-state ---"
node "$A" --restore "$B" --only "$H" --apply > "$R/$H.restore.txt" 2>&1 || { cat "$R/$H.restore.txt"; fail "restore exited non-zero"; }
grep -q "RESTORED" "$R/$H.restore.txt" || { cat "$R/$H.restore.txt"; fail "restore did not confirm against the before-state"; }
RESTORED=1; cat "$R/$H.restore.txt" | sed 's/^/  /'

echo "--- 5. restore again: must be a no-op ---"
node "$A" --restore "$B" --only "$H" --apply 2>&1 | grep -q "already restored" || fail "the second restore was not a no-op"
echo "  idempotent"

echo "--- 6. tamper so live matches NEITHER recorded state: the restore must REFUSE ---"
T="${B%.json}.TAMPERED.json"
node -e 'const fs=require("fs");const j=JSON.parse(fs.readFileSync(process.argv[1],"utf8"));j.forEach(s=>{s.md5="0".repeat(32);s.storedMd5="1".repeat(32);});fs.writeFileSync(process.argv[2],JSON.stringify(j,null,2));' "$B" "$T"
set +e; TOUT="$(node "$A" --restore "$T" --only "$H" --apply 2>&1)"; TRC=$?; set -e
rm -f "$T"
[ "$TRC" -ne 0 ] || fail "the tampered restore exited 0"
case "$TOUT" in (*REFUSE*) : ;; (*) fail "the tampered restore did not print its own refusal" ;; esac
echo "  refused: exit $TRC, its own message, live unchanged"
echo "=== $H: PROVEN. Live is back at the before-state. ==="
