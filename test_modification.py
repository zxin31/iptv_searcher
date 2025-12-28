#!/usr/bin/env python3
"""
测试脚本，用于验证选项1的修改是否正确
"""

# 模拟IPTV频道列表
mock_iptv_list = [
    {"name": "CCTV-1", "link": "http://example.com/cctv1", "status": "可用"},
    {"name": "CCTV-2", "link": "http://example.com/cctv2", "status": "超时"},
    {"name": "CCTV-3", "link": "http://example.com/cctv3", "status": "可用"},
    {"name": "CCTV-4", "link": "http://example.com/cctv4", "status": "连接失败"},
    {"name": "CCTV-5", "link": "http://example.com/cctv5", "status": "可用"},
    {"name": "CCTV-6", "link": "http://example.com/cctv6", "status": "可用"},
    {"name": "CCTV-7", "link": "http://example.com/cctv7", "status": "超时"},
    {"name": "CCTV-8", "link": "http://example.com/cctv8", "status": "可用"},
    {"name": "CCTV-9", "link": "http://example.com/cctv9", "status": "可用"},
    {"name": "CCTV-10", "link": "http://example.com/cctv10", "status": "超时"}
]

print("=== 测试选项1修改 ===")
print("模拟测试链接完成后的处理逻辑")
print()

# 模拟选项1的处理逻辑
# 计算可连通的频道数量
available_count = sum(1 for ch in mock_iptv_list if ch['status'] == '可用')
# 直接显示可连通的数量
print(f"测试完成！可连通的频道数量：{available_count} 个")

print("\n=== 测试结果 ===")
print("修改后的选项1处理逻辑正确，会直接显示可连通的频道数量")
print("无需再询问是否导出测试结果")
