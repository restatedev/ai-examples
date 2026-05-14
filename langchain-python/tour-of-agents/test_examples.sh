#!/usr/bin/env bash
# Smoke-test every example in app/ against a local Restate server.
#
# Prereqs:
#   - Restate running locally with admin :9070 and ingress :8080
#       docker run --name restate_dev --rm \
#         -p 8080:8080 -p 9070:9070 -p 9071:9071 \
#         --add-host=host.docker.internal:host-gateway \
#         docker.restate.dev/restatedev/restate:latest
#   - OPENAI_API_KEY exported
#   - uv available on PATH
#
# Each example binds to :9080, so we run them sequentially: start the service,
# wait for the port, register the deployment, invoke a handler, kill it.

set -u

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$ROOT/app"
LOG_DIR="$ROOT/.test-logs"
mkdir -p "$LOG_DIR"

ADMIN="${RESTATE_ADMIN:-http://localhost:9070}"
INGRESS="${RESTATE_INGRESS:-http://localhost:8080}"
# When Restate runs in Docker and the example runs on the host, the deployment
# URI must use host.docker.internal. Override with RESTATE_DEPLOY_URI if Restate
# runs natively on the host (then use http://localhost:9080).
DEPLOY_URI="${RESTATE_DEPLOY_URI:-http://localhost:9080}"

INVOKE_TIMEOUT="${INVOKE_TIMEOUT:-120}"
PORT_WAIT_TIMEOUT="${PORT_WAIT_TIMEOUT:-30}"

PASS=()
FAIL=()

red()   { printf '\033[31m%s\033[0m' "$*"; }
green() { printf '\033[32m%s\033[0m' "$*"; }
yellow(){ printf '\033[33m%s\033[0m' "$*"; }

require() {
  command -v "$1" >/dev/null 2>&1 || { echo "Missing required command: $1" >&2; exit 1; }
}

check_restate() {
  if ! curl -sf "$ADMIN/health" >/dev/null; then
    echo "$(red "Restate admin not reachable at $ADMIN")" >&2
    echo "Start it with the docker command in this script's header." >&2
    exit 1
  fi
}

port_in_use() {
  (echo > "/dev/tcp/127.0.0.1/$1") 2>/dev/null
}

wait_for_port() {
  local port="$1" timeout="$2" pid="$3" t=0
  while ! port_in_use "$port"; do
    # If the service died before binding, bail out instead of timing out.
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
      return 2
    fi
    sleep 0.5
    t=$((t + 1))
    if [ "$t" -gt $((timeout * 2)) ]; then
      return 1
    fi
  done
  return 0
}

wait_for_port_free() {
  local port="$1" timeout="${2:-15}" t=0
  while port_in_use "$port"; do
    sleep 0.5
    t=$((t + 1))
    [ "$t" -gt $((timeout * 2)) ] && return 1
  done
  return 0
}

wait_for_pid_dead() {
  local pid="$1" t=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 0.2
    t=$((t + 1))
    [ "$t" -gt 50 ] && return 1
  done
  return 0
}

kill_port_holder() {
  local port="$1"
  local holder
  holder=$(lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | head -n1)
  if [ -n "$holder" ]; then
    kill "$holder" 2>/dev/null || true
    sleep 0.5
    if port_in_use "$port"; then
      kill -9 "$holder" 2>/dev/null || true
    fi
  fi
}

stop_service() {
  local pid="$1"
  if kill -0 "$pid" 2>/dev/null; then
    # Kill children first (uv -> python), then the wrapper.
    pkill -TERM -P "$pid" 2>/dev/null || true
    kill "$pid" 2>/dev/null || true
    wait_for_pid_dead "$pid" || kill -9 "$pid" 2>/dev/null || true
  fi
  # Belt & suspenders: if anything still holds :9080, evict it.
  if port_in_use 9080; then
    kill_port_holder 9080
  fi
}

REG_RESPONSE=""
register_deployment() {
  REG_RESPONSE=$(curl -sS -w '\n%{http_code}' "$ADMIN/deployments" \
    -H 'content-type: application/json' \
    --data "{\"uri\": \"$DEPLOY_URI\", \"force\": true}" 2>&1)
  local code="${REG_RESPONSE##*$'\n'}"
  REG_RESPONSE="${REG_RESPONSE%$'\n'*}"
  [ "$code" = "200" ] || [ "$code" = "201" ]
}

reg_has_service() {
  local svc="$1"
  printf '%s' "$REG_RESPONSE" | grep -q "\"name\"[[:space:]]*:[[:space:]]*\"$svc\""
}

# Watch a log file for a printed awakeable id ("sign_..."/"prom_..." — the SDK
# uses several prefixes, so match the curl line the example prints) and resolve
# it. Runs until the service log emits a resolvable line or the deadline hits.
resolve_awakeable_when_logged() {
  local log="$1" deadline="$2"
  local resolved_count=0
  while [ "$(date +%s)" -lt "$deadline" ]; do
    # Pull awakeable ids out of the printed `curl ... /restate/awakeables/<id>/resolve` line.
    local ids
    ids=$(grep -oE '/restate/awakeables/[A-Za-z0-9_-]+/resolve' "$log" 2>/dev/null \
          | awk -F/ '{print $4}' | sort -u)
    for id in $ids; do
      # idempotent: only resolve each id once
      if [ ! -f "$log.resolved.$id" ]; then
        if curl -sf "$INGRESS/restate/awakeables/$id/resolve" \
            -H 'content-type: application/json' \
            --data 'true' >/dev/null; then
          touch "$log.resolved.$id"
          resolved_count=$((resolved_count + 1))
          echo "    resolved awakeable $id"
        fi
      fi
    done
    [ "$resolved_count" -gt 0 ] && return 0
    sleep 0.5
  done
  return 1
}

# Run one example: start the service, register, invoke, capture status.
#
# Args: file service handler key body [hitl?]
#   - key: pass empty string for plain Service; non-empty for VirtualObject
#   - hitl: "hitl" enables awakeable resolution while invoke is pending
run_example() {
  local file="$1" service="$2" handler="$3" key="$4" body="$5" mode="${6:-}"
  local name="${file%.py}"
  local log="$LOG_DIR/$name.log"
  : > "$log"

  echo
  echo "=== $(yellow "$name") ==="

  # Make sure :9080 is free before starting (a previous run may have lingered).
  if port_in_use 9080; then
    if ! wait_for_port_free 9080 10; then
      echo "$(red "✗ :9080 still in use before start — kill the process holding it")"
      FAIL+=("$name (port-busy)")
      return
    fi
  fi

  # Start service. `disown` so bash doesn't print "Terminated: 15" when we kill it.
  ( cd "$ROOT" && uv run "app/$file" ) >"$log" 2>&1 &
  local svc_pid=$!
  disown "$svc_pid" 2>/dev/null || true

  wait_for_port 9080 "$PORT_WAIT_TIMEOUT" "$svc_pid"
  case $? in
    0) ;;
    2)
      echo "$(red "✗ service exited before binding :9080")"
      echo "  tail of log:"
      tail -n 15 "$log" | sed 's/^/    /'
      FAIL+=("$name (crash)")
      return
      ;;
    *)
      echo "$(red "✗ service did not bind :9080 within ${PORT_WAIT_TIMEOUT}s")"
      echo "  log: $log"
      stop_service "$svc_pid"
      FAIL+=("$name (port)")
      return
      ;;
  esac

  # Restate sometimes needs a beat after the port opens before discovery succeeds.
  sleep 1

  if ! register_deployment; then
    echo "$(red "✗ failed to register deployment at $DEPLOY_URI")"
    echo "  response: $(printf '%s' "$REG_RESPONSE" | head -c 400)"
    stop_service "$svc_pid"
    FAIL+=("$name (register)")
    return
  fi

  if ! reg_has_service "$service"; then
    echo "$(red "✗ Restate registered the deployment but did not discover service '$service'")"
    echo "  response: $(printf '%s' "$REG_RESPONSE" | head -c 400)"
    stop_service "$svc_pid"
    FAIL+=("$name (no-service)")
    return
  fi

  # Build invocation URL.
  local url
  if [ -n "$key" ]; then
    url="$INGRESS/$service/$key/$handler"
  else
    url="$INGRESS/$service/$handler"
  fi

  echo "  POST $url"

  # For HITL examples, kick off awakeable resolver in background while we invoke.
  local resolver_pid=""
  if [ "$mode" = "hitl" ]; then
    local deadline=$(( $(date +%s) + INVOKE_TIMEOUT ))
    resolve_awakeable_when_logged "$log" "$deadline" &
    resolver_pid=$!
  fi

  local resp_file="$LOG_DIR/$name.response"
  local http_code
  http_code=$(curl -sS -o "$resp_file" -w '%{http_code}' \
    --max-time "$INVOKE_TIMEOUT" \
    -H 'content-type: application/json' \
    --data "$body" \
    "$url" || echo "000")

  if [ -n "$resolver_pid" ]; then
    kill "$resolver_pid" 2>/dev/null || true
    wait "$resolver_pid" 2>/dev/null || true
  fi

  if [ "$http_code" = "200" ]; then
    echo "$(green "✓ 200")  body: $(head -c 200 "$resp_file")"
    PASS+=("$name")
  else
    echo "$(red "✗ HTTP $http_code")"
    echo "  body: $(head -c 400 "$resp_file")"
    echo "  log:  $log"
    FAIL+=("$name (http $http_code)")
  fi

  stop_service "$svc_pid"
  # Wait for the port to be released before the next iteration.
  wait_for_port_free 9080 10 || echo "  $(yellow "warning: :9080 still bound after stop")"
  # Clean any awakeable marker files for this run.
  rm -f "$log".resolved.* 2>/dev/null || true
}

# --- preflight ---
require curl
require uv
[ -n "${OPENAI_API_KEY:-}" ] || { echo "$(red "OPENAI_API_KEY not set")" >&2; exit 1; }
check_restate

if port_in_use 9080; then
  echo "$(red "✗ port 9080 is already in use")" >&2
  echo "Find and kill the process:  lsof -iTCP:9080 -sTCP:LISTEN" >&2
  exit 1
fi

# Default test inputs. The HITL examples receive a high-amount claim so the
# model is forced through the human_approval tool path; the awakeable resolver
# unblocks them.
CLAIM_LOW='{"message":"Process my hospital bill of 2024-10-01 for 200USD for a flu test at General Hospital."}'
CLAIM_HIGH='{"message":"Process my hospital bill of 2024-10-01 for 3000USD for a broken leg at General Hospital."}'
INSURANCE_CLAIM='{"date":"2024-10-01","amount":3000,"category":"orthopedic","placeOfService":"General Hospital","reason":"hospital bill for a broken leg"}'
WEATHER_PROMPT='{"message":"What is the weather like in Denver?"}'
CHAT_MESSAGE='{"message":"Make a poem about durable execution."}'
REPORT_REQUEST='{"topic":"The impact of renewable energy on global economies"}'
CODE_REQUEST='{"task":"Write a function that checks if a string is a palindrome"}'

# --- run all examples ---
# args: file               service                                 handler  key            body                  mode
run_example chat_agent.py                       Chat                                  message  user-1         "$CHAT_MESSAGE"
run_example error_handling.py                   WeatherAgent                          run      ""             "$WEATHER_PROMPT"
run_example multi_agent.py                      MultiAgentClaimApproval               run      claim-1        "$INSURANCE_CLAIM"
run_example parallel_tools_agent.py             ParallelToolClaimAgent                run      ""             "$INSURANCE_CLAIM"
run_example workflow_sequential.py              ClaimReimbursement                    process  ""             "$CLAIM_LOW"
run_example workflow_parallel.py                ParallelAgentClaimApproval            run      ""             "$INSURANCE_CLAIM"
run_example workflow_orchestrator.py            ResearchReport                        generate ""             "$REPORT_REQUEST"
run_example workflow_evaluator_optimizer.py     CodeGenerator                         generate ""             "$CODE_REQUEST"
run_example remote_agents.py                    MultiAgentClaimApproval               run      ""             "$INSURANCE_CLAIM"

# --- summary ---
echo
echo "=== Summary ==="
echo "$(green "Passed (${#PASS[@]}):")"
for n in "${PASS[@]}"; do echo "  ✓ $n"; done
echo "$(red "Failed (${#FAIL[@]}):")"
for n in "${FAIL[@]}"; do echo "  ✗ $n"; done

[ "${#FAIL[@]}" -eq 0 ] || exit 1
