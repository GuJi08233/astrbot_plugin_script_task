import aiohttp
import asyncio

async def get_public_ip():
    """获取公网IP地址"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get('https://api.ipify.org?format=json') as response:
                if response.status == 200:
                    data = await response.json()
                    return data['ip']
                else:
                    return "获取IP失败"
    except Exception as e:
        return f"获取IP出错: {str(e)}"

async def main():
    """主函数，返回IP地址"""
    ip = await get_public_ip()
    return ip 