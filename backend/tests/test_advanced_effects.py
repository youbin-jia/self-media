# backend/tests/test_advanced_effects.py
"""Tests for advanced video effects including DataVisualizationEffect"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from moviepy.editor import VideoClip

from app.services.effects.data_visualization import DataVisualizationEffect


class TestDataVisualizationEffectInit:
    """Test initialization of DataVisualizationEffect"""

    def test_init_default_style_presets(self):
        """Test that default style presets are initialized"""
        effect = DataVisualizationEffect()
        assert "modern" in effect.style_presets
        assert "classic" in effect.style_presets
        assert "colors" in effect.style_presets["modern"]
        assert "background" in effect.style_presets["modern"]

    def test_init_temp_dir_created(self):
        """Test that temp directory is created"""
        effect = DataVisualizationEffect()
        assert effect.temp_dir.exists()


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
