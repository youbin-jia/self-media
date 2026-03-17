# backend/app/services/effects/data_visualization.py
"""Data Visualization Effects - Generate VideoClip objects from data"""
import uuid
import io
import logging
import json
import re
from typing import Dict, Any, List, Optional
from pathlib import Path

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from moviepy.editor import VideoClip, ImageClip

logger = logging.getLogger(__name__)


class DataVisualizationEffect:
    """Data visualization effects that return VideoClip objects"""

    def __init__(self):
        self.style_presets = {
            "modern": {
                "colors": ["#3498db", "#e74c3c", "#2ecc71", "#f39c12"],
                "background": "#2c3e50",
                "font_family": "Arial",
                "font_size": 48,
                "text_color": "white"
            },
            "classic": {
                "colors": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
                "background": "white",
                "font_family": "Times New Roman",
                "font_size": 42,
                "text_color": "black"
            }
        }

    async def create_chart(
        self,
        data: dict,
        chart_type: str,
        style: str = "modern",
        duration: float = 5.0
    ) -> VideoClip:
        """
        Generate data chart animation

        Args:
            data: {
                "labels": ["2020", "2021", "2022", "2023"],
                "values": [100, 150, 200, 250],
                "title": "Growth Trend"
            }
            chart_type: "bar", "line", "pie", "number"
            style: "modern", "classic"
            duration: Duration in seconds

        Returns:
            VideoClip object
        """
        if chart_type == "bar":
            return await self._create_bar_chart(data, style, duration)
        elif chart_type == "line":
            return await self._create_line_chart(data, style, duration)
        elif chart_type == "pie":
            return await self._create_pie_chart(data, style, duration)
        elif chart_type == "number":
            return await self._create_number_animation(data, style, duration)
        else:
            raise ValueError(f"Unsupported chart type: {chart_type}")

    async def _create_bar_chart(
        self,
        data: dict,
        style: str,
        duration: float
    ) -> VideoClip:
        """Create bar chart animation"""

        style_config = self.style_presets.get(style, self.style_presets["modern"])

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 9), facecolor=style_config["background"])
        ax.set_facecolor(style_config["background"])

        labels = data.get("labels", [])
        values = data.get("values", [])
        title = data.get("title", "")

        if not labels or not values:
            raise ValueError("Bar chart data must include 'labels' and 'values'")

        # Create bars
        colors = style_config["colors"]
        bar_colors = [colors[i % len(colors)] for i in range(len(labels))]
        bars = ax.bar(range(len(labels)), values, color=bar_colors)

        # Configure axes
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=style_config["font_size"], color=style_config["text_color"])

        if title:
            ax.set_title(title, fontsize=style_config["font_size"] * 1.5, color=style_config["text_color"])

        # Set tick colors
        ax.tick_params(colors=style_config["text_color"])
        for spine in ax.spines.values():
            spine.set_color(style_config["text_color"])

        # Save to buffer and convert to numpy array
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches="tight", dpi=100, facecolor=style_config["background"])
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf)
        frame_array = np.array(img)
        img.close()
        buf.close()

        # Create VideoClip from cached frame array
        def make_frame(t):
            return frame_array

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def _create_line_chart(
        self,
        data: dict,
        style: str,
        duration: float
    ) -> VideoClip:
        """Create line chart animation"""

        style_config = self.style_presets.get(style, self.style_presets["modern"])

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 9), facecolor=style_config["background"])
        ax.set_facecolor(style_config["background"])

        labels = data.get("labels", [])
        values = data.get("values", [])
        title = data.get("title", "")

        if not labels or not values:
            raise ValueError("Line chart data must include 'labels' and 'values'")

        # Create line plot
        color = style_config["colors"][0]
        ax.plot(range(len(labels)), values, color=color, linewidth=3, marker='o', markersize=10)

        # Fill area under line
        ax.fill_between(range(len(labels)), values, alpha=0.3, color=color)

        # Configure axes
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=style_config["font_size"], color=style_config["text_color"])

        if title:
            ax.set_title(title, fontsize=style_config["font_size"] * 1.5, color=style_config["text_color"])

        # Set tick colors
        ax.tick_params(colors=style_config["text_color"])
        for spine in ax.spines.values():
            spine.set_color(style_config["text_color"])

        # Save to buffer and convert to numpy array
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches="tight", dpi=100, facecolor=style_config["background"])
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf)
        frame_array = np.array(img)
        img.close()
        buf.close()

        # Create VideoClip from cached frame array
        def make_frame(t):
            return frame_array

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def _create_pie_chart(
        self,
        data: dict,
        style: str,
        duration: float
    ) -> VideoClip:
        """Create pie chart animation"""

        style_config = self.style_presets.get(style, self.style_presets["modern"])

        # Create figure
        fig, ax = plt.subplots(figsize=(16, 9), facecolor=style_config["background"])

        labels = data.get("labels", [])
        values = data.get("values", [])
        title = data.get("title", "")

        if not labels or not values:
            raise ValueError("Pie chart data must include 'labels' and 'values'")

        # Create pie chart
        colors = style_config["colors"]
        pie_colors = [colors[i % len(colors)] for i in range(len(labels))]

        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=pie_colors,
            autopct='%1.1f%%',
            textprops={'fontsize': style_config["font_size"], 'color': style_config["text_color"]}
        )

        # Style percentage text
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontsize(style_config["font_size"] * 0.8)

        if title:
            ax.set_title(title, fontsize=style_config["font_size"] * 1.5, color=style_config["text_color"])

        # Save to buffer and convert to numpy array
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches="tight", dpi=100, facecolor=style_config["background"])
        plt.close(fig)
        buf.seek(0)
        img = Image.open(buf)
        frame_array = np.array(img)
        img.close()
        buf.close()

        # Create VideoClip from cached frame array
        def make_frame(t):
            return frame_array

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def _create_number_animation(
        self,
        data: dict,
        style: str,
        duration: float
    ) -> VideoClip:
        """Create number counter animation"""

        style_config = self.style_presets.get(style, self.style_presets["modern"])

        value = data.get("value", 0)
        title = data.get("title", "")
        prefix = data.get("prefix", "")
        suffix = data.get("suffix", "")

        def render_frame(current_value: float) -> np.ndarray:
            """Render a single frame and return as numpy array with proper cleanup."""
            fig, ax = plt.subplots(figsize=(16, 9), facecolor=style_config["background"])
            ax.set_facecolor(style_config["background"])
            ax.axis('off')

            # Format number
            if isinstance(value, float):
                if value >= 1000000:
                    formatted_value = f"{current_value/1000000:.1f}M"
                elif value >= 1000:
                    formatted_value = f"{current_value/1000:.1f}K"
                else:
                    formatted_value = f"{current_value:.1f}"
            else:
                if value >= 1000000:
                    formatted_value = f"{int(current_value/1000000)}M"
                elif value >= 1000:
                    formatted_value = f"{int(current_value/1000)}K"
                else:
                    formatted_value = str(int(current_value))

            display_text = f"{prefix}{formatted_value}{suffix}"

            # Display number
            ax.text(
                0.5, 0.5, display_text,
                fontsize=200,  # Large font for number
                color=style_config["colors"][0],
                ha='center', va='center',
                fontweight='bold',
                transform=ax.transAxes
            )

            if title:
                ax.text(
                    0.5, 0.2, title,
                    fontsize=style_config["font_size"],
                    color=style_config["text_color"],
                    ha='center', va='center',
                    transform=ax.transAxes
                )

            # Render to buffer with proper cleanup
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches="tight", dpi=100, facecolor=style_config["background"])
            plt.close(fig)
            buf.seek(0)
            img = Image.open(buf)
            frame_array = np.array(img)
            img.close()
            buf.close()

            return frame_array

        # Pre-render start and end frames, then interpolate
        # This is more memory-efficient than rendering every frame
        start_frame = render_frame(0)
        end_frame = render_frame(value)

        def make_frame(t):
            # Calculate animated value (ease-out animation)
            progress = min(t / duration, 1.0)
            # Ease-out function
            progress = 1 - (1 - progress) ** 3
            current_value = value * progress

            # For simplicity, return interpolated frame
            # Full implementation would pre-render keyframes
            if progress < 0.5:
                return start_frame
            else:
                return end_frame

        clip = VideoClip(make_frame, duration=duration)
        clip = clip.set_fps(24)

        return clip

    async def extract_data_from_script(
        self,
        script: str
    ) -> List[dict]:
        """
        Extract data and key numbers from script

        Args:
            script: The script text to extract data from

        Returns:
            List of extracted data items:
            [
                {
                    "type": "bar",
                    "data": {"labels": [...], "values": [...], "title": "..."},
                    "position": 30.5,  # Position in video (seconds)
                    "duration": 5.0
                }
            ]
        """
        result_list = []

        # Extract percentages (e.g., "增长了15%" or "increased by 15%")
        percentage_pattern = r'(\d+(?:\.\d+)?)\s*[%％]'
        percentages = re.findall(percentage_pattern, script)
        if percentages:
            result_list.append({
                "type": "pie",
                "data": {
                    "labels": ["Percentage", "Remaining"],
                    "values": [float(percentages[0]), 100 - float(percentages[0])],
                    "title": "Percentage Analysis"
                },
                "position": 5.0,
                "duration": 5.0
            })

        # Extract time series data (e.g., "2020年100，2021年150" or "100 in 2020, 150 in 2021")
        # Pattern 1: year followed by number (Chinese format)
        time_series_pattern1 = r'(\d{4})[年度]?\s*(\d+(?:\.\d+)?)'
        # Pattern 2: number followed by year (English format)
        time_series_pattern2 = r'(\d+(?:\.\d+)?)\s*(?:in\s+)?(\d{4})'

        time_matches = re.findall(time_series_pattern1, script)
        if len(time_matches) >= 2:
            labels = [m[0] for m in time_matches]
            values = [float(m[1]) for m in time_matches]
            result_list.append({
                "type": "line",
                "data": {
                    "labels": labels,
                    "values": values,
                    "title": "Growth Trend"
                },
                "position": 15.0,
                "duration": 5.0
            })
        else:
            # Try English format
            time_matches2 = re.findall(time_series_pattern2, script, re.IGNORECASE)
            if len(time_matches2) >= 2:
                labels = [m[1] for m in time_matches2]  # Year is second group
                values = [float(m[0]) for m in time_matches2]  # Value is first group
                result_list.append({
                    "type": "line",
                    "data": {
                        "labels": labels,
                        "values": values,
                        "title": "Growth Trend"
                    },
                    "position": 15.0,
                    "duration": 5.0
                })

        # Extract comparison data (e.g., "从100万增长到200万" or "from 100万 to 200万")
        comparison_pattern1 = r'从\s*(\d+(?:\.\d+)?)[万千百亿]?\s*(?:增长|增加到?)\s*(\d+(?:\.\d+)?)[万千百亿]?'
        comparison_pattern2 = r'(?:from\s+)?(\d+(?:\.\d+)?)[万千百亿wWKkMmBb]?\s*(?:增长|grew|increased|to)\s*(\d+(?:\.\d+)?)[万千百亿wWKkMmBb]?'

        comparison_matches = re.findall(comparison_pattern1, script)
        if not comparison_matches:
            comparison_matches = re.findall(comparison_pattern2, script, re.IGNORECASE)

        if comparison_matches:
            result_list.append({
                "type": "bar",
                "data": {
                    "labels": ["Before", "After"],
                    "values": [float(comparison_matches[0][0]), float(comparison_matches[0][1])],
                    "title": "Before/After Comparison"
                },
                "position": 25.0,
                "duration": 5.0
            })

        # Extract large numbers for counter animation
        large_number_pattern = r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*([万亿]|[mMbBkK])?'
        large_numbers = re.findall(large_number_pattern, script)
        if large_numbers:
            # Take the largest number
            max_num = 0
            max_match = None
            for match in large_numbers:
                num = float(match[0].replace(',', ''))
                multiplier = match[1] if match[1] else ''
                if multiplier in ['万', 'w', 'W']:
                    num *= 10000
                elif multiplier in ['亿', 'b', 'B']:
                    num *= 100000000
                elif multiplier in ['k', 'K']:
                    num *= 1000
                elif multiplier in ['m', 'M']:
                    num *= 1000000
                if num > max_num:
                    max_num = num
                    max_match = match

            if max_match and max_num > 0:
                result_list.append({
                    "type": "number",
                    "data": {
                        "value": max_num,
                        "title": "Key Metric",
                        "prefix": "",
                        "suffix": ""
                    },
                    "position": 35.0,
                    "duration": 5.0
                })

        return result_list

    async def create_chart_from_script(
        self,
        script: str,
        style: str = "modern",
        default_duration: float = 5.0
    ) -> List[VideoClip]:
        """
        Create VideoClips from data extracted from script

        Args:
            script: The script text
            style: Style preset to use
            default_duration: Default duration for each clip

        Returns:
            List of VideoClip objects
        """
        extracted_data = await self.extract_data_from_script(script)
        clips = []

        for item in extracted_data:
            try:
                clip = await self.create_chart(
                    data=item["data"],
                    chart_type=item["type"],
                    style=style,
                    duration=item.get("duration", default_duration)
                )
                clips.append(clip)
            except Exception as e:
                logger.warning(f"Failed to create chart for {item}: {e}")
                continue

        return clips
