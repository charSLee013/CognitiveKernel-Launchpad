#!/usr/bin/env python3
"""
CognitiveKernel-Pro 日志管理系统
自动生成控制台输出日志到本地文件夹
"""

import os
import sys
import time
import json
from datetime import datetime
from typing import Optional, TextIO
from pathlib import Path

class ConsoleLogger:
    """
    控制台输出日志记录器
    自动将控制台输出同时写入日志文件
    """
    
    def __init__(self, log_dir: str = "logs", task_name: str = None):
        """
        初始化日志记录器
        
        Args:
            log_dir: 日志目录
            task_name: 任务名称，用于生成日志文件名
        """
        self.log_dir = Path(log_dir)
        self.task_name = task_name or "cognitive_kernel"
        self.log_file = None
        self.original_stdout = None
        self.original_stderr = None
        self.start_time = time.time()
        
        # 创建日志目录
        self.log_dir.mkdir(exist_ok=True)
        
        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_filename = f"{self.task_name}_console_{timestamp}.log"
        self.log_filepath = self.log_dir / self.log_filename
        
        print(f"📁 日志将保存到: {self.log_filepath}")
    
    def start_logging(self):
        """
        开始记录控制台输出
        """
        try:
            # 保存原始的stdout和stderr
            self.original_stdout = sys.stdout
            self.original_stderr = sys.stderr
            
            # 打开日志文件
            self.log_file = open(self.log_filepath, 'w', encoding='utf-8')
            
            # 写入日志头部信息
            self._write_log_header()
            
            # 替换stdout和stderr
            sys.stdout = TeeOutput(self.original_stdout, self.log_file)
            sys.stderr = TeeOutput(self.original_stderr, self.log_file)
            
            print(f"✅ 控制台日志记录已启动")
            print(f"📝 日志文件: {self.log_filepath}")
            
        except Exception as e:
            print(f"❌ 启动日志记录失败: {e}")
            self.stop_logging()
    
    def stop_logging(self):
        """
        停止记录控制台输出
        """
        try:
            if self.original_stdout:
                sys.stdout = self.original_stdout
            if self.original_stderr:
                sys.stderr = self.original_stderr
            
            if self.log_file:
                # 写入日志尾部信息
                self._write_log_footer()
                self.log_file.close()
                self.log_file = None
            
            print(f"✅ 控制台日志记录已停止")
            print(f"📁 日志已保存到: {self.log_filepath}")
            
        except Exception as e:
            print(f"❌ 停止日志记录失败: {e}")
    
    def _write_log_header(self):
        """
        写入日志头部信息
        """
        header = f"""
{'='*80}
CognitiveKernel-Pro 控制台输出日志
{'='*80}
任务名称: {self.task_name}
开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
日志文件: {self.log_filename}
Python版本: {sys.version}
工作目录: {os.getcwd()}
{'='*80}

"""
        self.log_file.write(header)
        self.log_file.flush()
    
    def _write_log_footer(self):
        """
        写入日志尾部信息
        """
        end_time = time.time()
        duration = end_time - self.start_time
        
        footer = f"""

{'='*80}
日志记录结束
{'='*80}
结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
总执行时间: {duration:.2f} 秒
日志文件大小: {self.log_filepath.stat().st_size} 字节
{'='*80}
"""
        self.log_file.write(footer)
        self.log_file.flush()
    
    def __enter__(self):
        """
        上下文管理器入口
        """
        self.start_logging()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        上下文管理器出口
        """
        self.stop_logging()

class TeeOutput:
    """
    同时输出到控制台和文件的包装器
    """
    
    def __init__(self, console: TextIO, file: TextIO):
        self.console = console
        self.file = file
    
    def write(self, text: str):
        """
        同时写入控制台和文件
        """
        # 写入控制台
        self.console.write(text)
        self.console.flush()
        
        # 写入文件，添加时间戳
        if text.strip():  # 只对非空行添加时间戳
            timestamp = datetime.now().strftime('[%H:%M:%S] ')
            # 如果文本不是以换行符开始，添加时间戳
            if not text.startswith('\n'):
                self.file.write(timestamp)
        
        self.file.write(text)
        self.file.flush()
    
    def flush(self):
        """
        刷新缓冲区
        """
        self.console.flush()
        self.file.flush()
    
    def __getattr__(self, name):
        """
        代理其他属性到控制台
        """
        return getattr(self.console, name)

class SessionLogger:
    """
    会话详细日志记录器
    记录完整的会话数据
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
    
    def save_session_log(self, session, task_name: str = None) -> str:
        """
        保存会话详细日志
        
        Args:
            session: AgentSession对象
            task_name: 任务名称
            
        Returns:
            日志文件路径
        """
        try:
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            task_name = task_name or "session"
            filename = f"{task_name}_detailed_{timestamp}.json"
            filepath = self.log_dir / filename
            
            # 转换会话数据
            session_data = session.to_dict()
            
            # 添加元数据
            session_data['_metadata'] = {
                'log_created_at': datetime.now().isoformat(),
                'log_filename': filename,
                'total_steps': len(session_data.get('steps', [])),
                'task_summary': session_data.get('task', '')[:100] + '...' if len(session_data.get('task', '')) > 100 else session_data.get('task', '')
            }
            
            # 保存到文件
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
            
            print(f"📁 会话详细日志已保存: {filepath}")
            return str(filepath)
            
        except Exception as e:
            print(f"❌ 保存会话日志失败: {e}")
            return None

def setup_logging_environment():
    """
    设置日志环境
    创建日志目录并更新gitignore
    """
    # 创建logs目录
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # 创建子目录
    (logs_dir / "console").mkdir(exist_ok=True)
    (logs_dir / "sessions").mkdir(exist_ok=True)
    (logs_dir / "api_calls").mkdir(exist_ok=True)
    
    # 创建README文件
    readme_content = """# CognitiveKernel-Pro 日志目录

这个目录包含了CognitiveKernel-Pro运行时生成的各种日志文件。

## 目录结构

- `console/`: 控制台输出日志
- `sessions/`: 详细会话日志
- `api_calls/`: API调用日志

## 日志文件类型

### 控制台日志 (`*_console_*.log`)
- 完整的控制台输出
- 包含时间戳
- 实时执行过程记录

### 会话日志 (`*_detailed_*.json`)
- 完整的会话数据
- 每个步骤的详细信息
- Progress State历史

### API调用日志 (`*_api_*.log`)
- LLM API调用记录
- 请求和响应数据
- 性能统计

## 注意事项

- 这些日志文件已添加到 .gitignore 中
- 日志文件可能包含敏感信息，请勿提交到版本控制
- 定期清理旧的日志文件以节省磁盘空间
"""
    
    with open(logs_dir / "README.md", 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ 日志环境设置完成")
    print(f"📁 日志目录: {logs_dir.absolute()}")

# 便捷函数
def start_console_logging(task_name: str = None) -> ConsoleLogger:
    """
    启动控制台日志记录
    
    Args:
        task_name: 任务名称
        
    Returns:
        ConsoleLogger实例
    """
    logger = ConsoleLogger(task_name=task_name)
    logger.start_logging()
    return logger

def save_session_log(session, task_name: str = None) -> str:
    """
    保存会话详细日志
    
    Args:
        session: AgentSession对象
        task_name: 任务名称
        
    Returns:
        日志文件路径
    """
    logger = SessionLogger()
    return logger.save_session_log(session, task_name)
