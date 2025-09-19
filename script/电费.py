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
        # 验证学号格式
        if not account or not account.strip():
            return None, "学号不能为空"
        
        account = account.strip()
        
        customercode = 1575
        url = "https://xqh5.17wanxiao.com/smartWaterAndElectricityService/SWAEServlet"
        
        data = {
            "param": f'{{"cmd":"h5_getstuindexpage","account":"{account}"}}',
            "customercode": customercode,
        }

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        
        timeout = aiohttp.ClientTimeout(total=30)  # 设置30秒超时
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=data, headers=headers) as response:
                if response.status == 200:
                    response_text = await response.text()
                    
                    try:
                        response_data = json.loads(response_text)
                    except json.JSONDecodeError:
                        return None, "服务器返回数据格式错误"
                    
                    if response_data.get("code_") == 0:
                        try:
                            body = json.loads(response_data["body"])
                        except json.JSONDecodeError:
                            return None, "服务器返回的主体数据格式错误"
                        
                        # 获取房间号
                        room_number = body.get('roomfullname', '未知房间')
                        
                        # 获取电费信息
                        modist = body.get("modlist", [])
                        current_power = None
                        
                        # 遍历modlist查找电费 - 支持多种可能的字段名
                        for item in modist:
                            if isinstance(item, dict):
                                # 尝试多种可能的电费字段名
                                for field in ['odd', 'power', 'electricity', '剩余电量', 'balance', 'elec', 'elec_balance']:
                                    if field in item and item[field] is not None and str(item[field]).strip():
                                        try:
                                            current_power = float(str(item[field]).strip())
                                            break
                                        except (ValueError, TypeError):
                                            continue
                                if current_power is not None:
                                    break
                        
                        # 如果没有找到电费信息，检查是否有其他电量相关字段
                        if current_power is None:
                            # 检查body中是否有直接的电量信息
                            for field in ['electricity', 'power', 'balance', '剩余电量', 'elec', 'elec_balance']:
                                if field in body and body[field] is not None and str(body[field]).strip():
                                    try:
                                        current_power = float(str(body[field]).strip())
                                        break
                                    except (ValueError, TypeError):
                                        continue
                        
                        if current_power is None:
                            return None, "该学号未绑定房间号或电费信息获取失败"
                        
                        # 检查电量值是否合理（0-99999度）
                        if not (0 <= current_power <= 99999):
                            return None, f"获取到的电量值异常: {current_power}"
                        
                        # 电量预警逻辑
                        warning_msg = ""
                        if current_power < 10:
                            warning_msg = "\n⚠️ 电量严重不足，请及时充值！"
                        elif current_power < 20:
                            warning_msg = "\n⚠️ 电量偏低，建议及时充值"
                        elif current_power < 50:
                            warning_msg = "\n💡 电量适中，注意合理使用"
                        
                        # 格式化电量显示，保留2位小数
                        result_msg = f"房间号: {room_number}\n当前电量: {current_power:.2f} 度{warning_msg}"
                        
                        # 添加查询时间
                        query_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        result_msg += f"\n查询时间: {query_time}"
                        
                        return room_number, result_msg
                    else:
                        error_msg = response_data.get('message_', '未知错误')
                        if '未绑定' in error_msg or '不存在' in error_msg:
                            return None, "该学号未绑定宿舍或学号不存在"
                        return None, f"查询失败: {error_msg}"
                else:
                    return None, f"请求失败: HTTP {response.status}"
                    
    except asyncio.TimeoutError:
        return None, "查询超时，请稍后重试"
    except aiohttp.ClientError as e:
        return None, f"网络连接失败: {str(e)}"
    except Exception as e:
        return None, f"查询出错: {str(e)}"

async def main(account: str):
    """主函数，返回电费信息"""
    if not account:
        return "请提供学号或快捷码\n使用方法: /电费 学号 或 /电费 快捷码"
    
    account = account.strip()
    
    # 验证输入格式
    if not account.replace('-', '').replace('_', '').isalnum():
        return "学号格式错误，只能包含字母、数字、下划线和连字符"
    
    # 长度验证
    if len(account) > 20:
        return "学号长度不能超过20位"
    
    # 检查是否为快捷码（纯数字且长度较短，2-6位）
    if account.isdigit() and 2 <= len(account) <= 6:
        # 尝试通过快捷码获取学号
        full_account = room_manager.get_room_by_shortcut(account)
        if full_account:
            room_name, result = await get_electricity_usage(full_account)
            if room_name:
                return result
            else:
                return result
        else:
            return f"未找到快捷码 {account} 对应的学号\n请先使用完整学号查询一次以建立映射"
    else:
        # 完整学号查询
        room_name, result = await get_electricity_usage(account)
        if room_name:
            # 检查是否已存在快捷码
            existing_shortcut = room_manager.get_shortcut_by_account(account)
            if existing_shortcut:
                return f"{result}\n\n快捷查询码: {existing_shortcut}"
            else:
                # 自动生成快捷码（学号后4位，如果不足4位则使用完整学号）
                if len(account) >= 4:
                    shortcut = account[-4:]
                elif len(account) >= 2:
                    shortcut = account[-2:]
                else:
                    shortcut = account
                
                # 确保快捷码唯一且长度适中（2-6位）
                base_shortcut = shortcut
                counter = 1
                while shortcut in room_manager.mapping or len(shortcut) < 2:
                    if len(shortcut) < 2:
                        shortcut = f"0{shortcut}"  # 补足长度
                    else:
                        shortcut = f"{base_shortcut}{counter}"
                    counter += 1
                    # 防止无限循环，限制快捷码长度
                    if counter > 99:
                        shortcut = f"e{account[-2:]}"  # 使用前缀避免冲突
                        break
                
                # 保存映射
                room_manager.add_mapping(shortcut, account, room_name)
                return f"{result}\n\n已为您生成快捷查询码: {shortcut}\n下次可直接使用 /电费 {shortcut} 查询"
        else:
            return result

def get_help_info():
    """获取帮助信息"""
    return """电费查询插件使用说明：

🔍 查询电费：
/电费 学号 - 使用完整学号查询
/电费 快捷码 - 使用快捷码查询

📌 快捷码功能：
首次使用学号查询后会自动生成快捷码
下次查询可直接使用快捷码，无需输入完整学号

⚡ 电量预警：
• <10度：⚠️ 电量严重不足，请及时充值！
• <20度：⚠️ 电量偏低，建议及时充值
• <50度：💡 电量适中，注意合理使用

🔧 管理员功能：
/电费绑定 - 查看所有绑定关系
/重载 - 重新加载脚本

💡 提示：
• 学号格式支持字母、数字、下划线、连字符
• 快捷码为2-6位数字
• 查询结果包含实时时间和房间信息"""

async def get_status_info():
    """获取插件状态信息"""
    try:
        total_bindings = len(room_manager.mapping)
        if total_bindings == 0:
            return "电费查询插件状态：未建立任何绑定关系"
        
        # 获取最近绑定的5个记录
        recent_bindings = []
        for shortcut, info in list(room_manager.mapping.items())[-5:]:
            recent_bindings.append(f"快捷码: {shortcut} -> 学号: {info['account']}")
        
        status_msg = f"""电费查询插件状态：
• 总绑定数: {total_bindings}
• 最近绑定:
{chr(10).join(recent_bindings)}"""
        
        return status_msg
    except Exception as e:
        return f"获取状态信息失败: {str(e)}"