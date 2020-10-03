import dns.tsigkeyring
import dns.resolver
import dns.update
import dns.query
import dns.zone
import os

from pathlib import Path
from collections import defaultdict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


# Set up some variables
DNS_SERVER    = os.environ['BIND_SERVER']
TSIG_USERNAME = os.environ['TSIG_USERNAME']
TSIG_PASSWORD = os.environ['TSIG_PASSWORD']
VALID_ZONES   = [i + '.' for i in os.environ['BIND_ALLOWED_ZONES'].split(',')]
RECORD_TYPES  = ['A', 'AAAA', 'CNAME', 'MX', 'NS', 'TXT', 'SOA']
API_KEYS      = {
    x.split(',', maxsplit=1)[1]: x.split(',', maxsplit=1)[0]
    for x in 
    filter(lambda x: x[0] != '#', Path(os.environ['API_KEY_FILE']).read_text().split('\n'))
}



# Set up app
app = FastAPI()


@app.get('/dns/zone/{zone_name}')
def get_zone(zone_name: str):
    '''Get the json representation of a whole dns zone using 
    axfr
    '''
    if not zone_name.endswith('.'):  # make sure the zone is qualified
        zone_name = f'{zone_name}.'

    if zone_name not in VALID_ZONES:
        return HTTPException(400, 'zone file not permitted')
    
    try:
        zone = dns.zone.from_xfr(dns.query.xfr(DNS_SERVER, zone_name))
    except dns.exception.FormError:
        return {'error': zone_name}
    
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

