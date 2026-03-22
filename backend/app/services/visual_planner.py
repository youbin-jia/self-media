"""Visual planning service for storyboard generation."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.llm import llm_manager


class VisualPlanner:
    """Generate visual/storyboard plans from script content."""

    def __init__(self, provider_name: Optional[str] = None):
        self.provider_name = provider_name or settings.DEFAULT_LLM_PROVIDER

    async def generate_plan(
        self,
        *,
        topic: str,
        outline: str,
        full_script: str,
        segments: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Generate structured visual planning data."""
        provider = None
        try:
            provider = llm_manager.get_provider(self.provider_name)
        except Exception:
            provider = None

        prompt = self._build_prompt(
            topic=topic,
            outline=outline,
            full_script=full_script,
            segments=segments or []
        )
        if provider:
            try:
                content = await provider.generate(prompt, max_tokens=2200, temperature=0.35)
                parsed = self._parse_plan_json(content)
                if parsed:
                    parsed["mode"] = "real_visual_plan"
                    parsed["llm_input"] = {
                        "provider": provider.provider_name,
                        "model": getattr(provider, "default_model", None) or (provider.available_models[0] if provider.available_models else None),
                        "prompt": prompt
                    }
                    parsed.setdefault("message", "视觉规划已完成（大模型）")
                    return parsed
            except Exception:
                pass

        fallback = self._fallback_plan(topic=topic, outline=outline, full_script=full_script)
        fallback["mode"] = "fallback_visual_plan"
        fallback["llm_input"] = {
            "provider": self.provider_name,
            "model": None,
            "prompt": prompt
        }
        fallback["message"] = "视觉规划已完成（规则回退）"
        return fallback

    def _build_prompt(
        self,
        *,
        topic: str,
        outline: str,
        full_script: str,
        segments: List[Dict[str, Any]]
    ) -> str:
        segment_info = json.dumps(segments[:20], ensure_ascii=False)
        return f"""你是一名短视频导演与视觉统筹。请基于脚本产出“可执行的视觉规划”。

主题：{topic}

大纲：
{outline}

完整脚本：
{full_script}

已有片段（如有）：
{segment_info}

要求：
1. 以抖音/视频号爆款节奏组织镜头，开场 3-8 秒必须强钩子
2. 给出 10-16 个镜头，覆盖起承转合和结尾行动引导
3. 每个镜头必须包含：时长、画面内容、机位/运镜、素材建议、字幕要点、转场、音乐音效
4. 需要尽量具体，可直接给剪辑与拍摄执行
5. 风险点要提示（夸大/违规表述/素材版权）

请严格返回 JSON（不要 Markdown，不要解释）：
{{
  "summary": "一句话视觉策略",
  "style_direction": "风格方向",
  "target_duration_sec": 90,
  "shots": [
    {{
      "shot_no": 1,
      "duration_sec": 6,
      "objective": "该镜头目标",
      "visual_description": "画面与动作",
      "camera_language": "景别/机位/运镜",
      "material_suggestion": ["素材建议1", "素材建议2"],
      "on_screen_text": "字幕关键句",
      "transition": "转场方式",
      "music_sfx": "音乐和音效",
      "risk_note": "风险提醒（可空）"
    }}
  ]
}}
"""

    def _parse_plan_json(self, content: str) -> Optional[Dict[str, Any]]:
        if not content:
            return None
        text = content.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
        except Exception:
            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                return None
            try:
                data = json.loads(m.group(0))
            except Exception:
                return None

        shots_raw = data.get("shots")
        if not isinstance(shots_raw, list) or not shots_raw:
            return None

        shots: List[Dict[str, Any]] = []
        for idx, shot in enumerate(shots_raw[:20], start=1):
            if not isinstance(shot, dict):
                continue
            duration = float(shot.get("duration_sec", 6) or 6)
            materials = shot.get("material_suggestion", [])
            if not isinstance(materials, list):
                materials = [str(materials)]
            shots.append({
                "shot_no": int(shot.get("shot_no", idx) or idx),
                "duration_sec": round(max(1.0, duration), 1),
                "objective": str(shot.get("objective", "")).strip(),
                "visual_description": str(shot.get("visual_description", "")).strip(),
                "camera_language": str(shot.get("camera_language", "")).strip(),
                "material_suggestion": [str(x) for x in materials if str(x).strip()][:6],
                "on_screen_text": str(shot.get("on_screen_text", "")).strip(),
                "transition": str(shot.get("transition", "")).strip(),
                "music_sfx": str(shot.get("music_sfx", "")).strip(),
                "risk_note": str(shot.get("risk_note", "")).strip()
            })

        if not shots:
            return None

        target_duration = data.get("target_duration_sec")
        try:
            target_duration_val = float(target_duration)
        except Exception:
            target_duration_val = sum(item["duration_sec"] for item in shots)

        return {
            "summary": str(data.get("summary", "")).strip(),
            "style_direction": str(data.get("style_direction", "")).strip(),
            "target_duration_sec": round(max(10.0, target_duration_val), 1),
            "shots": shots
        }

    def _fallback_plan(self, *, topic: str, outline: str, full_script: str) -> Dict[str, Any]:
        paragraphs = [p.strip() for p in str(full_script or "").split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [f"围绕主题《{topic}》的引入", "核心观点展开", "总结与行动引导"]
        chosen = paragraphs[:12]
        shots = []
        for idx, p in enumerate(chosen, start=1):
            shots.append({
                "shot_no": idx,
                "duration_sec": 7.0 if idx == 1 else 6.0,
                "objective": "建立信息推进" if idx > 1 else "开场钩子吸引注意力",
                "visual_description": p[:120],
                "camera_language": "中近景 + 轻推镜 / 关键句切 B-roll",
                "material_suggestion": ["口播实拍", "相关素材插入"],
                "on_screen_text": p[:36],
                "transition": "节奏切换",
                "music_sfx": "轻快节奏BGM + 关键字音效",
                "risk_note": ""
            })
        return {
            "summary": f"围绕《{topic}》采用信息递进的口播+B-roll视觉方案",
            "style_direction": "信息密度型 / 节奏推进",
            "target_duration_sec": round(sum(s["duration_sec"] for s in shots), 1),
            "shots": shots,
            "outline_reference": outline[:500]
        }
