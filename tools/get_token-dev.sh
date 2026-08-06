#!/usr/bin/env bash

set -euo pipefail
source ../../.env
API_URL="http://localhost:${BACKEND_PORT_HTTP}/api/v1/calculate/dose/salinity?volume=100&current=30&target=35"
REDIRECT_URI="http://127.0.0.1:8400/callback"

ISSUER="${AQUALOG_OAUTH_ISSUER_URL}"
TOKEN_ENDPOINT="${AQUALOG_OAUTH_TOKEN_ENDPOINT}"
CLIENT_ID="${AQUALOG_OAUTH_CLIENT_ID:-}"
REDIRECT_URI="${REDIRECT_URI}"
# "groups" is a custom scope — it only yields a "groups" claim if the
# Authentik provider has a matching Scope Mapping attached. If yours
# doesn't yet, Authentik will simply ignore the unrecognized scope.
SCOPE="openid profile email offline_access aqualog-groups"

if [[ -z "$CLIENT_ID" ]]; then
  echo "Missing required environment variable: CLIENT_ID"
  exit 1
fi

base64url_encode() {
  python3 -c 'import base64,sys; data=sys.argv[1].encode("utf-8"); print(base64.urlsafe_b64encode(data).decode("utf-8").rstrip("="))' "$1"
}

sha256_base64url() {
  python3 -c 'import base64,hashlib,sys; data=sys.argv[1].encode("utf-8"); digest=hashlib.sha256(data).digest(); print(base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("="))' "$1"
}

random_urlsafe() {
  python3 -c 'import secrets; print(secrets.token_urlsafe(48))'
}

urlencode() {
  python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "$1"
}

capture_auth_code() {
  python3 - "$REDIRECT_URI" <<'PY'
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

redirect_uri = sys.argv[1]
parsed = urlparse(redirect_uri)

if parsed.scheme != "http":
  print("", end="")
  sys.exit(0)

host = parsed.hostname or "127.0.0.1"
port = parsed.port or 80
expected_path = parsed.path or "/"

state = {"code": "", "error": ""}

class Handler(BaseHTTPRequestHandler):
  def do_GET(self):
    req = urlparse(self.path)
    if req.path != expected_path:
      self.send_response(404)
      self.end_headers()
      self.wfile.write(b"Not found")
      return

    params = parse_qs(req.query)
    code = params.get("code", [""])[0]
    error = params.get("error", [""])[0]

    if code:
      state["code"] = code
      body = b"Authorization code received. You can return to the terminal."
      self.send_response(200)
    elif error:
      state["error"] = error
      body = f"Authorization failed: {error}".encode("utf-8")
      self.send_response(400)
    else:
      body = b"Missing authorization code."
      self.send_response(400)

    self.send_header("Content-Type", "text/plain; charset=utf-8")
    self.send_header("Content-Length", str(len(body)))
    self.end_headers()
    self.wfile.write(body)

  def log_message(self, format, *args):
    return

deadline = time.time() + 180
httpd = HTTPServer((host, port), Handler)
httpd.timeout = 1
while time.time() < deadline and not state["code"] and not state["error"]:
  httpd.handle_request()

if state["code"]:
  print(state["code"], end="")
PY
}

request_tokens() {
  local code="$1"
  local verifier="$2"

  curl -sk -X POST "$TOKEN_ENDPOINT" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=authorization_code" \
    --data-urlencode "client_id=$CLIENT_ID" \
    --data-urlencode "code=$code" \
    --data-urlencode "redirect_uri=$REDIRECT_URI" \
    --data-urlencode "code_verifier=$verifier"
}

request_refresh_token() {
  local refresh_token="$1"

  curl -sk -X POST "$TOKEN_ENDPOINT" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data-urlencode "grant_type=refresh_token" \
    --data-urlencode "client_id=$CLIENT_ID" \
    --data-urlencode "refresh_token=$refresh_token" \
    --data-urlencode "scope=$SCOPE"
}

CODE_VERIFIER="$(random_urlsafe)"
CODE_CHALLENGE="$(sha256_base64url "$CODE_VERIFIER")"

AUTH_URL="${ISSUER}.well-known/openid-configuration"
AUTHORIZATION_ENDPOINT="$(curl -sk "$AUTH_URL" | python3 -c 'import json,sys; print(json.load(sys.stdin)["authorization_endpoint"])')"

AUTH_REQUEST_URL="${AUTHORIZATION_ENDPOINT}?response_type=code&client_id=$(urlencode "$CLIENT_ID")&redirect_uri=$(urlencode "$REDIRECT_URI")&scope=$(urlencode "$SCOPE")&code_challenge=$CODE_CHALLENGE&code_challenge_method=S256&prompt=login"

if command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$AUTH_REQUEST_URL" >/dev/null 2>&1 || true
else
  echo "Please open the following URL in your browser to authorize:"
  echo "$AUTH_REQUEST_URL"
fi
AUTH_CODE="$(capture_auth_code || true)"


RESP="$(request_tokens "$AUTH_CODE" "$CODE_VERIFIER")"

INITIAL_REFRESH_TOKEN="$(echo "$RESP" | jq -r '.refresh_token // empty')"
if [[ -z "$INITIAL_REFRESH_TOKEN" ]]; then
  echo "No refresh token returned. Check that offline_access is allowed on the provider."
  exit 1
fi

RESP2="$(request_refresh_token "$INITIAL_REFRESH_TOKEN")"
NEXT_REFRESH_TOKEN="$(echo "$RESP2" | jq -r '.refresh_token // empty')"
if [[ -n "$NEXT_REFRESH_TOKEN" ]]; then
  TOKEN_FOR_NEXT_TEST="$NEXT_REFRESH_TOKEN"
else
  TOKEN_FOR_NEXT_TEST="$INITIAL_REFRESH_TOKEN"
fi

RESP3="$(request_refresh_token "$TOKEN_FOR_NEXT_TEST")"

JWT="$(echo "$RESP3" | jq -r '.access_token // empty')"
if [[ -z "$JWT" ]]; then
  echo "No access token returned from refresh exchange. Stopping."
  exit 1
fi

TEST_RESULT=$(curl -s -H "Authorization: Bearer $JWT" "$API_URL" | jq '.success')
if [[ "$TEST_RESULT" != "true" ]]; then
  echo "API test failed. Check that the access token is valid and has the required scopes."
  exit 1
fi

jwt decode -j $JWT | jq '.'
echo $JWT
