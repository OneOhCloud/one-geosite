# 🌐 适用 sing-box 项目的规则集

本项目提供适用于 sing-box 代理工具的中国大陆网站分流规则集。主要功能是帮助用户更好地管理国内外网站的访问路由。

## 📚 规则集说明

本项目包含两个规则集：

### 1. 基础规则集 ⚡️

此规则集直接采用 sing-box 官方维护的中国大陆网站域名列表，确保基础分流的准确性：

```
https://fastly.jsdelivr.net/gh/OneOhCloud/one-geosite@rules/geosite-cn.srs
```

### 2. 增强规则集 🚀

此规则集基于服务器访问日志分析得出，包含更多未被收录的中国大陆网站域名，提供更全面的分流支持：

```bash
https://fastly.jsdelivr.net/gh/OneOhCloud/one-geosite@rules/geosite-one-cn.srs
```

## 🔧 使用方法

1. 📥 在 sing-box 配置文件中引用规则集
2. 📋 将规则集 URL 复制到相应的规则配置部分
3. 🔄 重启 sing-box 使配置生效

## ⏰ 更新周期

规则集定期更新，确保规则的时效性和准确性.