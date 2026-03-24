# backend/app/services/script_generator.py
"""Script Generation Service"""
from typing import List, Dict, Any, Optional
import re
from app.services.llm import llm_manager, BaseLLMProvider
from app.services.quality_detector import QualityDetector, get_quality_detector
from app.schemas.script import ScriptSegment
from app.config import settings

# 用户自定义 prompt 中若未包含此锚点，则自动追加大纲口播容量硬约束（与 build_outline_prompt 一致）
SYS_MARK_OUTLINE_VOICEROVER = "【系统强制·口播字数与时长】"
# 用户自定义 prompt 中若未包含此锚点，则自动追加完整脚本旁白/时长硬约束
SYS_MARK_FULL_VOICEROVER = "【系统强制·旁白与镜头时长】"

# 落库 output.llm_input.voiceover_length_policy_zh，与下述注入规则一致
VOICEROVER_POLICY_SNAPSHOT_ZH = (
    "【口播/旁白长度（默认 prompt 与「系统强制」注入段已包含，此处为摘要）】\n"
    "· 中文口播约 4～6 汉字/秒；镜头时长 T 秒时，本镜「旁白」建议 ⌈T×4⌉～⌈T×6⌉ 个汉字（例：20 秒 → 约 80～120 字）。\n"
    "· 大纲每段须写「口播字数建议：约 A～B 字」（A=⌈秒×4⌉，B=⌈秒×6⌉）。\n"
    "· 「字幕」仅为上屏花字/关键词，勿复述整段旁白。"
)


def ensure_outline_prompt_includes_voiceover_policy(prompt: str) -> str:
    """前端可能传入历史落库的 outline_prompt（无口播规则）；追加强制段，保证实际发给模型的文本含约束。"""
    text = (prompt or "").strip()
    if not text:
        return text
    if SYS_MARK_OUTLINE_VOICEROVER in text:
        return text
    return (
        text
        + "\n\n---\n"
        + SYS_MARK_OUTLINE_VOICEROVER
        + "\n以下为必须遵守的硬约束（与用户上文叠加执行，不可忽略）：\n"
        "1. 每一信息段除「预计时长（秒）」外，必须另写一行「口播字数建议：约 A～B 字」，"
        "其中 A=⌈时长秒×4⌉、B=⌈时长秒×6⌉（向上取整）。\n"
        "2. 中文口播约 4～6 汉字/秒；例：20 秒 → 约 80～120 字；15 秒 → 约 60～90 字；3 秒 → 约 12～18 字。\n"
        "3. 禁止只写时长却不给口播字数区间。\n"
    )


def ensure_full_script_prompt_includes_voiceover_policy(prompt: str) -> str:
    text = (prompt or "").strip()
    if not text:
        return text
    if SYS_MARK_FULL_VOICEROVER in text:
        return text
    return (
        text
        + "\n\n---\n"
        + SYS_MARK_FULL_VOICEROVER
        + "\n以下为必须遵守的硬约束（与用户上文叠加执行，不可忽略）：\n"
        "1. 每个镜头「旁白」为口播全文；镜头时长 T 秒时，旁白汉字总数须落在 ⌈T×4⌉～⌈T×6⌉ 之间。\n"
        "2. 例：T=20 秒 → 约 80～120 字，绝不允许仅二十余字结束。\n"
        "3. 「字幕」仅为 4～12 字级花字/关键词，禁止复述整段旁白。\n"
    )


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

    def resolve_outline_prompt(
        self, topic: str, style: str = "educational", custom_prompt: Optional[str] = None
    ) -> str:
        """实际发给大纲模型的完整 prompt（含对用户自定义稿自动注入的口播容量硬约束）。"""
        if custom_prompt and str(custom_prompt).strip():
            return ensure_outline_prompt_includes_voiceover_policy(str(custom_prompt).strip())
        return self.build_outline_prompt(topic=topic, style=style)

    def resolve_full_script_prompt(
        self, outline: str, topic: str, custom_prompt: Optional[str] = None
    ) -> str:
        """实际发给脚本模型的完整 prompt（含对用户自定义稿自动注入的旁白/时长硬约束）。"""
        if custom_prompt and str(custom_prompt).strip():
            text = str(custom_prompt).strip().replace("{{OUTLINE}}", outline or "")
            return ensure_full_script_prompt_includes_voiceover_policy(text)
        return self.build_full_script_prompt(outline=outline, topic=topic)

    async def generate_outline(self, topic: str, style: str = "educational", custom_prompt: str = None) -> str:
        """
        Generate a video script outline based on topic

        Args:
            topic: The video topic/title
            style: The style of the video (educational, entertaining, news, etc.)

        Returns:
            Outline text
        """
        prompt = self.resolve_outline_prompt(topic, style, custom_prompt)

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
4. 主体至少拆成 4-6 个信息段，每段必须写明：目标、核心信息、证明素材、情绪基调、**预计时长（秒）**
5. **口播容量（大纲必须写清，供下游写完整脚本对齐）**：中文口播语速按约 **每秒 4～6 个汉字** 估算（信息密、语速略快可到约 6 字/秒；情绪段落可略慢但不得无故拖长静音）。  
   每一信息段在「预计时长」之外，必须再写一行 **「口播字数建议：约 A～B 字」**，其中 **A = 时长(秒) × 4** 向上取整，**B = 时长(秒) × 6** 向上取整。  
   例：本段 **20 秒** → 口播字数建议 **约 80～120 字**；**15 秒** → **约 60～90 字**；**3 秒** → **约 12～18 字**。  
   禁止只写时长却不给口播容量，否则下游无法写足旁白。
6. 明确每段建议画面类型（口播/B-roll/截图/实拍/动画）与转场方式
7. 单独列出“互动点设计”：评论引导、收藏引导、转发触发点
8. 单独列出“风险与合规提醒”：避免夸大、避免绝对化表述
9. 必须使用中文正文输出；除专业术语、品牌名、API 名称外，不要大段使用英文

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
- 口播字数建议：（必填，按 xx 秒 × 4～6 字/秒 写出约 A～B 字）
- 目标：
- 关键信息：
- 画面建议：
- 情绪与节奏：

...（继续到最后一段；每一段都必须含「口播字数建议」）

【互动与转化设计】
- 评论引导：
- 收藏引导：
- 转发引导：

【风险与合规提醒】
- ...
---
{SYS_MARK_OUTLINE_VOICEROVER}
本大纲须满足上文「口播字数建议」规则：A=⌈秒×4⌉、B=⌈秒×6⌉；中文约 4～6 字/秒。（本条为系统校验锚点，模型输出中请保留本标记所在段落）
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
        prompt = self.resolve_full_script_prompt(outline, topic, custom_prompt)

        full_script = await self.llm.generate(prompt, max_tokens=4096)
        if self._needs_chinese_rewrite(full_script):
            try:
                full_script = await self._rewrite_as_chinese(full_script, "视频脚本")
            except Exception:
                # Keep original if rewrite fails
                pass

        # 从正文解析「旁白/台词」等作为分段，供 TTS / LTX 口播对齐；解析失败再回退
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
        return f"""你是一位爆款短视频导演、编剧和后期统筹。请基于以下大纲，生成“可直接交给拍摄、TTS 口播与 AI 视频生成管线执行”的完整版脚本。

主题：{topic}

大纲：
{outline}

【旁白与字幕分工（必须严格遵守，违者视为不合格）】
1. 「旁白」= 口播正文：供配音/TTS、以及文生视频时的对白参考。必须是**完整、可逐字朗读**的一段话（可含 2-5 个短句），信息紧凑、有具体名词与动作，禁止口号式空话。
2. 「字幕」= **上屏花字/关键词**，仅供观众扫视，**禁止**写成旁白的缩略版或同义复述。每条字幕建议 **4-12 个汉字**（必要时可加单个英文缩写如 API），例如钩子词、数字、对比词、步骤序号；长镜可写 2 条短字幕用「｜」分隔，但不要拼成一整句旁白。
3. **旁白字数必须与该镜头「时长」严格匹配（硬性规则）**  
   中文口播按 **每秒约 4～6 个汉字**（同一段落内标点不计入「字数」也可，但信息密度要够）。记该镜头时长为 **T 秒**，则本镜 **旁白汉字总数** 建议落在 **⌈T×4⌉～⌈T×6⌉** 之间（⌈⌉ 表示向上取整）。  
   - 例：**T=20 秒** → 旁白约 **80～120 字**（绝不允许只有二十来字就结束）。  
   - 例：**T=15 秒** → 旁白约 **60～90 字**。  
   - 例：**T=3 秒** → 旁白约 **12～18 字**，一句完整钩子。  
   **自检（输出前在脑中过一遍）**：每个镜头旁白若 **少于 T×4 字**，视为不合格，必须扩写：加具体例子、步骤、对比、数据或一句过渡，直到听感能撑满 T 秒。
4. 「画面与动作」= 给摄影师与 **文生视频/分镜模型** 用的画面说明：必须写清 **场景环境、光线与色调、主体外观/界面关键区域、具体动作或 UI 变化、镜头运动节奏**；禁止只写“展示界面”“镜头推进”这类无法执行的概括句。

要求：
1. 总时长 90-150 秒，【详细执行脚本】部分中文正文不少于 1500 字，整体信息密度高于常规口播
2. 至少输出 12-16 个镜头，镜头之间有明确“起承转合”和节奏爬升
3. 每个镜头都必须包含以下字段（缺一不可），且旁白/字幕/画面三者**禁止同质化**：
   - 镜头编号与时长
   - 景别/机位/运镜（如推拉摇移跟、手持或稳定器）
   - 画面与动作（按上文「画面与动作」标准写细）
   - 旁白（按字数与时长匹配规则写足）
   - 字幕（仅关键词/花字，禁止复述旁白）
   - 音乐/音效（曲风、节奏点、卡点建议）
   - 剪辑提示（节奏、转场、是否叠加素材）
   - 导演提示
4. 开场前 3-8 秒必须有强钩子；中段至少 2 个情绪峰值；结尾必须有行动号召（评论/关注/私信/收藏）
5. 音频设计必须分层：人声、BGM、环境音、强调音效，标注出现时机与强弱
6. 若涉及数据/观点，在「画面与动作」或「剪辑提示」中写明可视化呈现（图表、关键词大字、对比画面）
7. 必须使用中文正文输出；除专业术语、品牌名、API 名称外，不要大段使用英文
8. 不要输出解释性前言，不要道歉，不要免责声明，直接给正文成片方案
9. 若你需要引用大纲，请以当前「大纲」字段为准（若用户自定义 Prompt 中包含 {{OUTLINE}}，系统会自动替换）

输出结构（严格遵守）：

【视频定位】
- 目标受众：
- 核心卖点：
- 情绪曲线：
- 对标账号风格关键词：

【详细执行脚本】
（逐镜头输出，至少 12-16 个镜头）
镜头1：
- 时长：（秒，需与旁白密度一致）
- 景别/机位：
- 画面与动作：（细化到可供拍摄/生成的画面要素）
- 旁白：（口播全文，字数与时长匹配）
- 字幕：（仅上屏关键词/花字，勿重复旁白语义）
- 音乐/音效：
- 剪辑提示：
- 导演提示：

...（持续到最后一个镜头）

【后期与剪辑建议】
- 转场节奏建议：
- 字幕排版建议：（强调花字层级、与旁白不同步时的设计）
- BGM与音效混音建议：
- 封面标题与前3秒文案建议（至少3套）：

请直接输出脚本正文，不要输出“说明、解释、免责声明”。
---
{SYS_MARK_FULL_VOICEROVER}
须满足上文「旁白与镜头时长」匹配规则：每镜旁白汉字数 ⌈T×4⌉～⌈T×6⌉（T 为秒）。（本条为系统校验锚点，模型输出中请保留本标记所在段落）
"""

    def _parse_narration_lines_from_script(self, full_script: str) -> List[str]:
        """兼容入口：与模块级 `extract_narration_lines_from_full_script` 一致。"""
        return extract_narration_lines_from_full_script(full_script)

    def _create_segments(self, full_script: str) -> List[ScriptSegment]:
        """
        由完整脚本生成 segments：优先按「旁白/台词」拆条，否则按段落回退。
        """
        import uuid

        narrations = self._parse_narration_lines_from_script(full_script)
        if narrations:
            n = len(narrations)
            avg = max(4.0, min(15.0, 120.0 / max(1, n)))
            return [
                ScriptSegment(
                    id=str(uuid.uuid4()),
                    text=t,
                    duration=float(avg),
                    emotion="neutral",
                    material_ids=[],
                )
                for t in narrations
            ]

        # 回退：按空行分段，再按单行长句
        parts = [p.strip() for p in str(full_script or "").split("\n\n") if p.strip()]
        if not parts:
            parts = [p.strip() for p in str(full_script or "").split("\n") if len(p.strip()) > 24]
        if not parts:
            return [
                ScriptSegment(
                    id=str(uuid.uuid4()),
                    text="（未能从脚本中解析出口播句，请检查是否包含「旁白：」字段）",
                    duration=6.0,
                    emotion="neutral",
                    material_ids=[],
                )
            ]

        preview_parts = parts[:20]
        avg = max(5.0, min(12.0, 120.0 / max(1, len(preview_parts))))
        return [
            ScriptSegment(
                id=str(uuid.uuid4()),
                text=text,
                duration=float(avg),
                emotion="neutral",
                material_ids=[],
            )
            for text in preview_parts
        ]


def _script_execution_section(full_script: str) -> str:
    """只保留「详细执行脚本」到「后期建议」之间的正文，减少误匹配元数据区。"""
    text = str(full_script or "")
    if not text.strip():
        return ""
    m0 = re.search(r"【详细执行脚本】\s*", text)
    if m0:
        text = text[m0.end() :]
    m1 = re.search(r"【后期与剪辑建议】", text)
    if m1:
        text = text[: m1.start()]
    return text.strip()


# 旁白字段之后到下一分镜字段或下一镜头块为止（与脚本模板字段名一致）
_STOP_AFTER_NARRATION_IN_SHOT = (
    r"(?=\n\s*[-–•*、\d\.\)\(]*\s*(?:字幕|景别|机位|画面与动作|画面|音乐|音效|剪辑|导演|时长)\s*[：:]"
    r"|\n\s*镜头\s*\d+\s*[：:]|\Z)"
)


def _extract_narration_by_shot_blocks(exec_text: str) -> List[str]:
    """
    按「镜头N：」块解析，每块取「旁白：」到下一字段之间的内容。
    与默认脚本模板（build_full_script_prompt）对齐。
    """
    if not (exec_text or "").strip():
        return []
    lines_out: List[str] = []
    parts = re.split(r"(?=^镜头\s*\d+\s*[：:])", exec_text, flags=re.MULTILINE)
    narr_pat = re.compile(
        r"旁白\s*[：:]\s*([\s\S]+?)" + _STOP_AFTER_NARRATION_IN_SHOT,
        re.IGNORECASE,
    )
    for part in parts:
        p = part.strip()
        if not re.match(r"镜头\s*\d+\s*[：:]", p, re.IGNORECASE):
            continue
        m = narr_pat.search(p)
        if not m:
            continue
        block = re.sub(r"\s+", " ", m.group(1).strip())
        block = block.strip('"').strip("“”").strip()
        if len(block) > 2 and "placeholder" not in block.lower():
            lines_out.append(block)
    return lines_out


def extract_narration_lines_from_full_script(full_script: str) -> List[str]:
    """
    从完整脚本提取每镜口播/旁白正文（顺序与镜头一致），供视觉规划、TTS 分段等使用。
    优先在「详细执行脚本」区内匹配，跳过【视频定位】等元数据。
    """
    text = str(full_script or "")
    if not text.strip():
        return []

    exec_text = _script_execution_section(full_script) or text
    lines_out: List[str] = []

    # 单行旁白/台词（同一行写完）
    line_pat = re.compile(
        r"(?:^|\n)\s*[-•\d\.\)\(、]*\s*(?:旁白|台词|口播)\s*[：:]\s*([^\n]+)",
        re.MULTILINE,
    )
    for m in line_pat.finditer(exec_text):
        chunk = m.group(1).strip().strip('"').strip("“”").strip()
        if len(chunk) > 1 and not chunk.startswith("Segment ") and "placeholder" not in chunk.lower():
            lines_out.append(chunk)

    if lines_out:
        return lines_out

    # 多行旁白块
    block_pat = re.compile(
        r"(?:^|\n)\s*[-•\d\.\)\(、]*\s*(?:旁白|台词|口播)\s*[：:]\s*\n([\s\S]*?)(?=\n\s*(?:[-•\d\.\)\(、]*\s*(?:景别|机位|画面|字幕|音乐|剪辑|导演|镜头)|\n\s*镜头|\Z))",
        re.MULTILINE,
    )
    for m in block_pat.finditer(exec_text):
        block = m.group(1).strip()
        block = re.sub(r"\s+", " ", block).strip()
        if len(block) > 8:
            lines_out.append(block)

    if lines_out:
        return lines_out

    # 按「镜头N」块抓取旁白（模板最常见）
    by_shots = _extract_narration_by_shot_blocks(exec_text)
    if by_shots:
        return by_shots

    # 全文再试一次按镜头块（有的模型未写【详细执行脚本】标题）
    return _extract_narration_by_shot_blocks(text)
