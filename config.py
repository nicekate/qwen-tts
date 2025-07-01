"""
Qwen-TTS FastAPI 应用配置文件
"""
import os
from typing import Dict, List
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(override=True)

class Config:
    # API 配置
    DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
    
    # 服务器配置
    HOST = "0.0.0.0"
    PORT = 8000
    DEBUG = True
    
    # TTS 模型配置
    DEFAULT_MODEL = "qwen-tts-latest"
    ALTERNATIVE_MODEL = "qwen-tts-2025-05-22"
    
    # 支持的音色配置
    VOICES: Dict[str, Dict] = {
        "Cherry": {
            "name": "Cherry",
            "language": "中英双语",
            "description": "温柔甜美的女声",
            "dialect": "标准普通话"
        },
        "Ethan": {
            "name": "Ethan", 
            "language": "中英双语",
            "description": "成熟稳重的男声",
            "dialect": "标准普通话"
        },
        "Chelsie": {
            "name": "Chelsie",
            "language": "中英双语", 
            "description": "活泼可爱的女声",
            "dialect": "标准普通话"
        },
        "Serena": {
            "name": "Serena",
            "language": "中英双语",
            "description": "优雅知性的女声", 
            "dialect": "标准普通话"
        },
        "Dylan": {
            "name": "Dylan",
            "language": "中文",
            "description": "地道的北京爷们儿",
            "dialect": "北京话"
        },
        "Jada": {
            "name": "Jada",
            "language": "中文",
            "description": "温婉的上海女声",
            "dialect": "上海话"
        },
        "Sunny": {
            "name": "Sunny", 
            "language": "中文",
            "description": "热情的四川女声",
            "dialect": "四川话"
        }
    }
    
    # 文件配置
    AUDIO_OUTPUT_DIR = "audio_output"
    MAX_TEXT_LENGTH = 1000
    ALLOWED_AUDIO_FORMATS = ["wav", "mp3"]
    DEFAULT_AUDIO_FORMAT = "wav"
    
    # 请求超时配置
    REQUEST_TIMEOUT = 30
    DOWNLOAD_TIMEOUT = 60

# 创建配置实例
config = Config()

# 验证必要的环境变量
if not config.DASHSCOPE_API_KEY:
    raise EnvironmentError(
        "DASHSCOPE_API_KEY 环境变量未设置。请创建 .env 文件并设置您的 API Key。"
    )
