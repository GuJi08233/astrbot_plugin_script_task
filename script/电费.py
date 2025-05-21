import aiohttp
import json
from datetime import datetime

async def get_electricity_usage(account: str):
    """获取电费使用情况"""
    try:
        customercode = 1575
        url = "https://xqh5.17wanxiao.com/smartWaterAndElectricityService/SWAEServlet"
        
        data = {
            "param": f'{{"cmd":"h5_getstuindexpage","account":"{account}"}}',
            "customercode": customercode,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    if response_data.get("code_") == 0:
                        body = json.loads(response_data["body"])
                        
                        # 获取房间号
                        room_number = body.get('roomfullname', '未知房间')
                        
                        # 获取电费信息
                        modist = body.get("modlist", [])
                        current_power = None
                        
                        # 遍历modlist查找电费
                        for item in modist:
                            if isinstance(item, dict) and 'odd' in item:
                                current_power = item['odd']
                                break
                        
                        if current_power is None:
                            return "该学号未绑定房间号或查询失败"
                            
                        return f"房间号: {room_number}\n当前电量: {current_power} 度"
                    else:
                        return f"查询失败: {response_data.get('message_', '未知错误')}"
                else:
                    return f"请求失败: HTTP {response.status}"
                    
    except Exception as e:
        return f"查询出错: {str(e)}"

async def main(account: str):
    """主函数，返回电费信息"""
    if not account:
        return "请提供学号"
    return await get_electricity_usage(account) 