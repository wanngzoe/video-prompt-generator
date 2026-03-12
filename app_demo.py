"""
视频生成提示词生成器 - Demo应用
基于方案一：直接生成 + 方案二：先解析后生成
包含真实的API调用实现
"""

import streamlit as st
import json
import time
import os
from datetime import datetime

# 导入API调用模块
from api_client import (
    call_prompt_api,
    call_video_api,
    get_video_result
)

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="视频生成提示词生成器",
    page_icon="🎬",
    layout="wide"
)

# ==================== 初始化session_state ====================
if 'prompts' not in st.session_state:
    st.session_state.prompts = []
if 'video_result' not in st.session_state:
    st.session_state.video_result = None
if 'parse_result' not in st.session_state:
    st.session_state.parse_result = None
if 'video_task_id' not in st.session_state:
    st.session_state.video_task_id = None
if 'scheme_step' not in st.session_state:
    st.session_state.scheme_step = {}  # 记录每个方案的当前步骤

# ==================== 辅助函数 ====================
def build_system_prompt(scheme, video_duration, change_elements, highlight, num_options):
    """构建系统提示词 - 基于文档的详细meta-prompt"""
    change_str = "、".join(change_elements)

    if scheme == "方案一：直接生成":
        prompt = f"""# 任务：根据参考视频生成生视频提示词

## 输入
- 变更类型：{change_str}
- 生成组数：{num_options}

## 核心规则
- **语言：输出中文提示词**
- 只按用户指定的变更类型生成提示词
- 其他未指定的要素100%保持不变
- 保持：动作、表情、运镜、场景、故事线、时间节点

---

## 变更规则

### 角色
- 保守：只换脸/面部，保持发型、服装、动作、表情
- 中等：换脸+发型，保持服装、动作、表情
- 激进：换脸+发型+服装，保持动作、表情
- 直接转化：不主动变更，利用模型随机性自然产生变化

### 场景
- 保守：只换地点，保持原有环境元素、动作
- 中等：换地点+部分环境元素，保持主要建筑风格
- 激进：完全不同的场景，保持动作
- 直接转化：不主动变更，利用模型随机性自然产生变化

### 画面氛围
- 保守：只变光线明暗，保持色调
- 中等：变光线+色调（冷/暖），保持情绪
- 激进：根据方案整体设定，自由重塑整体氛围
- 直接转化：不主动改写氛围描述

### 画风
- 保守：写实风格微调
- 中等：动物拟人化
- 激进：根据本方案整体设定，自由选择或混合画风
- 直接转化：保持当前画面风格不变，仅对细节轻微润色

### 其他（自由组合角色+场景+画面氛围+画风）
- 变更规则优先级：优先直接转化 > 保守 > 中等 > 激进
- 组合规则：
  - 多变更 ≤ 数量：每个变更项至少出现1次，剩余随机补
    - 例：4变更×5组 → 4个各1次 + 第5个随机合并项
  - 多变更 > 数量：优先保留"直接转化"，其余合并或择优
    - 例：4变更×2组 → 直接转化 + 随机合并项

---

## 输出格式

请严格按照以下格式输出，分镜要覆盖完整的视频时长：

【方案1】
变更类型：{change_str}
变更规则：保守/中等/激进/直接转化
保持了：动作、表情、运镜等
提示词：整体风格: 描述视频的整体风格、氛围、色调等

分镜1 (00:00-00:XX):
[时间点] 景别： 具体画面描述，包含人物动作、表情、场景元素等

分镜2 (00:XX-00:XX):
[时间点] 景别： 具体画面描述

（继续分镜，确保覆盖整个视频时长）

共{num_options}组，每组都要按照上述格式输出"""
        return prompt

    elif scheme == "方案二：先解析后生成":
        # 第一步：视频解析
        prompt = f"""# 方案二-第一步：视频解析提示词

## 角色定义

你是一个专业的视频内容分析师，擅长准确理解视频中的视觉元素、动作序列、情绪氛围、镜头语言，并将其转换为结构化的文字描述。同时，作为专业的投放专家，你需要分析这个视频为何会吸引人点击。

## 任务说明

请仔细分析用户提供的参考视频，将其转换为详细的结构化文字描述，并分析视频为何吸引人点击。

## ⚠️ 重要：输出格式要求

**你必须严格按照以下JSON格式输出，不要输出任何其他内容！**

## 视频规格

- 参考视频：1个
- 时长：{video_duration}秒

## 解析维度与输出格式

请严格按照以下JSON格式输出：

```json
{{
  "视频1": {{
    "基础信息": {{
      "时长": "{video_duration}秒",
      "分段时间节点": []
    }},
    "角色": {{
      "数量": "",
      "性别年龄": "",
      "外貌特征": "",
      "服装造型": "",
      "表情神态": ""
    }},
    "场景": {{
      "类型": "",
      "具体地点": "",
      "环境特征": "",
      "时间": "",
      "光线": "",
      "多场景切换": []
    }},
    "动作": {{
      "主要行为": "",
      "动作类型": "",
      "动作节奏": "",
      "分阶段动作": []
    }},
    "情绪": {{
      "整体氛围": "",
      "人物情绪": "",
      "情绪强度": ""
    }},
    "运镜": {{
      "镜头运动": "",
      "景别": "",
      "角度": "",
      "转场方式": "",
      "分镜描述": []
    }},
    "色调": {{
      "整体色彩": "",
      "色温": "",
      "风格": ""
    }},
    "高光情节": [
      {{
        "时间段": "",
        "描述": "",
        "保留重要性": "高/中/低"
      }}
    ],
    "道具": {{
      "主要物品": [],
      "次要物品": []
    }},
    "故事线": "一句话描述视频讲述的故事",
    "吸引点分析": {{
      "标题": "视频为何吸引人点击",
      "分析内容": {{
        "开头钩子": "视频开头用什么方式吸引观众（如悬念、冲突、视觉冲击等）",
        "情绪触发": "视频触发了什么情绪（如愤怒、好奇、同情、惊喜等）",
        "期待设置": "视频设置了什么期待或悬念让观众想看下去",
        "视觉亮点": "有哪些视觉元素吸引眼球（如颜值、场景、动作、特效等）",
        "内容槽点": "有哪些让人忍不住评论/吐槽的点",
        "传播动机": "观众看完会想分享/收藏/评论的原因"
      }}
    }}
  }}
}}
```

## 解析要求

### 角色
- 多人物时需分别描述每个人的位置，使用"画面左侧/右侧/中间"标记

### 场景
- 如有多场景切换，需分别描述每个场景和时间段

### 动作
- 分阶段动作：按时间段拆分描述
- 多人物时需分别描述每个人物的动作

### 高光情节（重要）
- 视频中最精彩、最吸引人的瞬间
- 后续变体中必须保留

## 输出要求

请严格按照JSON格式输出视频解析结果。"""
        return prompt

    return ""

def parse_api_result(result, video_duration, num_options):
    """解析API返回结果"""
    # 计算分段时间节点
    if video_duration <= 10:
        time_nodes = [f"0-{video_duration//2}秒", f"{video_duration//2}-{video_duration}秒"]
    elif video_duration <= 15:
        time_nodes = [f"0-{video_duration//3}秒", f"{video_duration//3}-{video_duration*2//3}秒", f"{video_duration*2//3}-{video_duration}秒"]
    else:
        time_nodes = [f"0-{video_duration//4}秒", f"{video_duration//4}-{video_duration//2}秒",
                      f"{video_duration//2}-{video_duration*3//4}秒", f"{video_duration*3//4}-{video_duration}秒"]

    prompts = []
    for i in range(num_options):
        prompts.append({
            "title": f"方案{i+1}",
            "duration": video_duration,
            "time_nodes": time_nodes,
            "prompt": result if result else "提示词内容"
        })
    return prompts


def build_step2_prompt(parse_result, video_duration, change_elements, highlight, num_options, image_count):
    """构建方案二第二步的提示词"""
    change_str = "、".join(change_elements)

    prompt = f"""# 任务：根据视频解析结果生成生视频提示词

## 输入
- 变更类型：{change_str}
- 生成组数：{num_options}
- 视频解析结果：
{parse_result}

## 核心规则
- **语言：输出中文提示词**
- 只按用户指定的变更类型生成提示词
- 其他未指定的要素100%保持不变
- 保持：动作、表情、运镜、场景、故事线、时间节点

## 重要：保留吸引点
视频解析结果中的"吸引点分析"是视频吸引观众的关键，生成的提示词必须保留这些吸引点：
- 开头钩子：保留视频开头的吸引力
- 情绪触发：保留触发的情绪
- 期待设置：保留设置的悬念
- 视觉亮点：保留吸引眼球的视觉元素
- 内容槽点：保留让人想评论的点
- 传播动机：保留让观众想分享的元素

---

## 变更规则

### 角色
- 保守：只换脸/面部，保持发型、服装、动作、表情
- 中等：换脸+发型，保持服装、动作、表情
- 激进：换脸+发型+服装，保持动作、表情
- 直接转化：不主动变更，利用模型随机性自然产生变化

### 场景
- 保守：只换地点，保持原有环境元素、动作
- 中等：换地点+部分环境元素，保持主要建筑风格
- 激进：完全不同的场景，保持动作
- 直接转化：不主动变更，利用模型随机性自然产生变化

### 画面氛围
- 保守：只变光线明暗，保持色调
- 中等：变光线+色调（冷/暖），保持情绪
- 激进：根据方案整体设定，自由重塑整体氛围
- 直接转化：不主动改写氛围描述

### 画风
- 保守：写实风格微调
- 中等：动物拟人化
- 激进：根据本方案整体设定，自由选择或混合画风
- 直接转化：保持当前画面风格不变，仅对细节轻微润色

### 其他（自由组合角色+场景+画面氛围+画风）
- 变更规则优先级：优先直接转化 > 保守 > 中等 > 激进
- 组合规则：
  - 多变更 ≤ 数量：每个变更项至少出现1次，剩余随机补
    - 例：4变更×5组 → 4个各1次 + 第5个随机合并项
  - 多变更 > 数量：优先保留"直接转化"，其余合并或择优
    - 例：4变更×2组 → 直接转化 + 随机合并项

---

## 输出格式

请严格按照以下格式输出，分镜要覆盖完整的视频时长：

【方案1】
变更类型：{change_str}
变更规则：保守/中等/激进/直接转化
保持了：动作、表情、运镜等
吸引点保留：描述保留了哪些吸引点
提示词：整体风格: 描述视频的整体风格、氛围、色调等

分镜1 (00:00-00:XX):
[时间点] 景别： 具体画面描述，包含人物动作、表情、场景元素等

分镜2 (00:XX-00:XX):
[时间点] 景别： 具体画面描述

（继续分镜，确保覆盖整个视频时长）

共{num_options}组，每组都要按照上述格式输出"""
    return prompt


def simulate_prompt_generation(scheme, video_duration, change_elements, highlight, image_count):
    """模拟提示词生成（当不使用真实API时）"""
    prompts = []
    change_str = "、".join(change_elements)

    # 计算分段时间节点
    if video_duration <= 10:
        time_nodes = [f"0-{video_duration//2}秒", f"{video_duration//2}-{video_duration}秒"]
    elif video_duration <= 15:
        time_nodes = [f"0-{video_duration//3}秒", f"{video_duration//3}-{video_duration*2//3}秒", f"{video_duration*2//3}-{video_duration}秒"]
    else:
        time_nodes = [f"0-{video_duration//4}秒", f"{video_duration//4}-{video_duration//2}秒",
                      f"{video_duration//2}-{video_duration*3//4}秒", f"{video_duration*3//4}-{video_duration}秒"]

    styles = ["电影感", "动漫风", "写实风", "浪漫唯美", "紧张刺激"]
    for i, style in enumerate(styles[:len(change_elements) + 2]):
        prompts.append({
            "title": f"{style}风格",
            "duration": video_duration,
            "time_nodes": time_nodes,
            "prompt": f"保留原视频的故事线、动作序列、运镜方式。变更{change_str}。主体：根据变更要素描述。场景：基于原场景调整。动作：参考视频的动作序列和节奏。运镜：专业运镜。氛围：与风格匹配。"
        })
    return prompts


def split_prompt(prompt, video_duration, model_type):
    """
    提示词拆分

    当视频时长超过生视频模型限制时，将提示词拆分成多个分段提示词

    Args:
        prompt: 原始完整提示词
        video_duration: 视频时长（秒）
        model_type: 模型类型 ("Seedance" 或 "Wan2.6")

    Returns:
        拆分后的提示词列表
    """
    # 模型时长限制
    max_duration = {
        "Seedance": 15,
        "Wan2.6": 10
    }.get(model_type, 15)

    # 如果视频时长不超过限制，不需要拆分
    if video_duration <= max_duration:
        return [{
            "task_id": 1,
            "time_range": f"0-{video_duration}秒",
            "duration": video_duration,
            "prompt": prompt
        }]

    # 计算需要拆分的数量
    import math
    num_splits = math.ceil(video_duration / max_duration)

    # 计算每个分段时长
    split_duration = video_duration / num_splits

    # 生成拆分结果
    split_prompts = []
    for i in range(num_splits):
        start_time = int(i * split_duration)
        end_time = int((i + 1) * split_duration) if i < num_splits - 1 else video_duration

        # 生成该时间段的提示词
        split_prompt_text = f"""【第{i+1}段：{start_time}-{end_time}秒】

原始提示词对应此时间段的描述：
- 时长：{end_time - start_time}秒

{prompt}

**注意**：此提示词对应原视频的{start_time}-{end_time}秒，请保留该时间段的完整动作和情节。"""

        # 添加承接描述（除了第一段）
        if i > 0:
            split_prompt_text = f"承接上一段：继续进行\n\n{split_prompt_text}"

        # 添加转出描述（除了最后一段）
        if i < num_splits - 1:
            split_prompt_text = f"{split_prompt_text}\n\n**准备转场**：为下一段做铺垫"

        split_prompts.append({
            "task_id": i + 1,
            "time_range": f"{start_time}-{end_time}秒",
            "duration": end_time - start_time,
            "prompt": split_prompt_text
        })

    return split_prompts


def optimize_prompt(user_prompt, model_type):
    """
    根据不同模型的特点优化提示词

    Args:
        user_prompt: 用户写的原始提示词
        model_type: 模型类型 ("Seedance" 或 "Wan2.6")

    Returns:
        优化后的提示词
    """
    if model_type == "Seedance":
        prompt = f"""请将以下提示词优化为适合 Seedance 2.0 模型的生视频提示词。

## Seedance 2.0 模型特点
- 支持多模态输入：文本、图片、视频、音频
- 用 @素材名 指定每个素材的用途
- 时长：4-15秒
- 优势：运镜参考、动作参考、视频延长
- 限制：不支持写实人脸

## 优化规则
1. 如需参考图片，用 @图片1、@图片2 格式
2. 如需参考视频，用 @视频1 格式
3. 如需首帧/尾帧，用"@图片1作为首帧"格式
4. 明确标注运镜要求（如"固定镜头"、"跟随镜头"）
5. 描述连续动作时用"然后"、"接着"连接

## 用户提示词
{user_prompt}

## 输出要求
输出优化后的中文提示词，保持原意但符合 Seedance 模型规范。"""
    else:  # Wan2.6
        prompt = f"""请将以下提示词优化为适合 Wan2.6 模型的生视频提示词。

## Wan2.6 模型特点
- 基础公式：主体 + 场景 + 运动
- 进阶公式：主体描述 + 场景描述 + 运动描述 + 美学控制 + 风格化
- 支持参考角色：@主角 + 动作 + 台词 + 场景
- 支持多镜头：总体描述 + 镜头序号 + 时间戳 + 分镜内容
- 时长：4-10秒

## 优化规则
1. 明确主体：人、动物、物品或想象物体
2. 具体场景：环境、背景、前景
3. 精确运动：幅度、频率、效果
4. 美学控制：光源、光线、景别、运镜
5. 风格化：画面风格描述

## 用户提示词
{user_prompt}

## 输出要求
输出优化后的中文提示词，按照 Wan2.6 公式结构：主体 + 场景 + 运动 + 美学 + 风格"""

    return prompt

# ==================== 样式 ====================
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .result-box {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .highlight {
        background-color: #e8f4fd;
        padding: 0.2rem 0.5rem;
        border-radius: 0.3rem;
    }
    .api-key-input input {
        font-family: monospace;
    }
    .tab-content {
        padding: 1rem 0;
    }
    .stProgress > div > div > div {
        background-color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 侧边栏 ====================
st.sidebar.title("⚙️ 配置")

# Tab切换：配置 / 生成 / 优化
tab_mode = st.sidebar.radio(
    "模式",
    ["配置", "生成提示词", "优化提示词", "手动生成视频"],
    index=1
)

# ==================== API配置区域 ====================
st.sidebar.markdown("---")
st.sidebar.subheader("🔑 API配置")

# 提示词生成模型配置
st.sidebar.markdown("### 提示词生成模型")
prompt_model = st.sidebar.selectbox(
    "选择模型",
    ["Gemini", "OpenAI GPT-4V", "Claude-3-5"],
    index=0,
    key="prompt_model_select"
)

if prompt_model == "Gemini":
    prompt_api_key = st.sidebar.text_input(
        "Gemini API Key",
        type="password",
        placeholder="请输入Gemini API Key",
        key="gemini_key"
    )
    prompt_model_name = st.sidebar.text_input(
        "模型名称",
        value="gemini-2.5-pro",
        key="gemini_model"
    )
elif prompt_model == "OpenAI GPT-4V":
    prompt_api_key = st.sidebar.text_input(
        "OpenAI API Key",
        type="password",
        placeholder="请输入OpenAI API Key",
        key="openai_key"
    )
    prompt_model_name = st.sidebar.selectbox(
        "模型名称",
        ["gpt-4o", "gpt-4o-mini"],
        key="openai_model"
    )
else:  # Claude
    prompt_api_key = st.sidebar.text_input(
        "Claude API Key",
        type="password",
        placeholder="请输入Claude API Key",
        key="claude_key"
    )
    prompt_model_name = st.sidebar.selectbox(
        "模型名称",
        ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022"],
        key="claude_model"
    )

# 视频生成模型配置
st.sidebar.markdown("---")
st.sidebar.subheader("🎬 视频生成模型")

video_model_provider = st.sidebar.selectbox(
    "选择平台",
    ["Seedance (即梦)", "Wan2.6 (阿里云)"],
    index=0,
    key="video_provider"
)

if video_model_provider == "Seedance (即梦)":
    video_api_key = st.sidebar.text_input(
        "即梦 API Key",
        type="password",
        placeholder="请输入即梦API Key",
        key="jimeng_key"
    )
else:  # Wan2.6
    video_api_key = st.sidebar.text_input(
        "阿里云 DashScope API Key",
        type="password",
        placeholder="请输入阿里云API Key",
        key="aliyun_key"
    )

# 保存配置到session_state
st.session_state.prompt_api_key = prompt_api_key
st.session_state.prompt_model = prompt_model
st.session_state.prompt_model_name = prompt_model_name
st.session_state.video_api_key = video_api_key
st.session_state.video_model_provider = video_model_provider

# ==================== 主页面 ====================
st.title("🎬 视频生成提示词生成器")

# ==================== 模式：生成提示词 ====================
if tab_mode == "生成提示词":
    st.header("📤 素材上传与参数配置")

    col1, col2 = st.columns(2)

    with col1:
        # 参考视频
        video_file = st.file_uploader(
            "上传参考视频",
            type=['mp4', 'mov'],
            help="支持2-30秒的视频"
        )

        # 保存视频文件到临时路径
        video_file_path = None
        if video_file:
            # 保存到临时文件
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_file.write(video_file.read())
                video_file_path = tmp_file.name
            st.video(video_file)
            video_duration = st.number_input(
                "视频时长（秒）",
                min_value=2,
                max_value=30,
                value=12,
                key="video_duration_input"
            )
        else:
            st.info("请上传参考视频")
            video_duration = st.number_input(
                "视频时长（秒）",
                min_value=2,
                max_value=30,
                value=12,
                disabled=True,
                key="video_duration_disabled"
            )

    with col2:
        # 参考图片
        st.write("上传参考图片（最多9张）")
        image_files = st.file_uploader(
            "选择参考图片",
            type=['jpg', 'jpeg', 'png', 'webp'],
            accept_multiple_files=True,
            help="最多9张"
        )

        # 保存图片文件到临时路径
        image_file_paths = []
        if image_files:
            st.write(f"已上传 {len(image_files)} 张图片")
            cols = st.columns(min(len(image_files), 3))
            import tempfile
            for i, img in enumerate(image_files[:9]):
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp_file:
                    tmp_file.write(img.read())
                    image_file_paths.append(tmp_file.name)
                with cols[i % 3]:
                    st.image(img, width=100)

    # 参数配置
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        # 单选变更要素
        change_type = st.radio(
            "选择变更要素",
            ["角色", "场景", "画面氛围", "画风", "其他（自由组合）"],
            index=0,
            horizontal=True,
            key="change_type_radio"
        )
        # "其他" 表示自由组合所有类型
        if change_type == "其他（自由组合）":
            change_elements = ["角色", "场景", "画面氛围", "画风"]
        else:
            change_elements = [change_type]

    with col2:
        num_options = st.selectbox(
            "生成提示词组数",
            options=list(range(1, 11)),
            index=2,
            key="num_options_input"
        )

    # 方案选择
    st.markdown("---")
    scheme = st.radio(
        "选择方案",
        ["方案一：直接生成", "方案二：先解析后生成"],
        index=0,
        horizontal=True,
        key="scheme_radio"
    )

    # 高光情节
    highlight = st.text_area(
        "高光情节（可选）",
        placeholder="描述视频中最精彩的瞬间，如：第6-8秒的360度旋转",
        help="用户可手动标注视频中最精彩的瞬间，生成时会保留",
        key="highlight_input"
    )

    # 生成按钮
    st.markdown("---")
    use_real_api = st.checkbox("使用真实API调用", value=True, key="use_real_api")

    # 方案二的两步流程状态
    scheme_key = f"{scheme}_{video_duration}"
    if scheme_key not in st.session_state.scheme_step:
        st.session_state.scheme_step[scheme_key] = {"step": 1, "parse_result": None}

    current_step = st.session_state.scheme_step[scheme_key]["step"]
    parse_result = st.session_state.scheme_step[scheme_key].get("parse_result")

    # 方案二：第一步-视频解析
    if scheme == "方案二：先解析后生成" and current_step == 1:
        st.info("📋 方案二流程：第一步 - 视频解析")

    # 生成按钮
    if st.button("🚀 生成提示词", type="primary", use_container_width=True, key="generate_btn"):

        if not change_type:
            st.error("请选择一个变更要素")
        elif use_real_api and not prompt_api_key:
            st.error("请先配置API Key")
        else:
            with st.spinner("生成中..."):
                try:
                    # 方案二：第一步 - 视频解析
                    if scheme == "方案二：先解析后生成" and current_step == 1:
                        # 第一步：解析视频
                        system_prompt = build_system_prompt(
                            scheme=scheme,
                            video_duration=video_duration,
                            change_elements=change_elements,
                            highlight=highlight,
                            num_options=num_options
                        )

                        if use_real_api and prompt_api_key:
                            result = call_prompt_api(
                                model=prompt_model,
                                api_key=prompt_api_key,
                                model_name=prompt_model_name,
                                system_prompt=system_prompt,
                                video_file_path=video_file_path,
                                image_files=image_file_paths if image_file_paths else None
                            )
                            # 保存解析结果
                            st.session_state.scheme_step[scheme_key]["parse_result"] = result
                            st.session_state.parse_result = result
                        else:
                            result = "视频解析结果（模拟）"
                            st.session_state.scheme_step[scheme_key]["parse_result"] = result
                            st.session_state.parse_result = result

                        # 更新步骤
                        st.session_state.scheme_step[scheme_key]["step"] = 2

                        st.success("✅ 视频解析完成！请确认解析结果后继续生成提示词")
                        st.rerun()

                    else:
                        # 方案一直接生成 或 方案二第二步
                        if scheme == "方案二：先解析后生成" and parse_result:
                            # 第二步：生成提示词
                            system_prompt = build_step2_prompt(
                                parse_result=parse_result,
                                video_duration=video_duration,
                                change_elements=change_elements,
                                highlight=highlight,
                                num_options=num_options,
                                image_count=len(image_file_paths)
                            )
                        else:
                            # 方案一
                            system_prompt = build_system_prompt(
                                scheme=scheme,
                                video_duration=video_duration,
                                change_elements=change_elements,
                                highlight=highlight,
                                num_options=num_options
                            )

                        if use_real_api and prompt_api_key:
                            # 调用真实API
                            result = call_prompt_api(
                                model=prompt_model,
                                api_key=prompt_api_key,
                                model_name=prompt_model_name,
                                system_prompt=system_prompt,
                                video_file_path=video_file_path if scheme == "方案一：直接生成" else None,
                                image_files=image_file_paths if image_file_paths else None
                            )

                            # 解析API返回结果
                            prompts = parse_api_result(result, video_duration, num_options)
                        else:
                            # 模拟生成
                            prompts = simulate_prompt_generation(
                                scheme=scheme,
                                video_duration=video_duration,
                                change_elements=change_elements,
                                highlight=highlight,
                                image_count=len(image_file_paths)
                            )

                        st.session_state.prompts = prompts
                        st.session_state.video_file_path = video_file_path
                        st.session_state.image_file_paths = image_file_paths
                        st.session_state.scheme_step[scheme_key]["step"] = 1  # 重置步骤
                        st.success("✅ 提示词生成成功！")

                except Exception as e:
                    st.error(f"生成失败: {str(e)}")

    # 显示方案二的解析结果（第一步）
    if scheme == "方案二：先解析后生成" and parse_result:
        st.markdown("---")
        st.subheader("📋 视频解析结果")

        with st.expander("查看解析详情", expanded=True):
            st.text_area(
                "解析结果",
                value=parse_result,
                height=300,
                key="parse_result_display",
                disabled=True
            )

        # 第二步生成按钮 - 直接执行第二步生成
        if st.button("继续生成提示词 →", type="primary", use_container_width=True, key="step2_btn"):
            if not change_elements:
                st.error("请至少选择一个变更要素")
            elif use_real_api and not prompt_api_key:
                st.error("请先配置API Key")
            else:
                with st.spinner("生成中..."):
                    try:
                        # 构建第二步提示词
                        system_prompt = build_step2_prompt(
                            parse_result=parse_result,
                            video_duration=video_duration,
                            change_elements=change_elements,
                            highlight=highlight,
                            num_options=num_options,
                            image_count=len(image_file_paths)
                        )

                        if use_real_api and prompt_api_key:
                            result = call_prompt_api(
                                model=prompt_model,
                                api_key=prompt_api_key,
                                model_name=prompt_model_name,
                                system_prompt=system_prompt,
                                video_file_path=None,  # 第二步不需要视频
                                image_files=image_file_paths if image_file_paths else None
                            )
                            prompts = parse_api_result(result, video_duration, num_options)
                        else:
                            prompts = simulate_prompt_generation(
                                scheme=scheme,
                                video_duration=video_duration,
                                change_elements=change_elements,
                                highlight=highlight,
                                image_count=len(image_file_paths)
                            )

                        st.session_state.prompts = prompts
                        st.session_state.video_file_path = video_file_path
                        st.session_state.image_file_paths = image_file_paths
                        st.session_state.scheme_step[scheme_key]["step"] = 1  # 重置
                        st.success("✅ 提示词生成成功！")
                        st.rerun()

                    except Exception as e:
                        st.error(f"生成失败: {str(e)}")

    # 重置方案二步骤按钮
    if scheme == "方案二：先解析后生成" and current_step == 2:
        if st.button("↩️ 重新开始", key="reset_scheme"):
            st.session_state.scheme_step[scheme_key] = {"step": 1, "parse_result": None}
            st.rerun()

    # 显示结果
    if st.session_state.prompts:
        st.markdown("---")
        st.header("📝 生成的提示词")

        # 选择要使用的提示词
        prompt_options = [f"方案{i+1}: {p['title']}" for i, p in enumerate(st.session_state.prompts)]
        selected_prompt_idx = st.radio(
            "选择提示词",
            options=list(range(len(st.session_state.prompts))),
            format_func=lambda x: prompt_options[x]
        )

        selected_prompt = st.session_state.prompts[selected_prompt_idx]

        # 保存选中的提示词
        st.session_state.selected_prompt_for_video = selected_prompt

        with st.expander("查看提示词详情", expanded=True):
            st.markdown(f"""
            <div class="result-box">
                <p><strong>原始视频时长：</strong>{selected_prompt['duration']}秒</p>
                <p><strong>分段时间节点：</strong>{', '.join(selected_prompt['time_nodes'])}</p>
                <p><strong>提示词：</strong></p>
                <div class="highlight">
                    {selected_prompt['prompt']}
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.code(selected_prompt['prompt'], language="markdown")

        # ==================== 提示词拆分功能 ====================
        st.markdown("---")
        st.subheader("✂️ 提示词拆分")

        # 选择生视频模型
        split_model = st.selectbox(
            "选择生视频模型",
            ["Seedance (最长15秒)", "Wan2.6 (最长10秒)"],
            key="split_model_select"
        )

        model_type = "Seedance" if "Seedance" in split_model else "Wan2.6"

        # 检查是否需要拆分
        video_dur = selected_prompt['duration']
        max_dur = 15 if model_type == "Seedance" else 10

        if video_dur > max_dur:
            st.warning(f"⚠️ 视频时长{video_dur}秒超过{model_type}限制{max_dur}秒，将自动拆分")

            # 执行拆分
            if st.button("执行拆分", key="split_btn"):
                split_results = split_prompt(
                    prompt=selected_prompt['prompt'],
                    video_duration=video_dur,
                    model_type=model_type
                )

                st.session_state.split_results = split_results

            # 显示拆分结果
            if 'split_results' in st.session_state and st.session_state.split_results:
                st.success(f"✅ 拆分完成，共{len(st.session_state.split_results)}段")

                for split in st.session_state.split_results:
                    with st.expander(f"📹 片段{split['task_id']}：{split['time_range']}（{split['duration']}秒）"):
                        st.markdown(f"**时长**：{split['duration']}秒")
                        st.code(split['prompt'], language="markdown")
        else:
            st.info(f"ℹ️ 视频时长{video_dur}秒，{model_type}可以直接生成，无需拆分")

# ==================== 模式：优化提示词 ====================
elif tab_mode == "优化提示词":
    st.header("✨ 提示词优化")

    # 选择生视频模型
    optimize_model = st.selectbox(
        "选择生视频模型",
        ["Seedance (即梦)", "Wan2.6 (阿里云)"],
        key="optimize_model"
    )

    # 输入原始提示词
    original_prompt = st.text_area(
        "输入要优化的提示词",
        height=200,
        placeholder="请输入您写的生视频提示词...",
        key="original_prompt"
    )

    # 优化按钮
    if st.button("✨ 优化提示词", type="primary", use_container_width=True, key="optimize_btn"):
        if not original_prompt:
            st.error("请输入提示词")
        else:
            with st.spinner("优化中..."):
                try:
                    # 根据选择的模型优化提示词
                    model_key = "Seedance" if "Seedance" in optimize_model else "Wan2.6"

                    # 构建优化提示词
                    system_prompt = optimize_prompt(original_prompt, model_key)

                    # 调用API
                    result = call_prompt_api(
                        model=prompt_model,
                        api_key=prompt_api_key,
                        model_name=prompt_model_name,
                        system_prompt=system_prompt,
                        video_file_path=None,
                        image_files=None
                    )

                    st.session_state.optimized_prompt = result
                    st.success("✅ 优化完成！")

                except Exception as e:
                    st.error(f"优化失败: {str(e)}")

    # 显示优化结果
    if 'optimized_prompt' in st.session_state and st.session_state.optimized_prompt:
        st.markdown("---")
        st.subheader("📝 优化后的提示词")

        optimized = st.session_state.optimized_prompt

        st.text_area(
            "优化结果",
            value=optimized,
            height=300,
            key="optimized_result",
            disabled=True
        )

        # 复制按钮
        if st.button("📋 复制提示词", key="copy_optimized"):
            st.toast("已复制到剪贴板")

# ==================== 模式：手动生成视频 ====================
elif tab_mode == "手动生成视频":
    st.header("🎬 手动生成视频")

    # 手动输入提示词
    manual_prompt = st.text_area(
        "输入视频提示词",
        placeholder="请输入视频生成提示词，如：一只可爱的小猫在草地上奔跑...",
        height=150,
        key="manual_prompt_input"
    )

    st.markdown("---")

    # 上传参考素材
    st.subheader("📎 参考素材（可选）")

    col1, col2 = st.columns(2)

    with col1:
        # 参考图片
        ref_images = st.file_uploader(
            "上传参考图片",
            type=['png', 'jpg', 'jpeg', 'webp'],
            accept_multiple_files=True,
            key="ref_images_uploader"
        )

    with col2:
        # 参考视频
        ref_video = st.file_uploader(
            "上传参考视频",
            type=['mp4', 'mov', 'avi'],
            accept_multiple_files=False,
            key="ref_video_uploader"
        )

    # 显示已上传的素材
    if ref_images:
        st.success(f"已上传 {len(ref_images)} 张参考图片")
    if ref_video:
        st.success(f"已上传参考视频: {ref_video.name}")

    st.markdown("---")

    # 视频生成参数
    st.subheader("⚙️ 生成参数")

    col1, col2 = st.columns(2)
    with col1:
        output_duration = st.number_input(
            "生成长度（秒）",
            min_value=4,
            max_value=15,
            value=5,
            key="manual_output_duration"
        )
    with col2:
        output_quality = st.selectbox(
            "输出质量",
            ["720p", "1080p"],
            index=0,
            key="manual_output_quality"
        )

    # 分辨率映射
    resolution_map = {
        "720p": "1280*720",
        "1080p": "1920*1080"
    }

    # 生成按钮
    st.markdown("---")

    if st.button("🎬 生成视频", type="primary", use_container_width=True, key="manual_generate_video_btn"):
        if not manual_prompt:
            st.error("请输入视频提示词")
        elif not video_api_key:
            st.error("请先配置视频生成API Key")
        else:
            with st.spinner("视频生成中，请稍候..."):
                try:
                    # 处理参考图片
                    ref_image_paths = []
                    if ref_images:
                        for img in ref_images:
                            # 保存上传的图片到临时文件
                            import tempfile
                            with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{img.name}") as tmp:
                                tmp.write(img.getvalue())
                                ref_image_paths.append(tmp.name)

                    # 处理参考视频
                    ref_video_path = None
                    if ref_video:
                        import tempfile
                        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{ref_video.name}") as tmp:
                            tmp.write(ref_video.getvalue())
                            ref_video_path = tmp.name

                    # 调用API生成视频
                    result = call_video_api(
                        provider=video_model_provider,
                        api_key=video_api_key,
                        prompt=manual_prompt,
                        reference_video_path=ref_video_path,
                        reference_images=ref_image_paths if ref_image_paths else None,
                        duration=output_duration,
                        resolution=resolution_map[output_quality]
                    )

                    if result.get("status") == "error":
                        st.error(f"生成失败: {result.get('error')}")
                    else:
                        st.session_state.video_task_id = result.get("task_id")
                        st.session_state.video_result = result

                        # 显示进度
                        progress_bar = st.progress(0.0)
                        status_text = st.empty()

                        # 轮询获取结果
                        max_retries = 60
                        for i in range(max_retries):
                            status_text.text(f"等待视频生成... ({i+1}/{max_retries})")
                            progress_bar.progress((i + 1) / max_retries)

                            # 检查结果
                            if st.session_state.video_task_id:
                                result = get_video_result(
                                    provider=video_model_provider,
                                    api_key=video_api_key,
                                    task_id=st.session_state.video_task_id
                                )

                                if result.get("status") == "completed":
                                    progress_bar.progress(1.0)
                                    status_text.text("✅ 视频生成完成！")
                                    st.session_state.video_result = result
                                    break
                                elif result.get("status") == "failed":
                                    progress_bar.progress(0.0)
                                    status_text.text(f"❌ 生成失败: {result.get('error')}")
                                    break

                            time.sleep(2)

                        if result.get("status") == "completed":
                            st.success("✅ 视频生成完成！")
                        else:
                            st.info("⏳ 视频正在后台生成，可稍后刷新查看结果")

                except Exception as e:
                    st.error(f"生成失败: {str(e)}")

    # 显示生成结果
    if st.session_state.get('video_result'):
        st.markdown("---")
        st.header("📹 生成结果")

        result = st.session_state.video_result
        col1, col2 = st.columns(2)
        with col1:
            st.metric("状态", result.get("status", "unknown"))
        with col2:
            st.metric("耗时", f"{result.get('duration', 'N/A')}秒")

        if result.get("video_url"):
            st.video(result["video_url"])
            st.markdown(f"**视频链接**: [点击下载]({result['video_url']})")

        if result.get("error"):
            st.error(f"错误信息: {result['error']}")

# ==================== 模式：配置 ====================
else:
    st.header("⚙️ 配置说明")

    st.markdown("""
    ### API配置说明

    #### 提示词生成模型
    | 模型 | 说明 | 获取方式 |
    |------|------|----------|
    | Gemini | Google视频理解模型 | [Google AI Studio](https://aistudio.google.com/app/apikey) |
    | OpenAI GPT-4V | OpenAI多模态模型 | [OpenAI Platform](https://platform.openai.com/api-keys) |
    | Claude | Anthropic多模态模型 | [Claude Console](https://console.anthropic.com/) |

    #### 视频生成模型
    | 平台 | 模型 | 获取方式 |
    |------|------|----------|
    | 即梦 (Seedance) | Seedance 2.0 | [即梦官网](https://jimeng.jianying.com/) |
    | 阿里云 (Wan2.6) | Wan2.6 | [DashScope](https://dashscope.console.aliyun.com/) |

    ### 使用流程
    1. 在「配置」页面获取API Key
    2. 在「生成提示词」页面上传素材，生成提示词
    3. 选择满意的提示词
    4. 在「生成视频」页面调用视频生成模型

    ### 注意事项
    - API调用会产生费用，请妥善保管API Key
    - 部分模型需要先在对应平台申请访问权限
    """)



    if scheme == "方案一：直接生成":
        prompt = f"""你是一个专业的视频创意导演。请根据以下信息生成视频生成提示词：

## 参考视频信息
- 时长：{video_duration}秒
- 变更要素：{change_str}
- 高光情节：{highlight if highlight else '无'}

## 生成要求
1. 保留参考视频的核心要素：故事线、动作序列、运镜方式、高光情节
2. 只变更指定的要素：{change_str}
3. 其他要素自由发挥
4. 生成{len(change_elements) + 2}组不同的提示词

## 输出格式
每组提示词包含：
- 标题：简短的风格描述
- 保留：保留的核心要素
- 变更：变更的要素
- 主体：角色描述
- 场景：环境描述
- 动作：动作描述
- 镜头：运镜描述
- 氛围：氛围描述

请直接输出提示词内容。"""
    else:
        # 方案二
        prompt = f"""你是一个专业的视频创意导演。请根据以下信息生成视频生成提示词：

## 用户需求
- 变更要素：{change_str}
- 高光情节：{highlight if highlight else '无'}

## 生成要求
1. 保留视频解析信息中的核心要素：故事线、动作序列、运镜方式、高光情节、场景切换
2. 只变更指定的要素：{change_str}
3. 其他要素自由发挥
4. 生成{len(change_elements) + 2}组不同的提示词

## 输出格式
每组提示词包含：
- 标题：简短的风格描述
- 保留：保留的核心要素
"""
