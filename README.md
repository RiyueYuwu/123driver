<p align="center">
<h1 align="center">123Driver</h1>
</p>

## 项目背景

123云盘作为一个优秀的云盘服务商，相较于其他云盘服务商，有着更高的上传速度、下载速度、存储空间、安全性等优势。因此123云盘是我的主要使用的云盘服务。

但是，由于个人需求，经常想要将123云盘的功能集成到自己的应用中，而且我也看了下官方的开发文档，发现123云盘提供了丰富的API接口，包括文件管理、文件预览、文件搜索、文件下载等功能。

于是，我萌生了开发一个Python模块来调用123云盘API的想法，以方便自己和他人使用123云盘的API。

就此，123Driver项目诞生了。

## 项目目标

- ✅ 支持所有官方API端点
- ✅ 内置速率限制控制
- ✅ 异步HTTP客户端
- ✅ 完整的类型注解
- ✅ 错误处理和重试机制
- ✅ 详细的文档和示例

## 项目方案

利用httpx库实现123云盘api的调用，

## 项目结构

### 项目目录

```
123driver  #项目根目录
├──__init__.py
├──__version__.py
├──_api.py
├──_logger.py
├──_utils.py
├──_main.py
├──CHANGELOG.md
├──README.md
├──requirements.txt
├── ...
```

### 项目模块

- `_api.py`接口模块：封装123云盘的交互接口，包括登录、查询、预订等功能。
- `_main.py`主模块：封装项目的入口函数，包括命令行参数解析、日志配置等。
- `_logger.py`日志模块：封装项目的日志操作，包括记录日志、输出日志等。
- `_utils.py`工具模块：封装项目的工具函数，包括时间戳转换、随机数生成等。

### 项目流程

![123Driver流程图](https://i.loli.net/2021/08/15/2y.png)

### 项目工具

- httpx：异步HTTP客户端库，用于发起HTTP请求。
- loguru：日志库，用于记录日志。

## 项目进度

- [x] 项目背景
- [x] 项目目标
- [x] 项目方案
- [x] 项目结构
- [x] 项目模块
- [ ] 项目流程
- [x] 项目工具
- [ ] 项目进度
- [ ] 项目总结
- [ ] 项目反思
- [ ] 项目后续规划
- [ ] 项目参考资料
- [ ] 项目实例
- [x] 项目贡献者

## 项目总结

## 项目反思

## 项目后续规划

## 项目参考资料

## 项目实例

## 项目贡献者

感谢以下[代码贡献者](https://github.com/RiyueYuwu/123driver/graphs/contributors)和社区里其他成员对 `123Driver` 的贡献：

<a href="https://github.com/RiyueYuwu/123driver/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=RiyueYuwu/123driver" />
</a>