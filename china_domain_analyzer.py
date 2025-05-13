"""优化后的Python脚本 - 改进日志输出以清晰展示逻辑关系"""

import json
import logging
import os

import requests
from dotenv import load_dotenv

# pylint: disable=c0103
skip_count = 0

load_dotenv()

gTLD = [
    "cn",
    "com",
    "net",
    "org",
]

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
ignore_domain_suffix_list = []


with open("ignore_domain_suffix.txt", "r", encoding="utf-8") as f:
    ignore_domain_suffix_list = [line.strip().lower() for line in f if line.strip()]


with open("rules.json", "r", encoding="utf-8") as f:
    rules_data = json.load(f)
    ignore_domain_suffix_list += rules_data["domain_suffix"]


def load_cache_file(cache_file: str):
    """加载缓存文件"""
    if not os.path.exists(cache_file):
        logger.warning("缓存文件[%s]不存在", cache_file)
        return set()

    try:
        # pylint: disable=W0621
        with open(cache_file, "r", encoding="utf-8") as f:
            domains = {line.strip().lower() for line in f if line.strip()}
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
        # pylint: disable=W0621
        with open(cache_file, "a", encoding="utf-8") as f:
            f.write(domain + "\n")

    except Exception as e:  # pylint: disable=W0718
        logger.error("保存域名[%s]到缓存文件[%s]失败: %s", domain, cache_file, str(e))


def load_domains():
    """读取未处理的域名列表"""
    global skip_count
    _data = []

    try:
        # pylint: disable=W0621
        with open("domains.txt", "r", encoding="utf-8") as f:
            domains = [line.strip().lower() for line in f if line.strip().lower()]

        for domain in domains:
            # 如果域名后缀在忽略列表中，则跳过
            if any(domain.endswith(suffix) for suffix in ignore_domain_suffix_list):
                skip_count += 1
                continue

            if domain.count(".") < 1:
                skip_count += 1
                continue

            if ":" in domain or "[" in domain:
                skip_count += 1
                continue

            if "google" in domain:
                skip_count += 1
                continue

            if domain.startswith("www"):
                skip_count += 1
                continue

            # 检查域名后缀是否在 gTLD 列表中
            if not any(domain.endswith(suffix) for suffix in gTLD):
                skip_count += 1
                continue

            _data.append(domain)

        return _data

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


def get_domain_list(domain_list: list[str]):
    """获取域名列表"""
    domain_suffix = set()
    for domain in domain_list:
        # 获取域名后缀
        if domain.count(".") > 1:
            # 取最后两级域名
            domain_suffix.add(".".join(domain.split(".")[-2:]))

    summary = {}
    for domain_suffix_item in domain_suffix:
        if domain_suffix_item not in summary:
            summary[domain_suffix_item] = 0

        for domain in domain_list:
            if domain.endswith(domain_suffix_item):
                summary[domain_suffix_item] += 1
    ready_delete_domain_list = []
    data = []

    for item, count in summary.items():
        if count >= 2:
            for domain in domain_list:
                if domain.endswith(item):
                    ready_delete_domain_list.append(domain)
            data.append(item)

    for domain in domain_list:
        if domain in ready_delete_domain_list:
            continue
        data.append(domain)

    return data


def sort_rule_file():
    """对规则文件进行排序"""
    # pylint: disable=W0621
    with open("rules.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 排序
    data["domain_suffix"] = sorted(set(data["domain_suffix"]))

    # 保存规则
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def remove_duplicates():
    """去重"""
    # 加载官方规则
    with open("./tmp/geosite-cn.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    sing_box_rules = data["rules"][0]["domain_suffix"]

    # 加载自定义规则
    with open("rules.json", "r", encoding="utf-8") as f:
        custom_rules = json.load(f)
    domain_suffix = custom_rules["domain_suffix"]

    finally_domain_list = set()

    for rule in domain_suffix:
        if any(rule.endswith(suffix) for suffix in sing_box_rules):
            logger.info("规则[%s]已存在，跳过", rule)
            continue
        finally_domain_list.add(rule)

    custom_rules["domain_suffix"] = sorted(set(finally_domain_list))
    # 保存规则
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump(custom_rules, f, ensure_ascii=False, indent=4)


def main():
    """主函数"""
    domain_list = load_domains()
    if not domain_list:
        logger.info("没有需要处理的域名")
        return
    logger.info("开始处理域名列表")
    finally_domain_list = set()
    total_domains = len(domain_list)
    for index, domain in enumerate(domain_list, start=1):
        logger.info("正在处理域名 [%d/%d]", index, total_domains)
        if is_china_domain(domain):
            # 获取中国域名后缀
            china_domain_suffix = get_china_domain_suffix(domain)
            finally_domain_list.add(china_domain_suffix)

    # 将最终的域名后缀保存到文件
    # pylint: disable=W0621
    with open("final_domain_suffix.txt", "w", encoding="utf-8") as f:
        for domain in finally_domain_list:
            f.write(domain + "\n")

    finally_domain_list = get_domain_list(finally_domain_list)

    # data = json.loads("rules.json")
    # pylint: disable=W0621
    with open("rules.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    # 添加中国域名后缀到规则中
    data["domain_suffix"] = data["domain_suffix"] + list(finally_domain_list)

    # 排序
    data["domain_suffix"] = sorted(set(data["domain_suffix"]))
    # 去掉以 cn 结尾的域名后缀，处理字符长度大于3的域名后缀
    data["domain_suffix"] = [
        suffix
        for suffix in data["domain_suffix"]
        if not (suffix.endswith("cn") and len(suffix) > 3)
    ]
    # 保存规则
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("域名处理完成，结果已保存到 final_domain_suffix.txt 和 rules.json")


if __name__ == "__main__":
    try:
        main()
        print("预加载阶段忽略的域名列表: ", skip_count)
    except Exception as e:  # pylint: disable=W0718
        logger.exception("程序执行出错: %s", str(e))
