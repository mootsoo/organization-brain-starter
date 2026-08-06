#!/usr/bin/env bash
# End-to-end smoke test for the Phase 1 workflow.
#
# Usage:
#   docker compose up --build -d
#   ./scripts/smoke.sh
#
# Optional:
#   RESTART_CHECK=1 ./scripts/smoke.sh   also proves data survives a restart
#
# Requires: bash, curl, python3. Prints one line per check and exits non-zero
# if any check failed.

set -u

API_URL="${API_URL:-http://localhost:8000}"
WEB_URL="${WEB_URL:-http://localhost:3000}"
TENDER_ID="${TENDER_ID:-1}"

pass_count=0
fail_count=0

ok() {
  printf 'PASS  %s\n' "$1"
  pass_count=$((pass_count + 1))
}

bad() {
  printf 'FAIL  %s\n' "$1"
  fail_count=$((fail_count + 1))
}

check() {
  # check "<description>" "<actual>" "<expected>"
  if [ "$2" = "$3" ]; then
    ok "$1"
  else
    bad "$1 (expected '$3', got '$2')"
  fi
}

json() {
  # json '<json document>' '<python expression over d>'
  printf '%s' "$1" | python3 -c "import json,sys; d=json.load(sys.stdin); print($2)"
}

status_of() {
  curl -s -o /dev/null -w '%{http_code}' "$@"
}

echo "== Organization Brain Starter - Phase 1 smoke test =="
echo "API: $API_URL"
echo "Web: $WEB_URL"
echo

# 1. Web dashboard -----------------------------------------------------------
check "1. dashboard responds" "$(status_of "$WEB_URL/")" "200"
dashboard=$(curl -s "$WEB_URL/")
case "$dashboard" in
  *"AI шийдвэр гаргахгүй"*) ok "1b. dashboard shows the core message" ;;
  *) bad "1b. dashboard shows the core message" ;;
esac

# 2. API health --------------------------------------------------------------
health=$(curl -s "$API_URL/health")
check "2. health status" "$(json "$health" 'd["status"]')" "ok"
check "2b. mock provider active" "$(json "$health" 'd["ai_provider"]')" "mock"

# 3. Tender appears ----------------------------------------------------------
overview=$(curl -s "$API_URL/api/v1/overview")
check "3. sample tender listed" \
  "$(json "$overview" '"yes" if any(t["id"]=='"$TENDER_ID"' for t in d["tenders"]) else "no"')" "yes"

# 4. Tender detail -----------------------------------------------------------
check "4. tender detail page responds" "$(status_of "$WEB_URL/tenders/$TENDER_ID")" "200"
detail=$(curl -s "$API_URL/api/v1/tenders/$TENDER_ID")
stage_before=$(json "$detail" 'd["tender"]["stage"]')

# 5. Bidder facts ------------------------------------------------------------
check "5. bidder facts present" \
  "$(json "$detail" '"yes" if len(d["submissions"])>0 and all("proposed_amount_mnt" in s for s in d["submissions"]) else "no"')" "yes"

# 6. Rule findings computed --------------------------------------------------
check "6. rule checks reported" "$(json "$detail" '"yes" if len(d["checks"])>0 else "no"')" "yes"
check "6b. rule findings produced" "$(json "$detail" '"yes" if len(d["findings"])>0 else "no"')" "yes"

# 7. Source references -------------------------------------------------------
check "7. every finding has a source reference" \
  "$(json "$detail" '"yes" if all(f.get("source_reference") for f in d["findings"]) else "no"')" "yes"

# 8. Mock AI draft -----------------------------------------------------------
draft=$(curl -s -X POST -H "X-Role: reviewer" "$API_URL/api/v1/tenders/$TENDER_ID/draft-summary")
decision_id=$(json "$draft" 'd["decision_id"]')
draft_text=$(json "$draft" 'd["summary_mn"]')
check "8. mock AI draft generated" "$(json "$draft" 'd["provider"]')" "mock"

# 8b. Data minimization: the draft cannot quote an internal pointer -----------
# `source_reference` is never sent to the provider, so it cannot come back.
case "$draft_text" in
  *"tender_submissions #"*)  bad "8b. AI draft quotes no internal row pointer" ;;
  *"Материалын хавтас №"*)   bad "8b. AI draft quotes no internal row pointer" ;;
  *) ok "8b. AI draft quotes no internal row pointer" ;;
esac

# 9. Draft is not an official decision ---------------------------------------
check "9. draft is not official" "$(json "$draft" 'str(d["official"])')" "False"
after_draft=$(curl -s "$API_URL/api/v1/tenders/$TENDER_ID")
check "9b. draft did not change the stage" \
  "$(json "$after_draft" 'd["tender"]["stage"]')" "$stage_before"

# 10. Unauthorized actions ---------------------------------------------------
body="{\"decision_id\": $decision_id, \"approved_by\": \"Жишээ хянагч\"}"
check "10. viewer cannot generate a draft" \
  "$(status_of -X POST -H 'X-Role: viewer' "$API_URL/api/v1/tenders/$TENDER_ID/draft-summary")" "403"
check "10b. reviewer cannot approve" \
  "$(status_of -X POST -H 'Content-Type: application/json' -H 'X-Role: reviewer' -d "$body" "$API_URL/api/v1/tenders/$TENDER_ID/approve")" "403"
check "10c. missing role cannot approve" \
  "$(status_of -X POST -H 'Content-Type: application/json' -d "$body" "$API_URL/api/v1/tenders/$TENDER_ID/approve")" "403"

# 11. Authorized approval ----------------------------------------------------
approval=$(curl -s -X POST -H 'Content-Type: application/json' -H 'X-Role: approver' \
  -d "$body" "$API_URL/api/v1/tenders/$TENDER_ID/approve")
check "11. approver can approve" "$(json "$approval" 'd["decision"]["status"]')" "approved"

# 12. Only the intended state changed ----------------------------------------
after_approval=$(curl -s "$API_URL/api/v1/tenders/$TENDER_ID")
check "12. tender stage is now approved" \
  "$(json "$after_approval" 'd["tender"]["stage"]')" "approved"
stored_text=$(printf '%s' "$after_approval" | DECISION_ID="$decision_id" python3 -c \
  'import json,os,sys; d=json.load(sys.stdin); print([x for x in d["decisions"] if x["id"]==int(os.environ["DECISION_ID"])][0]["content_mn"])')
check "12b. approval did not rewrite the AI draft text" "$stored_text" "$draft_text"
check "12c. approving twice is refused" \
  "$(status_of -X POST -H 'Content-Type: application/json' -H 'X-Role: approver' -d "$body" "$API_URL/api/v1/tenders/$TENDER_ID/approve")" "409"

# 13, 14, 15. Audit trail ----------------------------------------------------
audit=$(curl -s "$API_URL/api/v1/tenders/$TENDER_ID/audit")
check "13. approval recorded in the audit trail" \
  "$(json "$audit" '"yes" if any(e["event_type"]=="human_approval_recorded" for e in d["audit_events"]) else "no"')" "yes"
check "13b. exactly one approval event for this decision" \
  "$(printf '%s' "$audit" | DECISION_ID="$decision_id" python3 -c \
    'import json,os,sys; d=json.load(sys.stdin); t="decision:"+os.environ["DECISION_ID"]; print(sum(1 for e in d["audit_events"] if e["event_type"]=="human_approval_recorded" and e["target"]==t))')" "1"
check "14. AI generation recorded in the audit trail" \
  "$(json "$audit" '"yes" if any(e["event_type"]=="ai_draft_generated" for e in d["audit_events"]) else "no"')" "yes"
check "15. audit records are understandable" \
  "$(json "$audit" '"yes" if all(e.get("label_mn") and e.get("actor") and e.get("created_at") for e in d["audit_events"]) else "no"')" "yes"

# 16. Persistence ------------------------------------------------------------
if [ "${RESTART_CHECK:-0}" = "1" ]; then
  echo "-- restarting the stack, keeping the data volume --"
  docker compose down >/dev/null 2>&1
  docker compose up -d >/dev/null 2>&1
  for _ in $(seq 1 60); do
    if [ "$(status_of "$API_URL/health")" = "200" ]; then break; fi
    sleep 2
  done
  after_restart=$(curl -s "$API_URL/api/v1/tenders/$TENDER_ID")
  check "16. approved decision survived a restart" \
    "$(json "$after_restart" '"yes" if any(x["id"]=='"$decision_id"' and x["status"]=="approved" for x in d["decisions"]) else "no"')" "yes"
else
  echo "SKIP  16. restart persistence (set RESTART_CHECK=1 to include)"
fi

echo
echo "passed: $pass_count   failed: $fail_count"
[ "$fail_count" -eq 0 ]
