#!/usr/bin/env sh

#
# bindrestapi_key="abc123"
#

bindrestapiurl="https://dyndnsdev1.cdu.edu.au"

# Usage: add _acme-challenge.host.example.org "xxzzyy"

dns_bindrestapi_add() {
  fulldomain=$1
  txtvalue=$2

  _info "GrepForMe! - add"

  if [ "$bindrestapi_key" ]; then
    _saveaccountconf_mutable bindrestapi_key "$bindrestapi_key"
  else
    _err "You didn't specify a bindrestapi_key - export bindrestapi_key=\"abc123\""
    return 1
  fi

  _debug "First get root zone"
  # pass - not sure what to do here exactly

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

  _info "GrepForMe! - rm"

  if [ "$bindrestapi_key" ]; then
    _saveaccountconf_mutable bindrestapi_key "$bindrestapi_key"
  else
    _err "You didn't specify a bindrestapi_key - export bindrestapi_key=\"abc123\""
    return 1
  fi

  _debug "First get root zone"
  # pass - not sure what to do here exactly

  _info "deleting record $fulldomain"
  export _H1="X-Api-Key: $bindrestapi_key"
  export _H2="Content-Type: application/json"
  _debug "data: $data"
  response="$(_post "" "$bindrestapiurl/dns/record/$fulldomain?record_type=TXT" "" "DELETE" )"
  _debug "got response: $response"
}



