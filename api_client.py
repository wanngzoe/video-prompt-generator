"""
真实的API调用实现
支持：
- 提示词生成：Gemini, OpenAI GPT-4V, Claude
- 视频生成：Wan2.6 (阿里云DashScope), Seedance (即梦)
"""

import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any, Optional

# ==================== 提示词生成模型API ====================

def call_gemini_api(
    api_key: str,
    model_name: str,
    prompt: str,
    video_file_path: Optional[str] = None,
    image_files: Optional[List] = None
) -> str:
    """
    调用Gemini API生成提示词

    Args:
        api_key: Gemini API Key
        model_name: 模型名称 (如 gemini-2.0-flash-exp)
        prompt: 系统提示词
        video_file_path: 参考视频文件路径
        image_files: 参考图片文件列表

    Returns:
        生成的提示词文本
    """
    import google.generativeai as genai

    # 配置API
    genai.configure(api_key=api_key)

    # 准备内容
    contents = []

    # 添加视频（如果有）
    if video_file_path:
        video_file = genai.upload_file(video_file_path)
        # 等待文件处理完成
        while video_file.state.name == "PROCESSING":
            time.sleep(1)
            video_file = genai.get_file(video_file.name)
        if video_file.state.name != "ACTIVE":
            raise Exception(f"文件 {video_file.name} 状态: {video_file.state.name}，无法使用")
        contents.append(video_file)

    # 添加图片（如果有）
    if image_files:
        for img in image_files:
            image = genai.upload_file(img)
            # 等待文件处理完成
            while image.state.name == "PROCESSING":
                time.sleep(1)
                image = genai.get_file(image.name)
            if image.state.name != "ACTIVE":
                raise Exception(f"文件 {image.name} 状态: {image.state.name}，无法使用")
            contents.append(image)

    # 添加文本提示
    contents.append(prompt)

    # 调用模型
    model = genai.GenerativeModel(model_name=model_name)
    response = model.generate_content(contents)

    return response.text


def call_openai_api(
    api_key: str,
    model_name: str,
    prompt: str,
    video_file_path: Optional[str] = None,
    image_files: Optional[List] = None
) -> str:
    """
    调用OpenAI GPT-4V API生成提示词

    Args:
        api_key: OpenAI API Key
        model_name: 模型名称 (如 gpt-4o)
        prompt: 系统提示词
        video_file_path: 参考视频文件路径
        image_files: 参考图片文件列表

    Returns:
        生成的提示词文本
    """
    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    # 准备消息内容
    messages = [
        {
            "role": "system",
            "content": prompt
        }
    ]

    # 添加图片（OpenAI支持图片输入）
    if image_files:
        image_contents = []
        for img in image_files:
            # 读取图片并转为base64
            import base64
            with open(img, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{img_data}"
                }
            })

        if image_contents:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "text", "text": "请基于上述参考图片和提示词生成视频提示词。"},
                    *image_contents
                ]
            })
    else:
        messages.append({
            "role": "user",
            "content": prompt
        })

    # 调用模型
    response = client.chat.completions.create(
        model=model_name,
        messages=messages,
        max_tokens=2000
    )

    return response.choices[0].message.content


def call_claude_api(
    api_key: str,
    model_name: str,
    prompt: str,
    video_file_path: Optional[str] = None,
    image_files: Optional[List] = None
) -> str:
    """
    调用Claude API生成提示词

    Args:
        api_key: Claude API Key
        model_name: 模型名称 (如 claude-sonnet-4-20250514)
        prompt: 系统提示词
        video_file_path: 参考视频文件路径
        image_files: 参考图片文件列表

    Returns:
        生成的提示词文本
    """
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)

    # 准备消息内容
    content_blocks = [
        {
            "type": "text",
            "text": prompt
        }
    ]

    # 添加图片（Claude支持图片输入）
    if image_files:
        for img in image_files:
            import base64
            with open(img, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode('utf-8')
            content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": img_data
                }
            })

    # 调用模型
    message = client.messages.create(
        model=model_name,
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": content_blocks
            }
        ]
    )

    return message.content[0].text


# ==================== 视频生成模型API ====================

def call_wan26_api(
    api_key: str,
    prompt: str,
    reference_video_path: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    duration: int = 10,
    resolution: str = "1280*720",
    model: str = "wan2.6-r2v-flash"
) -> Dict[str, Any]:
    """
    调用阿里云万相Wan2.6 API生成视频

    Args:
        api_key: 阿里云DashScope API Key
        prompt: 视频提示词
        reference_video_path: 参考视频路径
        reference_images: 参考图片路径列表
        duration: 视频时长 (4-10秒)
        resolution: 分辨率 (如 1280*720)
        model: 模型名称

    Returns:
        包含任务ID和状态的字典
    """
    import dashscope
    from dashscope import VideoSynthesis

    # 配置API
    dashscope.api_key = api_key

    # 准备参数
    kwargs = {
        "model": model,
        "prompt": prompt,
    }

    # 添加到extra_input的参数
    extra_params = {
        "size": resolution,
        "duration": duration,
        "audio": True,
        "shot_type": "multi",
        "watermark": True
    }

    # 添加参考图片（使用img_url，单张图片）
    if reference_images and len(reference_images) > 0:
        kwargs["img_url"] = reference_images[0]

    # 添加参考视频URL（使用reference_video_urls）
    if reference_video_path:
        kwargs["reference_video_urls"] = [reference_video_path]

    # 将额外参数放入extra_input
    kwargs["extra_input"] = extra_params

    # 调用API
    response = VideoSynthesis.call(**kwargs)

    if response.status_code == 200:
        return {
            "status": "processing",
            "task_id": response.output.task_id,
            "message": "视频生成任务已提交"
        }
    else:
        return {
            "status": "error",
            "error": f"API调用失败: {response.code} - {response.message}",
            "message": response.message
        }


def get_wan26_result(
    api_key: str,
    task_id: str
) -> Dict[str, Any]:
    """
    获取Wan2.6视频生成结果

    Args:
        api_key: 阿里云DashScope API Key
        task_id: 任务ID

    Returns:
        包含视频URL或状态的字典
    """
    import dashscope
    from dashscope import VideoSynthesis

    dashscope.api_key = api_key

    # 使用VideoSynthesis.fetch获取任务状态
    response = VideoSynthesis.fetch(task_id)

    if response.status_code == 200:
        task_data = response.output
        # 检查任务状态
        if hasattr(task_data, 'task_status'):
            if task_data.task_status == "SUCCEEDED":
                # 获取视频URL
                video_url = None
                if hasattr(task_data, 'results') and task_data.results:
                    video_url = getattr(task_data.results, 'video_url', None) or \
                                getattr(task_data.results, 'output_video', None)
                return {
                    "status": "completed",
                    "video_url": video_url,
                    "duration": getattr(task_data, 'duration', None)
                }
            elif task_data.task_status == "FAILED":
                return {
                    "status": "failed",
                    "error": getattr(task_data, 'message', '生成失败')
                }
            else:
                return {
                    "status": "processing",
                    "progress": getattr(task_data, 'task_progress', 0)
                }
        else:
            # 如果没有task_status，检查是否有video_url
            video_url = getattr(task_data, 'video_url', None)
            if video_url:
                return {
                    "status": "completed",
                    "video_url": video_url,
                    "duration": getattr(task_data, 'duration', None)
                }
            else:
                return {
                    "status": "processing",
                    "progress": 0
                }
    else:
        return {
            "status": "error",
            "error": f"获取结果失败: {response.code} - {getattr(response, 'message', '')}"
        }


def call_seedance_api(
    api_key: str,
    prompt: str,
    reference_video_path: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    duration: int = 10,
    model: str = "seedance-2.0"
) -> Dict[str, Any]:
    """
    调用即梦Seedance API生成视频
    注意：这是基于即梦开放平台API的示例，实际API可能有所不同

    Args:
        api_key: 即梦 API Key
        prompt: 视频提示词
        reference_video_path: 参考视频路径
        reference_images: 参考图片路径列表
        duration: 视频时长 (4-15秒)
        model: 模型名称

    Returns:
        包含任务ID和状态的字典
    """
    import requests

    # 即梦API endpoint (示例，需要根据实际API调整)
    base_url = "https://api.jimeng.jianying.com"

    # 准备请求头
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # 准备请求体
    data = {
        "model": model,
        "prompt": prompt,
        "duration": duration
    }

    # 添加参考视频
    if reference_video_path:
        # 需要先上传文件获取URL
        # 这里假设已经获取到视频URL
        data["video_url"] = reference_video_path

    # 添加参考图片
    if reference_images:
        data["image_urls"] = reference_images

    # 调用API (示例)
    try:
        response = requests.post(
            f"{base_url}/v1/video/generation",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "status": "processing",
                "task_id": result.get("task_id"),
                "message": "视频生成任务已提交"
            }
        else:
            return {
                "status": "error",
                "error": f"API调用失败: {response.status_code} - {response.text}",
                "message": response.text
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


def get_seedance_result(
    api_key: str,
    task_id: str
) -> Dict[str, Any]:
    """
    获取即梦Seedance视频生成结果
    注意：这是基于即梦开放平台API的示例，实际API可能有所不同

    Args:
        api_key: 即梦 API Key
        task_id: 任务ID

    Returns:
        包含视频URL或状态的字典
    """
    import requests

    base_url = "https://api.jimeng.jianying.com"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(
            f"{base_url}/v1/video/generation/{task_id}",
            headers=headers,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            task_data = result.get("data", {})

            if task_data.get("status") == "completed":
                return {
                    "status": "completed",
                    "video_url": task_data.get("video_url"),
                    "duration": task_data.get("duration")
                }
            elif task_data.get("status") == "failed":
                return {
                    "status": "failed",
                    "error": task_data.get("error")
                }
            else:
                return {
                    "status": "processing",
                    "progress": task_data.get("progress", 0)
                }
        else:
            return {
                "status": "error",
                "error": f"获取结果失败: {response.status_code}"
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }


# ==================== 统一的API调用入口 ====================

def call_prompt_api(
    model: str,
    api_key: str,
    model_name: str,
    system_prompt: str,
    video_file_path: Optional[str] = None,
    image_files: Optional[List] = None
) -> str:
    """
    统一调用提示词生成API

    Args:
        model: 模型类型 (Gemini/OpenAI GPT-4V/Claude)
        api_key: API Key
        model_name: 模型名称
        system_prompt: 系统提示词
        video_file_path: 参考视频路径
        image_files: 参考图片路径列表

    Returns:
        生成的提示词文本
    """
    if model == "Gemini":
        return call_gemini_api(
            api_key=api_key,
            model_name=model_name,
            prompt=system_prompt,
            video_file_path=video_file_path,
            image_files=image_files
        )
    elif model == "OpenAI GPT-4V":
        return call_openai_api(
            api_key=api_key,
            model_name=model_name,
            prompt=system_prompt,
            video_file_path=video_file_path,
            image_files=image_files
        )
    elif model == "Claude":
        return call_claude_api(
            api_key=api_key,
            model_name=model_name,
            prompt=system_prompt,
            video_file_path=video_file_path,
            image_files=image_files
        )
    else:
        raise ValueError(f"不支持的模型: {model}")


def call_video_api(
    provider: str,
    api_key: str,
    prompt: str,
    reference_video_path: Optional[str] = None,
    reference_images: Optional[List[str]] = None,
    duration: int = 10,
    resolution: str = "1280*720",
    model: str = "wan2.6-r2v-flash"
) -> Dict[str, Any]:
    """
    统一调用视频生成API

    Args:
        provider: 平台 (Seedance/万相)
        api_key: API Key
        prompt: 视频提示词
        reference_video_path: 参考视频路径
        reference_images: 参考图片路径列表
        duration: 视频时长
        resolution: 分辨率
        model: 模型名称

    Returns:
        包含任务ID和状态的字典
    """
    if "即梦" in provider or "Seedance" in provider:
        return call_seedance_api(
            api_key=api_key,
            prompt=prompt,
            reference_video_path=reference_video_path,
            reference_images=reference_images,
            duration=duration,
            model=model
        )
    elif "阿里云" in provider or "Wan" in provider:
        return call_wan26_api(
            api_key=api_key,
            prompt=prompt,
            reference_video_path=reference_video_path,
            reference_images=reference_images,
            duration=duration,
            resolution=resolution,
            model=model
        )
    else:
        raise ValueError(f"不支持的平台: {provider}")


def get_video_result(
    provider: str,
    api_key: str,
    task_id: str
) -> Dict[str, Any]:
    """
    统一获取视频生成结果

    Args:
        provider: 平台 (Seedance/万相)
        api_key: API Key
        task_id: 任务ID

    Returns:
        包含视频URL或状态的字典
    """
    if "即梦" in provider or "Seedance" in provider:
        return get_seedance_result(api_key, task_id)
    elif "阿里云" in provider or "Wan" in provider:
        return get_wan26_result(api_key, task_id)
    else:
        raise ValueError(f"不支持的平台: {provider}")
