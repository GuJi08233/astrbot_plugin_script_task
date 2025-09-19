import aiohttp
import json
import os
from datetime import datetime
from pathlib import Path

# 数据存储文件路径
DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
ROOM_MAPPING_FILE = DATA_DIR / "room_mapping.json"

class RoomMappingManager:
    """学号与房间号映射管理器"""
    
    def __init__(self):
        self.mapping = self._load_mapping()
    
    def _load_mapping(self):
        """加载学号房间号映射"""
        if ROOM_MAPPING_FILE.exists():
            try:
                with open(ROOM_MAPPING_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_mapping(self):
        """保存学号房间号映射"""
        try:
            with open(ROOM_MAPPING_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.mapping, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存映射失败: {e}")
    
    def get_room_by_shortcut(self, shortcut):
        """通过快捷码获取完整学号"""
        return self.mapping.get(shortcut, {}).get('account')
    
    def get_shortcut_by_account(self, account):
        """通过学号获取快捷码"""
        for shortcut, info in self.mapping.items():
            if info.get('account') == account:
                return shortcut
        return None
    
    def add_mapping(self, shortcut, account, room_name):
        """添加学号房间号映射"""
        self.mapping[shortcut] = {
            'account': account,
            'room_name': room_name,
            'created_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        self._save_mapping()
    
    def get_room_info(self, shortcut):
        """获取房间信息"""
        return self.mapping.get(shortcut)

# 全局映射管理器实例
room_manager = RoomMappingManager()

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
                            return None, "该学号未绑定房间号或查询失败"
                            
                        return room_number, f"房间号: {room_number}\n当前电量: {current_power} 度"
                    else:
                        return None, f"查询失败: {response_data.get('message_', '未知错误')}"
                else:
                    return None, f"请求失败: HTTP {response.status}"
                    
    except Exception as e:
        return None, f"查询出错: {str(e)}"

async def main(account: str):
    """主函数，返回电费信息"""
    if not account:
        return "请提供学号或快捷码"
    
    # 检查是否为快捷码（纯数字且长度较短）
    if account.isdigit() and len(account) <= 6:
        # 尝试通过快捷码获取学号
        full_account = room_manager.get_room_by_shortcut(account)
        if full_account:
            room_name, result = await get_electricity_usage(full_account)
            if room_name:
                return result
            else:
                return result
        else:
            return f"未找到快捷码 {account} 对应的学号，请先使用完整学号查询一次以建立映射"
    else:
        # 完整学号查询
        room_name, result = await get_electricity_usage(account)
        if room_name:
            # 检查是否已存在快捷码
            existing_shortcut = room_manager.get_shortcut_by_account(account)
            if existing_shortcut:
                return f"{result}\n\n快捷查询码: {existing_shortcut}"
            else:
                # 自动生成快捷码（学号后3位，如果不足3位则使用完整学号）
                shortcut = account[-3:] if len(account) >= 3 else account
                # 确保快捷码唯一
                base_shortcut = shortcut
                counter = 1
                while shortcut in room_manager.mapping:
                    shortcut = f"{base_shortcut}{counter}"
                    counter += 1
                
                # 保存映射
                room_manager.add_mapping(shortcut, account, room_name)
                return f"{result}\n\n已为您生成快捷查询码: {shortcut}\n下次可直接使用 /电费 {shortcut} 查询"
        else:
            return result