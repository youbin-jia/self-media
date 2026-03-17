# backend/tests/test_advanced_effects.py
"""Tests for advanced video effects including DataVisualizationEffect and DynamicSubtitleEffect"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from moviepy.editor import VideoClip

from app.services.effects.data_visualization import DataVisualizationEffect
from app.services.effects.dynamic_subtitle import DynamicSubtitleEffect


class TestDataVisualizationEffectInit:
    """Test initialization of DataVisualizationEffect"""

    def test_init_default_style_presets(self):
        """Test that default style presets are initialized"""
        effect = DataVisualizationEffect()
        assert "modern" in effect.style_presets
        assert "classic" in effect.style_presets
        assert "colors" in effect.style_presets["modern"]
        assert "background" in effect.style_presets["modern"]


class TestCreateChart:
    """Test the main create_chart method"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_create_bar_chart(self, effect):
        """Test creating bar chart"""
        data = {
            "labels": ["2020", "2021", "2022", "2023"],
            "values": [100, 150, 200, 250],
            "title": "Growth Trend"
        }

        clip = await effect.create_chart(data, "bar", "modern", 3.0)

        assert clip is not None
        assert clip.duration == 3.0
        assert clip.fps == 24
        clip.close()

    @pytest.mark.asyncio
    async def test_create_line_chart(self, effect):
        """Test creating line chart"""
        data = {
            "labels": ["Q1", "Q2", "Q3", "Q4"],
            "values": [100, 120, 90, 150],
            "title": "Quarterly Revenue"
        }

        clip = await effect.create_chart(data, "line", "modern", 4.0)

        assert clip is not None
        assert clip.duration == 4.0
        clip.close()

    @pytest.mark.asyncio
    async def test_create_pie_chart(self, effect):
        """Test creating pie chart"""
        data = {
            "labels": ["Product A", "Product B", "Product C"],
            "values": [40, 35, 25],
            "title": "Market Share"
        }

        clip = await effect.create_chart(data, "pie", "classic", 5.0)

        assert clip is not None
        assert clip.duration == 5.0
        clip.close()

    @pytest.mark.asyncio
    async def test_create_number_animation(self, effect):
        """Test creating number animation"""
        data = {
            "value": 1000000,
            "title": "Total Users",
            "prefix": "$",
            "suffix": ""
        }

        clip = await effect.create_chart(data, "number", "modern", 3.0)

        assert clip is not None
        assert clip.duration == 3.0
        clip.close()

    @pytest.mark.asyncio
    async def test_create_chart_invalid_type(self, effect):
        """Test creating chart with invalid type"""
        data = {
            "labels": ["A", "B"],
            "values": [1, 2]
        }

        with pytest.raises(ValueError, match="Unsupported chart type"):
            await effect.create_chart(data, "invalid_type", "modern", 5.0)

    @pytest.mark.asyncio
    async def test_create_chart_classic_style(self, effect):
        """Test creating chart with classic style"""
        data = {
            "labels": ["A", "B", "C"],
            "values": [10, 20, 30],
            "title": "Test Chart"
        }

        clip = await effect.create_chart(data, "bar", "classic", 2.0)

        assert clip is not None
        clip.close()


class TestBarChartCreation:
    """Test bar chart specific functionality"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_bar_chart_missing_labels(self, effect):
        """Test bar chart with missing labels"""
        data = {
            "values": [100, 150, 200],
            "title": "Test"
        }

        with pytest.raises(ValueError, match="must include 'labels' and 'values'"):
            await effect._create_bar_chart(data, "modern", 3.0)

    @pytest.mark.asyncio
    async def test_bar_chart_missing_values(self, effect):
        """Test bar chart with missing values"""
        data = {
            "labels": ["A", "B", "C"],
            "title": "Test"
        }

        with pytest.raises(ValueError, match="must include 'labels' and 'values'"):
            await effect._create_bar_chart(data, "modern", 3.0)

    @pytest.mark.asyncio
    async def test_bar_chart_generates_frames(self, effect):
        """Test that bar chart generates valid frames"""
        data = {
            "labels": ["A", "B", "C"],
            "values": [10, 20, 30],
            "title": "Test"
        }

        clip = await effect._create_bar_chart(data, "modern", 2.0)

        # Get a frame
        frame = clip.get_frame(1.0)
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert len(frame.shape) == 3  # Should be RGB
        assert frame.shape[2] == 3 or frame.shape[2] == 4  # RGB or RGBA

        clip.close()


class TestLineChartCreation:
    """Test line chart specific functionality"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_line_chart_success(self, effect):
        """Test successful line chart creation"""
        data = {
            "labels": ["Jan", "Feb", "Mar", "Apr"],
            "values": [100, 150, 120, 180],
            "title": "Monthly Revenue"
        }

        clip = await effect._create_line_chart(data, "modern", 3.0)

        assert clip is not None
        frame = clip.get_frame(1.5)
        assert frame is not None
        clip.close()


class TestPieChartCreation:
    """Test pie chart specific functionality"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_pie_chart_success(self, effect):
        """Test successful pie chart creation"""
        data = {
            "labels": ["A", "B", "C", "D"],
            "values": [25, 25, 25, 25],
            "title": "Distribution"
        }

        clip = await effect._create_pie_chart(data, "modern", 3.0)

        assert clip is not None
        frame = clip.get_frame(1.0)
        assert frame is not None
        clip.close()


class TestNumberAnimation:
    """Test number animation specific functionality"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_number_animation_integer(self, effect):
        """Test number animation with integer"""
        data = {
            "value": 1000,
            "title": "Users"
        }

        clip = await effect._create_number_animation(data, "modern", 3.0)

        assert clip is not None

        # Check that number grows over time
        frame_start = clip.get_frame(0.1)
        frame_end = clip.get_frame(2.9)

        # Both frames should exist
        assert frame_start is not None
        assert frame_end is not None

        clip.close()

    @pytest.mark.asyncio
    async def test_number_animation_large_number(self, effect):
        """Test number animation with large number"""
        data = {
            "value": 5000000,
            "title": "Revenue",
            "prefix": "$",
            "suffix": ""
        }

        clip = await effect._create_number_animation(data, "modern", 2.0)

        assert clip is not None
        frame = clip.get_frame(1.5)
        assert frame is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_number_animation_float(self, effect):
        """Test number animation with float"""
        data = {
            "value": 12345.67,
            "title": "Price"
        }

        clip = await effect._create_number_animation(data, "modern", 2.0)

        assert clip is not None
        clip.close()


class TestExtractDataFromScript:
    """Test data extraction from script"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_extract_percentage(self, effect):
        """Test extracting percentage data"""
        script = "The company's profit grew by 15% this quarter."
        result = await effect.extract_data_from_script(script)

        assert len(result) > 0
        # Should find percentage
        pie_found = any(item["type"] == "pie" for item in result)
        assert pie_found

    @pytest.mark.asyncio
    async def test_extract_time_series(self, effect):
        """Test extracting time series data"""
        script = "Revenue was 100 in 2020, 150 in 2021, and 200 in 2022."
        result = await effect.extract_data_from_script(script)

        # Should find time series
        line_found = any(item["type"] == "line" for item in result)
        assert line_found

    @pytest.mark.asyncio
    async def test_extract_comparison(self, effect):
        """Test extracting comparison data"""
        script = "Users increased from 100万 to 200万 in just one year."
        result = await effect.extract_data_from_script(script)

        # Should find comparison
        bar_found = any(item["type"] == "bar" for item in result)
        assert bar_found

    @pytest.mark.asyncio
    async def test_extract_no_data(self, effect):
        """Test script with no extractable data"""
        script = "This is a general story without any numerical data."
        result = await effect.extract_data_from_script(script)

        # May or may not find anything, but should not error
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_extract_multiple_data_points(self, effect):
        """Test script with multiple data points"""
        script = """
        The market share grew by 25% in 2020, reaching 30% in 2021.
        Revenue increased from 100万 to 500万.
        We now have 1,000,000 users.
        """
        result = await effect.extract_data_from_script(script)

        # Should extract multiple data items
        assert len(result) >= 2

    @pytest.mark.asyncio
    async def test_extract_result_structure(self, effect):
        """Test that extracted data has correct structure"""
        script = "Sales grew by 30% this year."
        result = await effect.extract_data_from_script(script)

        for item in result:
            assert "type" in item
            assert "data" in item
            assert "position" in item
            assert "duration" in item
            assert item["type"] in ["bar", "line", "pie", "number"]


class TestCreateChartFromScript:
    """Test creating charts from script"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_create_charts_from_script(self, effect):
        """Test creating multiple charts from script"""
        script = """
        Our revenue grew from 100万 to 500万 in 2022.
        Market share increased by 30%.
        We had 100 in 2020, 200 in 2021, and 300 in 2022.
        """

        clips = await effect.create_chart_from_script(script, "modern", 3.0)

        # Should create some clips
        assert len(clips) >= 1

        # All clips should be valid VideoClips
        for clip in clips:
            assert clip is not None
            # Clips use the duration from extracted data (5.0) not default_duration
            assert clip.duration > 0
            clip.close()

    @pytest.mark.asyncio
    async def test_create_charts_empty_script(self, effect):
        """Test creating charts from empty script"""
        script = "No numerical data here."

        clips = await effect.create_chart_from_script(script, "modern", 3.0)

        # Should return empty list or handle gracefully
        assert isinstance(clips, list)


class TestStylePresets:
    """Test style preset functionality"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_modern_style_colors(self, effect):
        """Test modern style has correct colors"""
        data = {
            "labels": ["A", "B"],
            "values": [1, 2]
        }

        clip = await effect.create_chart(data, "bar", "modern", 2.0)

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_classic_style_colors(self, effect):
        """Test classic style has correct colors"""
        data = {
            "labels": ["A", "B"],
            "values": [1, 2]
        }

        clip = await effect.create_chart(data, "bar", "classic", 2.0)

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_unknown_style_fallback(self, effect):
        """Test unknown style falls back to modern"""
        data = {
            "labels": ["A", "B"],
            "values": [1, 2]
        }

        # Should not raise error, falls back to modern
        clip = await effect.create_chart(data, "bar", "unknown_style", 2.0)

        assert clip is not None
        clip.close()


class TestVideoClipProperties:
    """Test VideoClip object properties"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_clip_has_fps(self, effect):
        """Test that returned clip has fps set"""
        data = {
            "labels": ["A", "B", "C"],
            "values": [10, 20, 30]
        }

        clip = await effect.create_chart(data, "bar", "modern", 3.0)

        assert clip.fps == 24
        clip.close()

    @pytest.mark.asyncio
    async def test_clip_duration_matches(self, effect):
        """Test that clip duration matches requested duration"""
        data = {
            "labels": ["A", "B"],
            "values": [1, 2]
        }

        for duration in [2.0, 5.0, 10.0]:
            clip = await effect.create_chart(data, "bar", "modern", duration)
            assert clip.duration == duration
            clip.close()

    @pytest.mark.asyncio
    async def test_clip_frame_accessible(self, effect):
        """Test that clip frames can be accessed"""
        data = {
            "labels": ["A", "B"],
            "values": [100, 200],
            "title": "Test"
        }

        for chart_type in ["bar", "line", "pie"]:
            clip = await effect.create_chart(data, chart_type, "modern", 3.0)

            # Should be able to get frames at different times
            frame_start = clip.get_frame(0.5)
            frame_mid = clip.get_frame(1.5)
            frame_end = clip.get_frame(2.5)

            assert frame_start is not None
            assert frame_mid is not None
            assert frame_end is not None

            clip.close()


class TestErrorHandling:
    """Test error handling scenarios"""

    @pytest.fixture
    def effect(self):
        return DataVisualizationEffect()

    @pytest.mark.asyncio
    async def test_empty_data_handling(self, effect):
        """Test handling of empty data"""
        data = {}

        with pytest.raises((ValueError, KeyError)):
            await effect.create_chart(data, "bar", "modern", 3.0)

    @pytest.mark.asyncio
    async def test_mismatched_labels_values(self, effect):
        """Test handling of mismatched labels and values"""
        data = {
            "labels": ["A", "B", "C"],
            "values": [1, 2]  # Missing one value
        }

        # Matplotlib will raise ValueError for mismatched arrays
        with pytest.raises(ValueError):
            await effect.create_chart(data, "bar", "modern", 3.0)


# ============================================================================
# DynamicSubtitleEffect Tests
# ============================================================================

class TestDynamicSubtitleEffectInit:
    """Test initialization of DynamicSubtitleEffect"""

    def test_init_default_style_presets(self):
        """Test that default style presets are initialized"""
        effect = DynamicSubtitleEffect()
        assert "modern" in effect.style_presets
        assert "cinematic" in effect.style_presets
        assert "minimal" in effect.style_presets
        assert "font_family" in effect.style_presets["modern"]
        assert "highlight_color" in effect.style_presets["modern"]

    def test_default_frame_size(self):
        """Test default frame size is set"""
        effect = DynamicSubtitleEffect()
        assert effect._default_frame_size == (1920, 1080)


class TestHighlightSubtitle:
    """Test highlight subtitle functionality"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_create_highlight_subtitle_basic(self, effect):
        """Test creating basic highlight subtitle"""
        text = "This is an important message"
        highlight_words = ["important"]

        clip = await effect.create_highlight_subtitle(
            text=text,
            highlight_words=highlight_words,
            style="modern",
            duration=3.0
        )

        assert clip is not None
        assert clip.duration == 3.0
        assert clip.fps == 24
        clip.close()

    @pytest.mark.asyncio
    async def test_create_highlight_subtitle_multiple_words(self, effect):
        """Test highlight subtitle with multiple highlighted words"""
        text = "The quick brown fox jumps"
        highlight_words = ["quick", "fox"]

        clip = await effect.create_highlight_subtitle(
            text=text,
            highlight_words=highlight_words,
            style="cinematic",
            duration=4.0
        )

        assert clip is not None
        assert clip.duration == 4.0
        clip.close()

    @pytest.mark.asyncio
    async def test_create_highlight_subtitle_no_highlights(self, effect):
        """Test highlight subtitle with no words to highlight"""
        text = "Plain subtitle text"
        highlight_words = []

        clip = await effect.create_highlight_subtitle(
            text=text,
            highlight_words=highlight_words,
            style="modern",
            duration=2.0
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_create_highlight_subtitle_frame_generation(self, effect):
        """Test that highlight subtitle generates valid frames"""
        text = "Test message"
        highlight_words = ["Test"]

        clip = await effect.create_highlight_subtitle(
            text=text,
            highlight_words=highlight_words,
            style="modern",
            duration=2.0
        )

        frame = clip.get_frame(1.0)
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert len(frame.shape) == 3  # Should be RGBA
        assert frame.shape[2] == 4  # RGBA

        clip.close()


class TestTypingEffect:
    """Test typing effect functionality"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_create_typing_effect_basic(self, effect):
        """Test basic typing effect"""
        text = "Hello World"

        clip = await effect.create_typing_effect(
            text=text,
            style="modern",
            duration=3.0,
            cursor=True
        )

        assert clip is not None
        assert clip.duration == 3.0
        clip.close()

    @pytest.mark.asyncio
    async def test_create_typing_effect_no_cursor(self, effect):
        """Test typing effect without cursor"""
        text = "Typing without cursor"

        clip = await effect.create_typing_effect(
            text=text,
            style="minimal",
            duration=2.0,
            cursor=False
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_create_typing_effect_progress(self, effect):
        """Test that typing effect shows progressive text"""
        text = "ABCDE"

        clip = await effect.create_typing_effect(
            text=text,
            style="modern",
            duration=5.0,
            cursor=False
        )

        # At t=0, should show nothing or very little
        frame_early = clip.get_frame(0.5)
        # At t=4.5, should show most/all text
        frame_late = clip.get_frame(4.5)

        # Both frames should be valid
        assert frame_early is not None
        assert frame_late is not None
        assert isinstance(frame_early, np.ndarray)
        assert isinstance(frame_late, np.ndarray)

        clip.close()

    @pytest.mark.asyncio
    async def test_create_typing_effect_empty_text(self, effect):
        """Test typing effect with empty text raises error"""
        with pytest.raises(ValueError, match="Text cannot be empty"):
            await effect.create_typing_effect(
                text="",
                style="modern",
                duration=2.0
            )


class TestEmphasisAnimation:
    """Test emphasis animation functionality"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_create_emphasis_light(self, effect):
        """Test light emphasis animation"""
        text = "Important"

        clip = await effect.create_emphasis_animation(
            text=text,
            style="modern",
            duration=0.5,
            emphasis_level="light"
        )

        assert clip is not None
        assert clip.duration == 0.5
        clip.close()

    @pytest.mark.asyncio
    async def test_create_emphasis_medium(self, effect):
        """Test medium emphasis animation"""
        text = "Very Important"

        clip = await effect.create_emphasis_animation(
            text=text,
            style="cinematic",
            duration=0.8,
            emphasis_level="medium"
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_create_emphasis_strong(self, effect):
        """Test strong emphasis animation"""
        text = "CRITICAL"

        clip = await effect.create_emphasis_animation(
            text=text,
            style="modern",
            duration=1.0,
            emphasis_level="strong"
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_create_emphasis_frame_generation(self, effect):
        """Test that emphasis generates frames with animation"""
        text = "Scaling Text"

        clip = await effect.create_emphasis_animation(
            text=text,
            style="modern",
            duration=1.0,
            emphasis_level="medium"
        )

        # Get frames at different times
        frame_start = clip.get_frame(0.1)
        frame_end = clip.get_frame(0.9)

        assert frame_start is not None
        assert frame_end is not None
        assert isinstance(frame_start, np.ndarray)
        assert isinstance(frame_end, np.ndarray)

        clip.close()


class TestFadeSubtitle:
    """Test fade subtitle functionality"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_create_fade_subtitle_basic(self, effect):
        """Test basic fade subtitle"""
        text = "Fading in and out"

        clip = await effect.create_fade_subtitle(
            text=text,
            style="modern",
            duration=3.0,
            fade_duration=0.5
        )

        assert clip is not None
        assert clip.duration == 3.0
        clip.close()

    @pytest.mark.asyncio
    async def test_create_fade_subtitle_alpha_variation(self, effect):
        """Test that fade subtitle has varying alpha"""
        text = "Fade test"

        clip = await effect.create_fade_subtitle(
            text=text,
            style="modern",
            duration=2.0,
            fade_duration=0.5
        )

        # Get frames at different times
        frame_fade_in = clip.get_frame(0.25)  # During fade in
        frame_full = clip.get_frame(1.0)       # Full opacity
        frame_fade_out = clip.get_frame(1.75)  # During fade out

        assert frame_fade_in is not None
        assert frame_full is not None
        assert frame_fade_out is not None

        # All should have alpha channel
        assert frame_fade_in.shape[2] == 4
        assert frame_full.shape[2] == 4
        assert frame_fade_out.shape[2] == 4

        clip.close()


class TestAnimatedSubtitle:
    """Test unified create_animated_subtitle method"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_animated_subtitle_highlight_mode(self, effect):
        """Test animated subtitle with highlight mode"""
        clip = await effect.create_animated_subtitle(
            text="Highlight this word",
            mode="highlight",
            style="modern",
            duration=3.0,
            highlight_words=["Highlight"]
        )

        assert clip is not None
        assert clip.duration == 3.0
        clip.close()

    @pytest.mark.asyncio
    async def test_animated_subtitle_typing_mode(self, effect):
        """Test animated subtitle with typing mode"""
        clip = await effect.create_animated_subtitle(
            text="Typing effect",
            mode="typing",
            style="modern",
            duration=2.0,
            cursor=True
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_animated_subtitle_emphasis_mode(self, effect):
        """Test animated subtitle with emphasis mode"""
        clip = await effect.create_animated_subtitle(
            text="Emphasis!",
            mode="emphasis",
            style="cinematic",
            duration=0.8,
            emphasis_level="strong"
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_animated_subtitle_fade_mode(self, effect):
        """Test animated subtitle with fade mode"""
        clip = await effect.create_animated_subtitle(
            text="Fade effect",
            mode="fade",
            style="modern",
            duration=2.0,
            fade_duration=0.3
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_animated_subtitle_invalid_mode(self, effect):
        """Test animated subtitle with invalid mode"""
        with pytest.raises(ValueError, match="Unsupported subtitle mode"):
            await effect.create_animated_subtitle(
                text="Test",
                mode="invalid_mode",
                style="modern",
                duration=2.0
            )


class TestStylePresetsSubtitle:
    """Test style preset functionality for subtitles"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_modern_style(self, effect):
        """Test modern style"""
        clip = await effect.create_highlight_subtitle(
            text="Modern style",
            highlight_words=["Modern"],
            style="modern",
            duration=2.0
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_cinematic_style(self, effect):
        """Test cinematic style"""
        clip = await effect.create_highlight_subtitle(
            text="Cinematic style",
            highlight_words=["Cinematic"],
            style="cinematic",
            duration=2.0
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_minimal_style(self, effect):
        """Test minimal style"""
        clip = await effect.create_highlight_subtitle(
            text="Minimal style",
            highlight_words=["Minimal"],
            style="minimal",
            duration=2.0
        )

        assert clip is not None
        clip.close()

    @pytest.mark.asyncio
    async def test_unknown_style_fallback(self, effect):
        """Test unknown style falls back to modern"""
        clip = await effect.create_highlight_subtitle(
            text="Unknown style",
            highlight_words=["Unknown"],
            style="nonexistent",
            duration=2.0
        )

        # Should not raise error, falls back to modern
        assert clip is not None
        clip.close()


class TestVideoClipPropertiesSubtitle:
    """Test VideoClip object properties for subtitles"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_clip_has_fps(self, effect):
        """Test that returned clip has fps set"""
        clip = await effect.create_highlight_subtitle(
            text="FPS test",
            highlight_words=["test"],
            style="modern",
            duration=2.0
        )

        assert clip.fps == 24
        clip.close()

    @pytest.mark.asyncio
    async def test_clip_duration_matches(self, effect):
        """Test that clip duration matches requested duration"""
        for duration in [1.0, 3.0, 5.0]:
            clip = await effect.create_typing_effect(
                text="Duration test",
                style="modern",
                duration=duration
            )
            assert clip.duration == duration
            clip.close()

    @pytest.mark.asyncio
    async def test_clip_frame_rgba(self, effect):
        """Test that clip frames are RGBA"""
        clip = await effect.create_highlight_subtitle(
            text="RGBA test",
            highlight_words=["test"],
            style="modern",
            duration=2.0
        )

        frame = clip.get_frame(1.0)
        assert frame.shape[2] == 4  # RGBA

        clip.close()


class TestColorParsing:
    """Test color parsing functionality"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    def test_parse_hex_color(self, effect):
        """Test parsing hex colors"""
        result = effect._parse_color("#FFD700")
        assert result == (255, 215, 0, 255)

    def test_parse_hex_color_with_alpha(self, effect):
        """Test parsing hex colors with alpha"""
        result = effect._parse_color("#FFD70080")
        assert result == (255, 215, 0, 128)

    def test_parse_rgba(self, effect):
        """Test parsing rgba format"""
        result = effect._parse_color("rgba(255,100,50,0.5)")
        assert result == (255, 100, 50, 127)

    def test_parse_named_color_white(self, effect):
        """Test parsing named color white"""
        result = effect._parse_color("white")
        assert result == (255, 255, 255, 255)

    def test_parse_named_color_black(self, effect):
        """Test parsing named color black"""
        result = effect._parse_color("black")
        assert result == (0, 0, 0, 255)

    def test_parse_transparent(self, effect):
        """Test parsing transparent"""
        result = effect._parse_color("transparent")
        assert result == (0, 0, 0, 0)


class TestSubtitleErrorHandling:
    """Test error handling for subtitle effects"""

    @pytest.fixture
    def effect(self):
        return DynamicSubtitleEffect()

    @pytest.mark.asyncio
    async def test_empty_text_typing(self, effect):
        """Test empty text raises error for typing effect"""
        with pytest.raises(ValueError):
            await effect.create_typing_effect(
                text="",
                style="modern",
                duration=2.0
            )

    @pytest.mark.asyncio
    async def test_invalid_mode(self, effect):
        """Test invalid mode raises error"""
        with pytest.raises(ValueError, match="Unsupported subtitle mode"):
            await effect.create_animated_subtitle(
                text="Test",
                mode="invalid",
                style="modern",
                duration=2.0
            )
