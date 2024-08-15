import logging
import os
import csv
from datetime import datetime
from pkg.plugin.models import *
from pkg.plugin.host import EventContext, PluginHost

@register(name="cvs_format_save", description="以cvs格式存储对话并按日期创建文件夹", version="1.0.2", author="Zogur")
class ConversationLoggerPlugin(Plugin):
    def __init__(self, plugin_host: PluginHost):
        self.plugin_host = plugin_host
        self.base_path = os.path.join(os.path.dirname(__file__), "conversation_logs")
        self.logger =logging.getLogger("ConversationLoggerPlugin")
        self.logger.setLevel(logging.DEBUG)
        self.ensure_base_path()

    def ensure_base_path(self):
        """确保基础路径存在"""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            self.logger.info(f"创建基础路径: {self.base_path}")

    def get_log_path(self, is_group_chat):
        """根据当前日期和对话类型生成日志文件路径"""
        now = datetime.now()
        year_month_day = now.strftime("%Y/%m/%d")
        chat_type = "group" if is_group_chat else "private"
        file_name = f"conversation_{chat_type}_{now.strftime('%Y-%m-%d')}.csv"
        full_path = os.path.join(self.base_path, year_month_day)
        
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            self.logger.info(f"创建日期文件夹: {full_path}")
        
        return os.path.join(full_path, file_name)

    @on(NormalMessageResponded)
    def log_conversation(self, event: EventContext, **kwargs):
        # 对话事件
        self.logger.debug("开始记录对话")
        try:
            query = kwargs.get('query')
            response_text = kwargs.get('response_text')

            if query is None or response_text is None:
                self.logger.warning("kwargs 中缺少必要的信息")
                return

            sender_id = query.get('sender_id')
            message_event = query.get('message_event', {})
            sender = message_event.get('sender', {})
            is_group_chat = 'member_name' in sender
            
            if is_group_chat:
                sender_name = sender.get('member_name', 'Unknown')
            else:
                sender_name = sender.get('nickname', 'Unknown')

            message_chain = message_event.get('message_chain', [])
            user_message = next((item['text'] for item in message_chain if item.get('type') == 'Plain'), "")

            if not sender_id or not user_message:
                self.logger.warning("无法获取发送者ID或用户消息")
                return

            log_path = self.get_log_path(is_group_chat)
            self.logger.info(f"正在将对话记录到: {log_path}")

            # 检查文件是否存在，如果不存在则创建并写入表头
            file_exists = os.path.isfile(log_path)
            with open(log_path, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(['Timestamp', 'Chat Type', 'Sender ID', 'Sender Name', 'Role', 'Content'])

                # 写入用户消息
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Group' if is_group_chat else 'Private',
                    sender_id,
                    sender_name,
                    'user',
                    user_message
                ])

                # 写入AI响应
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'Group' if is_group_chat else 'Private',
                    'AI',
                    'AI Assistant',
                    'assistant',
                    response_text
                ])

            self.logger.info("对话记录成功保存")

        except Exception as e:
            self.logger.error(f"记录对话时发生错误: {str(e)}")

    def __del__(self):
        self.logger.info("cvs_format_save 插件已卸载")