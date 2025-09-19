from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import os
import importlib.util
import asyncio
from pathlib import Path

@register("script_task", "YourName", "一个动态执行脚本的插件", "1.2.0")
class ScriptTaskPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.script_dir = Path(__file__).parent / "script"
        self.script_dir.mkdir(exist_ok=True)
        self.scripts = {}  # 用于缓存已加载的脚本模块

    async def initialize(self):
        """初始化时扫描脚本目录"""
        await self.scan_scripts()

    async def scan_scripts(self):
        """扫描脚本目录，加载所有.py文件"""
        for file in self.script_dir.glob("*.py"):
            if file.stem.startswith("_"):  # 跳过以_开头的文件
                continue
            try:
                # 动态加载模块
                spec = importlib.util.spec_from_file_location(file.stem, file)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    self.scripts[file.stem] = module
                    logger.info(f"成功加载脚本: {file.stem}")
            except Exception as e:
                logger.error(f"加载脚本 {file.stem} 失败: {str(e)}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("script")
    async def list_scripts(self, event: AstrMessageEvent):
        """列出所有可用的脚本（管理员专用）"""
        if not self.scripts:
            yield event.plain_result("当前没有可用的脚本")
            return
        
        script_list = "\n".join([f"/{name}" for name in self.scripts.keys()])
        yield event.plain_result(f"可用的脚本列表：\n{script_list}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("reload")
    async def reload_scripts(self, event: AstrMessageEvent):
        """重新加载所有脚本（管理员专用）"""
        self.scripts.clear()
        await self.scan_scripts()
        yield event.plain_result("脚本重新加载完成")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("公网", args={})
    async def execute_script(self, event: AstrMessageEvent):
        """执行公网IP查询脚本（管理员专用）"""
        script_name = "公网ip"
        
        if script_name not in self.scripts:
            yield event.plain_result(f"未找到脚本: {script_name}")
            return

        try:
            script_module = self.scripts[script_name]
            if hasattr(script_module, 'main'):
                result = await script_module.main()
                yield event.plain_result(f"您的公网IP地址是：{result}")
            else:
                yield event.plain_result(f"脚本 {script_name} 没有 main 函数")
        except Exception as e:
            logger.error(f"执行脚本 {script_name} 时出错: {str(e)}")
            yield event.plain_result(f"执行脚本时出错: {str(e)}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("电费", args={"account": "学号/快捷码"})
    async def execute_electricity(self, event: AstrMessageEvent, account: str):
        """执行电费查询脚本（管理员专用）"""
        script_name = "电费"
        
        if script_name not in self.scripts:
            yield event.plain_result(f"未找到脚本: {script_name}")
            return

        try:
            script_module = self.scripts[script_name]
            if hasattr(script_module, 'main'):
                result = await script_module.main(account)
                yield event.plain_result(result)
            else:
                yield event.plain_result(f"脚本 {script_name} 没有 main 函数")
        except Exception as e:
            logger.error(f"执行脚本 {script_name} 时出错: {str(e)}")
            yield event.plain_result(f"执行脚本时出错: {str(e)}")

    @filter.permission_type(filter.PermissionType.ADMIN)
    @filter.command("电费绑定", args={})
    async def list_electricity_bindings(self, event: AstrMessageEvent):
        """查看电费查询绑定列表（管理员专用）"""
        script_name = "电费"
        
        if script_name not in self.scripts:
            yield event.plain_result(f"未找到脚本: {script_name}")
            return

        try:
            script_module = self.scripts[script_name]
            if hasattr(script_module, 'room_manager'):
                bindings = []
                for shortcut, info in script_module.room_manager.mapping.items():
                    bindings.append(f"快捷码: {shortcut} -> 学号: {info['account']} (房间: {info['room_name']})")
                
                if bindings:
                    result = "电费查询绑定列表：\n" + "\n".join(bindings)
                else:
                    result = "当前没有电费查询绑定记录"
                
                yield event.plain_result(result)
            else:
                yield event.plain_result("脚本不支持绑定管理功能")
        except Exception as e:
            logger.error(f"获取绑定列表时出错: {str(e)}")
            yield event.plain_result(f"获取绑定列表时出错: {str(e)}")

    async def terminate(self):
        """插件终止时的清理工作"""
        self.scripts.clear()
