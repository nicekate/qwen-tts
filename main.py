"""
Qwen-TTS FastAPI 应用主文件
功能丰富的语音合成服务，支持多种音色、方言和参数调节
"""
import os
import uuid
import asyncio
import re
import json
import zipfile
import tempfile
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
from enum import Enum

import aiofiles
import requests
import dashscope
from pydub import AudioSegment
from fastapi import FastAPI, HTTPException, Request, Form, File, UploadFile, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
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

# 枚举类型
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# Pydantic 模型
class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=config.MAX_TEXT_LENGTH, description="要合成的文本")
    voice: str = Field(default="Cherry", description="音色选择")
    model: str = Field(default=config.DEFAULT_MODEL, description="模型版本")

class TTSResponse(BaseModel):
    success: bool
    message: str
    audio_url: Optional[str] = None
    file_path: Optional[str] = None
    voice_info: Optional[Dict[str, Any]] = None
    duration: Optional[float] = None

class BatchTaskRequest(BaseModel):
    voice: str = Field(default="Cherry", description="音色选择")
    model: str = Field(default=config.DEFAULT_MODEL, description="模型版本")
    split_by: str = Field(default="paragraph", description="分割方式: paragraph, sentence, chapter")
    max_length: int = Field(default=500, description="每段最大字符数")

class BatchTaskResponse(BaseModel):
    success: bool
    message: str
    task_id: Optional[str] = None
    total_segments: Optional[int] = None

class TaskProgress(BaseModel):
    task_id: str
    status: TaskStatus
    total_segments: int
    completed_segments: int
    failed_segments: int
    progress_percentage: float
    created_at: datetime
    updated_at: datetime
    results: List[Dict[str, Any]] = []

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

            # 调用 Qwen-TTS API - 使用官方支持的参数
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

# 批量处理管理器
class BatchTaskManager:
    def __init__(self):
        self.tasks: Dict[str, TaskProgress] = {}
        self.max_concurrent_tasks = 3  # 最大并发任务数

    def create_task(self, segments: List[str], voice: str, model: str) -> str:
        """创建批量任务"""
        task_id = str(uuid.uuid4())
        task = TaskProgress(
            task_id=task_id,
            status=TaskStatus.PENDING,
            total_segments=len(segments),
            completed_segments=0,
            failed_segments=0,
            progress_percentage=0.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            results=[]
        )
        self.tasks[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> Optional[TaskProgress]:
        """获取任务状态"""
        return self.tasks.get(task_id)

    def update_task_progress(self, task_id: str, completed: int, failed: int, result: Dict[str, Any] = None):
        """更新任务进度"""
        if task_id not in self.tasks:
            return

        task = self.tasks[task_id]
        task.completed_segments = completed
        task.failed_segments = failed
        task.progress_percentage = (completed + failed) / task.total_segments * 100
        task.updated_at = datetime.now()

        if result:
            task.results.append(result)

        if completed + failed >= task.total_segments:
            task.status = TaskStatus.COMPLETED if failed == 0 else TaskStatus.FAILED
        else:
            task.status = TaskStatus.PROCESSING

# 文件解析器
class FileParser:
    @staticmethod
    def parse_text_file(content: str, split_by: str = "paragraph", max_length: int = 500) -> List[str]:
        """解析文本文件内容"""
        segments = []

        if split_by == "paragraph":
            # 按段落分割
            paragraphs = re.split(r'\n\s*\n', content.strip())
            for para in paragraphs:
                para = para.strip()
                if para:
                    segments.extend(FileParser._split_long_text(para, max_length))

        elif split_by == "sentence":
            # 按句子分割
            sentences = re.split(r'[。！？.!?]\s*', content)
            current_segment = ""
            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                if len(current_segment + sentence) <= max_length:
                    current_segment += sentence + "。"
                else:
                    if current_segment:
                        segments.append(current_segment.strip())
                    current_segment = sentence + "。"

            if current_segment:
                segments.append(current_segment.strip())

        elif split_by == "chapter":
            # 按章节分割（基于标题）
            chapters = re.split(r'\n#+\s+', content)
            for chapter in chapters:
                chapter = chapter.strip()
                if chapter:
                    segments.extend(FileParser._split_long_text(chapter, max_length))

        return [seg for seg in segments if seg.strip()]

    @staticmethod
    def _split_long_text(text: str, max_length: int) -> List[str]:
        """分割过长的文本"""
        if len(text) <= max_length:
            return [text]

        segments = []
        words = text.split()
        current_segment = ""

        for word in words:
            if len(current_segment + " " + word) <= max_length:
                current_segment += (" " + word) if current_segment else word
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = word

        if current_segment:
            segments.append(current_segment)

        return segments

# 创建实例
tts_service = QwenTTSService()
batch_manager = BatchTaskManager()
file_parser = FileParser()

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

@app.post("/api/batch/upload", response_model=BatchTaskResponse)
async def upload_batch_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    voice: str = Form(default="Cherry"),
    model: str = Form(default=config.DEFAULT_MODEL),
    split_by: str = Form(default="paragraph"),
    max_length: int = Form(default=500)
):
    """批量文件上传和处理"""
    try:
        # 验证文件类型
        if not file.filename.lower().endswith(('.txt', '.md')):
            raise HTTPException(status_code=400, detail="只支持 .txt 和 .md 文件")

        # 验证音色
        if voice not in config.VOICES:
            raise HTTPException(status_code=400, detail=f"不支持的音色: {voice}")

        # 读取文件内容
        content = await file.read()
        try:
            text_content = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text_content = content.decode('gbk')
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="文件编码不支持，请使用UTF-8或GBK编码")

        # 解析文件内容
        segments = file_parser.parse_text_file(text_content, split_by, max_length)

        if not segments:
            raise HTTPException(status_code=400, detail="文件内容为空或无法解析")

        if len(segments) > 100:  # 限制最大段落数
            raise HTTPException(status_code=400, detail="文件内容过多，请分割后再上传（最多100段）")

        # 创建批量任务
        task_id = batch_manager.create_task(segments, voice, model)

        # 启动后台处理
        background_tasks.add_task(process_batch_task, task_id, segments, voice, model)

        return BatchTaskResponse(
            success=True,
            message="批量任务已创建，正在处理中",
            task_id=task_id,
            total_segments=len(segments)
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件处理失败: {str(e)}")

@app.get("/api/batch/status/{task_id}")
async def get_batch_status(task_id: str):
    """获取批量任务状态"""
    task = batch_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return task

@app.get("/api/batch/download/{task_id}")
async def download_batch_results(task_id: str):
    """下载批量任务的所有音频文件（ZIP打包下载）"""
    task = batch_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="任务尚未完成")

    # 获取成功的音频文件
    success_results = [r for r in task.results if r['status'] == 'success']

    if not success_results:
        raise HTTPException(status_code=404, detail="没有可下载的音频文件")

    try:
        # 创建临时ZIP文件
        temp_zip = tempfile.NamedTemporaryFile(delete=False, suffix='.zip')
        temp_zip.close()

        with zipfile.ZipFile(temp_zip.name, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for result in success_results:
                file_path = os.path.join(config.AUDIO_OUTPUT_DIR, result['filename'])
                if os.path.exists(file_path):
                    # 添加文件到ZIP，使用原始文件名
                    zip_file.write(file_path, result['filename'])

        # 生成下载文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        zip_filename = f"batch_audio_{task_id[:8]}_{timestamp}.zip"

        # 返回ZIP文件
        def cleanup_temp_file():
            try:
                os.unlink(temp_zip.name)
            except:
                pass

        return FileResponse(
            path=temp_zip.name,
            filename=zip_filename,
            media_type="application/zip",
            background=BackgroundTasks([cleanup_temp_file])
        )

    except Exception as e:
        # 清理临时文件
        try:
            os.unlink(temp_zip.name)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"创建ZIP文件失败: {str(e)}")

@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "api_key_configured": bool(config.DASHSCOPE_API_KEY)
    }

# 批量处理后台任务
async def process_batch_task(task_id: str, segments: List[str], voice: str, model: str):
    """处理批量任务"""
    completed = 0
    failed = 0

    # 更新任务状态为处理中
    batch_manager.update_task_progress(task_id, completed, failed)

    # 创建信号量来控制并发数
    semaphore = asyncio.Semaphore(batch_manager.max_concurrent_tasks)

    async def process_single_segment(index: int, text: str):
        """处理单个文本段"""
        nonlocal completed, failed

        async with semaphore:
            try:
                # 调用TTS服务
                result = await tts_service.synthesize_speech(
                    text=text,
                    voice=voice,
                    model=model
                )

                if result["success"]:
                    # 生成文件名
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"batch_{task_id}_{index:03d}_{voice}_{timestamp}_{uuid.uuid4().hex[:8]}.wav"

                    # 下载音频文件
                    file_path = await tts_service.download_audio(result["audio_url"], filename)

                    # 记录成功结果
                    segment_result = {
                        "index": index,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "filename": filename,
                        "audio_url": f"/audio/{filename}",
                        "status": "success",
                        "voice": voice
                    }
                    completed += 1
                else:
                    # 记录失败结果
                    segment_result = {
                        "index": index,
                        "text": text[:100] + "..." if len(text) > 100 else text,
                        "status": "failed",
                        "error": result.get("error", "未知错误")
                    }
                    failed += 1

                # 更新进度
                batch_manager.update_task_progress(task_id, completed, failed, segment_result)

            except Exception as e:
                failed += 1
                segment_result = {
                    "index": index,
                    "text": text[:100] + "..." if len(text) > 100 else text,
                    "status": "failed",
                    "error": str(e)
                }
                batch_manager.update_task_progress(task_id, completed, failed, segment_result)

    # 创建所有任务
    tasks = [
        process_single_segment(i, segment)
        for i, segment in enumerate(segments)
    ]

    # 并发执行所有任务
    await asyncio.gather(*tasks, return_exceptions=True)

    print(f"批量任务 {task_id} 完成: 成功 {completed}, 失败 {failed}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.DEBUG
    )
