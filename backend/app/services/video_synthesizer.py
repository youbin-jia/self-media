# backend/app/services/video_synthesizer.py
"""Video Synthesis Service with MoviePy"""
import os
import logging
from typing import List, Dict, Any, Optional, Callable, Union
from pathlib import Path
from moviepy.editor import ImageClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, AudioFileClip, VideoClip

from app.config import settings
from app.utils.video_utils import VideoProcessor
from app.services.effects.data_visualization import DataVisualizationEffect
from app.services.effects.dynamic_subtitle import DynamicSubtitleEffect

logger = logging.getLogger(__name__)


class VideoSynthesizer:
    """Service for synthesizing videos from materials (Phase 1: Simplified)"""

    # Platform configurations for multi-platform export
    PLATFORM_CONFIGS = {
        "horizontal": {
            "resolution": (1920, 1080),
            "fps": 30,
            "description": "横屏 (16:9) - YouTube, B站"
        },
        "vertical": {
            "resolution": (1080, 1920),
            "fps": 30,
            "description": "竖屏 (9:16) - 抖音, 快手"
        },
        "square": {
            "resolution": (1080, 1080),
            "fps": 30,
            "description": "方形 (1:1) - Instagram"
        }
    }

    def __init__(self):
        self.videos_dir = Path(settings.DATA_DIR) / "videos"
        self._ensure_videos_dir()
        self.processor = VideoProcessor()
        # Initialize advanced effects services
        self.data_viz = DataVisualizationEffect()
        self.subtitle_effects = DynamicSubtitleEffect()

    def _ensure_videos_dir(self):
        """Ensure videos directory exists"""
        self.videos_dir.mkdir(parents=True, exist_ok=True)

    def synthesize(
        self,
        project_id: str,
        materials: List[Dict[str, Any]],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """
        Synthesize video from materials (simplified image concatenation)

        Args:
            project_id: The project ID
            materials: List of material dictionaries with 'local_path' or 'source_url'
            progress_callback: Optional callback for progress updates

        Returns:
            Path to the synthesized video file

        Raises:
            ValueError: If no valid materials provided
        """
        if not materials:
            raise ValueError("No materials provided for video synthesis")

        # Create project-specific output directory
        project_video_dir = self.videos_dir / project_id
        project_video_dir.mkdir(parents=True, exist_ok=True)

        # Output video path
        output_path = project_video_dir / "output.mp4"

        # Update progress
        if progress_callback:
            progress_callback(25, "Loading image materials...")

        # Create video clips from materials
        clips = []
        total_materials = len(materials)

        for idx, material in enumerate(materials):
            # Get image path
            image_path = material.get("local_path") or material.get("source_url")

            if not image_path:
                continue

            # Check if it's a local file
            if os.path.exists(image_path):
                # Create image clip (5 seconds per image for Phase 1)
                try:
                    clip = ImageClip(image_path, duration=5)
                    clips.append(clip)
                except Exception as e:
                    logger.warning(f"Failed to create clip from {image_path}: {e}")
                    continue

            # Update progress for each material processed
            if progress_callback:
                progress = 25 + int((idx + 1) / total_materials * 50)
                progress_callback(progress, f"Processing material {idx + 1}/{total_materials}...")

        if not clips:
            raise ValueError("No valid image materials found for video synthesis")

        # Update progress
        if progress_callback:
            progress_callback(75, "Concatenating video clips...")

        # Concatenate all clips
        final_video = concatenate_videoclips(clips, method="compose")

        # Update progress
        if progress_callback:
            progress_callback(85, "Writing video file...")

        # Write output video (Phase 1: no audio, 24 fps)
        final_video.write_videofile(
            str(output_path),
            fps=24,
            codec="libx264",
            audio=False,  # Phase 1: No audio
            verbose=False,
            logger=None
        )

        # Clean up clips
        for clip in clips:
            clip.close()
        final_video.close()

        # Update progress
        if progress_callback:
            progress_callback(100, "Video synthesis complete!")

        return str(output_path)

    def export_for_platform(
        self,
        video_clip: VideoFileClip,
        platform: str,
        output_path: str
    ) -> str:
        """
        为特定平台导出视频
        Args:
            video_clip: 视频片段
            platform: 平台类型 (horizontal, vertical, square)
            output_path: 输出路径
        Returns:
            输出文件路径
        """
        config = self.PLATFORM_CONFIGS.get(platform, self.PLATFORM_CONFIGS["horizontal"])
        target_width, target_height = config["resolution"]

        # 调整分辨率
        if video_clip.size != (target_width, target_height):
            video_clip = self._adapt_aspect_ratio(
                video_clip,
                target_width,
                target_height
            )

        # 导出
        video_clip.write_videofile(
            output_path,
            fps=config["fps"],
            codec="libx264",
            bitrate="8000k",
            audio_codec="aac",
            audio_bitrate="192k",
            verbose=False,
            logger=None
        )

        return output_path

    def _adapt_aspect_ratio(
        self,
        clip: VideoFileClip,
        target_width: int,
        target_height: int
    ) -> VideoFileClip:
        """
        适配视频宽高比
        Args:
            clip: 原始视频
            target_width: 目标宽度
            target_height: 目标高度
        Returns:
            适配后的视频
        """
        return self.processor._adapt_aspect_ratio(clip, target_width, target_height)

    def get_output_path(self, project_id: str, platform: str) -> str:
        """
        获取输出视频路径
        Args:
            project_id: 项目ID
            platform: 平台类型
        Returns:
            输出文件路径
        """
        project_video_dir = self.videos_dir / project_id
        project_video_dir.mkdir(parents=True, exist_ok=True)
        return str(project_video_dir / f"output_{platform}.mp4")

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video file information

        Args:
            video_path: Path to the video file

        Returns:
            Dictionary with video information
        """
        if not os.path.exists(video_path):
            return {"exists": False}

        try:
            from moviepy.editor import VideoFileClip

            clip = VideoFileClip(video_path)
            info = {
                "exists": True,
                "duration": clip.duration,
                "fps": clip.fps,
                "width": clip.w,
                "height": clip.h,
                "size": os.path.getsize(video_path)
            }
            clip.close()

            return info
        except Exception as e:
            return {
                "exists": True,
                "error": str(e)
            }

    async def synthesize_video(
        self,
        project_id: str,
        materials: List[Dict[str, Any]],
        output_format: str = "horizontal",
        transition_type: str = "fade",
        color_grading: Optional[str] = None,
        enable_ken_burns: bool = False,
        audio_path: Optional[str] = None,
        subtitles: Optional[List[Dict[str, Any]]] = None,
        enable_effects: bool = False,
        effects: Optional[List[VideoClip]] = None,
        script: Optional[str] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """
        Synthesize video with transitions and effects (Phase 2: Enhanced, Phase 3: Advanced Effects)

        Args:
            project_id: The project ID
            materials: List of material dictionaries with 'local_path'
            output_format: Output format (horizontal, vertical, square)
            transition_type: Transition type (fade, crossfade, wipe, none)
            color_grading: Color grading preset (cinematic, warm, cool, None)
            enable_ken_burns: Enable Ken Burns zoom effect
            audio_path: Path to audio file
            subtitles: List of subtitle dictionaries with timing
            enable_effects: Enable advanced effects (data visualization, dynamic subtitles)
            effects: List of pre-generated VideoClip effects to composite
            script: Script text for extracting data visualizations
            progress_callback: Optional callback for progress updates

        Returns:
            Path to the synthesized video file

        Raises:
            ValueError: If no valid materials provided
        """
        if not materials:
            raise ValueError("No materials provided for video synthesis")

        # Create project-specific output directory
        project_video_dir = self.videos_dir / project_id
        project_video_dir.mkdir(parents=True, exist_ok=True)

        # Get platform config
        platform_config = self.PLATFORM_CONFIGS.get(output_format, self.PLATFORM_CONFIGS["horizontal"])
        target_width, target_height = platform_config["resolution"]
        fps = platform_config["fps"]

        # Output video path
        output_path = project_video_dir / f"output_{output_format}.mp4"

        if progress_callback:
            progress_callback(10, "Loading video materials...")

        # Load and process materials
        clips = []
        total_materials = len(materials)

        for idx, material in enumerate(materials):
            # Get material path
            material_path = material.get("local_path")

            if not material_path or not os.path.exists(material_path):
                continue

            try:
                # Load video clip
                clip = VideoFileClip(material_path)

                # Get target duration (from subtitles or default)
                target_duration = 5.0  # Default 5 seconds
                if subtitles and idx < len(subtitles):
                    target_duration = subtitles[idx].get("duration", 5.0)

                # Adjust clip duration
                if clip.duration < target_duration:
                    # Loop if too short
                    clip = clip.loop(duration=target_duration)
                else:
                    # Trim if too long
                    clip = clip.subclip(0, target_duration)

                # Apply Ken Burns effect if enabled
                if enable_ken_burns:
                    clip = self.processor.add_ken_burns_effect(
                        clip,
                        zoom_start=1.0,
                        zoom_end=1.1,
                        direction="center"
                    )

                # Apply color grading if specified
                if color_grading:
                    clip = self.processor.add_color_grading(clip, preset=color_grading)

                # Adapt aspect ratio
                clip = self.processor._adapt_aspect_ratio(clip, target_width, target_height)

                clips.append(clip)

            except Exception as e:
                logger.warning(f"Failed to process material {material_path}: {e}")
                continue

            # Update progress
            if progress_callback:
                progress = 10 + int((idx + 1) / total_materials * 50)
                progress_callback(progress, f"Processing material {idx + 1}/{total_materials}...")

        if not clips:
            raise ValueError("No valid video materials found for video synthesis")

        if progress_callback:
            progress_callback(65, "Adding transitions...")

        # Add transitions between clips
        final_video = None
        try:
            if len(clips) > 1 and transition_type != "none":
                # Build concatenated video with transitions
                # Start with first clip
                current_video = clips[0]

                for i in range(1, len(clips)):
                    # Add transition between current and next clip
                    current_video = self.processor.add_transition(
                        current_video,
                        clips[i],
                        transition_type=transition_type,
                        duration=1.0
                    )

                final_video = current_video
            else:
                # Concatenate without transitions
                final_video = concatenate_videoclips(clips, method="compose")

            if progress_callback:
                progress_callback(75, "Adding audio...")

            # Add audio if provided
            if audio_path and os.path.exists(audio_path):
                try:
                    audio = AudioFileClip(audio_path)
                    # Adjust audio duration to match video
                    if audio.duration < final_video.duration:
                        audio = audio.loop(duration=final_video.duration)
                    elif audio.duration > final_video.duration:
                        audio = audio.subclip(0, final_video.duration)
                    final_video = final_video.set_audio(audio)
                except Exception as e:
                    logger.warning(f"Failed to add audio: {e}")

            # Composite advanced effects if enabled
            effect_clips = []
            if enable_effects:
                if progress_callback:
                    progress_callback(80, "Adding advanced effects...")

                # Use provided effects or generate from script
                if effects:
                    effect_clips = effects
                elif script:
                    # Generate effects from script
                    effect_clips = await self._generate_effects_from_script(
                        script, subtitles, target_width, target_height
                    )

                # Composite effects onto final video
                if effect_clips:
                    try:
                        final_video = self._composite_effects(final_video, effect_clips)
                        logger.info(f"Composited {len(effect_clips)} effect clips onto video")
                    except Exception as e:
                        logger.warning(f"Failed to composite effects: {e}")

            if progress_callback:
                progress_callback(85, "Writing video file...")

            # Write output video
            final_video.write_videofile(
                str(output_path),
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                verbose=False,
                logger=None
            )

        finally:
            # Clean up all clips to prevent resource leaks
            for clip in clips:
                try:
                    clip.close()
                except Exception as e:
                    logger.debug(f"Error closing clip: {e}")

            # Clean up effect clips
            for clip in effect_clips:
                try:
                    clip.close()
                except Exception as e:
                    logger.debug(f"Error closing effect clip: {e}")

            if final_video:
                try:
                    final_video.close()
                except Exception as e:
                    logger.debug(f"Error closing final video: {e}")

        if progress_callback:
            progress_callback(100, "Video synthesis complete!")

        return str(output_path)

    async def _generate_effects_from_script(
        self,
        script: str,
        subtitles: Optional[List[Dict[str, Any]]],
        target_width: int,
        target_height: int
    ) -> List[VideoClip]:
        """
        Generate effect clips from script text

        Args:
            script: Script text to extract effects from
            subtitles: List of subtitle dictionaries with timing info
            target_width: Target video width
            target_height: Target video height

        Returns:
            List of VideoClip effect objects
        """
        effect_clips = []

        try:
            # Extract data visualizations from script
            data_items = await self.data_viz.extract_data_from_script(script)

            for item in data_items:
                try:
                    clip = await self.data_viz.create_chart(
                        data=item["data"],
                        chart_type=item["type"],
                        duration=item.get("duration", 5.0)
                    )
                    # Set start position
                    clip = clip.set_start(item.get("position", 0))
                    # Resize to match target dimensions
                    if clip.size != (target_width, target_height):
                        clip = clip.resize((target_width, target_height))
                    effect_clips.append(clip)
                except Exception as e:
                    logger.warning(f"Failed to create data visualization: {e}")
                    continue

            # Generate dynamic subtitles if provided
            if subtitles:
                for sub in subtitles:
                    try:
                        text = sub.get("text", "")
                        start_time = sub.get("start_time", 0)
                        duration = sub.get("duration", 3.0)
                        highlight_words = sub.get("highlight_words", [])

                        if highlight_words:
                            sub_clip = await self.subtitle_effects.create_highlight_subtitle(
                                text=text,
                                highlight_words=highlight_words,
                                duration=duration
                            )
                        else:
                            sub_clip = await self.subtitle_effects.create_fade_subtitle(
                                text=text,
                                duration=duration
                            )

                        sub_clip = sub_clip.set_start(start_time)
                        # Resize to match target dimensions
                        if sub_clip.size != (target_width, target_height):
                            sub_clip = sub_clip.resize((target_width, target_height))
                        effect_clips.append(sub_clip)
                    except Exception as e:
                        logger.warning(f"Failed to create subtitle effect: {e}")
                        continue

        except Exception as e:
            logger.error(f"Failed to generate effects from script: {e}")

        return effect_clips

    def _composite_effects(
        self,
        base_video: VideoClip,
        effect_clips: List[VideoClip]
    ) -> VideoClip:
        """
        Composite effect clips onto base video

        Args:
            base_video: The base video to composite onto
            effect_clips: List of effect VideoClips with timing set

        Returns:
            CompositeVideoClip with all effects layered
        """
        if not effect_clips:
            return base_video

        # Build list of clips for composition
        all_clips = [base_video]

        for effect_clip in effect_clips:
            # Ensure effect clip is properly positioned
            all_clips.append(effect_clip)

        # Create composite video
        composite = CompositeVideoClip(all_clips)

        return composite

    def _extract_keywords(self, text: str) -> List[str]:
        """
        Extract keywords from text for highlighting

        Args:
            text: Text to extract keywords from

        Returns:
            List of keywords to highlight
        """
        import re

        # Simple keyword extraction: numbers, percentages, and capitalized words
        keywords = []

        # Extract numbers with units
        number_pattern = r'\d+(?:\.\d+)?(?:%|[万千百亿]|[mMbBkK])?'
        numbers = re.findall(number_pattern, text)
        keywords.extend(numbers[:3])  # Limit to first 3

        # Extract capitalized words (likely proper nouns)
        cap_pattern = r'\b[A-Z][a-zA-Z]+\b'
        caps = re.findall(cap_pattern, text)
        keywords.extend(caps[:2])  # Limit to first 2

        return keywords[:5]  # Return up to 5 keywords
