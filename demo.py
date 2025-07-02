#!/usr/bin/env python3

import requests
import json
import time

def demo_tts_api():
    """演示 TTS API 功能"""
    base_url = "http://localhost:8000"
    
    print("🎤 Qwen-TTS 语音合成服务演示")
    print("=" * 50)
    
    # 测试不同音色的文本
    test_cases = [
        {
            "text": "你好，欢迎使用 Qwen-TTS 语音合成服务！",
            "voice": "Cherry",
            "description": "温柔甜美的女声"
        },
        {
            "text": "哟，您猜怎么着？今儿个我看NBA，库里投篮跟闹着玩似的！",
            "voice": "Dylan", 
            "description": "地道的北京爷们儿"
        },
        {
            "text": "侬好，欢迎来到上海！",
            "voice": "Jada",
            "description": "温婉的上海女声"
        },
        {
            "text": "Hello! Welcome to use Qwen-TTS speech synthesis service!",
            "voice": "Ethan",
            "description": "成熟稳重的男声"
        }
    ]
    
    for i, case in enumerate(test_cases, 1):
        print(f"\n🎵 测试 {i}: {case['description']} ({case['voice']})")
        print(f"📝 文本: {case['text']}")
        
        try:
            # 调用合成 API
            response = requests.post(
                f"{base_url}/api/synthesize",
                json={
                    "text": case["text"],
                    "voice": case["voice"]
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 合成成功!")
                print(f"🔗 音频链接: {base_url}{result['audio_url']}")
                print(f"⏱️  处理时间: {result['duration']:.2f}秒")
                print(f"🎭 音色信息: {result['voice_info']['description']}")
            else:
                print(f"❌ 合成失败: {response.status_code}")
                print(f"错误信息: {response.text}")
                
        except Exception as e:
            print(f"❌ 请求失败: {e}")
        
        # 等待一下再进行下一个测试
        if i < len(test_cases):
            time.sleep(1)
    
    print("\n" + "=" * 50)
    print("🎉 演示完成！")
    print("💡 提示: 您可以访问 http://localhost:8000 使用 Web 界面")
    print("📚 API 文档: http://localhost:8000/docs")

def check_service():
    """检查服务是否运行"""
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ 服务运行正常")
            print(f"🔑 API Key 已配置: {health['api_key_configured']}")
            return True
        else:
            print(f"❌ 服务异常: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 无法连接到服务: {e}")
        print("💡 请确保服务已启动: python start.py")
        return False

if __name__ == "__main__":
    print("🔍 检查服务状态...")
    if check_service():
        print("\n开始演示...")
        demo_tts_api()
    else:
        print("\n请先启动服务后再运行演示。")
