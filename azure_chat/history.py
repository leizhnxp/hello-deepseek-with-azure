"""
聊天历史记录模块，负责管理跨会话的历史记录
"""

import os
import json
import time
import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple


class ChatHistory:
    """聊天历史记录类，负责管理跨会话的历史记录"""
    def __init__(self, history_file: str = None):
        """初始化聊天历史记录
        
        Args:
            history_file: 历史记录文件路径，默认为用户主目录下的 .azure_chat_history.json
        """
        if history_file is None:
            home_dir = str(Path.home())
            self.history_file = os.path.join(home_dir, ".azure_chat_history.json")
        else:
            self.history_file = history_file
        
        # 确保历史记录文件存在
        if not os.path.exists(self.history_file):
            # 创建空的历史记录文件
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def save_session(self, messages: List[Dict[str, Any]]) -> None:
        """保存当前会话到历史记录
        
        Args:
            messages: 当前会话的消息列表
        """
        # 跳过只有系统消息的会话
        if len(messages) <= 1:
            return
            
        # 转换消息格式，只保留角色和内容
        simplified_messages = []
        for msg in messages:
            if hasattr(msg, "role") and hasattr(msg, "content"):
                simplified_messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
            elif isinstance(msg, dict) and "role" in msg and "content" in msg:
                simplified_messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # 读取现有历史记录
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            history = []
        
        # 添加新会话，包含时间戳
        history.append({
            "timestamp": datetime.datetime.now().isoformat(),
            "messages": simplified_messages
        })
        
        # 保存更新后的历史记录
        with open(self.history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    
    def load_history(self) -> List[Dict[str, Any]]:
        """加载历史记录
        
        Returns:
            历史记录列表
        """
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    
    def get_session_count(self) -> int:
        """获取历史会话数量
        
        Returns:
            历史会话数量
        """
        history = self.load_history()
        return len(history)
    
    def get_session(self, index: int) -> Tuple[str, List[Dict[str, str]]]:
        """获取指定索引的历史会话
        
        Args:
            index: 会话索引
            
        Returns:
            (时间戳, 消息列表)
        """
        history = self.load_history()
        if 0 <= index < len(history):
            session = history[index]
            return session["timestamp"], session["messages"]
        return "", []
    
    def display_session(self, index: int) -> None:
        """显示指定索引的历史会话
        
        Args:
            index: 会话索引
        """
        timestamp, messages = self.get_session(index)
        if not timestamp:
            print("未找到历史会话")
            return
        
        # 格式化时间戳
        try:
            dt = datetime.datetime.fromisoformat(timestamp)
            formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            formatted_time = timestamp
        
        print(f"\n===== 历史会话 {index + 1} ({formatted_time}) =====")
        
        for msg in messages:
            if msg["role"] == "system":
                continue
            elif msg["role"] == "user":
                print(f"\n用户: {msg['content']}")
            elif msg["role"] == "assistant":
                print(f"\n助手: {msg['content']}")
        print("\n" + "=" * 50)
    
    def browse_history(self) -> None:
        """浏览历史会话"""
        history = self.load_history()
        if not history:
            print("没有历史会话记录")
            return
        
        session_count = len(history)
        page_size = 5
        current_page = 0
        total_pages = (session_count + page_size - 1) // page_size
        
        while True:
            # 清屏
            os.system('cls' if os.name == 'nt' else 'clear')
            
            print(f"历史会话记录 (第 {current_page + 1}/{total_pages} 页)")
            print("=" * 50)
            
            # 显示当前页的会话
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, session_count)
            
            for i in range(start_idx, end_idx):
                session = history[i]
                # 格式化时间戳
                try:
                    dt = datetime.datetime.fromisoformat(session["timestamp"])
                    formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    formatted_time = session["timestamp"]
                
                # 提取第一个用户问题作为摘要
                summary = "空会话"
                for msg in session["messages"]:
                    if msg["role"] == "user":
                        summary = msg["content"]
                        if len(summary) > 60:
                            summary = summary[:57] + "..."
                        break
                
                print(f"{i + 1}. [{formatted_time}] {summary}")
            
            print("\n" + "=" * 50)
            print("操作: [数字]查看详情 | [n]下一页 | [p]上一页 | [q]退出")
            
            choice = input("请输入: ").strip().lower()
            
            if choice == 'q':
                break
            elif choice == 'n':
                if current_page < total_pages - 1:
                    current_page += 1
            elif choice == 'p':
                if current_page > 0:
                    current_page -= 1
            elif choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < session_count:
                    self.display_session(idx)
                    input("按回车键继续...")
                else:
                    print("无效的会话索引")
                    time.sleep(1)
            else:
                print("无效的输入")
                time.sleep(1)
    
    def search_history(self, keyword: str) -> None:
        """搜索历史会话
        
        Args:
            keyword: 搜索关键词
        """
        history = self.load_history()
        if not history:
            print("没有历史会话记录")
            return
        
        results = []
        
        # 搜索所有会话
        for i, session in enumerate(history):
            for msg in session["messages"]:
                if keyword.lower() in msg["content"].lower():
                    results.append((i, session["timestamp"]))
                    break
        
        if not results:
            print(f"未找到包含关键词 '{keyword}' 的历史会话")
            return
        
        print(f"找到 {len(results)} 个包含关键词 '{keyword}' 的历史会话:")
        print("=" * 50)
        
        for i, (idx, timestamp) in enumerate(results):
            # 格式化时间戳
            try:
                dt = datetime.datetime.fromisoformat(timestamp)
                formatted_time = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                formatted_time = timestamp
            
            print(f"{i + 1}. [{formatted_time}] 会话 {idx + 1}")
        
        print("\n" + "=" * 50)
        print("输入数字查看详情，或按回车键返回")
        
        choice = input("请输入: ").strip()
        
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(results):
                self.display_session(results[idx][0])
