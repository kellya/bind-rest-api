import dns.tsigkeyring
import dns.resolver
import dns.update
import dns.query
import dns.zone
import dns.asyncquery
import dns.asyncresolver
import dns.name
import os
import functools
import traceback
from pathlib import Path
from typing import Optional, List, Tuple
from enum import Enum
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Security, Depends, Query
from fastapi.security.api_key import APIKey, APIKeyHeader
from pydantic import BaseModel


# Set up some variables
DNS_SERVER    = os.environ['BIND_SERVER']
TSIG = dns.tsigkeyring.from_text({os.environ['TSIG_USERNAME']: os.environ['TSIG_PASSWORD']})
VALID_ZONES   = [i + '.' for i in os.environ['BIND_ALLOWED_ZONES'].split(',')]
# RECORD_TYPES  = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA']
API_KEYS      = {
    x.split(',', maxsplit=1)[1]: x.split(',', maxsplit=1)[0]
    for x in 
    filter(lambda x: x[0] != '#', Path(os.environ['API_KEY_FILE']).read_text().split('\n'))
}

# Allowed record types
class RecordType(str, Enum):
    a = 'A'
    aaaa = 'AAAA'
    cname = 'CNAME'
    mx = 'MX'
    ns = 'NS'
    txt = 'TXT'
    soa = 'SOA'

# Record
class Record(BaseModel):
    response: str
    rrtype: RecordType
    ttl: int = 3600

# Some wrappers
asyncresolver = dns.asyncresolver.Resolver()
asyncresolver.nameservers = [DNS_SERVER]
tcpquery = functools.partial(dns.asyncquery.tcp, where=DNS_SERVER)

# Set up app
app = FastAPI()


# Set up API Key authorization
api_key_header = APIKeyHeader(name='access_token')
async def check_api_key(api_key_header: str = Security(api_key_header)) -> str:
    try:
        return API_KEYS[api_key_header]
    except KeyError:
        raise HTTPException(401, 'invalid api key')


@app.get('/dns/zone/{zone_name}')
def get_zone(zone_name: str, api_key_name: APIKey = Depends(check_api_key)):
    '''Get the json representation of a whole dns zone using 
    axfr
    '''
    if not zone_name.endswith('.'):  # make sure the zone is qualified
        zone_name = f'{zone_name}.'

    if zone_name not in VALID_ZONES:
        raise HTTPException(400, 'zone file not permitted')
    
    zone = dns.zone.from_xfr(dns.query.xfr(DNS_SERVER, zone_name))
    
    result = {}
    records = defaultdict(list)
    for (name, ttl, rdata) in zone.iterate_rdatas():
        if rdata.rdtype.name == 'SOA':
            result['SOA'] = {
                'ttl': ttl,
            }
            for n in ('expire', 'minimum','refresh','retry','rname','mname','serial'):
                if n in ('rname', 'mname'):
                    result['SOA'][n] = str(getattr(rdata, n))
                else:
                    result['SOA'][n] = getattr(rdata, n)
        else:
            records[str(name)].append({
                'Answer': str(rdata),
                'RecordType': rdata.rdtype.name,
                'TTL': ttl,
            })
    result['records'] = records
    return result


@app.get('/dns/record/{domain}')
async def get_record(domain: str, record_type: List[RecordType] = Query(list(RecordType)), api_key_name: APIKey = Depends(check_api_key)):
    if not domain.endswith('.'):  # make sure the domain is qualified
        domain = f'{domain}.'

    if not domain.endswith(tuple(VALID_ZONES)):
        raise HTTPException(400, 'domain not permitted')
    
    records = defaultdict(list)
    for t in record_type:
        try:
            answers = await asyncresolver.resolve(domain, t)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            continue
        records[t] = [str(x) for x in answers.rrset]
    
    return records
        

async def dns_update_helper(domain: str):
    if not domain.endswith('.'):  # make sure the domain is qualified
        domain = f'{domain}.'

    zone = b'.'.join(dns.name.from_text(domain).labels[1:]).decode()
    if zone not in VALID_ZONES:
        raise HTTPException(400, 'zone not permitted')
    
    action = dns.update.Update(zone, keyring=TSIG)
    return (domain, action)    


@app.post('/dns/record/{domain}')
async def create_record(
            record: Record,
            helper: Tuple[str, dns.update.Update] = Depends(dns_update_helper),
            api_key_name: APIKey = Depends(check_api_key),
        ):
    domain, action = helper

    action.add(dns.name.from_text(domain), record.ttl, record.rrtype, record.response)

    try:
        response = await tcpquery(action)
    except Exception as e:
        traceback.print_exc()
        return {'error': 'DNS transaction failed - check logs'}

    return {domain: 'DNS request successful'}


@app.put('/dns/record/{domain}')
async def replace_record(
            record: Record,
            helper: Tuple[str, dns.update.Update] = Depends(dns_update_helper),
            api_key_name: APIKey = Depends(check_api_key),
        ):
    domain, action = helper

    action.replace(dns.name.from_text(domain), record.ttl, record.rrtype, record.response)

    try:
        response = await tcpquery(action)
    except Exception as e:
        traceback.print_exc()
        return {'error': 'DNS transaction failed - check logs'}

    return {domain: 'DNS request successful'}


@app.delete('/dns/record/{domain}')
async def delete_record(
            record_type: List[RecordType] = Query(list(RecordType)),
            helper: Tuple[str, dns.update.Update] = Depends(dns_update_helper),
            api_key_name: APIKey = Depends(check_api_key),
        ):
    domain, action = helper

    for t in record_type:
        print(f'deleteing {domain} type {t}')
        action.delete(dns.name.from_text(domain).labels[0].decode(), t)
        try:
            response = await tcpquery(action)
        except Exception as e:
            traceback.print_exc()
            return {'error': 'DNS transaction failed - check logs'}

    return {domain: 'DNS request successful'}


