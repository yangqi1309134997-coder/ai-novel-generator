"""
质量评估系统
评估生成小说的质量，包括AI痕迹、连贯性、一致性等

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

import re
import logging
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import Counter

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """质量报告"""
    # AI痕迹
    ai_taste_score: float  # 0-100，100表示无AI痕迹
    ai_taste_details: Dict[str, int]

    # 连贯性
    coherence_score: float  # 0-10
    coherence_issues: List[str]

    # 一致性
    consistency_score: float  # 0-10
    consistency_issues: List[str]

    # 可读性
    readability_score: float  # 0-10
    readability_details: Dict[str, float]

    # 整体评分
    overall_score: float  # 0-10

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'ai_taste_score': self.ai_taste_score,
            'ai_taste_details': self.ai_taste_details,
            'coherence_score': self.coherence_score,
            'coherence_issues': self.coherence_issues,
            'consistency_score': self.consistency_score,
            'consistency_issues': self.consistency_issues,
            'readability_score': self.readability_score,
            'readability_details': self.readability_details,
            'overall_score': self.overall_score
        }


class QualityEvaluator:
    """质量评估器"""

    # AI痕迹词列表
    AI_TASTE_WORDS = [
        "突然", "竟然", "霎时间", "不由得", "禁不住",
        "心中涌起", "却然", "陡然", "刹那间", "瞬间"
    ]

    def __init__(self):
        """初始化质量评估器"""
        self.logger = logging.getLogger(__name__)

    def evaluate_chapter(
        self,
        chapter_text: str,
        chapter_number: int = 1
    ) -> QualityReport:
        """
        评估单章节质量

        Args:
            chapter_text: 章节文本
            chapter_number: 章节号

        Returns:
            QualityReport对象
        """
        self.logger.info(f"[质量评估] 开始评估第{chapter_number}章...")

        # 评估AI痕迹
        ai_score, ai_details = self._evaluate_ai_taste(chapter_text)

        # 评估连贯性
        coherence_score, coherence_issues = self._evaluate_coherence(chapter_text)

        # 评估一致性
        consistency_score, consistency_issues = self._evaluate_consistency(chapter_text)

        # 评估可读性
        readability_score, readability_details = self._evaluate_readability(chapter_text)

        # 计算整体评分
        overall_score = self._calculate_overall_score(
            ai_score / 10,  # 转换到0-10
            coherence_score,
            consistency_score,
            readability_score
        )

        report = QualityReport(
            ai_taste_score=ai_score,
            ai_taste_details=ai_details,
            coherence_score=coherence_score,
            coherence_issues=coherence_issues,
            consistency_score=consistency_score,
            consistency_issues=consistency_issues,
            readability_score=readability_score,
            readability_details=readability_details,
            overall_score=overall_score
        )

        self.logger.info(f"[质量评估] 第{chapter_number}章评估完成，整体评分: {overall_score:.1f}/10")

        return report

    def evaluate_multiple_chapters(
        self,
        chapters: List[Tuple[int, str]]
    ) -> Dict[str, Any]:
        """
        评估多个章节

        Args:
            chapters: 章节列表 [(chapter_number, text), ...]

        Returns:
            评估结果字典
        """
        self.logger.info(f"[质量评估] 开始评估{len(chapters)}个章节...")

        reports = []
        for chapter_number, text in chapters:
            report = self.evaluate_chapter(text, chapter_number)
            reports.append((chapter_number, report))

        # 汇总报告
        summary = self._summarize_reports(reports)

        self.logger.info(f"[质量评估] 所有章节评估完成，整体评分: {summary['overall_score']:.1f}/10")

        return {
            'summary': summary,
            'chapter_reports': {str(num): report.to_dict() for num, report in reports}
        }

    def _evaluate_ai_taste(self, text: str) -> Tuple[float, Dict[str, int]]:
        """
        评估AI痕迹

        Args:
            text: 文本

        Returns:
            (分数, 详细信息)
        """
        found_words = {}
        total_count = 0

        for word in self.AI_TASTE_WORDS:
            count = text.count(word)
            if count > 0:
                found_words[word] = count
                total_count += count

        # 计算分数（100分制）
        # 每1000字1个AI痕迹扣10分
        text_length = len(text)
        expected_count = max(1, text_length / 1000)
        score = max(0, 100 - (total_count / expected_count * 10))

        self.logger.debug(f"[AI痕迹] 发现{total_count}个，得分: {score:.1f}")

        return score, found_words

    def _evaluate_coherence(self, text: str) -> Tuple[float, List[str]]:
        """
        评估连贯性

        Args:
            text: 文本

        Returns:
            (分数, 问题列表)
        """
        issues = []

        # 检查是否有明显的断点
        # 检查段落之间的过渡
        paragraphs = text.split('\n\n')
        for i, para in enumerate(paragraphs):
            if i > 0 and len(para.strip()) > 0:
                # 检查是否有过渡词
                prev_para = paragraphs[i-1]
                if not self._has_transition(prev_para, para):
                    issues.append(f"段落{i+1}与{i+2}之间缺少过渡")

        # 检查是否有明显的逻辑跳跃
        # 这里可以添加更复杂的逻辑

        # 计算分数
        score = max(0, 10 - len(issues) * 0.5)

        return score, issues

    def _evaluate_consistency(self, text: str) -> Tuple[float, List[str]]:
        """
        评估一致性

        Args:
            text: 文本

        Returns:
            (分数, 问题列表)
        """
        issues = []

        # 检查人物名字一致性
        # 这里可以添加更复杂的人名提取和比对逻辑

        # 检查时间线一致性
        # 这里可以添加时间线分析逻辑

        # 暂时返回满分
        score = 10.0

        return score, issues

    def _evaluate_readability(self, text: str) -> Tuple[float, Dict[str, float]]:
        """
        评估可读性

        Args:
            text: 文本

        Returns:
            (分数, 详细信息)
        """
        details = {}

        # 平均句长
        sentences = re.split(r'[。！？]', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        avg_sentence_length = sum(len(s) for s in sentences) / len(sentences) if sentences else 0
        details['avg_sentence_length'] = avg_sentence_length

        # 段落数
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        details['paragraph_count'] = len(paragraphs)

        # 短句比例（古龙风格特征）
        short_sentences = [s for s in sentences if len(s) < 20]
        short_sentence_ratio = len(short_sentences) / len(sentences) if sentences else 0
        details['short_sentence_ratio'] = short_sentence_ratio

        # 计算分数
        # 短句比例高（古龙风格）得分高
        score = min(10, short_sentence_ratio * 10 + 5)

        return score, details

    def _has_transition(self, prev_para: str, curr_para: str) -> bool:
        """
        检查两个段落之间是否有过渡

        Args:
            prev_para: 前一段
            curr_para: 当前段

        Returns:
            是否有过渡
        """
        # 简单检查：如果前一段结尾和后一段开头都提到相关内容
        transition_words = ["但是", "然而", "不过", "于是", "因此", "所以", "接着"]

        for word in transition_words:
            if word in curr_para[:50]:
                return True

        return False

    def _calculate_overall_score(
        self,
        ai_score: float,
        coherence_score: float,
        consistency_score: float,
        readability_score: float
    ) -> float:
        """
        计算整体评分

        Args:
            ai_score: AI痕迹得分（0-10）
            coherence_score: 连贯性得分（0-10）
            consistency_score: 一致性得分（0-10）
            readability_score: 可读性得分（0-10）

        Returns:
            整体得分（0-10）
        """
        # 权重：AI痕迹30%，连贯性30%，一致性20%，可读性20%
        weights = {
            'ai': 0.3,
            'coherence': 0.3,
            'consistency': 0.2,
            'readability': 0.2
        }

        overall = (
            ai_score * weights['ai'] +
            coherence_score * weights['coherence'] +
            consistency_score * weights['consistency'] +
            readability_score * weights['readability']
        )

        return round(overall, 1)

    def _summarize_reports(self, reports: List[Tuple[int, QualityReport]]) -> Dict[str, Any]:
        """
        汇总多个报告

        Args:
            reports: 报告列表

        Returns:
            汇总信息
        """
        total_ai_score = sum(report.ai_taste_score for _, report in reports)
        total_coherence_score = sum(report.coherence_score for _, report in reports)
        total_consistency_score = sum(report.consistency_score for _, report in reports)
        total_readability_score = sum(report.readability_score for _, report in reports)
        total_overall_score = sum(report.overall_score for _, report in reports)

        count = len(reports)

        # 统计所有AI痕迹词
        all_ai_taste = {}
        for _, report in reports:
            for word, count in report.ai_taste_details.items():
                all_ai_taste[word] = all_ai_taste.get(word, 0) + count

        return {
            'chapter_count': count,
            'avg_ai_taste_score': total_ai_score / count,
            'avg_coherence_score': total_coherence_score / count,
            'avg_consistency_score': total_consistency_score / count,
            'avg_readability_score': total_readability_score / count,
            'overall_score': total_overall_score / count,
            'total_ai_taste_words': all_ai_taste
        }


# 便捷函数
def create_quality_evaluator() -> QualityEvaluator:
    """创建质量评估器"""
    return QualityEvaluator()
