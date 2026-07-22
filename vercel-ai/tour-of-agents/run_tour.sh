#!/usr/bin/env bash
#
# Tour of Agents runner (Vercel AI SDK + Restate, TypeScript).
#
# Spins up each example service one at a time, registers it with an
# already-running Restate server, sends one or two requests through the
# ingress, then shuts the service down and moves to the next example.
#
# Human-in-the-loop examples are intentionally SKIPPED (they block on an
# awakeable waiting for a manual approval):
#   - human-approval-agent
#   - human-approval-agent-with-timeout
#   - sub-workflow-agent
#
# This script does NOT start or stop Restate itself — start Restate yourself
# first (Docker or `restate-server`) and keep the UI open; all invocations
# made here will show up there afterwards.
#
# Config via env vars:
#   RESTATE_ADMIN     admin API host:port      (default localhost:9070)
#   RESTATE_INGRESS   ingress host:port        (default localhost:8080)
#   SERVICE_PORT      port each example binds   (default 9080)
#   DEPLOYMENT_URI    override the endpoint URI Restate registers
#                     (default: auto-detect localhost vs host.docker.internal)
#   ONLY              space-separated list of example basenames to run
#                     e.g. ONLY="chat-agent multi-agent" ./run_tour.sh

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_DIR"

ADMIN=${RESTATE_ADMIN:-localhost:9070}
INGRESS=${RESTATE_INGRESS:-localhost:8080}
PORT=${SERVICE_PORT:-9080}
DEPLOYMENT_URI=${DEPLOYMENT_URI:-}
ONLY=${ONLY:-}

LOGDIR=$(mktemp -d)
SVC_PID=""
SVC_LOG=""

cleanup() {
  [ -z "$SVC_PID" ] && return 0
  pkill -KILL -P "$SVC_PID" 2>/dev/null
  kill -KILL "$SVC_PID" 2>/dev/null
}
trap cleanup EXIT INT TERM

# ---------------------------------------------------------------- preflight ---
if [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "✗ OPENAI_API_KEY is not set. Every example makes real LLM calls."
  echo "  export OPENAI_API_KEY=... and re-run."
  exit 1
fi

if ! curl -s -o /dev/null "http://$ADMIN/deployments"; then
  echo "✗ Cannot reach Restate admin API at $ADMIN."
  echo "  Start Restate first, e.g.:"
  echo "    restate-server"
  echo "  or via Docker (see README.md), then re-run this script."
  exit 1
fi
echo "✓ Restate admin reachable at $ADMIN"
echo

# ------------------------------------------------------------------ helpers ---
http_register() {
  # $1 = uri ; prints http status code, body -> $LOGDIR/reg.json
  curl -s -o "$LOGDIR/reg.json" -w '%{http_code}' \
    -H 'content-type: application/json' \
    -d "{\"uri\":\"$1\",\"force\":true}" \
    "http://$ADMIN/deployments"
}

register_deployment() {
  local code
  if [ -z "$DEPLOYMENT_URI" ]; then
    for cand in "http://localhost:$PORT" "http://host.docker.internal:$PORT"; do
      code=$(http_register "$cand")
      if [ "$code" = "200" ] || [ "$code" = "201" ]; then
        DEPLOYMENT_URI=$cand
        echo "  ✓ registered ($cand)"
        return 0
      fi
    done
    echo "  ✗ registration failed (tried localhost and host.docker.internal):"
    sed 's/^/    /' "$LOGDIR/reg.json"; echo
    return 1
  fi
  code=$(http_register "$DEPLOYMENT_URI")
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then
    echo "  ✓ registered ($DEPLOYMENT_URI)"
    return 0
  fi
  echo "  ✗ registration failed ($code):"
  sed 's/^/    /' "$LOGDIR/reg.json"; echo
  return 1
}

port_listening() { lsof -ti tcp:"$PORT" >/dev/null 2>&1; }

start_service() {
  # $1 = ts file (relative to repo root, e.g. src/chat-agent.ts)
  local file=$1 name
  name=$(basename "$file" .ts)
  SVC_LOG="$LOGDIR/$name.log"
  echo "  ▶ starting $file  (:$PORT)"
  PORT="$PORT" npx tsx "$file" >"$SVC_LOG" 2>&1 &
  SVC_PID=$!
  local i
  for i in $(seq 1 120); do
    if ! kill -0 "$SVC_PID" 2>/dev/null; then
      echo "  ✗ service exited during startup:"
      tail -n 25 "$SVC_LOG" | sed 's/^/    /'
      SVC_PID=""
      return 1
    fi
    if port_listening; then
      sleep 0.3   # tiny grace so discovery is ready
      return 0
    fi
    sleep 0.5
  done
  echo "  ✗ timed out waiting for :$PORT"
  tail -n 25 "$SVC_LOG" | sed 's/^/    /'
  return 1
}

stop_service() {
  [ -z "$SVC_PID" ] && return 0
  local i
  # `npx tsx` may spawn a child node process; terminate the whole group.
  pkill -TERM -P "$SVC_PID" 2>/dev/null
  kill -TERM "$SVC_PID" 2>/dev/null
  for i in $(seq 1 20); do
    kill -0 "$SVC_PID" 2>/dev/null || break
    sleep 0.25
  done
  if kill -0 "$SVC_PID" 2>/dev/null; then
    pkill -KILL -P "$SVC_PID" 2>/dev/null
    kill -KILL "$SVC_PID" 2>/dev/null
  fi
  wait "$SVC_PID" 2>/dev/null
  SVC_PID=""
  # make sure :$PORT is free before starting the next example
  for i in $(seq 1 40); do
    port_listening || return 0
    sleep 0.25
  done
  local holder; holder=$(lsof -ti tcp:"$PORT" 2>/dev/null)
  [ -n "$holder" ] && kill -KILL $holder 2>/dev/null
}

invoke() {
  # $1 = path (Service/handler or Object/key/handler) ; $2 = json body ; $3 = max-time
  local path=$1 body=$2 maxtime=${3:-120} out
  echo "  → POST $INGRESS/$path"
  echo "    $body"
  out=$(curl -s --max-time "$maxtime" -H 'content-type: application/json' \
    -d "$body" "http://$INGRESS/$path")
  [ -z "$out" ] && out="(no response / timed out after ${maxtime}s)"
  echo "  ← ${out:0:700}"
  echo
}

invoke_get() {
  # $1 = path ; no body
  local path=$1 out
  echo "  → GET $INGRESS/$path"
  out=$(curl -s --max-time 30 "http://$INGRESS/$path")
  echo "  ← ${out:0:500}"
  echo
}

want() {
  [ -z "$ONLY" ] && return 0
  local n; for n in $ONLY; do [ "$n" = "$1" ] && return 0; done
  return 1
}

example() {
  # $1 = ts file (relative to repo root) ; returns 0 to proceed with requests
  local file=$1 name; name=$(basename "$file" .ts)
  if ! want "$name"; then return 1; fi
  echo "════════════════════════════════════════════════════════════════"
  echo "▓ $name"
  echo "════════════════════════════════════════════════════════════════"
  if ! start_service "$file"; then stop_service; return 1; fi
  if ! register_deployment; then stop_service; return 1; fi
  return 0
}

# ------------------------------------------------------------------ payloads --
CLAIM='{"date":"2024-10-01","category":"orthopedic","reason":"hospital bill for a broken leg","amount":3000,"placeOfService":"General Hospital"}'

# ================================================================== EXAMPLES ==

if example src/chat-agent.ts; then
  # Virtual Object keyed by session id — two turns share durable history.
  invoke "Chat/user123/message" '{"message":"Write a two-line poem about durable execution."}' 90
  invoke "Chat/user123/message" '{"message":"Now make it rhyme."}' 90
  invoke_get "Chat/user123/getHistory"
  stop_service
fi

if example src/mcp-agent.ts; then
  invoke "McpChat/message" '{"prompt":"Show me how to implement a Virtual Object with Restate"}' 150
  stop_service
fi

if example src/multi-agent.ts; then
  invoke "MultiAgentClaimApproval/run" "$CLAIM" 120
  stop_service
fi

if example src/parallel-tools-agent.ts; then
  invoke "ParallelToolClaimAgent/run" "$CLAIM" 120
  stop_service
fi

if example src/remote-agents.ts; then
  invoke "MultiAgentClaimApproval/run" "$CLAIM" 150
  stop_service
fi

if example src/rollback-agent.ts; then
  invoke "BookingWithRollbackAgent/book" \
    '{"id":"booking_123","prompt":"Book a business trip to San Francisco from March 15-17. Flying from JFK. And a hotel downtown for 1 guest."}' 150
  stop_service
fi

if example src/workflow-sequential.ts; then
  invoke "ClaimReimbursement/process" \
    '{"prompt":"Process my hospital bill of 2024-10-01 for 3000EUR for a broken leg at General Hospital."}' 120
  stop_service
fi

if example src/workflow-parallel.ts; then
  invoke "ParallelAgentClaimApproval/run" "$CLAIM" 150
  stop_service
fi

if example src/workflow-orchestrator.ts; then
  # Planner -> parallel researchers -> writer: several LLM calls, give it time.
  invoke "ResearchReport/generate" \
    '{"topic":"The impact of renewable energy on global economies"}' 240
  stop_service
fi

if example src/workflow-evaluator-optimizer.ts; then
  invoke "CodeGenerator/generate" \
    '{"task":"Write a function that checks if a string is a palindrome"}' 180
  stop_service
fi

if example src/errorhandling/fail-on-terminal-tool-agent.ts; then
  # Handler takes a raw JSON string. Denver triggers a simulated failure.
  invoke "FailOnTerminalErrorAgent/run" '"What is the weather in Denver?"' 120
  stop_service
fi

if example src/errorhandling/stop-on-terminal-tool-agent.ts; then
  invoke "StopOnTerminalErrorAgent/run" '"What is the weather in Denver?"' 120
  stop_service
fi

echo "════════════════════════════════════════════════════════════════"
echo "✓ Tour complete. Restate is still running — open the UI at"
echo "  http://$INGRESS  /  admin http://$ADMIN to browse invocations."
echo "  Service logs for this run: $LOGDIR"
