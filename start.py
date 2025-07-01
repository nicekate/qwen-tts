#!/usr/bin/env python3
"""
Qwen-TTS FastAPI 应用启动脚本
"""
import os
import sys
import uvicorn
from pathlib import Path

def check_dependencies():
    """检查依赖包"""
    print("📦 检查依赖包...")

    # 检查关键依赖包
    required_packages = {
        "fastapi": "fastapi",
        "uvicorn": "uvicorn",
        "dashscope": "dashscope",
        "requests": "requests",
        "jinja2": "jinja2",
        "aiofiles": "aiofiles",
        "pydantic": "pydantic",
        "python-dotenv": "dotenv"
    }

    missing_packages = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)

    if missing_packages:
        print(f"❌ 缺少依赖包: {', '.join(missing_packages)}")
        print("📝 请运行: pip install -r requirements.txt")
        return False

    print("✅ 依赖包检查通过")
    return True

def check_environment():
    """检查环境配置"""
    print("🔍 检查环境配置...")

    # 检查 .env 文件
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ 未找到 .env 文件")
        print("📝 请复制 .env.example 为 .env 并配置您的 DASHSCOPE_API_KEY")
        return False

    # 检查 API Key
    from dotenv import load_dotenv
    load_dotenv()

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ DASHSCOPE_API_KEY 未配置")
        print("📝 请在 .env 文件中设置您的 API Key")
        return False

    print("✅ 环境配置检查通过")
    return True

def create_directories():
    """创建必要的目录"""
    print("📁 创建必要目录...")
    
    directories = ["audio_output", "static", "templates"]
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
    
    print("✅ 目录创建完成")

def main():
    """主函数"""
    print("🎤 Qwen-TTS 语音合成服务启动中...")
    print("=" * 50)

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    # 检查环境
    if not check_environment():
        sys.exit(1)

    # 创建目录
    create_directories()
    
    # 启动服务
    print("🚀 启动 FastAPI 服务...")
    print("📱 访问地址: http://localhost:8000")
    print("📚 API 文档: http://localhost:8000/docs")
    print("🔄 按 Ctrl+C 停止服务")
    print("=" * 50)
    
    try:
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 服务已停止")

if __name__ == "__main__":
    main()
