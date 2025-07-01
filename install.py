#!/usr/bin/env python3
"""
Qwen-TTS 语音合成服务安装脚本
自动安装依赖并配置环境
"""
import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    print("🐍 检查 Python 版本...")
    
    if sys.version_info < (3, 8):
        print("❌ Python 版本过低，需要 Python 3.8 或更高版本")
        print(f"当前版本: {sys.version}")
        return False
    
    print(f"✅ Python 版本: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """安装依赖包"""
    print("📦 安装项目依赖...")
    
    try:
        # 检查 requirements.txt 是否存在
        if not Path("requirements.txt").exists():
            print("❌ 未找到 requirements.txt 文件")
            return False
        
        # 安装依赖
        result = subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ 依赖安装成功")
            return True
        else:
            print("❌ 依赖安装失败")
            print(f"错误信息: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 安装过程出错: {e}")
        return False

def setup_env_file():
    """设置环境变量文件"""
    print("⚙️  配置环境变量...")
    
    env_example = Path(".env.example")
    env_file = Path(".env")
    
    if not env_example.exists():
        print("❌ 未找到 .env.example 文件")
        return False
    
    if env_file.exists():
        print("✅ .env 文件已存在")
        return True
    
    try:
        # 复制 .env.example 到 .env
        with open(env_example, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(env_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ 已创建 .env 文件")
        print("📝 请编辑 .env 文件，设置您的 DASHSCOPE_API_KEY")
        return True
        
    except Exception as e:
        print(f"❌ 创建 .env 文件失败: {e}")
        return False

def show_next_steps():
    """显示后续步骤"""
    print("\n" + "=" * 50)
    print("🎉 安装完成！")
    print("\n📋 后续步骤:")
    print("1. 获取 API Key:")
    print("   访问: https://bailian.console.aliyun.com/?tab=model#/api-key")
    print("   登录阿里云账号并创建 API Key")
    print("\n2. 配置 API Key:")
    print("   编辑 .env 文件，将您的 API Key 填入:")
    print("   DASHSCOPE_API_KEY=sk-your_api_key_here")
    print("\n3. 启动服务:")
    print("   python start.py")
    print("\n4. 访问应用:")
    print("   Web 界面: http://localhost:8000")
    print("   API 文档: http://localhost:8000/docs")
    print("\n5. 运行演示:")
    print("   python demo.py")
    print("\n💡 提示: 确保您的阿里云账户有足够的余额或免费额度")

def main():
    """主函数"""
    print("🎤 Qwen-TTS 语音合成服务安装程序")
    print("=" * 50)
    
    # 检查 Python 版本
    if not check_python_version():
        sys.exit(1)
    
    # 安装依赖
    if not install_dependencies():
        sys.exit(1)
    
    # 设置环境文件
    if not setup_env_file():
        sys.exit(1)
    
    # 显示后续步骤
    show_next_steps()

if __name__ == "__main__":
    main()
