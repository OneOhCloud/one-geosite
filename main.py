"""Sing Box Rule Set Decompiler and Merger
1. 下载 Sing Box
2. 下载 geosite-cn.srs
3. 执行 Sing Box 的 rule-set decompile 命令
4. 合并规则
5. 执行 Sing Box 的 rule-set compile 命令
"""

import json
import os
import platform
import shutil
import subprocess
import tarfile

import requests


def get_system_info():
    """
    获取系统信息
    :return: (os_platform, os_arch)
    """
    # GitHub Actions 环境检测
    if os.getenv("GITHUB_ACTIONS"):
        return "linux", "amd64"  # GitHub hosted runner 使用 x64 架构

    # 常规环境检测
    system = platform.system().lower()
    machine = platform.machine().lower()

    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }

    platform_map = {"linux": "linux", "darwin": "darwin"}

    system_arch = arch_map.get(machine)
    if not system_arch:
        raise ValueError(f"不支持的系统架构: {machine}")

    detected_platform = platform_map.get(system)
    if not os_platform:
        raise ValueError(f"不支持的操作系统: {system}")

    return detected_platform, system_arch


os_platform, os_arch = get_system_info()

# pylint: disable=invalid-name,C0301
sing_box_ver = "1.11.8"
# pylint: disable=invalid-name
sing_box_url = f"https://github.com/SagerNet/sing-box/releases/download/v{sing_box_ver}/sing-box-{sing_box_ver}-{os_platform}-{os_arch}.tar.gz"
sing_box_bin = "tmp/sing-box"
# pylint: disable=invalid-name
geosite_cn_url = "https://raw.githubusercontent.com/SagerNet/sing-geosite/refs/heads/rule-set/geosite-cn.srs"


def download_sing_box():
    """
    下载 Sing Box
    """

    os.makedirs("tmp", exist_ok=True)

    def tar_filter(member, _):
        # 只允许 sing-box 可执行文件
        if member.name.endswith("sing-box"):
            member.name = os.path.basename(member.name)
            return member
        return None

    if not os.path.exists(sing_box_bin):
        print("Downloading Sing Box...")
        print(f"URL: {sing_box_url}")
        response = requests.get(sing_box_url, timeout=10)
        with open("tmp/sing-box.tar.gz", "wb") as f:
            f.write(response.content)
        print("Download complete.")

        print("Extracting Sing Box...")
        with tarfile.open("tmp/sing-box.tar.gz", "r:gz") as tar:
            tar.extractall(path="tmp", filter=tar_filter)
        print("Extraction complete.")
    else:
        print("Sing Box already downloaded.")


# 下载 geosite-cn
def download_geosite_cn():
    """
    下载 geosite-cn.srs
    """

    os.makedirs("tmp", exist_ok=True)

    if not os.path.exists("tmp/geosite-cn.srs"):
        print("Downloading geosite-cn...")
        print(f"URL: {geosite_cn_url}")
        response = requests.get(geosite_cn_url, timeout=10)
        with open("tmp/geosite-cn.srs", "wb") as f:
            f.write(response.content)
        print("Download complete.")
    else:
        print("geosite-cn already downloaded.")


def merge_domain_regex(geosite_rules: dict, custom_rules: dict) -> None:
    """合并正则表达式域名规则"""
    if "domain_regex" in custom_rules:
        if "domain_regex" not in geosite_rules:
            geosite_rules["domain_regex"] = []
        for rule in custom_rules["domain_regex"]:
            if rule not in geosite_rules["domain_regex"]:
                geosite_rules["domain_regex"].append(rule)


def merge_domain(geosite_rules: dict, custom_rules: dict) -> None:
    """合并完整域名规则"""
    if "domain" in custom_rules:
        if "domain" not in geosite_rules:
            geosite_rules["domain"] = []
        for rule in custom_rules["domain"]:
            if rule not in geosite_rules["domain"]:
                geosite_rules["domain"].append(rule)


def merge_domain_suffix(geosite_rules: dict, custom_rules: dict) -> None:
    """合并域名后缀规则"""
    if "domain_suffix" in custom_rules:
        if "domain_suffix" not in geosite_rules:
            geosite_rules["domain_suffix"] = []
        for rule in custom_rules["domain_suffix"]:
            # 如果 rule 的域名后缀在 geosite_rules["domain_suffix"] 中，则跳过
            if any(rule.endswith(suffix) for suffix in geosite_rules["domain_suffix"]):
                print(f"Skipping rule: {rule} (already in domain_suffix)")
                continue
            if rule not in geosite_rules["domain_suffix"]:
                geosite_rules["domain_suffix"].append(rule)


def merge_ip_cidr(geosite_rules: dict, custom_rules: dict) -> None:
    """合并 IP CIDR 规则"""
    if "ip_cidr" in custom_rules:
        if "ip_cidr" not in geosite_rules:
            geosite_rules["ip_cidr"] = []
        for rule in custom_rules["ip_cidr"]:
            if rule not in geosite_rules["ip_cidr"]:
                geosite_rules["ip_cidr"].append(rule)


# 执行 sing-box rule-set decompile  geosite-cn.srs


def execute_sing_box(args="rule-set decompile tmp/geosite-cn.srs"):
    """
    执行 Sing Box
    :param args: 命令行参数
    :return:
    """
    if not os.path.exists("tmp/geosite-cn.srs"):
        print("geosite-cn.srs not found. Please download it first.")
        return

    print("Executing Sing Box...")
    try:
        cmd = [sing_box_bin] + args.split()
        print(f"Command: {cmd}")
        subprocess.run(cmd, check=True)
        print("Execution complete.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing Sing Box: {e}")


def merge_rules():
    """
    合并规则
    """

    # 读取自定义规则
    with open("rules.json", "r", encoding="utf-8") as f:
        custom_rules = json.load(f)

    # 读取解压后的 geosite-cn.json
    try:
        with open("tmp/geosite-cn.json", "r", encoding="utf-8") as f:

            data = json.load(f)
            geosite_rules = data["rules"][0]
    except FileNotFoundError:
        print(
            "Error: tmp/geosite-cn.json not found. Please run sing-box decompile first."
        )
        return

    print(f"当前规则键值: {geosite_rules.keys()}")

    # 分别处理每种规则
    merge_domain_regex(geosite_rules, custom_rules)
    merge_domain(geosite_rules, custom_rules)
    merge_domain_suffix(geosite_rules, custom_rules)
    merge_ip_cidr(geosite_rules, custom_rules)

    # 对所有规则进行排序
    rule_keys = ["domain_regex", "domain", "domain_suffix", "ip_cidr"]
    for key in rule_keys:
        geosite_rules[key].sort()

    data["rules"] = [geosite_rules]

    # 保存更新后的文件
    with open("tmp/geosite-one-cn.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Rules merged successfully.")

    execute_sing_box("rule-set compile tmp/geosite-one-cn.json")


# 将 tmp/*.srs 移动到 output 目录
def move_files():
    """
    将 tmp/*.srs 移动到 output 目录
    """
    os.makedirs("output", exist_ok=True)

    for file in os.listdir("tmp"):
        if file.endswith(".srs"):
            shutil.move(os.path.join("tmp", file), os.path.join("output", file))

    print("Files moved to output directory.")


if __name__ == "__main__":
    download_sing_box()
    download_geosite_cn()
    execute_sing_box()
    merge_rules()
    move_files()
