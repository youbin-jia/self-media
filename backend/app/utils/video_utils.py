# backend/app/utils/video_utils.py
"""Video Processing Utilities with Transitions and Effects"""
from typing import List, Dict, Any, Optional
from moviepy.editor import VideoFileClip, CompositeVideoClip, ColorClip
from moviepy.video.fx.fadein import fadein
from moviepy.video.fx.fadeout import fadeout
from moviepy.video.fx.resize import resize
import numpy as np


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
        """
        if transition_type == "fade":
            # 淡入淡出
            clip1 = fadeout(clip1, duration)
            clip2 = fadein(clip2, duration)
            return CompositeVideoClip([clip1, clip2.set_start(clip1.duration - duration)])

        elif transition_type == "crossfade":
            # 交叉淡入淡出
            clip1 = clip1.fadeout(duration)
            clip2 = clip2.fadein(duration)
            return CompositeVideoClip([
                clip1,
                clip2.set_start(clip1.duration - duration).crossfadein(duration)
            ])

        elif transition_type == "wipe":
            # 擦除转场
            def make_wipe_frame(t):
                """生成擦除帧"""
                progress = t / duration
                w = clip1.w

                def get_frame(get_frame_func):
                    def frame(t):
                        frame1 = clip1.get_frame(t)
                        frame2 = clip2.get_frame(t)
                        x = int(w * progress)
                        return np.hstack([frame1[:, :x], frame2[:, x:]])
                    return frame
                return get_frame

            return CompositeVideoClip([clip1, clip2], duration=duration)

        else:
            # 无转场
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
        """
        def make_frame(t):
            """动态缩放帧"""
            progress = t / clip.duration
            zoom = zoom_start + (zoom_end - zoom_start) * progress

            frame = clip.get_frame(t)
            h, w = frame.shape[:2]

            # 计算缩放后的尺寸
            new_h, new_w = int(h / zoom), int(w / zoom)

            # 根据方向确定裁剪位置
            if direction == "center":
                y = (h - new_h) // 2
                x = (w - new_w) // 2
            elif direction == "left":
                y = (h - new_h) // 2
                x = 0
            elif direction == "right":
                y = (h - new_h) // 2
                x = w - new_w
            else:
                y, x = 0, 0

            # 裁剪并缩放
            cropped = frame[y:y+new_h, x:x+new_w]
            from PIL import Image
            img = Image.fromarray(cropped)
            img = img.resize((w, h), Image.LANCZOS)
            return np.array(img)

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
            if preset == "cinematic":
                # 电影感：降低饱和度，增加对比度
                from PIL import Image
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
        from moviepy.video.VideoClip import TextClip

        txt = TextClip(
            text,
            fontsize=fontsize,
            color=color,
            font="Arial-Unicode-MS"
        )

        txt = txt.set_position(position).set_duration(duration or clip.duration)
        return CompositeVideoClip([clip, txt])
