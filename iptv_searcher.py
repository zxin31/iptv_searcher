import requests
import re
import time
import csv
import os
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures

def search_iptv_links():
    """
    搜索IPTV链接并返回频道名称和链接地址的列表
    """
    # 这里使用一个公开的IPTV列表源，实际使用时可以根据需要修改
    url = "https://iptv-org.github.io/iptv/index.m3u"
    
    # 重试次数和超时时间
    max_retries = 3
    timeout = 30  # 增加超时时间到30秒
    retry_delay = 5  # 重试间隔5秒
    
    for retry in range(max_retries):
        try:
            print(f"正在尝试获取IPTV链接 (尝试 {retry + 1}/{max_retries})...")
            # 获取IPTV列表数据
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            content = response.text
            
            # 使用正则表达式提取频道名称和链接
            # M3U格式通常是：#EXTINF:-1 tvg-name="频道名称" tvg-id="" group-title="",频道名称
            # 然后是链接地址
            pattern = r'#EXTINF:-1.*?,(.*?)\n(.*?)\n'
            matches = re.findall(pattern, content, re.DOTALL)
            
            # 整理结果，去重并过滤掉无效链接
            iptv_list = []
            seen = set()
            for name, link in matches:
                name = name.strip()
                link = link.strip()
                if link and link not in seen:
                    iptv_list.append({"name": name, "link": link, "status": "未测试"})
                    seen.add(link)
            
            return iptv_list
        except requests.exceptions.Timeout:
            print(f"请求超时，{retry_delay}秒后重试...")
            time.sleep(retry_delay)
        except Exception as e:
            print(f"搜索IPTV链接时出错：{e}")
            if retry < max_retries - 1:
                print(f"{retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                return []
    
    return []

def display_iptv_list(iptv_list):
    """
    以列表形式展示IPTV频道和链接
    """
    if not iptv_list:
        print("未找到IPTV链接")
        return
    
    print("\nIPTV频道列表：")
    print("=" * 90)
    print(f"{'序号':<5} {'频道名称':<30} {'链接地址':<40} {'状态':<10}")
    print("=" * 90)
    
    for index, item in enumerate(iptv_list, 1):
        name = item["name"]
        link = item["link"]
        status = item.get("status", "未测试")
        # 截断过长的名称和链接，以便更好地展示
        display_name = name[:27] + "..." if len(name) > 30 else name
        display_link = link[:37] + "..." if len(link) > 40 else link
        print(f"{index:<5} {display_name:<30} {display_link:<40} {status:<10}")
    
    print("=" * 90)
    print(f"共找到 {len(iptv_list)} 个IPTV频道")

async def async_test_single_link(session, channel, index, timeout=1):
    """
    异步测试单个IPTV链接是否可用
    
    参数:
        session: aiohttp会话对象
        channel: 包含频道信息的字典
        index: 频道序号
        timeout: 测试超时时间，默认为1秒
    
    返回:
        更新后的频道字典，包含测试结果
    """
    # 只测试HTTP/HTTPS链接，其他协议直接标记为需手动测试
    if not channel['link'].startswith(('http://', 'https://')):
        channel['status'] = "需手动测试"
        return channel, index
    
    try:
        # 使用HEAD请求，禁用重定向，设置较短超时
        async with session.head(
            channel['link'], 
            timeout=timeout, 
            allow_redirects=False,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*'
            }
        ) as response:
            if response.status < 400:
                channel['status'] = "可用"
            else:
                channel['status'] = "不可用"
    except asyncio.TimeoutError:
        channel['status'] = "超时"
    except aiohttp.ClientConnectionError:
        channel['status'] = "连接失败"
    except Exception:
        channel['status'] = "错误"
    
    return channel, index

async def async_test_iptv_links(iptv_list, max_concurrent=200, timeout=1):
    """
    异步批量测试IPTV链接是否可用
    
    参数:
        iptv_list: IPTV频道列表
        max_concurrent: 最大并发数，默认为200
        timeout: 每个链接的测试超时时间，默认为1秒
    
    返回:
        更新后的IPTV频道列表，包含测试结果
    """
    if not iptv_list:
        print("没有可测试的IPTV链接")
        return iptv_list
    
    print(f"\n正在异步测试 {len(iptv_list)} 个IPTV链接，并发数: {max_concurrent}，超时时间: {timeout}秒")
    print("=" * 60)
    
    # 创建TCP连接器，设置限制
    connector = aiohttp.TCPConnector(
        limit=max_concurrent,  # 最大并发连接数
        ttl_dns_cache=300,     # DNS缓存时间
        enable_cleanup_closed=True,
        limit_per_host=100     # 每个主机的最大连接数
    )
    
    completed = 0
    available_count = 0
    start_time = time.time()
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # 创建任务列表
        tasks = []
        for index, channel in enumerate(iptv_list):
            task = asyncio.ensure_future(async_test_single_link(session, channel, index, timeout))
            tasks.append(task)
        
        # 并发执行所有任务
        for future in asyncio.as_completed(tasks):
            try:
                channel, idx = await future
                iptv_list[idx] = channel
                completed += 1
                if channel['status'] == "可用":
                    available_count += 1
                # 减少打印频率以提高速度
                if completed % 200 == 0 or completed == len(iptv_list):
                    elapsed_time = time.time() - start_time
                    speed = completed / elapsed_time if elapsed_time > 0 else 0
                    print(f"已测试 {completed}/{len(iptv_list)} 个链接，可用: {available_count}，速度: {speed:.1f}个/秒")
            except Exception as e:
                print(f"测试出错: {e}")
                completed += 1
    
    elapsed_time = time.time() - start_time
    print(f"测试耗时: {elapsed_time:.2f}秒")
    print("=" * 60)
    # 统计测试结果
    total = len(iptv_list)
    available = available_count
    unavailable = sum(1 for c in iptv_list if c.get('status') in ['不可用', '超时', '连接失败', '错误'])
    manual = sum(1 for c in iptv_list if c.get('status') == '需手动测试')
    unknown = sum(1 for c in iptv_list if c.get('status') == '未知协议')
    
    print(f"测试完成！")
    print(f"总频道数: {total}")
    print(f"可用: {available} ({available/total*100:.1f}%)")
    print(f"不可用: {unavailable} ({unavailable/total*100:.1f}%)")
    print(f"需手动测试: {manual} ({manual/total*100:.1f}%)")
    print(f"未知协议: {unknown} ({unknown/total*100:.1f}%)")
    print(f"测试速度: {total/elapsed_time:.1f}个/秒")
    
    return iptv_list

def test_single_link(channel, index, timeout=1):
    """
    测试单个IPTV链接是否可用
    
    参数:
        channel: 包含频道信息的字典
        index: 频道序号
        timeout: 测试超时时间，默认为1秒
    
    返回:
        更新后的频道字典，包含测试结果
    """
    # 只测试HTTP/HTTPS链接，其他协议直接标记为需手动测试
    if not channel['link'].startswith(('http://', 'https://')):
        channel['status'] = "需手动测试"
        return channel, index
    
    try:
        # 使用GET请求但只获取响应头，禁用重定向以提高速度
        response = requests.get(
            channel['link'], 
            timeout=timeout, 
            allow_redirects=False, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': '*/*'
            },
            stream=True  # 流式请求，只获取响应头
        )
        # 立即关闭连接
        response.close()
        # 只检查状态码，不处理响应内容
        if response.status_code < 400:
            channel['status'] = "可用"
        else:
            channel['status'] = "不可用"
    except requests.exceptions.Timeout:
        channel['status'] = "超时"
    except requests.exceptions.ConnectionError:
        channel['status'] = "连接失败"
    except Exception:
        # 简化错误处理，不获取详细错误信息
        channel['status'] = "错误"
    
    return channel, index

def test_iptv_links(iptv_list, max_workers=200, timeout=1):
    """
    批量测试IPTV链接是否可用，优先使用异步方式
    
    参数:
        iptv_list: IPTV频道列表
        max_workers: 最大并发数，默认为200
        timeout: 每个链接的测试超时时间，默认为1秒
    
    返回:
        更新后的IPTV频道列表，包含测试结果
    """
    try:
        # 尝试使用异步方式测试
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(async_test_iptv_links(iptv_list, max_concurrent=max_workers, timeout=timeout))
    except Exception as e:
        print(f"异步测试失败，使用线程池方式: {e}")
        # 回退到线程池方式
        if not iptv_list:
            print("没有可测试的IPTV链接")
            return iptv_list
        
        print(f"\n正在测试 {len(iptv_list)} 个IPTV链接，并发数: {max_workers}，超时时间: {timeout}秒")
        print("=" * 60)
        
        start_time = time.time()
        # 使用线程池并发测试
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建任务
            future_to_channel = {
                executor.submit(test_single_link, channel, index, timeout): index
                for index, channel in enumerate(iptv_list)
            }
            
            # 处理结果
            completed = 0
            available_count = 0
            for future in concurrent.futures.as_completed(future_to_channel):
                index = future_to_channel[future]
                try:
                    channel, idx = future.result()
                    iptv_list[idx] = channel
                    completed += 1
                    if channel['status'] == "可用":
                        available_count += 1
                    # 减少打印频率以提高速度
                    if completed % 200 == 0 or completed == len(iptv_list):
                        elapsed_time = time.time() - start_time
                        speed = completed / elapsed_time if elapsed_time > 0 else 0
                        print(f"已测试 {completed}/{len(iptv_list)} 个链接，可用: {available_count}，速度: {speed:.1f}个/秒")
                except Exception as e:
                    print(f"测试频道 {index + 1} 时出错: {e}")
                    completed += 1
        
        elapsed_time = time.time() - start_time
        print(f"测试耗时: {elapsed_time:.2f}秒")
        print("=" * 60)
        # 统计测试结果
        total = len(iptv_list)
        available = available_count
        unavailable = sum(1 for c in iptv_list if c.get('status') in ['不可用', '超时', '连接失败', '错误'])
        manual = sum(1 for c in iptv_list if c.get('status') == '需手动测试')
        unknown = sum(1 for c in iptv_list if c.get('status') == '未知协议')
        
        print(f"测试完成！")
        print(f"总频道数: {total}")
        print(f"可用: {available} ({available/total*100:.1f}%)")
        print(f"不可用: {unavailable} ({unavailable/total*100:.1f}%)")
        print(f"需手动测试: {manual} ({manual/total*100:.1f}%)")
        print(f"未知协议: {unknown} ({unknown/total*100:.1f}%)")
        print(f"测试速度: {total/elapsed_time:.1f}个/秒")
        
        return iptv_list

def export_to_csv(iptv_list, filename="iptv_channels.csv"):
    """
    将IPTV频道列表导出为CSV文件
    
    参数:
        iptv_list: IPTV频道列表
        filename: 导出的文件名，默认为iptv_channels.csv
    """
    if not iptv_list:
        print("没有可导出的IPTV链接")
        return
    
    try:
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['序号', '频道名称', '链接地址', '状态']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            writer.writeheader()
            for index, item in enumerate(iptv_list, 1):
                writer.writerow({
                    '序号': index,
                    '频道名称': item['name'],
                    '链接地址': item['link'],
                    '状态': item.get('status', '未测试')
                })
        
        print(f"\n已成功将 {len(iptv_list)} 个IPTV频道导出到 {os.path.abspath(filename)}")
    except Exception as e:
        print(f"导出CSV文件时出错：{e}")

def export_to_txt(iptv_list, filename="iptv_channels.txt"):
    """
    将IPTV频道列表导出为文本文件
    
    参数:
        iptv_list: IPTV频道列表
        filename: 导出的文件名，默认为iptv_channels.txt
    """
    if not iptv_list:
        print("没有可导出的IPTV链接")
        return
    
    try:
        with open(filename, 'w', encoding='utf-8') as txtfile:
            txtfile.write("IPTV频道列表\n")
            txtfile.write("=" * 100 + "\n")
            txtfile.write(f"{'序号':<5} {'频道名称':<30} {'链接地址':<50} {'状态':<15}\n")
            txtfile.write("=" * 100 + "\n")
            
            for index, item in enumerate(iptv_list, 1):
                status = item.get('status', '未测试')
                txtfile.write(f"{index:<5} {item['name']:<30} {item['link']:<50} {status:<15}\n")
        
        print(f"已成功将 {len(iptv_list)} 个IPTV频道导出到 {os.path.abspath(filename)}")
    except Exception as e:
        print(f"导出文本文件时出错：{e}")

def export_to_m3u(iptv_list, filename="iptv_channels.m3u", only_available=False):
    """
    将IPTV频道列表导出为M3U格式文件
    
    参数:
        iptv_list: IPTV频道列表
        filename: 导出的文件名，默认为iptv_channels.m3u
        only_available: 是否只导出可用的频道，默认为False
    """
    if not iptv_list:
        print("没有可导出的IPTV链接")
        return
    
    # 过滤可用的频道（如果需要）
    if only_available:
        filtered_list = [c for c in iptv_list if c.get('status') == '可用']
        print(f"过滤后导出 {len(filtered_list)} 个可用频道")
    else:
        filtered_list = iptv_list
    
    try:
        with open(filename, 'w', encoding='utf-8') as m3ufile:
            # M3U文件头
            m3ufile.write("#EXTM3U\n")
            
            for item in filtered_list:
                m3ufile.write(f"#EXTINF:-1 tvg-name=\"{item['name']}\" tvg-id=\"\" group-title=\"\",{item['name']}\n")
                m3ufile.write(f"{item['link']}\n")
        
        print(f"已成功将 {len(filtered_list)} 个IPTV频道导出为M3U格式到 {os.path.abspath(filename)}")
    except Exception as e:
        print(f"导出M3U文件时出错：{e}")

def main():
    """
    主函数
    """
    print("正在搜索IPTV链接...")
    iptv_list = search_iptv_links()
    
    if not iptv_list:
        print("未找到任何IPTV链接，程序退出")
        return
    
    # 自动测试所有链接的连通性
    print("\n自动测试所有链接的连通性...")
    iptv_list = test_iptv_links(iptv_list, max_workers=300, timeout=1)
    
    # 计算可连通的频道数量
    available_count = sum(1 for ch in iptv_list if ch['status'] == '可用')
    # 直接显示可连通的数量
    print(f"\n测试完成！可连通的频道数量：{available_count} 个")
    
    # 显示测试结果
    display_iptv_list(iptv_list)
    
    # 显示功能选项
    print("\n功能选项：")
    print("1. 重新测试链接可用性")
    print("2. 导出为CSV文件")
    print("3. 导出为文本文件")
    print("4. 导出为M3U格式")
    print("5. 全部导出")
    print("6. 只导出可用频道(M3U格式)")
    print("0. 退出程序")
    
    try:
        choice = input("请选择功能选项 (0-6): ")
        
        if choice == "1":
            # 重新测试链接
            iptv_list = test_iptv_links(iptv_list, max_workers=300, timeout=1)
            # 显示测试结果
            display_iptv_list(iptv_list)
            # 计算可连通的频道数量
            available_count = sum(1 for ch in iptv_list if ch['status'] == '可用')
            # 用更显眼的格式显示可连通的数量
            print(f"\n" + "="*60)
            print(f"🎯 测试完成！可连通的频道数量：{available_count} 个")
            print(f"="*60)
        elif choice == "2":
            export_to_csv(iptv_list)
        elif choice == "3":
            export_to_txt(iptv_list)
        elif choice == "4":
            export_to_m3u(iptv_list)
        elif choice == "5":
            export_to_csv(iptv_list)
            export_to_txt(iptv_list)
            export_to_m3u(iptv_list)
        elif choice == "6":
            # 导出可用的频道
            export_to_m3u(iptv_list, "iptv_available_channels.m3u", only_available=True)
        elif choice == "0":
            print("已退出程序")
        else:
            print("无效选项，已退出程序")
    except KeyboardInterrupt:
        print("\n已取消操作")
    except Exception as e:
        print(f"操作过程中出错：{e}")

if __name__ == "__main__":
    main()