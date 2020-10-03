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
import pathlib
import logging
from typing import Optional, List, Tuple
from enum import Enum
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Security, Depends, Query, Path
from fastapi.security.api_key import APIKey, APIKeyHeader
from pydantic import BaseModel, Field


# Set up some variables
DNS_SERVER    = os.environ['BIND_SERVER']
TSIG = dns.tsigkeyring.from_text({os.environ['TSIG_USERNAME']: os.environ['TSIG_PASSWORD']})
VALID_ZONES   = [i + '.' for i in os.environ['BIND_ALLOWED_ZONES'].split(',')]
API_KEYS      = {
    x.split(',', maxsplit=1)[1]: x.split(',', maxsplit=1)[0]
    for x in 
    filter(lambda x: x[0] != '#', pathlib.Path(os.environ['API_KEY_FILE']).read_text().split('\n'))
}


# Set up logging
auditlogger = logging.getLogger('bind-api.audit')
auditlogger.setLevel(logging.INFO)
auditlogger.addHandler(logging.handlers.TimedRotatingFileHandler(
    'dns-api-audit.log', when='M', interval=5
))
logger = logging.getLogger('bind-api')
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.handlers.RotatingFileHandler(
    'dns-api-debug.log', maxBytes=(1024 * 1024 * 100), backupCount=10
))
logger.debug('starting up')

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
    response: str = Field(..., example='10.9.1.135')
    rrtype: RecordType
    ttl: int = Field(3600, example=3600)


# Some wrappers
asyncresolver = dns.asyncresolver.Resolver()
asyncresolver.nameservers = [DNS_SERVER]
tcpquery = functools.partial(dns.asyncquery.tcp, where=DNS_SERVER)
# Used to properly fix unqualified domains
qualify = lambda s: f'{s}.' if not s.endswith('.') else s

# Set up app
app = FastAPI()


# Set up API Key authorization
async def check_api_key(api_key_header: str = Security(APIKeyHeader(name='X-Api-Key'))) -> str:
    try:
        return API_KEYS[api_key_header]
    except KeyError:
        raise HTTPException(401, 'invalid api key')


@app.get('/dns/zone/{zone_name}')
def get_zone(zone_name: str = Path(..., example='example.org.'), api_key_name: APIKey = Depends(check_api_key)):
    '''Get the json representation of a whole dns zone using 
    axfr
    '''
    logger.debug(f'api key {api_key_name} requested zone {zone_name}')

    zone_name = qualify(zone_name)

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
    logger.debug(f'api key {api_key_name} requested zone {zone_name} - sending zone')
    return result


@app.get('/dns/record/{domain}')
async def get_record(domain: str = Path(..., example='server.example.org.'), record_type: List[RecordType] = Query(list(RecordType)), api_key_name: APIKey = Depends(check_api_key)):
    domain = qualify(domain)
    logger.debug(f'api key {api_key_name} requested domain records {domain} with types {record_type}')

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
        

async def dns_update_helper(domain: str = Path(..., example='server.example.org.')):
    domain = qualify(domain)

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
    try:
        action.add(dns.name.from_text(domain), record.ttl, record.rrtype, record.response)
        try:
            await tcpquery(action)
        except Exception:
            logger.debug(traceback.format_exc())
            raise HTTPException(500, 'DNS transaction failed - check logs')

        auditlogger.info(f'create {record} for key {api_key_name} on domain {domain}')
    except:
        auditlogger.error(f'FAILED: create {record} for key {api_key_name} on domain {domain}')
        raise


@app.put('/dns/record/{domain}')
async def replace_record(
            record: Record,
            helper: Tuple[str, dns.update.Update] = Depends(dns_update_helper),
            api_key_name: APIKey = Depends(check_api_key),
        ):
    domain, action = helper

    try:
        action.replace(dns.name.from_text(domain), record.ttl, record.rrtype, record.response)
        try:
            await tcpquery(action)
        except Exception:
            logger.debug(traceback.format_exc())
            raise HTTPException(500, 'DNS transaction failed - check logs')
        auditlogger.info(f'replace {record} for key {api_key_name} on domain {domain}')
    except:
        auditlogger.error(f'FAILED: replace {record} for key {api_key_name} on domain {domain}')
        raise

@app.delete('/dns/record/{domain}')
async def delete_record(
            record_type: List[RecordType] = Query(list(RecordType)),
            helper: Tuple[str, dns.update.Update] = Depends(dns_update_helper),
            api_key_name: APIKey = Depends(check_api_key),
        ):
    domain, action = helper

    try:
        for t in record_type:
            print(f'deleteing {domain} type {t}')
            action.delete(dns.name.from_text(domain).labels[0].decode(), t)
            try:
                await tcpquery(action)
            except Exception:
                logger.debug(traceback.format_exc())
                raise HTTPException(500, 'DNS transaction failed - check logs')
        auditlogger.info(f'delete {record_type} for key {api_key_name} on domain {domain}')
    except:
        auditlogger.error(f'FAILED: delete {record_type} for key {api_key_name} on domain {domain}')
        raise