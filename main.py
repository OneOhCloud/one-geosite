import os
import platform


def get_system_info():
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

    os_arch = arch_map.get(machine)
    if not os_arch:
        raise ValueError(f"不支持的系统架构: {machine}")

    os_platform = platform_map.get(system)
    if not os_platform:
        raise ValueError(f"不支持的操作系统: {system}")

    return os_platform, os_arch


os_platform, os_arch = get_system_info()

sing_box_ver = "1.11.7"

sing_box_url = f"https://github.com/SagerNet/sing-box/releases/download/v{sing_box_ver}/sing-box-{sing_box_ver}-{os_platform}-{os_arch}.tar.gz"
sing_box_bin = "tmp/sing-box"
geosite_cn_url = "https://raw.githubusercontent.com/SagerNet/sing-geosite/refs/heads/rule-set/geosite-cn.srs"


def download_sing_box():
    import requests
    import tarfile

    os.makedirs("tmp", exist_ok=True)

    def tar_filter(member, path):
        # 只允许 sing-box 可执行文件
        if member.name.endswith("sing-box"):
            member.name = os.path.basename(member.name)
            return member
        return None

    if not os.path.exists(sing_box_bin):
        print("Downloading Sing Box...")
        print(f"URL: {sing_box_url}")
        response = requests.get(sing_box_url)
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
    import requests

    os.makedirs("tmp", exist_ok=True)

    if not os.path.exists("tmp/geosite-cn.srs"):
        print("Downloading geosite-cn...")
        print(f"URL: {geosite_cn_url}")
        response = requests.get(geosite_cn_url)
        with open("tmp/geosite-cn.srs", "wb") as f:
            f.write(response.content)
        print("Download complete.")
    else:
        print("geosite-cn already downloaded.")


# 执行 sing-box rule-set decompile  geosite-cn.srs


def execute_sing_box(args="rule-set decompile tmp/geosite-cn.srs"):
    import subprocess

    if not os.path.exists("tmp/geosite-cn.srs"):
        print("geosite-cn.srs not found. Please download it first.")
        return

    print("Executing Sing Box...")
    try:
        cmd = [sing_box_bin] + args.split()
        print(f"Command: {cmd}")
        subprocess.run(
           cmd , check=True
        )
        print("Execution complete.")
    except subprocess.CalledProcessError as e:
        print(f"Error executing Sing Box: {e}")


def merge_rules():
    import json

    # 读取自定义规则
    with open("rules.json", "r") as f:
        custom_rules = json.load(f)

    # 读取解压后的 geosite-cn.json
    try:
        with open("tmp/geosite-cn.json", "r") as f:

            data = json.load(f)
            geosite_rules = data["rules"][0]
    except FileNotFoundError:
        print(
            "Error: tmp/geosite-cn.json not found. Please run sing-box decompile first."
        )
        return

    rule_keys = ["domain_regex", "domain", "domain_suffix"]
    print(geosite_rules.keys())

    for key in rule_keys:
        if key in custom_rules:
            if key not in geosite_rules:
                geosite_rules[key] = []
            for rule in custom_rules[key]:
                if rule not in geosite_rules[key]:
                    geosite_rules[key].append(rule)

        else:
            print(f"Warning: {key} not found in custom rules.")
    # 排序
    for key in rule_keys:
        geosite_rules[key].sort()

    data["rules"] = [geosite_rules]

    # 保存更新后的文件
    with open("tmp/geosite-one-cn.json", "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print("Rules merged successfully.")

    execute_sing_box(
        "rule-set compile tmp/geosite-one-cn.json"
    )

# 将 tmp/*.srs 移动到 output 目录
def move_files():
    import shutil

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

