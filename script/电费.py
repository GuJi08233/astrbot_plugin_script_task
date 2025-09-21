import aiohttp
import asyncio
import json
import os
from pathlib import Path

class RoomManager:
    """房间绑定管理器"""
    def __init__(self):
        self.config_file = Path(__file__).parent / "electricity_bindings.json"
        self.mapping = {}
        self.load_bindings()
    
    def load_bindings(self):
        """加载绑定配置"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self.mapping = json.load(f)
            except Exception as e:
                print(f"加载绑定配置失败: {e}")
                self.mapping = {}
    
    def save_bindings(self):
        """保存绑定配置"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存绑定配置失败: {e}")
    
    def add_binding(self, shortcut, account, room_name=""):
        """添加绑定"""
        self.mapping[shortcut] = {
            "account": account,
            "room_name": room_name,
            "created_at": asyncio.get_event_loop().time()
        }
        self.save_bindings()
    
    def get_account(self, shortcut):
        """通过快捷码获取学号"""
        if shortcut in self.mapping:
            return self.mapping[shortcut]["account"]
        return None
    
    def remove_binding(self, shortcut):
        """移除绑定"""
        if shortcut in self.mapping:
            del self.mapping[shortcut]
            self.save_bindings()
            return True
        return False

# 全局房间管理器实例
room_manager = RoomManager()

async def ele_usage(account):
    """查询电费信息"""
    try:
        customercode = 1575  # 直接硬编码customercode
        
        url = "https://xqh5.17wanxiao.com/smartWaterAndElectricityService/SWAEServlet"
        
        data = {
            "param": f'{{"cmd":"h5_getstuindexpage","account":"{account}"}}',
            "customercode": customercode,
        }
        
        # 使用aiohttp进行异步请求
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=data, ssl=True) as response:
                if response.status == 200:
                    response_data = await response.json()
                    
                    if response_data.get("code_") == 0:
                        body = json.loads(response_data["body"])
                        
                        # 获取房间号
                        room_number = body.get('roomfullname', [])
                        
                        # 获取电费信息
                        modist = body.get("modlist", [])
                        current_power = None
                        weekuselist = None
                        
                        # 遍历modlist查找电费和用电记录
                        for item in modist:
                            if not isinstance(item, dict):
                                continue
                            
                            # 获取当前电费
                            if 'odd' in item:
                                current_power = item['odd']
                            
                            # 获取周用电记录
                            if 'weekuselist' in item:
                                weekuselist = item['weekuselist']
                        
                        # 处理周用电数据
                        weekly_usage = []
                        if weekuselist:
                            for week in weekuselist:
                                if isinstance(week, dict):
                                    usage_entry = {
                                        "date": week.get('date', '未知日期'),
                                        "usage": week.get('dayuse', '0'),
                                        "day_of_week": week.get('weekday', '未知')
                                    }
                                    weekly_usage.append(usage_entry)
                        
                        # 构建返回数据
                        return {
                            "status_code": 200,
                            "room_number": room_number,
                            "current_power": current_power if current_power is not None else '该学号未绑定房间号',
                            "weekly_usage": weekly_usage
                        }
                    else:
                        # API 返回错误
                        return {
                            "status_code": response_data.get("code_"),
                            "error_message": response_data.get("message_", "未知错误")
                        }
                else:
                    # HTTP 请求失败
                    return {
                        "status_code": response.status,
                        "error_message": "HTTP请求失败"
                    }
    
    except json.JSONDecodeError as e:
        return {
            "status_code": 500,
            "error_message": "数据格式错误"
        }
    except Exception as e:
        return {
            "status_code": 500,
            "error_message": f"系统错误: {str(e)}"
        }

async def main(account=None):
    """主函数，处理电费查询"""
    try:
        if not account:
            return "请输入学号，格式：电费 20225080905096"
        
        # 检查是否是快捷码
        actual_account = room_manager.get_account(account)
        if actual_account:
            account = actual_account
        
        # 调用函数并获取结果
        result = await ele_usage(account)
        
        # 处理返回结果
        if result["status_code"] == 200:
            response_lines = []
            response_lines.append("电费查询成功！")
            response_lines.append(f"房间号: {result['room_number']}")
            
            if isinstance(result['current_power'], (int, float)):
                response_lines.append(f"当前电量: {result['current_power']} 度")
            else:
                response_lines.append(f"当前电量: {result['current_power']}")
            
            if result["weekly_usage"]:
                response_lines.append("\n最近一周用电情况:")
                response_lines.append("-" * 20)
                for day in result["weekly_usage"]:
                    response_lines.append(f"{day['date']} ({day['day_of_week']}): {day['usage']} 度")
            
            # 如果是新查询的学号，询问是否绑定房间号
            if account not in room_manager.mapping.values():
                response_lines.append("\n💡 提示：您可以绑定房间号，方便下次查询")
                response_lines.append("使用方法：绑定房间 房间号 学号")
            
            return "\n".join(response_lines)
        else:
            return f"查询失败！\n错误信息: {result['error_message']}"
            
    except Exception as e:
        return f"发生未知错误：{str(e)}"

async def bind_room(shortcut, account):
    """绑定房间号"""
    try:
        # 先查询一次验证学号是否有效
        result = await ele_usage(account)
        
        if result["status_code"] == 200:
            room_name = result.get("room_number", "未知房间")
            room_manager.add_binding(shortcut, account, room_name)
            return f"绑定成功！\n房间号: {shortcut} -> 学号: {account}\n房间: {room_name}"
        else:
            return f"绑定失败！学号无效或查询出错: {result['error_message']}"
    
    except Exception as e:
        return f"绑定过程出错：{str(e)}"

async def unbind_room(shortcut):
    """解除绑定"""
    if room_manager.remove_binding(shortcut):
        return f"解除绑定成功！房间号 {shortcut} 已删除"
    else:
        return f"解除绑定失败！未找到房间号 {shortcut}"

# 测试函数
if __name__ == "__main__":
    async def test():
        # 测试查询
        result = await main("20225080905096")
        print(result)
    
    asyncio.run(test())