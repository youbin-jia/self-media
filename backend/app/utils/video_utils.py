# backend/app/utils/video_utils.py
"""Video Processing Utilities with Transitions and Effects"""
import logging
from typing import List, Dict, Any, Optional
from moviepy.editor import VideoFileClip, CompositeVideoClip, ColorClip
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from moviepy.video.fx.resize import resize
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class VideoProcessor:
    """视频处理工具集"""

    @staticmethod
    def add_transition(
        clip1: VideoFileClip,
        clip2: VideoFileClip,
        transition_type: str = "fade",
        duration: float = 1.0
    ) -> CompositeVideoClip:
        """
        添加转场效果
        Args:
            clip1: 第一个视频片段
            clip2: 第二个视频片段
            transition_type: 转场类型 (fade, crossfade, wipe)
            duration: 转场时长(秒)
        Returns:
            合成后的视频
        Raises:
            ValueError: If duration is invalid or clips are invalid
        """
        # Validate parameters
        if duration <= 0:
            raise ValueError(f"Transition duration must be positive, got {duration}")

        if clip1 is None or clip2 is None:
            raise ValueError("Both clips must be provided for transition")

        if clip1.duration is None or clip2.duration is None:
            raise ValueError("Both clips must have valid duration")

        if duration >= clip1.duration:
            logger.warning(f"Transition duration {duration}s >= clip1 duration {clip1.duration}s, adjusting")
            duration = min(duration, clip1.duration * 0.5, clip2.duration * 0.5)

        try:
            if transition_type == "fade":
                # 淡入淡出
                clip1_faded = fadeout(clip1, duration)
                clip2_faded = fadein(clip2, duration)
                return CompositeVideoClip([clip1_faded, clip2_faded.set_start(clip1.duration - duration)])

            elif transition_type == "crossfade":
                # 交叉淡入淡出
                clip1_faded = fadeout(clip1, duration)
                clip2_faded = fadein(clip2, duration)
                # Use crossfade by setting opacity
                clip2_crossfaded = clip2_faded.set_start(clip1.duration - duration).set_opacity(lambda t: t / duration)
                return CompositeVideoClip([clip1_faded, clip2_crossfaded])

            elif transition_type == "wipe":
                # 擦除转场 - implement proper wipe effect
                def make_wipe_frame(get_frame1, get_frame2, w, d):
                    def frame(t):
                        progress = t / d
                        frame1 = get_frame1(t)
                        frame2 = get_frame2(t)
                        x = int(w * min(progress, 1.0))
                        # Ensure we don't exceed frame dimensions
                        x = min(x, w - 1)
                        return np.hstack([frame1[:, :x], frame2[:, x:]])
                    return frame

                # Create a custom video clip with the wipe effect
                from moviepy.video.VideoClip import VideoClip
                wipe_duration = duration
                wipe_clip = VideoClip(
                    lambda t: make_wipe_frame(
                        clip1.get_frame,
                        clip2.get_frame,
                        clip1.w,
                        wipe_duration
                    )(t),
                    duration=wipe_duration
                )
                return wipe_clip

            else:
                # 无转场 - simple concatenation
                return CompositeVideoClip([clip1, clip2.set_start(clip1.duration)])

        except Exception as e:
            logger.error(f"Failed to create {transition_type} transition: {e}")
            # Fallback to simple concatenation
            return CompositeVideoClip([clip1, clip2.set_start(clip1.duration)])

    @staticmethod
    def add_ken_burns_effect(
        clip: VideoFileClip,
        zoom_start: float = 1.0,
        zoom_end: float = 1.2,
        direction: str = "center"
    ) -> VideoFileClip:
        """
        添加Ken Burns效果（缓慢缩放）
        Args:
            clip: 视频片段
            zoom_start: 起始缩放比例
            zoom_end: 结束缩放比例
            direction: 缩放方向 (center, left, right)
        Returns:
            添加效果后的视频
        Raises:
            ValueError: If parameters are invalid
        """
        # Validate parameters
        if zoom_start <= 0 or zoom_end <= 0:
            raise ValueError(f"Zoom values must be positive, got start={zoom_start}, end={zoom_end}")

        if clip is None or clip.duration is None or clip.duration <= 0:
            raise ValueError("Clip must have valid positive duration")

        def make_frame(t):
            """动态缩放帧"""
            try:
                # Avoid division by zero
                if clip.duration == 0:
                    progress = 0
                else:
                    progress = t / clip.duration

                zoom = zoom_start + (zoom_end - zoom_start) * progress

                # Prevent zero or negative zoom
                if zoom <= 0:
                    zoom = 1.0

                frame = clip.get_frame(t)
                h, w = frame.shape[:2]

                # 计算缩放后的尺寸
                new_h = max(1, int(h / zoom))
                new_w = max(1, int(w / zoom))

                # 根据方向确定裁剪位置
                if direction == "center":
                    y = max(0, (h - new_h) // 2)
                    x = max(0, (w - new_w) // 2)
                elif direction == "left":
                    y = max(0, (h - new_h) // 2)
                    x = 0
                elif direction == "right":
                    y = max(0, (h - new_h) // 2)
                    x = max(0, w - new_w)
                else:
                    logger.warning(f"Unknown direction '{direction}', using center")
                    y = max(0, (h - new_h) // 2)
                    x = max(0, (w - new_w) // 2)

                # Ensure crop region is within bounds
                y = min(y, h - new_h)
                x = min(x, w - new_w)
                y = max(0, y)
                x = max(0, x)

                # 裁剪并缩放
                cropped = frame[y:y+new_h, x:x+new_w]

                # Validate cropped frame
                if cropped.size == 0:
                    logger.warning("Empty crop region, returning original frame")
                    return frame

                img = Image.fromarray(cropped)
                img = img.resize((w, h), Image.LANCZOS)
                return np.array(img)

            except Exception as e:
                logger.error(f"Error in Ken Burns effect at t={t}: {e}")
                # Return original frame on error
                return clip.get_frame(t)

        return clip.fl(lambda gf, t: make_frame(t), apply_to=[])

    @staticmethod
    def add_color_grading(
        clip: VideoFileClip,
        preset: str = "cinematic"
    ) -> VideoFileClip:
        """
        添加调色滤镜
        Args:
            clip: 视频片段
            preset: 预设 (cinematic, warm, cool, vintage)
        Returns:
            调色后的视频
        """
        def apply_color_grading(frame):
            """应用调色"""
            try:
                if preset == "cinematic":
                    # 电影感：降低饱和度，增加对比度
                    img = Image.fromarray(frame)
                    img = img.point(lambda p: p * 1.1 if p > 128 else p * 0.9)
                    return np.array(img)

                elif preset == "warm":
                    # 暖色调：增加红色和黄色
                    frame = frame.astype(np.float32)
                    frame[:, :, 0] = frame[:, :, 0] * 1.1  # R
                    frame[:, :, 1] = frame[:, :, 1] * 1.05  # G
                    frame = np.clip(frame, 0, 255).astype(np.uint8)
                    return frame

                elif preset == "cool":
                    # 冷色调：增加蓝色
                    frame = frame.astype(np.float32)
                    frame[:, :, 2] = frame[:, :, 2] * 1.15  # B
                    frame = np.clip(frame, 0, 255).astype(np.uint8)
                    return frame

                else:
                    # Unknown preset, return original
                    logger.warning(f"Unknown color grading preset '{preset}', no effect applied")
                    return frame

            except Exception as e:
                logger.error(f"Error applying color grading preset '{preset}': {e}")
                return frame

        return clip.fl_image(apply_color_grading)

    @staticmethod
    def _adapt_aspect_ratio(
        clip: VideoFileClip,
        target_width: int,
        target_height: int
    ) -> VideoFileClip:
        """
        适配视频宽高比
        Args:
            clip: 视频片段
            target_width: 目标宽度
            target_height: 目标高度
        Returns:
            适配后的视频
        """
        current_ratio = clip.w / clip.h
        target_ratio = target_width / target_height

        if abs(current_ratio - target_ratio) < 0.01:
            # 宽高比基本相同，直接缩放
            return clip.resize((target_width, target_height))

        # 需要裁剪
        if current_ratio > target_ratio:
            # 视频更宽，需要裁剪两侧
            new_width = int(clip.h * target_ratio)
            x_center = (clip.w - new_width) // 2
            clip = clip.crop(
                x1=x_center,
                width=new_width,
                y1=0,
                height=clip.h
            )
        else:
            # 视频更高，需要裁剪上下
            new_height = int(clip.w / target_ratio)
            y_center = (clip.h - new_height) // 2
            clip = clip.crop(
                x1=0,
                width=clip.w,
                y1=y_center,
                height=new_height
            )

        return clip.resize((target_width, target_height))

    @staticmethod
    def add_text_overlay(
        clip: VideoFileClip,
        text: str,
        position: tuple = ("center", "bottom"),
        fontsize: int = 50,
        color: str = "white",
        duration: Optional[float] = None
    ) -> CompositeVideoClip:
        """
        添加文字叠加
        Args:
            clip: 视频片段
            text: 文字内容
            position: 位置
            fontsize: 字体大小
            color: 颜色
            duration: 显示时长
        Returns:
            添加文字后的视频
        """
        try:
            from moviepy.video.VideoClip import TextClip

            # Validate parameters
            if not text:
                logger.warning("Empty text provided for overlay")
                return CompositeVideoClip([clip])

            if fontsize <= 0:
                raise ValueError(f"Fontsize must be positive, got {fontsize}")

            txt = TextClip(
                text,
                fontsize=fontsize,
                color=color,
                font="Arial-Unicode-MS"
            )

            txt = txt.set_position(position).set_duration(duration or clip.duration)
            return CompositeVideoClip([clip, txt])

        except Exception as e:
            logger.error(f"Failed to add text overlay: {e}")
            # Return original clip on error
            return CompositeVideoClip([clip])
