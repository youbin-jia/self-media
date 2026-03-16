# backend/app/services/video_synthesizer.py
"""Video Synthesis Service with MoviePy"""
import os
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from moviepy.editor import ImageClip, concatenate_videoclips, VideoFileClip, CompositeVideoClip, AudioFileClip

from app.config import settings
from app.utils.video_utils import VideoProcessor


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
                    print(f"Warning: Failed to create clip from {image_path}: {e}")
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
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> str:
        """
        Synthesize video with transitions and effects (Phase 2: Enhanced)

        Args:
            project_id: The project ID
            materials: List of material dictionaries with 'local_path'
            output_format: Output format (horizontal, vertical, square)
            transition_type: Transition type (fade, crossfade, wipe, none)
            color_grading: Color grading preset (cinematic, warm, cool, None)
            enable_ken_burns: Enable Ken Burns zoom effect
            audio_path: Path to audio file
            subtitles: List of subtitle dictionaries with timing
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
                print(f"Warning: Failed to process material {material_path}: {e}")
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
        if len(clips) > 1 and transition_type != "none":
            final_clips = [clips[0]]
            for i in range(1, len(clips)):
                transition = self.processor.add_transition(
                    final_clips[-1],
                    clips[i],
                    transition_type=transition_type,
                    duration=1.0
                )
                final_clips.append(transition)
            final_video = CompositeVideoClip(final_clips)
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
                print(f"Warning: Failed to add audio: {e}")

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

        # Clean up
        for clip in clips:
            clip.close()
        final_video.close()

        if progress_callback:
            progress_callback(100, "Video synthesis complete!")

        return str(output_path)
