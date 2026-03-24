"""Visual planning service for storyboard generation."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from app.config import settings
from app.services.llm import llm_manager
from app.services.script_generator import extract_narration_lines_from_full_script

# 口播边界：尽量在标点处截断
_PUNCT_BREAK = frozenset("，。！？、；：;,.!?）】\"'（【")


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
                    self._assign_narrations_from_full_script(
                        parsed["shots"], full_script
                    )
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
        self._assign_narrations_from_full_script(fallback["shots"], full_script)
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
4. **口播/旁白**：`narration` 可填 `""`（空字符串）。**服务端会按「完整脚本」与各镜 `duration_sec` 自动切分口播并对齐语速**，你无需编造口播正文。
5. **镜头时长**：请合理设置 `duration_sec`，使全片总时长与脚本体量匹配；中文口播约 **每秒 4～6 字**，系统会按每镜时长把脚本切成可念完的片段。
6. **字幕与口播分工**：on_screen_text 仅为 **4～12 字** 级上屏花字/关键词；**禁止**写拍摄说明、占位符（如「【视频定位】」单条）、或元叙事句（如「这一段我们结合画面…」）。
7. 需要尽量具体，可直接给剪辑、拍摄与 TTS/文生视频执行
8. 风险点要提示（夸大/违规表述/素材版权）

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
      "narration": "",
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
            narr = (
                str(shot.get("narration") or shot.get("voiceover") or shot.get("narration_script") or "")
                .strip()
            )
            shots.append({
                "shot_no": int(shot.get("shot_no", idx) or idx),
                "duration_sec": round(max(1.0, duration), 1),
                "objective": str(shot.get("objective", "")).strip(),
                "narration": narr,
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

    _META_LINE_SKIP = (
        re.compile(r"^[-*•·\d\.\)\(、]*\s*目标受众\s*[：:]"),
        re.compile(r"^[-*•·\d\.\)\(、]*\s*核心卖点\s*[：:]"),
        re.compile(r"^[-*•·\d\.\)\(、]*\s*情绪曲线\s*[：:]"),
        re.compile(r"^[-*•·\d\.\)\(、]*\s*对标账号"),
        re.compile(r"^[-*•·\d\.\)\(、]*\s*受众画像\s*[：:]"),
        re.compile(r"^[-*•·\d\.\)\(、]*\s*核心痛点\s*[：:]"),
        re.compile(r"^[-*•·\d\.\)\(、]*\s*内容承诺\s*[：:]"),
        re.compile(r"^【视频定位】\s*$"),
        re.compile(r"^【后期与剪辑建议】"),
        re.compile(r"^【详细执行脚本】\s*$"),
    )

    @classmethod
    def _flatten_script_sanitized_for_voiceover(cls, full_script: str) -> str:
        """
        无「旁白：」可解析时的回退：尽量只用执行脚本区，并跳过明显元数据行。
        """
        t = str(full_script or "")
        start_m = re.search(r"【详细执行脚本】\s*", t)
        if start_m:
            t = t[start_m.end() :]
        end_m = re.search(r"【后期与剪辑建议】", t)
        if end_m:
            t = t[: end_m.start()]
        parts: List[str] = []
        for raw in t.splitlines():
            s = raw.strip()
            if not s:
                continue
            if any(p.search(s) for p in cls._META_LINE_SKIP):
                continue
            if re.fullmatch(r"【[^】]{1,20}】", s):
                continue
            # 去掉字段标签行，只保留值（避免「旁白：」整行进时间轴时重复标签）
            s = re.sub(r"^[-*•·\d\.\)\(、]*\s*(?:旁白|台词|口播)\s*[：:]\s*", "", s)
            s = re.sub(r"^[-*•·]\s*", "", s)
            s = re.sub(r"^\d+[\.)]\s*", "", s)
            if not s.strip():
                continue
            parts.append(s.strip())
        text = " ".join(parts)
        text = re.sub(r"\s+", " ", text).strip()
        # 去掉残留的 【xxx】 标签碎片
        text = re.sub(r"【[^】]{1,24}】", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _flatten_script_for_narration(full_script: str) -> str:
        """兼容旧名：优先走旁白提取，否则净化后的全文展平。"""
        lines = extract_narration_lines_from_full_script(full_script)
        if lines:
            return re.sub(r"\s+", " ", " ".join(lines)).strip()
        return VisualPlanner._flatten_script_sanitized_for_voiceover(full_script)

    @staticmethod
    def _clean_voiceover_fragment(text: str) -> str:
        """去掉口播里不应念出的结构标签与重复空格。"""
        s = re.sub(r"\s+", " ", str(text or "").strip())
        s = re.sub(r"【[^】]{1,32}】", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    @staticmethod
    def _shot_line_boundaries(num_lines: int, num_shots: int, durs: List[float]) -> List[int]:
        """把 K 条旁白行按时长权重切成 M+1 个索引边界（含 0 与 K）。"""
        if num_shots <= 0:
            return [0]
        K, M = num_lines, num_shots
        if K <= 0:
            return [0] * (M + 1)
        total_d = sum(durs) or 1.0
        idxs = [0]
        for i in range(M - 1):
            acc = sum(durs[: i + 1]) / total_d
            idxs.append(min(K, int(round(acc * K))))
        idxs.append(K)
        for i in range(1, len(idxs)):
            if idxs[i] < idxs[i - 1]:
                idxs[i] = idxs[i - 1]
        for i in range(1, M):
            if idxs[i] <= idxs[i - 1] and idxs[i] < K:
                idxs[i] = idxs[i - 1] + 1
        idxs[-1] = K
        return idxs

    @staticmethod
    def _snap_cut_backward(text: str, cut: int, left_min: int) -> int:
        """把切分点向左挪到最近的句读，避免半句拦腰断开。"""
        cut = max(left_min, min(cut, len(text)))
        lo = max(left_min, cut - 36)
        i = cut
        while i > lo:
            if i > 0 and text[i - 1] in _PUNCT_BREAK:
                return i
            i -= 1
        return cut

    @staticmethod
    def _truncate_spoken_at_budget(chunk: str, hi: int) -> str:
        """超过单镜上限时在标点处截断。"""
        s = chunk.strip()
        if len(s) <= hi:
            return s
        lo = max(8, hi - 48)
        i = hi
        while i > lo:
            if i < len(s) and s[i] in _PUNCT_BREAK:
                return s[: i + 1].strip()
            if i > 0 and s[i - 1] in _PUNCT_BREAK:
                return s[:i].strip()
            i -= 1
        return s[:hi].strip()

    @classmethod
    def _split_at_spoken_budget(cls, combined: str, hi: int) -> tuple[str, str]:
        """拆成 (本镜口播, 溢出到下镜的剩余文案)。kept 长度不超过 hi（尽量在标点截断）。"""
        s = re.sub(r"\s+", " ", str(combined or "").strip())
        if not s:
            return "", ""
        if len(s) <= hi:
            return s, ""
        kept = cls._truncate_spoken_at_budget(s, hi)
        if not kept:
            return s[:hi].strip(), s[hi:].strip()
        if s.startswith(kept):
            rest = s[len(kept) :].strip()
        else:
            rest = s[len(kept) :].strip() if len(kept) < len(s) else ""
        return kept, rest

    @staticmethod
    def _polish_spoken_chunk(chunk: str) -> str:
        """去掉重复半段、连续重复短句。"""
        s = re.sub(r"\s+", " ", str(chunk or "").strip())
        if not s:
            return ""
        half = len(s) // 2
        if half > 12 and s[:half].strip() == s[half:].strip():
            return s[:half].strip()
        parts = re.split(r"(?<=[。！？!?])", s)
        out: List[str] = []
        for p in parts:
            t = p.strip()
            if not t:
                continue
            if out and t == out[-1]:
                continue
            out.append(t)
        return "".join(out).strip() or s

    @classmethod
    def _assign_narrations_from_full_script(
        cls, shots: List[Dict[str, Any]], full_script: str
    ) -> None:
        """
        口播优先来自脚本里每镜「旁白：」正文（extract_narration_lines_from_full_script）；
        再按各镜 duration_sec 做字数与时长对齐（溢出顺延下一镜）。
        若解析不到旁白，则用净化后的执行脚本区全文按比例切分。
        """
        if not shots:
            return
        raw_lines = extract_narration_lines_from_full_script(full_script)
        lines = [cls._clean_voiceover_fragment(x) for x in raw_lines if cls._clean_voiceover_fragment(x)]

        n = len(shots)
        durs = [max(1.0, float(s.get("duration_sec", 6) or 6)) for s in shots]

        if lines:
            K = len(lines)
            if K == n:
                bodies = list(lines)
            elif K > n:
                bounds = cls._shot_line_boundaries(K, n, durs)
                bodies = []
                for i in range(n):
                    chunk = lines[bounds[i] : bounds[i + 1]]
                    bodies.append(" ".join(chunk).strip())
            else:
                # 旁白条少于镜头：合并后按时长比例切开，避免多镜空口播
                joined = re.sub(r"\s+", " ", " ".join(lines)).strip()
                total_d = sum(durs) or 1.0
                L = len(joined)
                cuts = [0]
                acc = 0.0
                for d in durs:
                    acc += d
                    cuts.append(min(L, int(round(L * acc / total_d))))
                cuts[-1] = L
                for i in range(1, n):
                    cuts[i] = cls._snap_cut_backward(joined, cuts[i], cuts[i - 1] + 1)
                    if cuts[i] <= cuts[i - 1]:
                        cuts[i] = min(L, cuts[i - 1] + 1)
                bodies = [joined[cuts[i] : cuts[i + 1]].strip() for i in range(n)]
        else:
            body = cls._flatten_script_sanitized_for_voiceover(full_script)
            if not body:
                return
            total_d = sum(durs) or 1.0
            L = len(body)
            cuts = [0]
            acc = 0.0
            for d in durs:
                acc += d
                cuts.append(min(L, int(round(L * acc / total_d))))
            cuts[-1] = L
            for i in range(1, n):
                cuts[i] = cls._snap_cut_backward(body, cuts[i], cuts[i - 1] + 1)
                if cuts[i] <= cuts[i - 1]:
                    cuts[i] = min(L, cuts[i - 1] + 1)
            bodies = [body[cuts[i] : cuts[i + 1]].strip() for i in range(n)]

        buffer = ""
        for i in range(n):
            raw = bodies[i] if i < len(bodies) else ""
            if buffer and raw:
                piece = f"{buffer} {raw}".strip()
            else:
                piece = (buffer + raw).strip()
            hi = max(12, int(durs[i] * 6.8) + 4)
            kept, buffer = cls._split_at_spoken_budget(piece, hi)
            shots[i]["narration"] = cls._polish_spoken_chunk(kept)

        if buffer:
            shots[-1]["narration"] = cls._polish_spoken_chunk(
                f"{shots[-1].get('narration', '')} {buffer}".strip()
            )

    def _fallback_plan(self, *, topic: str, outline: str, full_script: str) -> Dict[str, Any]:
        paragraphs = [p.strip() for p in str(full_script or "").split("\n") if p.strip()]
        if not paragraphs:
            paragraphs = [f"围绕主题《{topic}》的引入", "核心观点展开", "总结与行动引导"]
        chosen = paragraphs[:12]
        shots = []
        for idx, p in enumerate(chosen, start=1):
            dur = 7.0 if idx == 1 else 6.0
            shots.append({
                "shot_no": idx,
                "duration_sec": dur,
                "objective": "建立信息推进" if idx > 1 else "开场钩子吸引注意力",
                "narration": "",
                "visual_description": p[:120],
                "camera_language": "中近景 + 轻推镜 / 关键句切 B-roll",
                "material_suggestion": ["口播实拍", "相关素材插入"],
                "on_screen_text": (p[:10] + "…") if len(p) > 10 else p[:12],
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
