# backend/app/services/video_synthesizer.py
"""Video Synthesis Service with MoviePy"""
import os
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from moviepy.editor import ImageClip, concatenate_videoclips

from app.config import settings


class VideoSynthesizer:
    """Service for synthesizing videos from materials (Phase 1: Simplified)"""

    def __init__(self):
        self.videos_dir = Path(settings.DATA_DIR) / "videos"
        self._ensure_videos_dir()

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
