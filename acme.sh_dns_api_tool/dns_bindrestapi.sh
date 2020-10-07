#!/usr/bin/env sh

# This shell script lets you issue letsencrypt certificates with this bind API
# see https://acme.sh
# export bindrestapi_key="abc123"
# export bindrestapi_url="https://dyndns1.example.org"

# Testing notes - command used to test:
# ./acme.sh --insecure --issue --staging --debug 2 --domain test.example.org --dns dns_bindrestapi | tee debug_run.log
# Usage: add _acme-challenge.host.example.org "xxzzyy"

dns_bindrestapi_add() {
  fulldomain=$1
  txtvalue=$2

  if [ "$bindrestapi_key" ]; then
    _saveaccountconf_mutable bindrestapi_key "$bindrestapi_key"
  else
    _err "You didn't specify a bindrestapi_key - export bindrestapi_key=\"abc123\""
    return 1
  fi

  if [ "$bindrestapi_url" ]; then
    _saveaccountconf_mutable bindrestapi_url "$bindrestapi_url"
  else
    _err "You didn't specify a bindrestapi_url - export bindrestapi_url=\"https://dyndns1.example.org\""
    return 1
  fi

  _info "Adding record $fulldomain"
  export _H1="X-Api-Key: $bindrestapi_key"
  export _H2="Content-Type: application/json"
  data="{\"response\":\"$txtvalue\",\"rrtype\":\"TXT\",\"ttl\":30}"
  _debug "data: $data"
  response="$(_post "$data" "$bindrestapiurl/dns/record/$fulldomain")"
  _debug "got response: $response"
}

dns_bindrestapi_rm() {
  fulldomain=$1
  txtvalue=$2

  if [ "$bindrestapi_key" ]; then
    _saveaccountconf_mutable bindrestapi_key "$bindrestapi_key"
  else
    _err "You didn't specify a bindrestapi_key - export bindrestapi_key=\"abc123\""
    return 1
  fi

  if [ "$bindrestapi_url" ]; then
    _saveaccountconf_mutable bindrestapi_url "$bindrestapi_url"
  else
    _err "You didn't specify a bindrestapi_url - export bindrestapi_url=\"https://dyndns1.example.org\""
    return 1
  fi

  _info "deleting record $fulldomain"
  export _H1="X-Api-Key: $bindrestapi_key"
  export _H2="Content-Type: application/json"
  _debug "data: $data"
  response="$(_post "" "$bindrestapiurl/dns/record/$fulldomain?record_type=TXT" "" "DELETE" )"
  _debug "got response: $response"
}



