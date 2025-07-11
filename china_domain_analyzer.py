"""优化后的Python脚本 - 改进日志输出以清晰展示逻辑关系"""

import asyncio
import json
import logging
import time

from helper import sort_rule_file
from utils import check_domain

# pylint: disable=c0103
skip_count = 0


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


cn_domain = set()
non_cn_domain = set()


def update_cache(domain: str, is_cn: bool):
    """更新内存中的缓存"""
    if is_cn:
        cn_domain.add(domain)
    else:
        non_cn_domain.add(domain)


def load_domains():
    """读取未处理的域名列表"""
    # pylint: disable=W0603
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


# 添加全局变量
MAX_CONCURRENCY = 200
session = None
semaphore = None


async def is_china_domain(domain):
    """检查域名是否为中国域名"""
    # 确保 semaphore 已初始化
    if semaphore is None:
        raise RuntimeError("Semaphore 未初始化")

    # 检查缓存
    if domain in cn_domain:
        logger.info("域名检查: [%s] -> [%s]", "✅", domain)
        return True
    if domain in non_cn_domain:
        logger.info("域名检查: [%s] -> [%s]", "❌", domain)
        return False

    try:
        async with semaphore:  # 此时 semaphore 已确保不为 None
            data = await check_domain(domain)
            is_chinese = data.get("is_chinese_ip", False)
            logger.info("域名检查: [%s] -> [%s]", "✅" if is_chinese else "❌", domain)

            # 更新缓存
            update_cache(domain, is_chinese)
            return is_chinese

    except Exception as e:
        logger.error("检查域名[%s]失败: %s", domain, str(e))
        return False


async def get_china_domain_suffix(domain):
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

        if await is_china_domain(sub_domain):
            finally_domain = sub_domain
        else:
            break

        current_domain = sub_domain

    return finally_domain


def get_domain_list(domain_list: set[str]):
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


async def process_domain(domain, index, total):
    """处理单个域名"""
    is_cn = await is_china_domain(domain)
    result = None
    if is_cn:
        result = await get_china_domain_suffix(domain)

    logger.info("正在处理域名 [%d/%d]  [%s]", index, total, "✅" if is_cn else "❌")

    return result


# 合并 rules/china.txt
async def merge_local_china_rules():
    """合并本地的中国域名规则"""

    try:
        with open("rules/china.txt", "r", encoding="utf-8") as f:
            data = f.read().strip().split("\n")
            if not data:
                return []

            # 过滤掉空行和注释行
            data = [
                line.strip()
                for line in data
                if line.strip() and not line.startswith("#")
            ]

            with open("rules.json", "r", encoding="utf-8") as f:
                rules_data = json.load(f)
            # 添加到 rules.json 中
            rules_data["domain_suffix"] += data
            rules_data["domain_suffix"] = sorted(set(rules_data["domain_suffix"]))
            with open("rules.json", "w", encoding="utf-8") as f:
                json.dump(rules_data, f, ensure_ascii=False, indent=4)
            logger.info("成功合并 rules/china.txt 到 rules.json")

    except Exception as e:  # pylint: disable=W0718
        logger.error("读取 rules/china.txt 失败: %s", str(e))


async def main():
    """主函数"""
    global semaphore
    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    domain_list = load_domains()
    if not domain_list:
        logger.info("没有需要处理的域名")
        return

    logger.info("开始处理域名列表")
    total_domains = len(domain_list)

    # 并发处理域名
    tasks = [
        process_domain(domain, i + 1, total_domains)
        for i, domain in enumerate(domain_list)
    ]
    results = await asyncio.gather(*tasks)

    # 过滤掉None结果
    finally_domain_list = set(filter(None, results))

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

    # 保存规则
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    logger.info("域名处理完成，结果已保存到 final_domain_suffix.txt 和 rules.json")


if __name__ == "__main__":
    try:
        asyncio.run(main())
        time.sleep(5)  # 等待日志输出完成
        asyncio.run(sort_rule_file(True))
        print("预加载阶段忽略的域名列表: ", skip_count)
    except Exception as e:  # pylint: disable=W0718
        logger.exception("程序执行出错: %s", str(e))

    asyncio.run(merge_local_china_rules())
