# backend/app/services/script_generator.py
"""Script Generation Service"""
from typing import List, Dict, Any
import re
from app.services.llm import llm_manager, BaseLLMProvider
from app.services.quality_detector import QualityDetector, get_quality_detector
from app.schemas.script import ScriptSegment
from app.config import settings


class ScriptGenerator:
    """Service for generating video scripts"""

    def __init__(self, provider_name: str = None, quality_detector: QualityDetector = None):
        self.provider_name = provider_name or settings.DEFAULT_LLM_PROVIDER
        self.quality_detector = quality_detector or get_quality_detector()

    @property
    def llm(self) -> BaseLLMProvider:
        """Get the LLM provider"""
        return llm_manager.get_provider(self.provider_name)

    def _needs_chinese_rewrite(self, text: str) -> bool:
        """Detect if output should be rewritten to Chinese-centric content."""
        if not text:
            return False

        zh_count = len(re.findall(r"[\u4e00-\u9fff]", text))
        en_count = len(re.findall(r"[A-Za-z]", text))

        # If there are enough Chinese chars, or English is minimal, no rewrite needed.
        if zh_count >= 80:
            return False
        if en_count <= 120:
            return False

        # Rewrite when English significantly outweighs Chinese.
        return en_count > zh_count * 1.2

    async def _rewrite_as_chinese(self, text: str, content_type: str) -> str:
        """Rewrite generated text to Chinese body content."""
        prompt = f"""请将以下{content_type}改写为中文正文版本，保持信息完整，不要删减关键内容。

要求：
1. 正文必须以中文为主
2. 专业术语、品牌名、API 名称可保留英文
3. 不要整段英文输出
4. 保持原有结构与逻辑层次
5. 直接输出改写结果，不要解释

原文：
{text}
"""
        return await self.llm.generate(prompt, max_tokens=4096, temperature=0.2)

    async def generate_outline(self, topic: str, style: str = "educational", custom_prompt: str = None) -> str:
        """
        Generate a video script outline based on topic

        Args:
            topic: The video topic/title
            style: The style of the video (educational, entertaining, news, etc.)

        Returns:
            Outline text
        """
        prompt = custom_prompt.strip() if custom_prompt else self.build_outline_prompt(topic=topic, style=style)

        outline = await self.llm.generate(prompt, max_tokens=2048)
        if self._needs_chinese_rewrite(outline):
            try:
                outline = await self._rewrite_as_chinese(outline, "视频大纲")
            except Exception:
                # Keep original if rewrite fails
                pass
        return outline

    def build_outline_prompt(self, topic: str, style: str = "educational") -> str:
        """Build the outline prompt sent to LLM."""
        return f"""你是一位资深短视频内容策划师（抖音/视频号/小红书方向），请为以下主题产出“高完播率、高互动”的可执行大纲。

主题：{topic}
风格：{style}

要求：
1. 输出总时长建议：90-150秒，按“3秒钩子-主体推进-结尾行动引导”设计节奏
2. 先给出受众画像（痛点、期待、认知水平）与内容定位
3. 给出至少 3 个开场钩子备选（反差、提问、冲突、数据震撼任选）
4. 主体至少拆成 4-6 个信息段，每段必须写明：目标、核心信息、证明素材、情绪基调、预计时长
5. 明确每段建议画面类型（口播/B-roll/截图/实拍/动画）与转场方式
6. 单独列出“互动点设计”：评论引导、收藏引导、转发触发点
7. 单独列出“风险与合规提醒”：避免夸大、避免绝对化表述
8. 必须使用中文正文输出；除专业术语、品牌名、API 名称外，不要大段使用英文

输出格式（严格遵守）：
【受众与定位】
- 受众画像：
- 核心痛点：
- 内容承诺：

【开场钩子（3选1）】
1)
2)
3)

【分段大纲（90-150秒）】
第1段（xx秒）：
- 目标：
- 关键信息：
- 画面建议：
- 情绪与节奏：

...（继续到最后一段）

【互动与转化设计】
- 评论引导：
- 收藏引导：
- 转发引导：

【风险与合规提醒】
- ...
"""

    async def generate_full_script(self, outline: str, topic: str, custom_prompt: str = None) -> Dict[str, Any]:
        """
        Generate full script with segments from outline

        Args:
            outline: The video outline
            topic: The video topic

        Returns:
            Dictionary containing full_script text, segments list, and quality report
        """
        prompt = custom_prompt.strip() if custom_prompt else self.build_full_script_prompt(outline=outline, topic=topic)
        if "{{OUTLINE}}" in prompt:
            prompt = prompt.replace("{{OUTLINE}}", outline or "")

        full_script = await self.llm.generate(prompt, max_tokens=4096)
        if self._needs_chinese_rewrite(full_script):
            try:
                full_script = await self._rewrite_as_chinese(full_script, "视频脚本")
            except Exception:
                # Keep original if rewrite fails
                pass

        # Create simplified segments for now (10 segments with placeholder text)
        # In production, this would parse the actual script into segments
        segments = self._create_segments(full_script)

        # Detect script quality
        quality_report = self.quality_detector.detect_script_quality(full_script, segments)

        return {
            "full_script": full_script,
            "segments": segments,
            "quality_report": quality_report
        }

    def build_full_script_prompt(self, outline: str, topic: str) -> str:
        """Build the full script prompt sent to LLM."""
        return f"""你是一位爆款短视频导演、编剧和后期统筹。请基于以下大纲，生成“可直接交给拍摄与剪辑团队执行”的完整版脚本。

主题：{topic}

大纲：
{outline}

要求：
1. 总时长 90-150 秒，中文正文不少于 1500 字，信息密度高于常规口播
2. 至少输出 12-16 个镜头，镜头之间有明确“起承转合”和节奏爬升
3. 必须覆盖：分镜、旁白、画面调度、音乐/音效、字幕、转场、导演提示
4. 每个镜头都必须包含：
   - 镜头编号与时长
   - 景别/机位/运镜（如推拉摇移跟、手持或稳定器）
   - 画面内容与人物动作（具体到可执行）
   - 旁白（完整台词，避免空话）
   - 字幕（精简有力，可做重点高亮）
   - 音乐/音效（曲风、节奏点、卡点建议）
   - 剪辑提示（节奏、转场、是否叠加素材）
5. 开场前 3-8 秒必须有强钩子；中段至少 2 个情绪峰值；结尾必须有行动号召（评论/关注/私信/收藏）
6. 音频设计必须分层：人声、BGM、环境音、强调音效，标注出现时机与强弱
7. 若涉及数据/观点，优先加入“可视化呈现建议”（图表、关键词大字、对比画面）
8. 必须使用中文正文输出；除专业术语、品牌名、API 名称外，不要大段使用英文
9. 不要输出解释性前言，不要道歉，不要免责声明，直接给正文成片方案
10. 若你需要引用大纲，请以当前“大纲”字段为准（若用户自定义 Prompt 中包含 {{OUTLINE}}，系统会自动替换）

输出结构（严格遵守）：

【视频定位】
- 目标受众：
- 核心卖点：
- 情绪曲线：
- 对标账号风格关键词：

【详细执行脚本】
（逐镜头输出，至少 12-16 个镜头）
镜头1：
- 时长：
- 景别/机位：
- 画面与动作：
- 旁白：
- 字幕：
- 音乐/音效：
- 剪辑提示：
- 导演提示：

...（持续到最后一个镜头）

【后期与剪辑建议】
- 转场节奏建议：
- 字幕排版建议：
- BGM与音效混音建议：
- 封面标题与前3秒文案建议（至少3套）：

请直接输出脚本正文，不要输出“说明、解释、免责声明”。"""

    def _create_segments(self, full_script: str) -> List[ScriptSegment]:
        """
        Create script segments from full script text

        Args:
            full_script: The complete script text

        Returns:
            List of ScriptSegment objects
        """
        import uuid

        # Simplified implementation: create 10 segments
        # In production, this would intelligently parse the script
        segments = []
        for i in range(10):
            segment = ScriptSegment(
                id=str(uuid.uuid4()),
                text=f"Segment {i+1} content placeholder",
                duration=6.0,  # 6 seconds per segment
                emotion="neutral",
                material_ids=[]
            )
            segments.append(segment)

        return segments
