# backend/app/services/effects/dynamic_subtitle.py
"""Dynamic Subtitle Effects - Generate VideoClip objects with animated subtitles"""
import logging
from typing import List, Dict, Any, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import  VideoClip

logger = logging.getLogger(__name__)


class DynamicSubtitleEffect:
    """Dynamic subtitle effects that return VideoClip objects"""

    def __init__(self):
        self.style_presets = {
            "modern": {
                "font_family": "Arial",
                "font_size": 60,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 2,
                "highlight_color": "#FFD700",  # Gold
                "bg_color": None,  # Transparent background
            },
            "cinematic": {
                "font_family": "Arial",
                "font_size": 70,
                "color": "white",
                "stroke_color": "black",
                "stroke_width": 3,
                "highlight_color": "#FF6B6B",  # Coral
                "bg_color": "rgba(0,0,0,0.5)",  # Semi-transparent black
            },
            "minimal": {
                "font_family": "Arial",
                "font_size": 50,
                "color": "white",
                "stroke_color": None,
                "stroke_width": 0,
                "highlight_color": "#00D9FF",  # Cyan
                "bg_color": None,
            }
        }
        self._default_frame_size = (1920, 1080)

    def _get_font(self, font_family: str, font_size: int) -> ImageFont.FreeTypeFont:
        """Get font object with fallback to default"""
        try:
            # Try to load specified font
            font = ImageFont.truetype(font_family, font_size)
        except (OSError, IOError):
            # Fallback to default font
            try:
                font = ImageFont.truetype("Arial.ttf", font_size)
            except (OSError, IOError):
                # Use default PIL font
                font = ImageFont.load_default()
        return font

    def _render_text_frame(
        self,
        text: str,
        style_config: dict,
        frame_size: Tuple[int, int] = None,
        highlight_words: List[str] = None,
        position: Tuple[int, int] = None,
    ) -> np.ndarray:
        """
        Render text to a numpy array frame.

        Args:
            text: Text to render
            style_config: Style configuration dict
            frame_size: (width, height) of the frame
            highlight_words: Words to highlight with different color
            position: (x, y) position for text anchor

        Returns:
            numpy array of RGBA image
        """
        if frame_size is None:
            frame_size = self._default_frame_size

        width, height = frame_size

        # Create RGBA image with transparent background
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        try:
            draw = ImageDraw.Draw(img)

            # Parse background color if set
            if style_config.get("bg_color"):
                bg_color = self._parse_color(style_config["bg_color"])
                # Draw semi-transparent background rectangle
                bg_img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
                try:
                    bg_draw = ImageDraw.Draw(bg_img)
                    bg_draw.rectangle([(0, height - 150), (width, height)], fill=bg_color)
                    img = Image.alpha_composite(img, bg_img)
                    draw = ImageDraw.Draw(img)
                finally:
                    bg_img.close()

            # Get font
            font = self._get_font(
                style_config["font_family"],
                style_config["font_size"]
            )

            # Calculate text position (centered horizontally, near bottom)
            if position is None:
                # Get text bounding box
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]

                x = (width - text_width) // 2
                y = height - text_height - 100  # 100px from bottom
            else:
                x, y = position

            # Draw stroke if configured AND not using highlights (highlights draw their own stroke)
            stroke_color = style_config.get("stroke_color")
            stroke_width = style_config.get("stroke_width", 0)

            if stroke_color and stroke_width > 0 and not highlight_words:
                stroke_rgba = self._parse_color(stroke_color)
                # Draw stroke by offsetting text
                for offset_x in range(-stroke_width, stroke_width + 1):
                    for offset_y in range(-stroke_width, stroke_width + 1):
                        if offset_x ** 2 + offset_y ** 2 <= stroke_width ** 2:
                            draw.text(
                                (x + offset_x, y + offset_y),
                                text,
                                font=font,
                                fill=stroke_rgba
                            )

            # If highlight_words provided, render with highlighting
            if highlight_words:
                self._render_text_with_highlights(
                    draw, text, highlight_words, font, style_config, x, y
                )
            else:
                # Draw main text
                text_color = self._parse_color(style_config["color"])
                draw.text((x, y), text, font=font, fill=text_color)

            return np.array(img)
        finally:
            img.close()

    def _render_text_with_highlights(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        highlight_words: List[str],
        font: ImageFont.FreeTypeFont,
        style_config: dict,
        start_x: int,
        start_y: int
    ) -> None:
        """Render text with highlighted words in different color"""
        # Parse colors
        normal_color = self._parse_color(style_config["color"])
        highlight_color = self._parse_color(style_config["highlight_color"])

        current_x = start_x

        # Split text while preserving positions
        words_to_highlight = set(highlight_words)
        segments = []
        remaining = text
        highlight_font = self._get_font(
            style_config["font_family"],
            int(style_config["font_size"] * 1.1)  # Slightly larger for highlight
        )

        # Build segments list
        for word in words_to_highlight:
            if word in remaining:
                parts = remaining.split(word, 1)
                if parts[0]:
                    segments.append((parts[0], False))
                segments.append((word, True))
                remaining = parts[1] if len(parts) > 1 else ""

        if remaining:
            segments.append((remaining, False))

        # Draw each segment
        for segment_text, is_highlight in segments:
            current_font = highlight_font if is_highlight else font
            current_color = highlight_color if is_highlight else normal_color

            # Draw stroke for this segment if configured
            stroke_color = style_config.get("stroke_color")
            stroke_width = style_config.get("stroke_width", 0)

            if stroke_color and stroke_width > 0:
                stroke_rgba = self._parse_color(stroke_color)
                for offset_x in range(-stroke_width, stroke_width + 1):
                    for offset_y in range(-stroke_width, stroke_width + 1):
                        if offset_x ** 2 + offset_y ** 2 <= stroke_width ** 2:
                            draw.text(
                                (current_x + offset_x, start_y + offset_y),
                                segment_text,
                                font=current_font,
                                fill=stroke_rgba
                            )

            draw.text(
                (current_x, start_y),
                segment_text,
                font=current_font,
                fill=current_color
            )

            # Advance x position
            bbox = draw.textbbox((0, 0), segment_text, font=current_font)
            current_x += bbox[2] - bbox[0]

    def _parse_color(self, color_str: str) -> Tuple[int, int, int, int]:
        """Parse color string to RGBA tuple"""
        if color_str.startswith('rgba('):
            # Parse rgba(r,g,b,a)
            values = color_str[5:-1].split(',')
            r, g, b = int(values[0]), int(values[1]), int(values[2])
            a = int(float(values[3]) * 255) if len(values) > 3 else 255
            return (r, g, b, a)
        elif color_str.startswith('#'):
            # Parse hex color
            hex_str = color_str[1:]
            if len(hex_str) == 6:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                return (r, g, b, 255)
            elif len(hex_str) == 8:
                r = int(hex_str[0:2], 16)
                g = int(hex_str[2:4], 16)
                b = int(hex_str[4:6], 16)
                a = int(hex_str[6:8], 16)
                return (r, g, b, a)
        elif color_str.lower() == 'white':
            return (255, 255, 255, 255)
        elif color_str.lower() == 'black':
            return (0, 0, 0, 255)
        elif color_str.lower() == 'transparent':
            return (0, 0, 0, 0)

        # Default to white
        return (255, 255, 255, 255)

    async def create_highlight_subtitle(
        self,
        text: str,
        highlight_words: List[str],
        style: str = "modern",
        duration: float = 3.0
    ) -> VideoClip:
        """
        Create subtitle with highlighted keywords.

        Args:
            text: The subtitle text
            highlight_words: List of words to highlight
            style: Style preset ("modern", "cinematic", "minimal")
            duration: Duration in seconds

        Returns:
            VideoClip object
        """
        style_config = self.style_presets.get(style, self.style_presets["modern"])

        # Render static frame with highlights
        frame_array = self._render_text_frame(
            text=text,
            style_config=style_config,
            highlight_words=highlight_words
        )

        # Create VideoClip from static frame
        def make_frame(t):
            return frame_array

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def create_typing_effect(
        self,
        text: str,
        style: str = "modern",
        duration: float = 3.0,
        cursor: bool = True
    ) -> VideoClip:
        """
        Create typewriter effect animation.

        Args:
            text: The text to animate
            style: Style preset
            duration: Total duration for typing animation
            cursor: Whether to show blinking cursor

        Returns:
            VideoClip object with typing animation
        """
        style_config = self.style_presets.get(style, self.style_presets["modern"])
        chars = len(text)

        if chars == 0:
            raise ValueError("Text cannot be empty for typing effect")

        char_duration = duration / chars
        frame_size = self._default_frame_size

        # Pre-render frames for each character position (for efficiency, render key frames)
        # For a smooth typing effect, we'll render on-the-fly but cache style config

        def make_frame(t):
            # Calculate how many characters should be visible
            progress = min(t / duration, 1.0)
            visible_chars = int(progress * chars)

            # Get partial text
            partial_text = text[:visible_chars]

            # Add cursor if enabled
            if cursor:
                # Blinking cursor effect
                cursor_visible = (int(t * 3) % 2) == 0
                if cursor_visible:
                    partial_text += "|"

            # Render this frame
            return self._render_text_frame(
                text=partial_text,
                style_config=style_config,
                frame_size=frame_size
            )

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def create_emphasis_animation(
        self,
        text: str,
        style: str = "modern",
        duration: float = 1.0,
        emphasis_level: str = "medium"
    ) -> VideoClip:
        """
        Create emphasis animation with scaling effect.

        Args:
            text: The text to emphasize
            style: Style preset
            duration: Animation duration
            emphasis_level: "light", "medium", or "strong"

        Returns:
            VideoClip object with emphasis animation
        """
        style_config = self.style_presets.get(style, self.style_presets["modern"])

        # Scale parameters based on emphasis level
        emphasis_params = {
            "light": {"scale_factor": 1.1, "bounce": False},
            "medium": {"scale_factor": 1.3, "bounce": True},
            "strong": {"scale_factor": 1.5, "bounce": True}
        }

        params = emphasis_params.get(emphasis_level, emphasis_params["medium"])
        scale_factor = params["scale_factor"]
        use_bounce = params["bounce"]

        # Get base font size
        base_font_size = style_config["font_size"]
        frame_size = self._default_frame_size

        def make_frame(t):
            # Calculate animation progress
            progress = t / duration

            if use_bounce:
                # Bounce effect: overshoot and settle
                # Use elastic easing
                if progress < 0.5:
                    # First half: rapid expansion with overshoot
                    scale = 1 + (scale_factor - 1) * (2 * progress) * 1.2
                else:
                    # Second half: settle back
                    scale = scale_factor - (scale_factor - 1) * 0.2 * (2 * progress - 1)
                    scale = max(1, min(scale_factor * 1.2, scale))
            else:
                # Simple scale up
                scale = 1 + (scale_factor - 1) * progress

            # Create modified style with scaled font
            scaled_style = style_config.copy()
            scaled_style["font_size"] = int(base_font_size * scale)

            return self._render_text_frame(
                text=text,
                style_config=scaled_style,
                frame_size=frame_size
            )

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def create_fade_subtitle(
        self,
        text: str,
        style: str = "modern",
        duration: float = 3.0,
        fade_duration: float = 0.5
    ) -> VideoClip:
        """
        Create subtitle with fade in/out effect.

        Args:
            text: The subtitle text
            style: Style preset
            duration: Total duration
            fade_duration: Duration of fade in/out (each)

        Returns:
            VideoClip object with fade effect
        """
        style_config = self.style_presets.get(style, self.style_presets["modern"])

        # Render base frame
        base_frame = self._render_text_frame(
            text=text,
            style_config=style_config
        )

        def make_frame(t):
            # Calculate alpha based on position in video
            if t < fade_duration:
                # Fade in
                alpha = t / fade_duration
            elif t > duration - fade_duration:
                # Fade out
                alpha = (duration - t) / fade_duration
            else:
                alpha = 1.0

            alpha = max(0.0, min(1.0, alpha))

            # Apply alpha to the frame
            frame = base_frame.copy()
            frame[:, :, 3] = (frame[:, :, 3] * alpha).astype(np.uint8)

            return frame

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def create_animated_subtitle(
        self,
        text: str,
        mode: str = "highlight",
        style: str = "modern",
        duration: float = 3.0,
        **kwargs
    ) -> VideoClip:
        """
        Unified method to create animated subtitles.

        Args:
            text: The subtitle text
            mode: Animation mode ("highlight", "typing", "emphasis", "fade")
            style: Style preset
            duration: Duration in seconds
            **kwargs: Additional mode-specific parameters

        Returns:
            VideoClip object
        """
        if mode == "highlight":
            highlight_words = kwargs.get("highlight_words", [])
            return await self.create_highlight_subtitle(
                text=text,
                highlight_words=highlight_words,
                style=style,
                duration=duration
            )
        elif mode == "typing":
            cursor = kwargs.get("cursor", True)
            return await self.create_typing_effect(
                text=text,
                style=style,
                duration=duration,
                cursor=cursor
            )
        elif mode == "emphasis":
            emphasis_level = kwargs.get("emphasis_level", "medium")
            return await self.create_emphasis_animation(
                text=text,
                style=style,
                duration=duration,
                emphasis_level=emphasis_level
            )
        elif mode == "fade":
            fade_duration = kwargs.get("fade_duration", 0.5)
            return await self.create_fade_subtitle(
                text=text,
                style=style,
                duration=duration,
                fade_duration=fade_duration
            )
        else:
            raise ValueError(f"Unsupported subtitle mode: {mode}")
