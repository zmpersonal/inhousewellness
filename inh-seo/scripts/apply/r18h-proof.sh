#!/usr/bin/env bash
# Restore-proof sequence for a product state change (CLAUDE.md hard rule), HALTING on any failure.
# Round 18h: the first version piped each step through grep, so a FAILED restore did not stop the
# chain, and a mis-designed tamper step then ran against the wrong live state and archived a live
# product. This version checks every exit code directly, and the tamper alters BOTH recorded states.
set -uo pipefail
H="$1"; CH="$2"; S=scripts/apply/r18h-sellout.mjs
step() { echo "=== $1 ==="; }
die() { echo "!!! HALT: $1"; exit 1; }
step "1. APPLY";   node $S --handle "$H" --channels "$CH" --apply || die "apply failed"
B="$(ls -td data/backups/*/ | head -1)r18h-$H.json"; [ -f "$B" ] || die "no backup at $B"
step "2. RESTORE"; node $S --restore "$B" --apply || die "restore did not return the before-state"
step "3. RESTORE AGAIN (must be a no-op)"; out=$(node $S --restore "$B" --apply) || die "second restore failed"; echo "$out" | tail -1; echo "$out" | grep -q "already restored" || die "second restore was not a no-op"
step "4. FAKED THIRD-PARTY CHANGE (must refuse)"
node -e "const fs=require('fs');const b=JSON.parse(fs.readFileSync('$B','utf8'));b.before={status:'ARCHIVED',policy:'CONTINUE',channels:['Point of Sale']};b.after={status:'ARCHIVED',policy:'DENY',channels:['Point of Sale']};fs.writeFileSync('/tmp/r18h-tamper.json',JSON.stringify(b));"
if node $S --restore /tmp/r18h-tamper.json --apply; then die "the guard ALLOWED a restore it should have refused"; else echo "   refused, as required"; fi
step "5. APPLY FOR REAL"; node $S --handle "$H" --channels "$CH" --apply || die "final apply failed"
echo "PROOF SEQUENCE COMPLETE"
