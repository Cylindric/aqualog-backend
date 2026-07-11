#!/usr/bin/env bash

# 0) Required inputs
ISSUER="${ISSUER:-https://auth.aqualog.home.cylindric.net/application/o/aqualog-api/}"
TOKEN_ENDPOINT="${TOKEN_ENDPOINT:-https://auth.aqualog.home.cylindric.net/application/o/token/}"
API_URL="${API_URL:-http://localhost:8000/api/v1/calculate/dose/salinity?volume=100&current=30&target=35}"

set -euo pipefail

required_vars=(USERNAME PASSWORD CLIENT_ID CLIENT_SECRET)
for var in "${required_vars[@]}"; do
  if [[ -z "${!var:-}" ]]; then
    echo "Missing required environment variable: $var"
    echo "Copy test.sh.example and export values before running this script."
    exit 1
  fi
done

base64url_decode() {
  local input="$1"
  python3 -c 'import base64,sys; s=sys.argv[1]; s += "=" * (-len(s) % 4); print(base64.urlsafe_b64decode(s).decode("utf-8"))' "$input"
}

echo "== 1) Fetch token =="
RESP="$(curl -sk -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "grant_type=password" \
  --data-urlencode "username=$USERNAME" \
  --data-urlencode "password=$PASSWORD" \
  --data-urlencode "client_id=$CLIENT_ID" \
  --data-urlencode "client_secret=$CLIENT_SECRET" \
  --data-urlencode "scope=openid profile email")"

echo "$RESP" | jq '{error, error_description, token_type, expires_in, has_access_token:(.access_token!=null), has_id_token:(.id_token!=null)}'

JWT="$(echo "$RESP" | jq -r '.id_token // .access_token // empty')"
if [[ -z "$JWT" ]]; then
  echo "No JWT returned. Stopping."
  exit 1
fi

echo "== 2) Decode JWT header and claims =="
HEADER_SEGMENT="$(echo "$JWT" | cut -d. -f1)"
CLAIMS_SEGMENT="$(echo "$JWT" | cut -d. -f2)"

HEADER_JSON="$(base64url_decode "$HEADER_SEGMENT")"
CLAIMS_JSON="$(base64url_decode "$CLAIMS_SEGMENT")"

echo "$HEADER_JSON" | jq .
echo "$CLAIMS_JSON" | jq '{iss,aud,sub,exp,iat}'

KID="$(echo "$HEADER_JSON" | jq -r '.kid // empty')"
ALG="$(echo "$HEADER_JSON" | jq -r '.alg // empty')"
echo "kid=$KID alg=$ALG"

echo "== 3) Check JWKS has matching key =="
JWKS_URI="$(curl -sk "${ISSUER}.well-known/openid-configuration" | jq -r '.jwks_uri')"
echo "jwks_uri=$JWKS_URI"
curl -sk "$JWKS_URI" | jq --arg kid "$KID" '
  if .keys then
    {
      key_count:(.keys|length),
      matching_key:(.keys[]? | select(.kid==$kid) | {kid,kty,alg,use,has_n:(.n!=null),has_e:(.e!=null)}),
      rsa_keys_with_e_n:([.keys[]? | select(.kty=="RSA" and .n!=null and .e!=null)] | length)
    }
  else
    {raw:.}
  end
'

echo "== 4) Call API =="
curl -s -H "Authorization: Bearer $JWT" "$API_URL" | jq .

echo $JWT