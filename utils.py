"""Utility functions for IP address handling and GeoLite2 database management."""

import asyncio
import logging
import os
import random
import time
from pathlib import Path

import aiodns
import aiohttp
import geoip2.database

logger = logging.getLogger(__name__)

GEOLITE2_URL = "http://geolite2-mirror.nesnode.com/GeoLite2-Country.mmdb"
DB_PATH = Path(__file__).parent / "data" / "GeoLite2-Country.mmdb"
LAST_UPDATE_FILE = Path(__file__).parent / "data" / ".last_update"


async def download_geolite2_db():
    """Download the GeoLite2 database if it needs to be updated."""
    logger.info("Starting download of GeoLite2 database...")
    os.makedirs(DB_PATH.parent, exist_ok=True)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GEOLITE2_URL) as response:
                if response.status == 200:
                    with open(DB_PATH, "wb") as f:
                        while True:
                            chunk = await response.content.read(8192)
                            if not chunk:
                                break
                            f.write(chunk)
                    with open(LAST_UPDATE_FILE, "w", encoding="utf-8") as f:
                        f.write(str(int(time.time())))
                    logger.info("GeoLite2 database download completed")
                    return True
                else:
                    logger.error(
                        "Download failed, HTTP status code: %d", response.status
                    )
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error occurred during download: %s", str(e))
    return False


def needs_update():
    """Check if the GeoLite2 database needs to be updated."""
    if not DB_PATH.exists() or not LAST_UPDATE_FILE.exists():
        logger.info("Database or last update file does not exist, downloading...")
        return True

    with open(LAST_UPDATE_FILE, "r", encoding="utf-8") as f:
        last_update = int(f.read().strip())

    flag = (time.time() - last_update) > 24 * 3600
    if flag:
        logger.info("Database is older than 24 hours, downloading...")
    else:
        logger.info("Database is up to date, no need to download")

    return flag


dns_server_list = ["8.8.8.8"]


async def get_ip_from_domain(domain: str) -> str:
    """
    异步获取域名的 IP 地址
    """
    try:
        dns_server = random.choice(dns_server_list)
        resolver = aiodns.DNSResolver()
        resolver.nameservers = [dns_server]
        result = await resolver.query(domain, "A")
        ip = result[0].host
        logger.info("Domain %s resolved to IP: %s using %s", domain, ip, dns_server)
        return ip
    except Exception as e:
        logger.error("Failed to resolve domain %s: %s", domain, str(e))
        return None


async def check_domain(domain: str):
    """检查域名是否为中国大陆域名"""

    ip = await get_ip_from_domain(domain)
    if not ip:
        return {"domain": domain, "ip": ip, "is_chinese_ip": False}

    is_chinese = await is_chinese_ip(ip)
    return {"domain": domain, "ip": ip, "is_chinese_ip": is_chinese}


async def is_chinese_ip(ip: str) -> bool:
    """异步检查 IP 地址是否来自中国"""
    if not DB_PATH.exists():
        logger.error("GeoLite2 database file does not exist")
        return False

    try:
        # 使用线程池执行同步的 geoip2 查询
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _sync_is_chinese_ip, ip)
    except Exception as e:
        logger.error("Error checking IP %s: %s", ip, str(e))
        return False


def _sync_is_chinese_ip(ip: str) -> bool:
    """同步检查 IP 地址是否来自中国"""
    try:
        with geoip2.database.Reader(DB_PATH) as reader:
            response = reader.country(ip)
            result = response.country.iso_code == "CN"
            logger.info("IP %s is %s China", ip, "from" if result else "not from")
            return result
    except (geoip2.errors.AddressNotFoundError, ValueError) as e:
        logger.error("Failed to query IP %s: %s", ip, str(e))
        return False
    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error checking IP %s: %s", ip, str(e))
        return False
