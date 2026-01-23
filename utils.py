"""Utility functions for IP address handling and GeoLite2 database management."""

import logging
import os
import random
import time
from pathlib import Path
from typing import Optional

import aiodns
import aiohttp
import geoip2.database
from urllib3 import Retry

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


dns_server_list = ["223.5.5.5", "119.29.29.29"]


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
        return f"{ip}"
    except Exception as e:
        logger.error(
            "Error resolving domain %s: %s from dns server: %s",
            domain,
            str(e),
            dns_server,
        )
        os.system(
            f"echo 'Error resolving domain {domain}: {str(e)}:{dns_server}' >> error.log"
        )
        return "172.217.12.132"


async def check_domain(domain: str):
    """检查域名是否为中国大陆域名"""

    ip = await get_ip_from_domain(domain)
    if not ip:
        return {"domain": domain, "ip": ip, "is_chinese_ip": False}

    is_chinese = await is_chinese_ip(ip, domain)
    return {"domain": domain, "ip": ip, "is_chinese_ip": is_chinese}


async def is_chinese_ip(ip: str, domain: Optional[str] = None) -> bool:
    """异步检查 IP 地址是否来自中国"""
    if not DB_PATH.exists():
        logger.error("GeoLite2 database file does not exist")
        raise FileNotFoundError("GeoLite2 database file does not exist")

    try:
        with geoip2.database.Reader(DB_PATH) as reader:
            response = reader.country(ip)
            is_cn_res = response.country.iso_code == "CN"
            logger.info("IP %s is %s China", ip, "from" if is_cn_res else "not from")
            if not is_cn_res:
                # 如果 IP 不在中国，则直接返回 False
                return False

            # 如果 IP 在中国，则检查域名的HTTP状态码
            if domain:
                http_available = await check_http_status(domain)
                if http_available:
                    logger.info("Domain %s returned HTTPS 200", domain)
                    return True
                else:
                    # 如果HTTPS不返回200，则返回 False
                    logger.info("Domain %s does not return HTTPS 200", domain)
                    return False
            else:
                # 如果没有提供域名，只能返回IP地理位置的结果
                return True

    except Exception as e:  # pylint: disable=broad-except
        logger.error("Error checking IP %s: %s", ip, str(e))
        return False


async def check_http_status(domain: str) -> bool:
    """异步检查域名的HTTPS状态码，返回200,或重定向到200则返回True"""
    url = f"https://{domain}"
    success_statuses = [200, 403, 404]

    # 如果 2 秒内都无法连接，可以认为此网站的提供者没有服务用户的诚意。
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2)) as session:
        try:
            async with session.get(url) as response:
                if response.status in success_statuses:
                    logger.info("URL %s returned status 200", url)
                    return True
                elif response.status in {301, 302, 303, 307, 308}:
                    logger.info(
                        "URL %s returned redirect status %d", url, response.status
                    )
                    # 跟随重定向检查最终状态码
                    final_url = str(response.url)
                    async with session.get(final_url) as final_response:
                        if final_response.status in success_statuses:
                            logger.info(
                                "Final URL %s after redirect returned status 200",
                                final_url,
                            )
                            return True
                        else:
                            logger.info(
                                "Final URL %s after redirect returned status %d",
                                final_url,
                                final_response.status,
                            )
                else:
                    logger.info("URL %s returned status %d", url, response.status)
        except Exception as e:
            logger.info("Error checking URL %s: %s", url, str(e))

    logger.info("No successful HTTPS connections for domain %s", domain)
    return False


def get_main_domain(domain: str) -> str:
    """
    提取主域名
    """

    domain_parts = domain.split(".")
    if len(domain_parts) > 2:
        return ".".join(domain_parts[-2:])
    return domain


async def check_domain_availability(url: str) -> bool:
    """
    检查主域名是否可用
    Args:
        url: 完整的URL或域名
    Returns:
        bool: 如果域名可访问则返回True，否则返回False
    """
    try:
        # 提取主域名
        main_domain = get_main_domain(url)
        domains_to_check = [main_domain, f"www.{main_domain}"]

        for domain in domains_to_check:
            try:
                # 解析域名
                ip = await get_ip_from_domain(domain)
                if not ip:
                    logger.warning("Failed to resolve domain %s", domain)
                    continue

                if ip == "172.217.12.132":
                    continue

                if not (await is_chinese_ip(ip, domain)):
                    logger.info("Domain %s is not a Chinese IP", domain)
                    continue

                # 检查HTTPS状态码
                http_available = await check_http_status(domain)

                if http_available:
                    logger.info("Domain %s is available", domain)
                    return True

            except Exception as e:
                logger.error("Error checking domain %s: %s", domain, str(e))
                continue

        logger.info("No available domains found for %s", url)
        return False

    except Exception as e:
        logger.error("Failed to process URL %s: %s", url, str(e))
        return False
