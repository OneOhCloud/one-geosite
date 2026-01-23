# 🌐 介绍

本仓库提供两套中国大陆网站域名分流规则，方便在 sing-box 中直接引用以优化国内流量走向。


## 规则集：

其中 **增强规则集** 包含了基础规则集的所有内容，增强部分为处理约 **15 万条/周** 来自生产环境的新增域名请求。


### 基础规则集：

```txt 
https://fastly.jsdelivr.net/gh/OneOhCloud/one-geosite@rules/geosite-cn.srs
```

### 增强规则集：
```txt
https://fastly.jsdelivr.net/gh/OneOhCloud/one-geosite@rules/geosite-one-cn.srs
```