import logging
import os
import csv
from datetime import datetime
from pkg.plugin.models import *
from pkg.plugin.host import EventContext, PluginHost

@register(name="csv_format_save", description="以csv格式存储所有对话", version="1.1.1", author="Zogur")
class ConversationLoggerPlugin(Plugin):
    def __init__(self, plugin_host: PluginHost):
        self.plugin_host = plugin_host
        self.base_path = os.path.join(os.path.dirname(__file__), "conversation_logs")
        self.logger = logging.getLogger("ConversationLogger")
        self.logger.setLevel(logging.DEBUG)
        self.ensure_base_path()

    def ensure_base_path(self):
        """确保基础路径存在"""
        if not os.path.exists(self.base_path):
            os.makedirs(self.base_path)
            self.ap.logger.info(f"创建基础路径: {self.base_path}")

    def get_log_path(self):
        """生成日志文件路径"""
        now = datetime.now()
        year_month = now.strftime("%Y/%m")
        full_path = os.path.join(self.base_path, year_month)
        
        if not os.path.exists(full_path):
            os.makedirs(full_path)
            self.ap.logger.info(f"创建年月文件夹: {full_path}")
        
        file_name = f"conversation_{now.strftime('%d')}.csv"
        return os.path.join(full_path, file_name)

    @on(NormalMessageResponded)
    def log_conversation(self, event: EventContext, **kwargs):
        self.ap.logger.info("开始记录对话")
        try:
            query = kwargs.get('query')
            response_text = kwargs.get('response_text')

            if query is None or response_text is None:
                self.ap.logger.info("kwargs 中缺少必要的信息")

            sender_id = query.get('sender_id')
            message_event = query.get('message_event', {})
            sender = message_event.get('sender', {})
            is_group_chat = 'member_name' in sender
            
            chat_type = 'Group' if is_group_chat else 'Private'

            message_chain = message_event.get('message_chain', [])
            user_message = next((item['text'] for item in message_chain if item.get('type') == 'Plain'), "")

            if not sender_id or not user_message:
                self.ap.logger.warning("无法获取发送者ID或用户消息")

            log_path = self.get_log_path()
            self.ap.logger.info(f"正在将对话记录到: {log_path}")

            # 检查文件是否存在，如果不存在则创建并写入表头
            file_exists = os.path.isfile(log_path)
            with open(log_path, 'a', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                if not file_exists:
                    writer.writerow(['Timestamp', 'Chat Type', 'Sender ID', 'query', 'Content'])

                # 写入用户消息和AI响应
                writer.writerow([
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    chat_type,
                    sender_id,
                    user_message,  # query 字段是用户的问题
                    response_text  # Content 字段是AI的回复
                ])

            self.ap.logger.info("对话记录成功保存")

        except Exception as e:
            self.ap.logger.error(f"记录对话时发生错误: {str(e)}")

    def __del__(self):
        self.ap.logger.info("csv_format_save 插件已卸载")