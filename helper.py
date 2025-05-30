# 提取主域名
import json


def get_main_domain(domain: str):
    """获取主域名"""
    if domain.count(".") > 1:
        return ".".join(domain.split(".")[-2:])
    return domain


# 从列表中去掉重复的域名
def remove_duplicates_from_list(domain_list: list[str]):
    """
    如果域名列表中有重复的域名，则删除。
    如果有多个相同的主域名的子域名，则删除子域名，只保留主域名
    """
    data = sorted(set(domain_list))
    print("去重前: ", len(domain_list))
    # 提取主域名
    domain_suffix_list = []
    for domain in data:
        domain_suffix_list.append(get_main_domain(domain))

    domain_suffix_list = sorted(domain_suffix_list)

    domain_suffix_unique_list = list(set(domain_suffix_list))

    ready_delete_domain_list = []

    for i in domain_suffix_unique_list:
        # 如果 i 在 domain_suffix_list 中出现多次，则删除
        if domain_suffix_list.count(i) > 1:
            ready_delete_domain_list.append(i)

    new_domain_list = []

    for domain in domain_list:
        for i in ready_delete_domain_list:
            if domain.endswith(i):
                print("删除重复的域名: ", domain)
                new_domain_list.append(i)
                break
        else:
            new_domain_list.append(domain)

    print("去重后: ", len(new_domain_list))

    return sorted(set(new_domain_list))


def sort_rule_file():
    """对规则文件进行排序"""
    # pylint: disable=W0621
    with open("rules.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # 排序
    data["domain_suffix"] = sorted(set(data["domain_suffix"]))

    domain_suffix = data["domain_suffix"]

    domain_suffix = remove_duplicates_from_list(domain_suffix)

    data["domain_suffix"] = domain_suffix

    # 保存规则
    with open("rules.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
