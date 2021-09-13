""" REST api to handle BIND updates via TSIG and Dynamic DNS Updates """
import os
import functools
import traceback
import pathlib
import logging
from typing import List
from enum import Enum
from collections import defaultdict, namedtuple
import dns.tsigkeyring
import dns.resolver
import dns.update
import dns.query
import dns.zone
import dns.asyncquery
import dns.asyncresolver
import dns.name
from fastapi import FastAPI, HTTPException, Security, Depends, Query, Path
from fastapi.security.api_key import APIKey, APIKeyHeader
from pydantic import BaseModel, Field
from .constants import VERSION


# Set up some variables
DNS_SERVER = os.environ["BIND_SERVER"]
LOGGING_APPLICATION_NAME = os.environ["LOGGING_APPLICATION_NAME"]
LOGGING_DIR = os.environ.get("LOGGING_DIR", "./logs")
TSIG = dns.tsigkeyring.from_text(
    {os.environ["TSIG_USERNAME"]: os.environ["TSIG_PASSWORD"]}
)
VALID_ZONES = [i + "." for i in os.environ["BIND_ALLOWED_ZONES"].split(",")]
API_KEYS = {
    x.split(",", maxsplit=1)[1]: x.split(",", maxsplit=1)[0]
    for x in filter(
        lambda x: x != "" and x[0] != "#",
        pathlib.Path(os.environ["API_KEY_FILE"]).read_text().split("\n"),
    )
}


# Set up logging
formatter = logging.Formatter(
    f"%(asctime)s == {LOGGING_APPLICATION_NAME} == %(message)s",
    datefmt="%Y-%m-%dT%H:%M%z",
)
auditlogger = logging.getLogger("bind-api.audit")
auditlogger.setLevel(logging.INFO)
handler1 = logging.handlers.TimedRotatingFileHandler(
    f"{LOGGING_DIR}/dns-api-audit.log", when="D", interval=7
)
handler1.setFormatter(formatter)
auditlogger.addHandler(handler1)
logger = logging.getLogger("bind-api")
logger.setLevel(logging.DEBUG)
handler2 = logging.handlers.RotatingFileHandler(
    f"{LOGGING_DIR}/dns-api-debug.log", maxBytes=(1024 * 1024 * 100), backupCount=10
)
handler2.setFormatter(formatter)
logger.addHandler(handler2)
logger.debug("starting up")


class RecordType(str, Enum):
    """define allowed record types"""

    A = "A"
    AAAA = "AAAA"
    CNAME = "CNAME"
    MX = "MX"
    NS = "NS"
    TXT = "TXT"
    SOA = "SOA"


# Record
class Record(BaseModel):
    response: str = Field(..., example="10.9.1.135")
    rrtype: RecordType
    ttl: int = Field(3600, example=3600)


HelperResponse = namedtuple("HelperResponse", "domain action zone")

# Some wrappers
asyncresolver = dns.asyncresolver.Resolver()
asyncresolver.nameservers = [DNS_SERVER]
tcpquery = functools.partial(dns.asyncquery.tcp, where=DNS_SERVER)
# Used to properly fix unqualified domains


def qualify(domain):
    """Ensure the domain given ends with a period"""
    if not domain.endswith("."):
        domain = f"{domain}."
    return domain


# Set up app
app = FastAPI(title="bind-rest-api", version=VERSION)


async def check_api_key(
    api_key_header: str = Security(APIKeyHeader(name="X-Api-Key")),
) -> str:
    """Set up API Key authorization"""
    try:
        return API_KEYS[api_key_header]
    except KeyError as error:
        raise HTTPException(401, "invalid api key") from error


@app.get("/dns/zone/{zone_name}")
def get_zone(
    zone_name: str = Path(..., example="example.org."),
    api_key_name: APIKey = Depends(check_api_key),
):
    """Get the json representation of a whole dns zone using
    axfr
    """
    logger.debug("api key %s requested zone %s", api_key_name, zone_name)

    zone_name = qualify(zone_name)

    if zone_name not in VALID_ZONES:
        raise HTTPException(400, "zone file not permitted")

    zone = dns.zone.from_xfr(dns.query.xfr(DNS_SERVER, zone_name))

    result = {}
    records = defaultdict(list)
    for (name, ttl, rdata) in zone.iterate_rdatas():
        if rdata.rdtype.name == "SOA":
            result["SOA"] = {
                "ttl": ttl,
            }
            for n in (
                "expire",
                "minimum",
                "refresh",
                "retry",
                "rname",
                "mname",
                "serial",
            ):
                if n in ("rname", "mname"):
                    result["SOA"][n] = str(getattr(rdata, n))
                else:
                    result["SOA"][n] = getattr(rdata, n)
        else:
            records[str(name)].append(
                {
                    "response": str(rdata),
                    "rrtype": rdata.rdtype.name,
                    "ttl": ttl,
                }
            )
    result["records"] = records
    logger.debug("api key %s requested zone %s - sending zone", api_key_name, zone_name)
    return result


@app.get("/dns/record/{domain}")
async def get_record(
    domain: str = Path(..., example="server.example.org."),
    record_type: List[RecordType] = Query(list(RecordType)),
    api_key_name: APIKey = Depends(check_api_key),
):
    domain = qualify(domain)
    logger.debug(
        "api key %s requested domain records %s with types %s",
        api_key_name,
        domain,
        record_type,
    )

    if not domain.endswith(tuple(VALID_ZONES)):
        raise HTTPException(400, "domain not permitted")

    records = defaultdict(list)
    for t in record_type:
        try:
            answers = await asyncresolver.resolve(domain, t)
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            continue
        records[t] = [str(x) for x in answers.rrset]

    return records


async def dns_update_helper(domain: str = Path(..., example="server.example.org.")):
    domain = qualify(domain)

    for valid_zone in VALID_ZONES:
        if domain.endswith(valid_zone):
            action = dns.update.Update(valid_zone, keyring=TSIG)
            return HelperResponse(domain=domain, action=action, zone=valid_zone)
    raise HTTPException(400, "domain zone not permitted")


@app.post("/dns/record/{domain}")
async def create_record(
    record: Record,
    helper: HelperResponse = Depends(dns_update_helper),
    api_key_name: APIKey = Depends(check_api_key),
):
    try:
        helper.action.add(
            dns.name.from_text(helper.domain),
            record.ttl,
            record.rrtype,
            record.response,
        )
        try:
            await tcpquery(helper.action)
        except Exception as error:
            logger.debug(traceback.format_exc())
            raise HTTPException(500, "DNS transaction failed - check logs") from error

        auditlogger.info(
            "CREATE %s %s %s -> %s record %s for key %s",
            helper.domain,
            record.rrtype,
            api_key_name,
            helper.domain,
            record,
            api_key_name,
        )
    except:
        auditlogger.error(
            "FAILED:CREATE %s %s %s -> %s record %s for key %s",
            helper.domain,
            record.rrtype,
            api_key_name,
            helper.domain,
            record,
            api_key_name,
        )
        raise


@app.put("/dns/record/{domain}")
async def replace_record(
    record: Record,
    helper: HelperResponse = Depends(dns_update_helper),
    api_key_name: APIKey = Depends(check_api_key),
):
    try:
        helper.action.replace(
            dns.name.from_text(helper.domain),
            record.ttl,
            record.rrtype,
            record.response,
        )
        try:
            await tcpquery(helper.action)
        except Exception as error:
            logger.debug(traceback.format_exc())
            raise HTTPException(500, "DNS transaction failed - check logs") from error
        auditlogger.info(
            "REPLACE %s %s %s -> %s record %s for key %s",
            helper.domain,
            record.rrtype,
            api_key_name,
            helper.domain,
            record,
            api_key_name,
        )
    except:
        auditlogger.info(
            "FAILED:REPLACE %s %s %s -> %s record %s for key %s",
            helper.domain,
            record.rrtype,
            api_key_name,
            helper.domain,
            record,
            api_key_name,
        )
        raise


@app.delete("/dns/record/{domain}")
async def delete_single_record(
    record: Record,
    helper: HelperResponse = Depends(dns_update_helper),
    api_key_name: APIKey = Depends(check_api_key),
):
    try:
        helper.action.delete(
            dns.name.from_text(helper.domain), record.rrtype, record.response
        )
        try:
            await tcpquery(helper.action)
        except Exception as error:
            logger.debug(traceback.format_exc())
            raise HTTPException(500, "DNS transaction failed - check logs") from error
        auditlogger.info(
            "DELETE %s %s %s -> %s record %s for key %s",
            helper.domain,
            record.rrtype,
            api_key_name,
            helper.domain,
            record,
            api_key_name,
        )
    except:
        auditlogger.info(
            "FAILED:DELETE %s %s %s -> %s record %s for key %s",
            helper.domain,
            record.rrtype,
            api_key_name,
            helper.domain,
            record,
            api_key_name,
        )
        raise


@app.delete("/dns/allrecords/{domain}")
async def delete_record_type(
    recordtypes: List[RecordType] = Query(list(RecordType)),
    helper: HelperResponse = Depends(dns_update_helper),
    api_key_name: APIKey = Depends(check_api_key),
):
    try:
        for rtype in recordtypes:
            logger.debug("deleteing %s type %s", helper.domain, rtype)
            helper.action.delete(dns.name.from_text(helper.domain), rtype)
            try:
                await tcpquery(helper.action)
            except Exception as error:
                logger.debug(traceback.format_exc())
                raise HTTPException(
                    500, "DNS transaction failed - check logs"
                ) from error
        auditlogger.info(
            "DELETE %s %s %s -> %s record %s for key %s",
            helper.domain,
            ",".join(recordtypes),
            api_key_name,
            helper.domain,
            recordtypes,
            api_key_name,
        )
    except:
        auditlogger.info(
            "FAILED:DELETE %s %s %s -> %s record %s for key %s",
            helper.domain,
            ",".join(recordtypes),
            api_key_name,
            helper.domain,
            recordtypes,
            api_key_name,
        )
        raise
