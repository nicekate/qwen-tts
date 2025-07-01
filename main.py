"""
Qwen-TTS FastAPI 应用主文件
功能丰富的语音合成服务，支持多种音色、方言和参数调节
"""
import os
import uuid
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

import aiofiles
import requests
import dashscope
from pydub import AudioSegment
from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from config import config

# 创建 FastAPI 应用
app = FastAPI(
    title="Qwen-TTS 语音合成服务",
    description="基于 Qwen-TTS 的功能丰富的语音合成 API 服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 创建必要的目录
os.makedirs(config.AUDIO_OUTPUT_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# 静态文件和模板配置
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/audio", StaticFiles(directory=config.AUDIO_OUTPUT_DIR), name="audio")
templates = Jinja2Templates(directory="templates")

# Pydantic 模型
class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=config.MAX_TEXT_LENGTH, description="要合成的文本")
    voice: str = Field(default="Cherry", description="音色选择")
    model: str = Field(default=config.DEFAULT_MODEL, description="模型版本")
    speed: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="语速调节 (0.5-2.0)")
    pitch: Optional[float] = Field(default=1.0, ge=0.5, le=2.0, description="音调调节 (0.5-2.0)")
    volume: Optional[float] = Field(default=1.0, ge=0.1, le=2.0, description="音量调节 (0.1-2.0)")

class TTSResponse(BaseModel):
    success: bool
    message: str
    audio_url: Optional[str] = None
    file_path: Optional[str] = None
    voice_info: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None

# TTS 服务类
class QwenTTSService:
    def __init__(self):
        self.api_key = config.DASHSCOPE_API_KEY
        
    async def synthesize_speech(
        self,
        text: str,
        voice: str = "Cherry",
        model: str = config.DEFAULT_MODEL,
        **kwargs
    ) -> Dict[str, Any]:
        """异步语音合成"""
        try:
            # 验证音色
            if voice not in config.VOICES:
                raise ValueError(f"不支持的音色: {voice}")

            # 调用 Qwen-TTS API - 使用正确的 API 格式
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: dashscope.audio.qwen_tts.SpeechSynthesizer.call(
                    model=model,
                    api_key=self.api_key,
                    text=text,
                    voice=voice,
                )
            )

            # 检查响应是否为空
            if response is None:
                raise RuntimeError("API call returned None response")

            # 检查 response.output 是否为空
            if response.output is None:
                raise RuntimeError("API call failed: response.output is None")

            # 检查 response.output.audio 是否存在
            if not hasattr(response.output, 'audio') or response.output.audio is None:
                raise RuntimeError("API call failed: response.output.audio is None or missing")

            # 获取音频 URL
            audio_url = response.output.audio["url"]

            return {
                "success": True,
                "audio_url": audio_url,
                "voice_info": config.VOICES[voice]
            }

        except Exception as e:
            print(f"语音合成错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def download_audio(self, audio_url: str, filename: str) -> str:
        """异步下载音频文件"""
        try:
            file_path = os.path.join(config.AUDIO_OUTPUT_DIR, filename)
            
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(audio_url, timeout=config.DOWNLOAD_TIMEOUT)
            )
            response.raise_for_status()
            
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(response.content)
            
            return file_path
            
        except Exception as e:
            raise RuntimeError(f"音频下载失败: {e}")

# 创建 TTS 服务实例
tts_service = QwenTTSService()

# API 路由
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "voices": config.VOICES,
        "title": "Qwen-TTS 语音合成服务"
    })

@app.get("/api/voices")
async def get_voices():
    """获取支持的音色列表"""
    return {"voices": config.VOICES}

@app.post("/api/synthesize", response_model=TTSResponse)
async def synthesize_text(request: TTSRequest):
    """文本转语音 API"""
    start_time = datetime.now()

    try:
        # 调用 TTS 服务
        result = await tts_service.synthesize_speech(
            text=request.text,
            voice=request.voice,
            model=request.model
        )

        if not result["success"]:
            error_msg = result["error"]

            # 特殊处理 API Key 错误
            if "401" in error_msg or "InvalidApiKey" in error_msg:
                error_msg = "API Key 无效。请检查您的 DashScope API Key 是否正确配置。API Key 应该是以 'sk-' 开头的格式。"
            elif "403" in error_msg:
                error_msg = "API Key 权限不足。请确保您的 API Key 有访问 Qwen-TTS 服务的权限。"
            elif "429" in error_msg:
                error_msg = "请求频率过高，请稍后再试。"
            elif "500" in error_msg:
                error_msg = "服务器内部错误，请稍后再试。"

            raise HTTPException(status_code=500, detail=error_msg)

        # 生成唯一文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tts_{request.voice}_{timestamp}_{uuid.uuid4().hex[:8]}.wav"

        # 下载音频文件
        file_path = await tts_service.download_audio(result["audio_url"], filename)

        # 计算处理时间
        duration = (datetime.now() - start_time).total_seconds()

        return TTSResponse(
            success=True,
            message="语音合成成功",
            audio_url=f"/audio/{filename}",
            file_path=file_path,
            voice_info=result["voice_info"],
            duration=duration
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"语音合成失败: {str(e)}")

@app.get("/api/download/{filename}")
async def download_audio_file(filename: str):
    """下载音频文件"""
    file_path = os.path.join(config.AUDIO_OUTPUT_DIR, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="audio/wav"
    )

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "api_key_configured": bool(config.DASHSCOPE_API_KEY)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG
    )
