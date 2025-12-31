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





改进其流程：

1.获取域名列表
2.判断是否为中国域名
3.如果是中国域名则追加放入预处理的列表 txt 文件
4.对预处理列表进行去重，检查443端口可访问性，如果只有一个域名则放入rules.json中，若有多个子域名，则其中有一个可访问，则将主域名和可访问的子域名放回预处理列表文件中，并将主域名放入到rules.json中。

