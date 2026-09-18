#!/usr/bin/env bash
# Restore-proof sequence for a product state change (CLAUDE.md hard rule), HALTING on any failure.
# Round 18h: the first version piped each step through grep, so a FAILED restore did not stop the
# chain, and a mis-designed tamper step then ran against the wrong live state and archived a live
# product. This version checks every exit code directly, and the tamper alters BOTH recorded states.
set -uo pipefail
H="$1"; CH="$2"; S="${SELLOUT:-scripts/apply/r18h-sellout.mjs}"   # SELLOUT/PROOF_BACKUP: guard-test overrides only
step() { echo "=== $1 ==="; }
die() { echo "!!! HALT: $1"; exit 1; }
step "1. APPLY";   node $S --handle "$H" --channels "$CH" --apply || die "apply failed"
B="${PROOF_BACKUP:-$(ls -td data/backups/*/ | head -1)r18h-$H.json}"; [ -f "$B" ] || die "no backup at $B"
step "2. RESTORE"; node $S --restore "$B" --apply || die "restore did not return the before-state"
step "3. RESTORE AGAIN (must be a no-op)"; out=$(node $S --restore "$B" --apply) || die "second restore failed"; echo "$out" | tail -1; echo "$out" | grep -q "already restored" || die "second restore was not a no-op"
step "4. FAKED THIRD-PARTY CHANGE (must refuse)"
node -e "const fs=require('fs');const b=JSON.parse(fs.readFileSync('$B','utf8'));b.before={status:'ARCHIVED',policy:'CONTINUE',channels:['Point of Sale']};b.after={status:'ARCHIVED',policy:'DENY',channels:['Point of Sale']};fs.writeFileSync('/tmp/r18h-tamper.json',JSON.stringify(b));"
# PREMISE (Round 18i): a refusal only proves something if live matches NEITHER recorded state. Assert it,
# rather than assume the steps above left live where we think they did.
LIVE=$(node $S --handle "$H" --state) || die "could not read live state"
node -e "const b=JSON.parse(require('fs').readFileSync('/tmp/r18h-tamper.json','utf8'));const l=process.argv[1];if(l===JSON.stringify(b.before)||l===JSON.stringify(b.after)){console.log('live '+l+' matches a recorded state');process.exit(1)}" "$LIVE" || die "tamper premise does not hold — a refusal here would prove nothing"
echo "   premise holds: live $LIVE matches neither recorded state"
# A refusal is three things, not one: non-zero exit, the REFUSE line, and live UNCHANGED. Round 18i: with the
# guard deleted, a restore that WROTE to the product and then failed its read-back also exited 1, and this step
# used to count that as "refused".
out4=$(node $S --restore /tmp/r18h-tamper.json --apply); rc4=$?; echo "$out4" | tail -1
[ $rc4 -ne 0 ] || die "the guard ALLOWED a restore it should have refused"
echo "$out4" | grep -q "REFUSE:" || die "exited $rc4 but NOT by refusing — something else failed, and it may have written"
AFTER4=$(node $S --handle "$H" --state) || die "could not re-read live state"
[ "$AFTER4" = "$LIVE" ] || die "live CHANGED during the refusal test: $LIVE -> $AFTER4"
echo "   refused, as required — and live unchanged"
step "5. APPLY FOR REAL"; node $S --handle "$H" --channels "$CH" --apply || die "final apply failed"
echo "PROOF SEQUENCE COMPLETE"
