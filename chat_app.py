"""
聊天应用主程序，整合各个模块实现完整的聊天功能
"""

import sys

from azure_chat.config import AzureConfig
from azure_chat.client import AzureClient
from azure_chat.session import ChatSession
from azure_chat.history import ChatHistory


def main():
    """主函数，实现一问一答的交互形式"""
    try:
        # 初始化历史记录管理器
        chat_history = ChatHistory()
        
        # 初始化配置和客户端
        config = AzureConfig()
        client = AzureClient(config)
        
        # 创建聊天会话
        chat_session = ChatSession(client)
        
        print("欢迎使用DeepSeek聊天助手！输入'退出'或'exit'结束对话。")
        print("支持编辑功能：Backspace删除，Home跳到行首，End跳到行尾，方向键移动光标")
        print("已启用流式响应模式，回复将实时显示")
        print("特殊命令：'history'查看历史会话，'search 关键词'搜索历史会话")
        
        # 开始对话循环
        while True:
            # 获取用户输入
            user_input = chat_session.get_user_input()
            
            # 处理空输入
            if not user_input:
                continue
                
            # 检查是否退出
            if user_input.lower() in ['退出', 'exit', 'quit', 'q']:
                # 保存当前会话到历史记录
                chat_history.save_session(chat_session.messages)
                chat_session.print_final_stats()
                break
            
            # 检查是否查看历史
            if user_input.lower() == 'history':
                chat_history.browse_history()
                continue
            
            # 检查是否搜索历史
            if user_input.lower().startswith('search '):
                keyword = user_input[7:].strip()
                if keyword:
                    chat_history.search_history(keyword)
                else:
                    print("请提供搜索关键词")
                continue
            
            # 添加用户消息到历史
            chat_session.add_user_message(user_input)
            
            try:
                # 获取助手响应
                response = chat_session.get_assistant_response()
                
                # 打印统计信息
                chat_session.print_response_stats(response)
                
                # 将助手回复添加到消息历史
                chat_session.add_assistant_message(response.content)
                
            except Exception as e:
                print(f"\n发生错误: {str(e)}")
                print("请重试或检查网络连接")
    
    except Exception as e:
        print(f"程序初始化失败: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
