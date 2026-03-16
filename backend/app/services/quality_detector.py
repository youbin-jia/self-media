# backend/app/services/quality_detector.py
"""Quality Detection Service for Script Analysis"""
from typing import Dict, Any, List
from decimal import Decimal
from app.schemas.script import ScriptSegment
from app.schemas.quality import QualityReportBase


class QualityDetector:
    """Service for detecting and analyzing script quality"""

    # Grading thresholds
    GRADE_THRESHOLDS = {
        'A': 90,
        'B': 75,
        'C': 60,
        'D': 45,
        'E': 0
    }

    # Score weights
    SCORE_WEIGHTS = {
        'density': 30,      # Content density score (max 30)
        'duration': 20,     # Duration appropriateness score (max 20)
        'emotion_diversity': 20  # Emotion diversity score (max 20)
    }

    # Optimal duration range (in seconds)
    OPTIMAL_DURATION_MIN = 60.0
    OPTIMAL_DURATION_MAX = 90.0

    def __init__(self):
        pass

    def detect_script_quality(
        self,
        full_script: str,
        segments: List[ScriptSegment]
    ) -> QualityReportBase:
        """
        Analyze script quality and generate a quality report

        Args:
            full_script: The complete script text
            segments: List of script segments

        Returns:
            QualityReportBase containing quality analysis results
        """
        # Calculate individual metrics
        density_score = self._calculate_density_score(full_script, segments)
        duration_score = self._calculate_duration_score(segments)
        emotion_score = self._calculate_emotion_diversity_score(segments)

        # Calculate total score
        total_score = density_score + duration_score + emotion_score

        # Determine grade
        grade = self._calculate_grade(total_score)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            density_score,
            duration_score,
            emotion_score,
            segments
        )

        # Build metrics detail
        metrics = {
            'density': {
                'score': float(density_score),
                'max_score': self.SCORE_WEIGHTS['density'],
                'description': 'Content density and information richness'
            },
            'duration': {
                'score': float(duration_score),
                'max_score': self.SCORE_WEIGHTS['duration'],
                'description': 'Duration appropriateness for short video format'
            },
            'emotion_diversity': {
                'score': float(emotion_score),
                'max_score': self.SCORE_WEIGHTS['emotion_diversity'],
                'description': 'Variety of emotional tones throughout the script'
            },
            'total_duration': self._get_total_duration(segments),
            'segment_count': len(segments)
        }

        # Identify issues
        issues = self._identify_issues(
            density_score,
            duration_score,
            emotion_score,
            segments
        )

        return QualityReportBase(
            report_type='script_quality',
            overall_score=Decimal(str(total_score)),
            grade=grade,
            metrics=metrics,
            issues=issues,
            recommendations=recommendations
        )

    def _calculate_density_score(
        self,
        full_script: str,
        segments: List[ScriptSegment]
    ) -> Decimal:
        """
        Calculate content density score (max 30 points)

        Criteria:
        - Text length per segment
        - Information density (words per second)
        - Segment count appropriateness

        Args:
            full_script: The complete script text
            segments: List of script segments

        Returns:
            Density score (0-30)
        """
        if not segments:
            return Decimal('0')

        total_duration = self._get_total_duration(segments)
        if total_duration == 0:
            return Decimal('0')

        # Calculate word count
        word_count = len(full_script.replace('\n', ' ').split())

        # Calculate words per second
        words_per_second = word_count / total_duration

        # Optimal words per second for video: 2.5-4.0 (Chinese) or 2.0-3.5 (English)
        # Score based on deviation from optimal range
        optimal_min = 2.0
        optimal_max = 3.5

        if optimal_min <= words_per_second <= optimal_max:
            # Perfect range
            density_score = self.SCORE_WEIGHTS['density']
        elif words_per_second < optimal_min:
            # Too slow - reduce score proportionally
            ratio = words_per_second / optimal_min
            density_score = self.SCORE_WEIGHTS['density'] * ratio
        else:
            # Too fast - reduce score proportionally
            excess_ratio = (words_per_second - optimal_max) / optimal_max
            density_score = max(0, self.SCORE_WEIGHTS['density'] * (1 - excess_ratio * 0.5))

        # Adjust for segment count (optimal: 8-12 segments for 60-90s video)
        segment_count = len(segments)
        if 8 <= segment_count <= 12:
            pass  # No adjustment needed
        else:
            # Penalize slightly for too few or too many segments
            deviation = abs(segment_count - 10) / 10
            density_score = density_score * (1 - deviation * 0.2)

        return Decimal(str(round(min(density_score, self.SCORE_WEIGHTS['density']), 2)))

    def _calculate_duration_score(self, segments: List[ScriptSegment]) -> Decimal:
        """
        Calculate duration appropriateness score (max 20 points)

        Criteria:
        - Total duration within optimal range (60-90 seconds)
        - Individual segment duration consistency

        Args:
            segments: List of script segments

        Returns:
            Duration score (0-20)
        """
        if not segments:
            return Decimal('0')

        total_duration = self._get_total_duration(segments)

        # Check if total duration is in optimal range
        if self.OPTIMAL_DURATION_MIN <= total_duration <= self.OPTIMAL_DURATION_MAX:
            # Perfect duration
            base_score = self.SCORE_WEIGHTS['duration']
        elif total_duration < self.OPTIMAL_DURATION_MIN:
            # Too short
            ratio = total_duration / self.OPTIMAL_DURATION_MIN
            base_score = self.SCORE_WEIGHTS['duration'] * ratio
        else:
            # Too long
            excess_ratio = (total_duration - self.OPTIMAL_DURATION_MAX) / self.OPTIMAL_DURATION_MAX
            base_score = max(0, self.SCORE_WEIGHTS['duration'] * (1 - excess_ratio * 0.5))

        # Adjust for segment duration consistency
        if len(segments) > 1:
            durations = [s.duration for s in segments]
            avg_duration = sum(durations) / len(durations)

            # Calculate variance
            variance = sum((d - avg_duration) ** 2 for d in durations) / len(durations)
            std_dev = variance ** 0.5

            # Lower standard deviation is better (more consistent)
            # Ideal: std_dev < 2 seconds
            consistency_bonus = max(0, 1 - (std_dev / 5)) * 0.1
            base_score = base_score * (1 + consistency_bonus)

        return Decimal(str(round(min(base_score, self.SCORE_WEIGHTS['duration']), 2)))

    def _calculate_emotion_diversity_score(self, segments: List[ScriptSegment]) -> Decimal:
        """
        Calculate emotion diversity score (max 20 points)

        Criteria:
        - Number of distinct emotions used
        - Distribution of emotions (more balanced is better)

        Args:
            segments: List of script segments

        Returns:
            Emotion diversity score (0-20)
        """
        if not segments:
            return Decimal('0')

        # Extract emotions from segments
        emotions = [s.emotion for s in segments if s.emotion]

        if not emotions:
            # No emotions specified - give partial score
            return Decimal('10')

        # Count unique emotions
        unique_emotions = set(emotions)
        unique_count = len(unique_emotions)

        # Score based on number of unique emotions
        # Ideal: 3-5 different emotions for a short video
        if 3 <= unique_count <= 5:
            diversity_score = self.SCORE_WEIGHTS['emotion_diversity']
        elif unique_count < 3:
            # Too monotonous
            ratio = unique_count / 3
            diversity_score = self.SCORE_WEIGHTS['emotion_diversity'] * ratio
        else:
            # Too many emotions - might feel chaotic
            excess_ratio = (unique_count - 5) / 5
            diversity_score = max(0, self.SCORE_WEIGHTS['emotion_diversity'] * (1 - excess_ratio * 0.3))

        # Bonus for balanced distribution
        if unique_count > 1:
            from collections import Counter
            emotion_counts = Counter(emotions)
            total = len(emotions)

            # Calculate distribution balance (entropy-like measure)
            expected_ratio = 1 / unique_count
            balance_score = 0
            for count in emotion_counts.values():
                actual_ratio = count / total
                balance_score += min(actual_ratio, expected_ratio)

            balance_score /= unique_count
            diversity_score = diversity_score * (0.8 + 0.2 * balance_score)

        return Decimal(str(round(min(diversity_score, self.SCORE_WEIGHTS['emotion_diversity']), 2)))

    def _calculate_grade(self, total_score: Decimal) -> str:
        """
        Calculate letter grade from total score

        Args:
            total_score: Total quality score (0-70)

        Returns:
            Letter grade (A-E)
        """
        score = float(total_score)

        # Convert to percentage (max score is 70)
        percentage = (score / 70) * 100

        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if percentage >= threshold:
                return grade

        return 'E'

    def _generate_recommendations(
        self,
        density_score: Decimal,
        duration_score: Decimal,
        emotion_score: Decimal,
        segments: List[ScriptSegment]
    ) -> List[str]:
        """
        Generate improvement recommendations based on scores

        Args:
            density_score: Content density score
            duration_score: Duration appropriateness score
            emotion_score: Emotion diversity score
            segments: List of script segments

        Returns:
            List of recommendation strings
        """
        recommendations = []

        # Density recommendations
        if float(density_score) < self.SCORE_WEIGHTS['density'] * 0.7:
            recommendations.append(
                "建议增加内容密度，可以考虑在脚本中添加更多有价值的信息点"
            )
        elif float(density_score) < self.SCORE_WEIGHTS['density'] * 0.5:
            recommendations.append(
                "内容密度较低，建议重新梳理脚本结构，增加核心观点和关键信息"
            )

        # Duration recommendations
        total_duration = self._get_total_duration(segments)
        if total_duration < self.OPTIMAL_DURATION_MIN:
            recommendations.append(
                f"视频时长偏短（{total_duration:.1f}秒），建议扩充内容至60-90秒以获得更好的观众体验"
            )
        elif total_duration > self.OPTIMAL_DURATION_MAX:
            recommendations.append(
                f"视频时长偏长（{total_duration:.1f}秒），建议精简内容控制在60-90秒以内"
            )

        if float(duration_score) < self.SCORE_WEIGHTS['duration'] * 0.6:
            recommendations.append(
                "段落时长分布不够均匀，建议调整各段落的时长使整体节奏更加流畅"
            )

        # Emotion recommendations
        emotions = [s.emotion for s in segments if s.emotion]
        unique_emotions = set(emotions)

        if not emotions:
            recommendations.append(
                "建议为每个段落标注情感基调，这有助于后期配音和素材选择"
            )
        elif len(unique_emotions) < 3:
            recommendations.append(
                f"情感表达较为单一（仅{len(unique_emotions)}种），建议增加情感变化以提升视频吸引力"
            )
        elif len(unique_emotions) > 5:
            recommendations.append(
                "情感变化过于频繁，可能影响叙事连贯性，建议适当精简情感类型"
            )

        # Add general recommendation if score is low
        total = float(density_score + duration_score + emotion_score)
        if total < 35:
            recommendations.append(
                "整体质量评分较低，建议重新规划脚本结构，确保内容丰富、时长适中、情感多元"
            )

        return recommendations

    def _identify_issues(
        self,
        density_score: Decimal,
        duration_score: Decimal,
        emotion_score: Decimal,
        segments: List[ScriptSegment]
    ) -> List[Dict[str, Any]]:
        """
        Identify specific issues in the script

        Args:
            density_score: Content density score
            duration_score: Duration appropriateness score
            emotion_score: Emotion diversity score
            segments: List of script segments

        Returns:
            List of issue dictionaries
        """
        issues = []

        # Check for density issues
        if float(density_score) < self.SCORE_WEIGHTS['density'] * 0.5:
            issues.append({
                'type': 'density',
                'severity': 'high',
                'message': '内容密度严重不足',
                'score': float(density_score)
            })
        elif float(density_score) < self.SCORE_WEIGHTS['density'] * 0.7:
            issues.append({
                'type': 'density',
                'severity': 'medium',
                'message': '内容密度偏低',
                'score': float(density_score)
            })

        # Check for duration issues
        total_duration = self._get_total_duration(segments)
        if total_duration < self.OPTIMAL_DURATION_MIN * 0.5:
            issues.append({
                'type': 'duration',
                'severity': 'high',
                'message': f'视频时长过短（{total_duration:.1f}秒）',
                'score': float(duration_score)
            })
        elif total_duration > self.OPTIMAL_DURATION_MAX * 1.5:
            issues.append({
                'type': 'duration',
                'severity': 'high',
                'message': f'视频时长过长（{total_duration:.1f}秒）',
                'score': float(duration_score)
            })
        elif float(duration_score) < self.SCORE_WEIGHTS['duration'] * 0.6:
            issues.append({
                'type': 'duration',
                'severity': 'medium',
                'message': '段落时长分布不均',
                'score': float(duration_score)
            })

        # Check for emotion issues
        emotions = [s.emotion for s in segments if s.emotion]
        if not emotions:
            issues.append({
                'type': 'emotion',
                'severity': 'medium',
                'message': '未标注情感基调',
                'score': float(emotion_score)
            })
        elif len(set(emotions)) < 2 and float(emotion_score) < self.SCORE_WEIGHTS['emotion_diversity'] * 0.7:
            issues.append({
                'type': 'emotion',
                'severity': 'medium',
                'message': '情感表达单一',
                'score': float(emotion_score)
            })

        return issues

    def _get_total_duration(self, segments: List[ScriptSegment]) -> float:
        """
        Calculate total duration from segments

        Args:
            segments: List of script segments

        Returns:
            Total duration in seconds
        """
        return sum(s.duration for s in segments)

    async def detect_audio_quality(
        self,
        audio_path: str
    ) -> Dict[str, Any]:
        """
        检测音频质量
        Args:
            audio_path: 音频文件路径
        Returns:
            质量报告
        """
        import librosa

        # 加载音频
        y, sr = librosa.load(audio_path)

        # 计算指标
        duration = len(y) / sr
        rms = librosa.feature.rms(y=y)[0]
        avg_volume = float(rms.mean())

        # 检测静音段
        silence_ratio = 1 - (len(librosa.effects.split(y, top_db=20)) / (len(y) / sr))

        # 评分
        score = 0.0
        issues = []

        # 音量评分 (30分)
        if 0.01 <= avg_volume <= 0.3:
            volume_score = 30
        elif 0.005 <= avg_volume <= 0.5:
            volume_score = 20
        else:
            volume_score = 10
            issues.append({
                "type": "volume",
                "message": f"音量异常: {avg_volume:.3f}"
            })
        score += volume_score

        # 清晰度评分 (40分) - 基于信噪比估计
        clarity_score = min(40, silence_ratio * 40)
        score += clarity_score

        # 时长合理性 (30分)
        if duration >= 30:  # 至少30秒
            duration_score = 30
        elif duration >= 10:
            duration_score = 20
        else:
            duration_score = 10
            issues.append({
                "type": "duration",
                "message": f"音频时长过短: {duration:.1f}秒"
            })
        score += duration_score

        overall_score = Decimal(str(score)).quantize(Decimal("0.01"))
        grade = self._calculate_grade(overall_score)

        return {
            "overall_score": overall_score,
            "grade": grade,
            "metrics": {
                "duration": duration,
                "average_volume": avg_volume,
                "silence_ratio": silence_ratio,
                "sample_rate": sr
            },
            "issues": issues,
            "recommendations": self._generate_audio_recommendations(grade, issues)
        }

    def _generate_audio_recommendations(self, grade: str, issues: List[Dict[str, Any]]) -> List[str]:
        """生成音频质量改进建议"""
        recommendations = []

        for issue in issues:
            if issue["type"] == "volume":
                recommendations.append("建议调整音频音量至正常范围")
            elif issue["type"] == "duration":
                recommendations.append("建议增加音频时长以保证内容完整性")

        if grade in ["D", "E"]:
            recommendations.append("音频质量较低，建议重新录制或使用专业音频处理工具优化")

        return recommendations


# Singleton instance
_quality_detector_instance = None


def get_quality_detector() -> QualityDetector:
    """Get or create QualityDetector singleton instance"""
    global _quality_detector_instance
    if _quality_detector_instance is None:
        _quality_detector_instance = QualityDetector()
    return _quality_detector_instance
