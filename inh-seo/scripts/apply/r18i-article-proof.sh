#!/usr/bin/env bash
# Restore-proof sequence for an ARTICLE edit (CLAUDE.md hard rule), HALTING on any failure. Round 18i.
#   scripts/apply/r18i-article-proof.sh <edit-script.mjs> <label> <one-real-handle>
# The earlier article proofs were `&&` chains ending `; echo exit $?` — the refusal step printed its exit code for a
# reader to judge. Here every step is asserted: an injection must LAND and be REFUSED by message; a refusal must be
# non-zero AND say REFUSE AND leave live unchanged; the tamper premise (live matches neither recorded state) is
# checked before the refusal is believed.
set -uo pipefail
E="$1"; LABEL="$2"; H="$3"
R="${RESTORE:-scripts/apply/r18-restore.mjs}"          # RESTORE / PROOF_BACKUP_DIR: guard-test overrides only
die() { echo "!!! HALT: $1"; exit 1; }
step() { echo "=== $1 ==="; }
latest() { if [ -n "${PROOF_BACKUP_DIR:-}" ]; then echo "$PROOF_BACKUP_DIR/$LABEL.json"; else echo "$(ls -td data/backups/*/ | head -1)$LABEL.json"; fi; }
for k in --inject-stray --inject-link; do
  step "0. $k (must land and be REFUSED)"
  out=$(node "$E" --only "$H" $k 2>&1); rc=$?
  echo "$out" | grep -qE "did not land" && die "$k did not land — the test would be vacuous"
  [ $rc -ne 0 ] || die "$k was NOT refused"
  echo "$out" | grep -qE "TEXT OUTSIDE|LINK MULTISET" || die "$k exited $rc but not by a proof refusing: $(echo "$out" | tail -1)"
  echo "   refused by: $(echo "$out" | grep -oE 'TEXT OUTSIDE[^\n]*|LINK MULTISET[^\n]*' | head -1)"
done
step "1. APPLY one real target ($H)"; node "$E" --only "$H" --apply || die "apply failed"
B="$(latest)"; [ -f "$B" ] || die "no backup at $B"
step "2. RESTORE"; out=$(node "$R" "$B" --apply) || die "restore failed: $out"; echo "$out" | grep -q "== before-state" || die "restore did not report == before-state"; echo "$out" | grep RESTORED
step "3. RESTORE AGAIN (must be a no-op)"; out=$(node "$R" "$B" --apply) || die "second restore failed"; echo "$out" | grep -q "already restored" || die "not a no-op"; echo "$out" | grep -q RESTORED && die "second restore WROTE"
echo "   no-op"
step "4. FAKED THIRD-PARTY EDIT (must refuse)"
node -e "const fs=require('fs');const s=JSON.parse(fs.readFileSync('$B','utf8'));for(const x of s){x.md5='0'.repeat(32);x.storedMd5='f'.repeat(32);x.afterMd5='e'.repeat(32)}fs.writeFileSync('/tmp/r18i-tamper.json',JSON.stringify(s))"
node "$R" /tmp/r18i-tamper.json --premise || die "tamper premise does not hold — a refusal would prove nothing"
before4=$(node "$R" "$B" --premise 2>&1 | grep -oE 'live [0-9a-f]{32}' | sort | tr '\n' ' ')
out=$(node "$R" /tmp/r18i-tamper.json --apply); rc=$?
[ $rc -ne 0 ] || die "the guard ALLOWED a restore it should have refused"
echo "$out" | grep -q "REFUSE" || die "exited $rc but not by refusing — it may have written"
after4=$(node "$R" "$B" --premise 2>&1 | grep -oE 'live [0-9a-f]{32}' | sort | tr '\n' ' ')
[ "$before4" = "$after4" ] || die "live CHANGED during the refusal test"
echo "   refused, and live unchanged"
step "5. APPLY FOR REAL (full set)"; node "$E" --apply || die "full apply failed"
echo "PROOF SEQUENCE COMPLETE — backup: $(latest)"
