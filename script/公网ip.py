import aiohttp
import asyncio

# 多个IP查询网站的备用方案
IP_QUERY_URLS = [
    'https://ip.3322.net',
    'https://api.ipify.org',
    'https://ifconfig.me',
    'https://api.ip.sb/ip',
    'https://httpbin.org/ip'
]

async def get_public_ip_from_url(session, url):
    """从指定URL获取公网IP"""
    try:
        async with session.get(url, timeout=10) as response:
            if response.status == 200:
                if 'httpbin.org' in url:
                    # httpbin.org返回的是JSON格式
                    data = await response.json()
                    return data.get('origin', '').split(',')[0].strip()
                else:
                    # 其他网站返回纯文本IP
                    ip = await response.text()
                    return ip.strip()
    except Exception as e:
        return None

async def get_public_ip():
    """获取公网IP地址（多备用方案）"""
    try:
        async with aiohttp.ClientSession() as session:
            # 按顺序尝试各个备用网站
            for url in IP_QUERY_URLS:
                ip = await get_public_ip_from_url(session, url)
                if ip and _is_valid_ip(ip):
                    return ip
            
            return "获取IP失败 - 所有备用网站均不可用"
    except Exception as e:
        return f"获取IP出错: {str(e)}"

def _is_valid_ip(ip):
    """简单的IP地址格式验证"""
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
    except:
        return False

async def main():
    """主函数，返回IP地址"""
    ip = await get_public_ip()
    return ip