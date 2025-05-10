"""优化后的Python脚本 - 改进日志输出以清晰展示逻辑关系"""

import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()


# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# 预设的域名后缀列表
ignore_domain_suffix_list = [
    "baidu.com",
    "casalemedia.com",
    "fbcdn.net",
    "fbcdn.net",
    "google.com",
    "googlesyndication.com",
    "googlesyndication.com",
    "microsoft.com",
    "nesnode.com",
    "provider",
    "push.apple.com",
    "qq.com",
    "sensic.net",
    "tiktokv.com",
    "tiktokv.us",
]


def load_cache_file(cache_file: str):
    """加载缓存文件"""
    if not os.path.exists(cache_file):
        logger.warning("缓存文件[%s]不存在", cache_file)
        return set()

    try:
        with open(cache_file, "r", encoding="utf-8") as f:
            domains = {line.strip() for line in f if line.strip()}
        logger.info("加载缓存文件[%s]成功", cache_file)
        return set(domains)
    except Exception as e:  # pylint: disable=W0718
        logger.error("加载缓存文件[%s]失败: %s", cache_file, str(e))
        return set()


cn_domain = load_cache_file("cn_cache.txt")
non_cn_domain = load_cache_file("non_cn_cache.txt")


def save_cache_file(domain: str, is_cn: bool):
    """保存缓存文件"""
    # 保存到 cn 缓存文件和非 cn 缓存文件
    if is_cn:
        cache_file = "cn_cache.txt"
        cn_domain.add(domain)
    else:
        cache_file = "non_cn_cache.txt"
        non_cn_domain.add(domain)
    try:
        with open(cache_file, "a", encoding="utf-8") as f:
            f.write(domain + "\n")

    except Exception as e:  # pylint: disable=W0718
        logger.error("保存域名[%s]到缓存文件[%s]失败: %s", domain, cache_file, str(e))


def load_domains():
    """读取未处理的域名列表"""
    data = []
    try:
        with open("domains.txt", "r", encoding="utf-8") as f:
            domains = [line.strip() for line in f if line.strip()]

        for domain in domains:
            # 如果域名后缀在忽略列表中，则跳过
            if any(domain.endswith(suffix) for suffix in ignore_domain_suffix_list):
                logger.info("忽略域名后缀: %s", domain)
                continue

            if domain.count(".") < 1:
                continue

            data.append(domain)

        return data

    except Exception as e:  # pylint: disable=W0718
        logger.error("加载domains.txt失败: %s", str(e))
        return []


def is_china_domain(domain):
    """检查域名是否为中国域名"""
    api_url = os.getenv("api_url")
    if not api_url:
        logger.error("API URL未设置，请在环境变量中设置api_url")
        raise ValueError("API URL未设置，请在环境变量中设置api_url")

    url = f"{os.getenv("api_url")}/is-china-domain?domain={domain}"

    # 检查缓存
    if domain in cn_domain:
        logger.info("域名检查: [%s] -> [%s]", "✅", domain)

        return True
    if domain in non_cn_domain:
        logger.info("域名检查: [%s] -> [%s]", "❌", domain)
        return False

    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        is_chinese = data.get("is_chinese_ip", False)
        # logger.info("域名检查: [%s] -> %s", domain, "is cn" if is_chinese else "!! cn")
        logger.info("域名检查: [%s] -> [%s]", "✅" if is_chinese else "❌", domain)
        if is_chinese:
            save_cache_file(domain, True)
        else:
            save_cache_file(domain, False)
        return is_chinese
    except Exception as e:  # pylint: disable=W0718
        logger.error("检查域名[%s]失败: %s", domain, str(e))
        # 如果请求失败，默认返回 False

        return False


def get_china_domain_suffix(domain):
    """获取中国域名的后缀"""

    finally_domain = domain
    current_domain = domain

    # 记录已检查过的域名以避免重复检查
    checked_domains = set()

    while current_domain.count(".") > 1:
        # 获取当前域名去掉最左边一级后的部分
        sub_domain = current_domain.split(".", 1)[1]

        # 如果该域名已经检查过，直接跳过
        if sub_domain in checked_domains:
            break

        checked_domains.add(sub_domain)

        if is_china_domain(sub_domain):
            finally_domain = sub_domain
        else:
            break

        current_domain = sub_domain

    return finally_domain


def main():
    """主函数"""
    domain_list = load_domains()
    if not domain_list:
        logger.info("没有需要处理的域名")
        return
    logger.info("开始处理域名列表")
    finally_domain_list = set()
    for domain in domain_list:
        if is_china_domain(domain):
            # 获取中国域名后缀
            china_domain_suffix = get_china_domain_suffix(domain)
            finally_domain_list.add(china_domain_suffix)

    # 将最终的域名后缀保存到文件
    with open("final_domain_suffix.txt", "w", encoding="utf-8") as f:
        for domain in finally_domain_list:
            f.write(domain + "\n")


if __name__ == "__main__":
    try:

        main()
        # get_china_domain_suffix("www.g.alicdn.com")
    except Exception as e:  # pylint: disable=W0718
        logger.exception("程序执行出错: %s", str(e))
