#!/usr/bin/env bash

# User to use for testing
export USERNAME='replace-with-username'

# An "App Password" generated for the user
export PASSWORD='replace-with-user-app-password'

# This is the 'aqualog-api' Provider Client ID
export CLIENT_ID='replace-with-aqualog-api-client-id'

# This is the 'aqualog-api' Provider Client Secret
export CLIENT_SECRET='replace-with-aqualog-api-client-secret'

# This is the 'aqualog-api' Provider OpenID Configuration Issuer
export ISSUER='https://auth.aqualog.home.cylindric.net/application/o/aqualog-api/'

# This is the 'aqualog-api' Provider Token URL
export TOKEN_ENDPOINT='https://auth.aqualog.home.cylindric.net/application/o/token/'

# The API endpoint to test
export API_URL='http://localhost:8000/api/v1/calculate/dose/salinity?volume=100&current=30&target=35'

./test_script.sh
