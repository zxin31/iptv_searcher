# IPTV搜索器

一个快速测试和获取IPTV链接的工具

## 功能特点
- ✅ 批量测试IPTV链接可用性
- ✅ 异步编程，测试速度快（最高可达每秒数百个链接）
- ✅ 支持多种导出格式（CSV、文本、M3U）
- ✅ 显示详细的测试结果和统计信息
- ✅ 支持只导出可用频道

## 安装依赖
```bash
pip install aiohttp requests
```

## 使用方法
```bash
python iptv_searcher.py
```

## 功能选项
1. 测试链接可用性
2. 导出为CSV文件
3. 导出为文本文件
4. 导出为M3U格式
5. 全部导出
6. 只导出可用频道(M3U格式)
0. 退出程序

## 技术栈
- Python 3.7+
- aiohttp - 异步HTTP客户端
- requests - HTTP客户端
- asyncio - 异步编程库

## 许可证
MIT
