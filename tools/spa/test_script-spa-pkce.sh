#!/usr/bin/env bash

set -euo pipefail

ISSUER="${AQUALOG_OAUTH_ISSUER_URL}"
TOKEN_ENDPOINT="${AQUALOG_OAUTH_TOKEN_ENDPOINT}"
CLIENT_ID="${AQUALOG_OAUTH_CLIENT_ID:-}"
REDIRECT_URI="${REDIRECT_URI}"
SCOPE="openid profile email offline_access"
AUTH_CODE=""
AUTO_CAPTURE_CODE="1"

echo "Using the following configuration:"
echo "  ISSUER: $ISSUER"
echo "  TOKEN_ENDPOINT: $TOKEN_ENDPOINT"
echo "  API_URL: $API_URL"

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

echo "== 1) Open this authorization URL in your browser =="
echo
printf '%s\n' "$AUTH_REQUEST_URL"
echo
echo "Redirect URI: $REDIRECT_URI"

if [[ -z "$AUTH_CODE" && "$AUTO_CAPTURE_CODE" == "1" ]]; then
  echo "Waiting for OAuth callback and attempting automatic code capture (180s timeout)..."
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$AUTH_REQUEST_URL" >/dev/null 2>&1 || true
  fi
  AUTH_CODE="$(capture_auth_code || true)"
fi

if [[ -z "$AUTH_CODE" ]]; then
  echo "Automatic capture unavailable or timed out."
  echo "Complete login in browser and paste the authorization code from the callback URL."
  read -r -p "Authorization code: " AUTH_CODE
fi

echo "== 2) Exchange authorization code for tokens =="
RESP="$(request_tokens "$AUTH_CODE" "$CODE_VERIFIER")"
echo "$RESP" | jq '{error, error_description, token_type, expires_in, has_access_token:(.access_token!=null), has_id_token:(.id_token!=null), has_refresh_token:(.refresh_token!=null)}'

INITIAL_REFRESH_TOKEN="$(echo "$RESP" | jq -r '.refresh_token // empty')"
if [[ -z "$INITIAL_REFRESH_TOKEN" ]]; then
  echo "No refresh token returned. Check that offline_access is allowed on the provider."
  exit 1
fi

echo "== 3a) Print initial access token =="
echo "$RESP" | jq -r '.access_token // empty'

echo "== 3b) Print initial refresh token =="
echo "$INITIAL_REFRESH_TOKEN"

echo "== 4) Test refresh-token exchange =="
RESP2="$(request_refresh_token "$INITIAL_REFRESH_TOKEN")"
echo "$RESP2" | jq '{error, error_description, token_type, expires_in, has_access_token:(.access_token!=null), has_id_token:(.id_token!=null), has_refresh_token:(.refresh_token!=null)}'
NEXT_REFRESH_TOKEN="$(echo "$RESP2" | jq -r '.refresh_token // empty')"
if [[ -n "$NEXT_REFRESH_TOKEN" ]]; then
  echo "== 5) Refreshed token issued successfully =="
  echo "$NEXT_REFRESH_TOKEN"
  TOKEN_FOR_NEXT_TEST="$NEXT_REFRESH_TOKEN"
else
  echo "== 5) No rotated refresh token returned =="
  echo "Provider appears to be configured for non-rotating refresh tokens."
  echo "Reusing the original refresh token for the next exchange test."
  TOKEN_FOR_NEXT_TEST="$INITIAL_REFRESH_TOKEN"
fi

echo "== 6) Verify refresh token can be exchanged again =="
RESP3="$(request_refresh_token "$TOKEN_FOR_NEXT_TEST")"
echo "$RESP3" | jq '{error, error_description, token_type, expires_in, has_access_token:(.access_token!=null), has_id_token:(.id_token!=null), has_refresh_token:(.refresh_token!=null)}'

echo "== 7) Print the JWT access token from the last refresh exchange =="
JWT="$(echo "$RESP3" | jq -r '.access_token // empty')"
if [[ -z "$JWT" ]]; then
  echo "No access token returned from refresh exchange. Stopping."
  exit 1
else
  echo "$JWT"
fi

echo "== 8) Call API =="
echo "  if an 'Unsupported token algorithm: RS256' error occurs, check that the provider is configured to use HS256 for JWT signing. Try removing and re-adding the signing key in Authentik."
curl -s -H "Authorization: Bearer $JWT" "$API_URL" | jq .
