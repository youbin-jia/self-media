# backend/app/services/script_generator.py
"""Script Generation Service"""
from typing import List, Dict, Any
from app.services.llm_provider import LLMProvider, get_llm_provider
from app.services.quality_detector import QualityDetector, get_quality_detector
from app.schemas.script import ScriptSegment


class ScriptGenerator:
    """Service for generating video scripts"""

    def __init__(self, llm_provider: LLMProvider = None, quality_detector: QualityDetector = None):
        self.llm = llm_provider or get_llm_provider()
        self.quality_detector = quality_detector or get_quality_detector()

    async def generate_outline(self, topic: str, style: str = "educational") -> str:
        """
        Generate a video script outline based on topic

        Args:
            topic: The video topic/title
            style: The style of the video (educational, entertaining, news, etc.)

        Returns:
            Outline text
        """
        prompt = f"""你是一位专业的短视频脚本策划师。请为以下主题创建一个详细的视频大纲。

主题：{topic}
风格：{style}

要求：
1. 分析这个主题的核心价值和吸引点
2. 确定目标受众
3. 设计视频结构（开头、主体、结尾）
4. 每个部分标注时长建议
5. 标注重点内容和关键信息

请以清晰的层次结构输出大纲。"""

        outline = await self.llm.generate(prompt, max_tokens=2048)
        return outline

    async def generate_full_script(self, outline: str, topic: str) -> Dict[str, Any]:
        """
        Generate full script with segments from outline

        Args:
            outline: The video outline
            topic: The video topic

        Returns:
            Dictionary containing full_script text, segments list, and quality report
        """
        prompt = f"""你是一位专业的短视频脚本撰写师。请根据以下大纲创作完整的视频脚本。

主题：{topic}

大纲：
{outline}

要求：
1. 语言生动、口语化，适合视频表达
2. 每个段落要有明确的情感基调
3. 标注每个段落的建议时长
4. 内容要有节奏感，注意起承转合
5. 总时长控制在60-90秒

请直接输出脚本内容，不需要解释。"""

        full_script = await self.llm.generate(prompt, max_tokens=4096)

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
