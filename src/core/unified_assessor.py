"""
统一评估系统

整合AI去味和质量评估，提供统一的评估接口

核心功能：
1. 统一评分系统（AI去味 + 质量评估）
2. AI去味等级设置（基础/强力）
3. 质量评估开关和重写阈值
4. 详细的评估报告输出

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import logging
import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum

from .style_optimizer import AITasteDetector, AITasteCorrector, StyleOptimizer
from .quality_assessor import QualityAssessor, QualityDimension

logger = logging.getLogger(__name__)


class AITasteLevel(Enum):
    """AI去味等级"""
    DISABLED = "disabled"  # 禁用
    BASIC = "basic"  # 基础去味
    STRONG = "strong"  # 强力去味


@dataclass
class AssessmentIssue:
    """评估问题"""
    category: str  # 问题类别：ai_taste / quality
    dimension: str  # 维度：forbidden_word / coherence / plot / ...
    severity: str  # 严重程度：low / medium / high
    description: str  # 问题描述
    position: Optional[int] = None  # 位置（可选）
    text: Optional[str] = None  # 问题文本（可选）
    suggestion: str = ""  # 修改建议


@dataclass
class AssessmentReport:
    """统一评估报告"""
    # 总分
    total_score: float = 0.0
    grade: str = "D"

    # AI去味评分
    ai_taste_score: float = 0.0
    ai_taste_grade: str = "D"
    ai_taste_issues: List[AssessmentIssue] = field(default_factory=list)

    # 质量评分
    quality_score: float = 0.0
    quality_grade: str = "D"
    quality_issues: List[AssessmentIssue] = field(default_factory=list)

    # 各维度评分
    dimension_scores: Dict[str, float] = field(default_factory=dict)

    # 风格一致性评分（新增维度）
    style_consistency_score: float = 0.0

    # 是否需要重写
    need_rewrite: bool = False
    rewrite_reason: str = ""

    # 优化后的内容
    optimized_content: Optional[str] = None

    # 详细报告文本
    detailed_report: str = ""

    # 改进建议（各维度低于阈值时生成）
    improvement_suggestions: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "total_score": self.total_score,
            "grade": self.grade,
            "ai_taste_score": self.ai_taste_score,
            "ai_taste_grade": self.ai_taste_grade,
            "quality_score": self.quality_score,
            "quality_grade": self.quality_grade,
            "dimension_scores": self.dimension_scores,
            "style_consistency_score": self.style_consistency_score,
            "need_rewrite": self.need_rewrite,
            "rewrite_reason": self.rewrite_reason,
            "detailed_report": self.detailed_report,
            "improvement_suggestions": self.improvement_suggestions,
            "ai_taste_issues_count": len(self.ai_taste_issues),
            "quality_issues_count": len(self.quality_issues),
        }


class UnifiedAssessor:
    """统一评估器"""
    
    def __init__(self, api_client=None):
        """
        初始化统一评估器
        
        Args:
            api_client: API客户端
        """
        self.api_client = api_client
        
        # 初始化子系统
        self.ai_detector = AITasteDetector()
        self.ai_corrector = AITasteCorrector()
        self.style_optimizer = StyleOptimizer(api_client)
        self.quality_assessor = QualityAssessor(api_client)
        
        # 评估配置
        self.config = {
            # AI去味配置
            "ai_taste_level": AITasteLevel.BASIC,  # 默认基础去味
            "ai_taste_weight": 0.4,  # AI去味权重
            
            # 质量评估配置
            "enable_quality_assessment": True,  # 启用质量评估
            "quality_weight": 0.6,  # 质量评估权重
            "quality_min_score": 75.0,  # 最低质量分
            "quality_rewrite_threshold": 68.0,  # 重写阈值

            # 总分配置
            "total_min_score": 70.0,  # 最低总分
            "total_rewrite_threshold": 60.0,  # 总分重写阈值
        }

        # 质量维度权重（四维度均分）
        self.dimension_weights = {
            "coherence": 0.25,           # 连贯性
            "literary": 0.25,            # 文学性
            "plot_advancement": 0.25,    # 情节推进
            "style_consistency": 0.25,   # 风格一致性
        }
    
    def configure(
        self,
        ai_taste_level: str = "basic",
        enable_quality_assessment: bool = True,
        quality_min_score: float = 75.0,
        quality_rewrite_threshold: float = 68.0,
        total_min_score: float = 70.0,
        total_rewrite_threshold: float = 60.0
    ):
        """
        配置评估参数
        
        Args:
            ai_taste_level: AI去味等级 (disabled/basic/strong)
            enable_quality_assessment: 是否启用质量评估
            quality_min_score: 最低质量分
            quality_rewrite_threshold: 质量重写阈值
            total_min_score: 最低总分
            total_rewrite_threshold: 总分重写阈值
        """
        # 设置AI去味等级
        if ai_taste_level == "disabled":
            self.config["ai_taste_level"] = AITasteLevel.DISABLED
        elif ai_taste_level == "basic":
            self.config["ai_taste_level"] = AITasteLevel.BASIC
        elif ai_taste_level == "strong":
            self.config["ai_taste_level"] = AITasteLevel.STRONG
        else:
            logger.warning(f"未知的AI去味等级: {ai_taste_level}，使用默认值basic")
            self.config["ai_taste_level"] = AITasteLevel.BASIC
        
        # 设置质量评估参数
        self.config["enable_quality_assessment"] = enable_quality_assessment
        self.config["quality_min_score"] = quality_min_score
        self.config["quality_rewrite_threshold"] = quality_rewrite_threshold
        self.config["total_min_score"] = total_min_score
        self.config["total_rewrite_threshold"] = total_rewrite_threshold
        
        logger.info(f"[统一评估] 配置更新: AI去味={ai_taste_level}, 质量评估={enable_quality_assessment}")
        logger.info(f"[统一评估] 阈值设置: 质量最低={quality_min_score}, 质量重写={quality_rewrite_threshold}")
        logger.info(f"[统一评估] 阈值设置: 总分最低={total_min_score}, 总分重写={total_rewrite_threshold}")
    
    def assess(
        self,
        content: str,
        chapter_num: int,
        chapter_outline: str = "",
        previous_summary: str = "",
        optimize: bool = True
    ) -> AssessmentReport:
        """
        统一评估章节
        
        Args:
            content: 章节内容
            chapter_num: 章节号
            chapter_outline: 章节大纲
            previous_summary: 前文摘要
            optimize: 是否进行优化
            
        Returns:
            评估报告
        """
        logger.info(f"[统一评估] 开始评估第{chapter_num}章")
        
        report = AssessmentReport()
        current_content = content
        
        # ========== 1. AI去味评估 ==========
        if self.config["ai_taste_level"] != AITasteLevel.DISABLED:
            ai_score, ai_grade, ai_issues = self._assess_ai_taste(
                current_content,
                chapter_num
            )
            
            report.ai_taste_score = ai_score
            report.ai_taste_grade = ai_grade
            report.ai_taste_issues = ai_issues
            
            # 如果启用优化，进行AI去味
            if optimize and self.config["ai_taste_level"] != AITasteLevel.DISABLED:
                current_content = self._optimize_ai_taste(
                    current_content,
                    chapter_num,
                    ai_score,
                    ai_issues
                )
                report.optimized_content = current_content

                # 优化后的 AI 去味分必须重新评估，
                # 否则总分和重写判断仍会沿用优化前的低分。
                optimized_ai_score, optimized_ai_grade, optimized_ai_issues = self._assess_ai_taste(
                    current_content,
                    chapter_num
                )
                report.ai_taste_score = optimized_ai_score
                report.ai_taste_grade = optimized_ai_grade
                report.ai_taste_issues = optimized_ai_issues
        
        # ========== 2. 质量评估 ==========
        if self.config["enable_quality_assessment"]:
            quality_score, quality_grade, quality_issues, dimension_scores = self._assess_quality(
                current_content,
                chapter_num,
                chapter_outline,
                previous_summary
            )
            
            report.quality_score = quality_score
            report.quality_grade = quality_grade
            report.quality_issues = quality_issues
            report.dimension_scores = dimension_scores

        # ========== 2.5 风格一致性评估 ==========
        style_consistency_score = self._assess_style_consistency(current_content)
        report.style_consistency_score = style_consistency_score
        report.dimension_scores["style_consistency"] = style_consistency_score

        # ========== 3. 计算总分 ==========
        report.total_score, report.grade = self._calculate_total_score(report)
        
        # ========== 4. 判断是否需要重写 ==========
        report.need_rewrite, report.rewrite_reason = self._check_need_rewrite(report)

        # ========== 4.5 生成改进建议 ==========
        report.improvement_suggestions = self._generate_improvement_suggestions(report)

        # ========== 5. 生成详细报告 ==========
        report.detailed_report = self._generate_detailed_report(report, chapter_num)
        
        logger.info(f"[统一评估] 第{chapter_num}章评估完成: 总分={report.total_score:.1f} ({report.grade})")
        
        return report
    
    def _assess_ai_taste(
        self,
        content: str,
        chapter_num: int
    ) -> Tuple[float, str, List[AssessmentIssue]]:
        """
        评估AI味道
        
        Args:
            content: 章节内容
            chapter_num: 章节号
            
        Returns:
            (分数, 等级, 问题列表)
        """
        logger.info(f"[AI去味评估] 开始检测第{chapter_num}章")
        
        # 检测AI味道
        style_issues = self.ai_detector.detect_ai_taste(content)
        
        # 转换为统一的问题格式
        issues = []
        for issue in style_issues:
            issues.append(AssessmentIssue(
                category="ai_taste",
                dimension=issue.issue_type,
                severity=issue.severity,
                description=f"发现AI化表达: {issue.text}",
                position=issue.position,
                text=issue.text,
                suggestion=issue.suggestion
            ))
        
        # 计算分数
        score, grade = self.ai_corrector.get_quality_score(content)
        
        # 统计问题
        high_count = sum(1 for i in issues if i.severity == "high")
        medium_count = sum(1 for i in issues if i.severity == "medium")
        low_count = sum(1 for i in issues if i.severity == "low")
        
        logger.info(f"[AI去味评估] 检测到 {len(issues)} 个问题: 高={high_count}, 中={medium_count}, 低={low_count}")
        logger.info(f"[AI去味评估] 得分: {score:.1f} ({grade})")
        
        return score, grade, issues
    
    def _optimize_ai_taste(
        self,
        content: str,
        chapter_num: int,
        current_score: float,
        issues: List[AssessmentIssue]
    ) -> str:
        """
        优化AI味道
        
        Args:
            content: 章节内容
            chapter_num: 章节号
            current_score: 当前分数
            issues: 问题列表
            
        Returns:
            优化后的内容
        """
        level = self.config["ai_taste_level"]
        
        if level == AITasteLevel.DISABLED:
            return content
        
        logger.info(f"[AI去味优化] 第{chapter_num}章，等级={level.value}, 当前分={current_score:.1f}")
        
        optimized_content = content
        
        # 基础去味：本地自动修正
        if level == AITasteLevel.BASIC:
            if current_score < 85:
                logger.info(f"[AI去味优化] 使用本地优化")
                optimized_content, _ = self.style_optimizer.optimize_chapter(
                    content,
                    auto_correct=True
                )
        
        # 强力去味：AI辅助优化
        elif level == AITasteLevel.STRONG:
            if current_score < 85:
                logger.info(f"[AI去味优化] 使用AI优化")
                try:
                    optimized_content, _ = self.style_optimizer.optimize_with_ai(content)
                except Exception as e:
                    logger.warning(f"[AI去味优化] AI优化失败: {e}，回退到本地优化")
                    optimized_content, _ = self.style_optimizer.optimize_chapter(
                        content,
                        auto_correct=True
                    )
        
        # 重新评估优化后的内容
        if optimized_content != content:
            new_score, new_grade = self.ai_corrector.get_quality_score(optimized_content)
            logger.info(f"[AI去味优化] 优化完成: {current_score:.1f} -> {new_score:.1f}")
        
        return optimized_content
    
    def _assess_quality(
        self,
        content: str,
        chapter_num: int,
        chapter_outline: str,
        previous_summary: str
    ) -> Tuple[float, str, List[AssessmentIssue], Dict[str, float]]:
        """
        评估质量
        
        Args:
            content: 章节内容
            chapter_num: 章节号
            chapter_outline: 章节大纲
            previous_summary: 前文摘要
            
        Returns:
            (分数, 等级, 问题列表, 维度分数)
        """
        logger.info(f"[质量评估] 开始评估第{chapter_num}章")
        
        # 使用质量评估器
        quality_report = self.quality_assessor.assess_chapter(
            content=content,
            chapter_num=chapter_num,
            chapter_outline=chapter_outline,
            previous_summary=previous_summary
        )
        
        # 提取分数
        total_score = quality_report.get("total_score", 0)
        
        # 提取维度分数
        dimension_scores = {}
        for dim_name, dim_data in quality_report.get("dimensions", {}).items():
            dimension_scores[dim_name] = dim_data.get("score", 0)
        
        # 提取问题
        issues = []
        for dim_name, dim_data in quality_report.get("dimensions", {}).items():
            for problem in dim_data.get("problems", []):
                issues.append(AssessmentIssue(
                    category="quality",
                    dimension=dim_name,
                    severity="medium",  # 默认中等严重程度
                    description=problem,
                    suggestion=dim_data.get("suggestions", [""])[0] if dim_data.get("suggestions") else ""
                ))
        
        # 计算等级
        if total_score >= 90:
            grade = "A"
        elif total_score >= 80:
            grade = "B"
        elif total_score >= 70:
            grade = "C"
        elif total_score >= 60:
            grade = "D"
        else:
            grade = "E"
        
        logger.info(f"[质量评估] 得分: {total_score:.1f} ({grade})")
        
        return total_score, grade, issues, dimension_scores

    def _assess_style_consistency(self, content: str) -> float:
        """
        评估风格一致性（新增维度）

        检查要点：
        - AI套话（forbidden_patterns）出现频率
        - 叙事视角是否一致（不应在第一人称和第三人称之间切换）
        - 语言风格是否与项目类型匹配

        Args:
            content: 章节内容

        Returns:
            风格一致性评分 (0-100)
        """
        logger.info("[风格一致性评估] 开始检测")

        score = 100.0

        # ----- 1. AI套话检测 -----
        forbidden_patterns = [
            "一股暖流涌上心头", "一股寒意涌上心头", "一股.*涌上心头",
            "眼中闪过一丝", "嘴角微微上扬", "心中涌起",
            "不由自主地", "情不自禁地",
            "仿佛.*一般", "宛如.*似的",
            "难以言喻的", "说不出.*的",
            "浑身一震", "瞳孔骤缩", "倒吸一口凉气",
            "迈着坚定的步伐", "头也不回地", "义无反顾地",
        ]
        ai_cliche_count = 0
        for pattern in forbidden_patterns:
            matches = re.findall(pattern, content)
            ai_cliche_count += len(matches)

        # 每5个AI套话扣10分
        ai_cliche_penalty = min(30, (ai_cliche_count // 5) * 10)
        if ai_cliche_count > 0:
            logger.info(f"[风格一致性评估] 检测到 {ai_cliche_count} 个AI套话模式，扣 {ai_cliche_penalty} 分")
        score -= ai_cliche_penalty

        # ----- 2. 叙事视角一致性检测 -----
        # 第一人称代词
        first_person_words = ["我", "我们", "我的", "我们的"]
        # 第三人称代词
        third_person_words = ["他", "她", "它", "他们", "她们", "它们", "他的", "她的", "它的"]

        first_person_count = sum(content.count(w) for w in first_person_words)
        third_person_count = sum(content.count(w) for w in third_person_words)

        total_pronouns = first_person_count + third_person_count
        if total_pronouns > 0:
            first_ratio = first_person_count / total_pronouns
            third_ratio = third_person_count / total_pronouns

            # 如果第一人称和第三人称都大量出现（各自占比超过20%），说明视角混乱
            if first_ratio > 0.2 and third_ratio > 0.2:
                pov_penalty = 20
                score -= pov_penalty
                logger.info(
                    f"[风格一致性评估] 叙事视角混乱（第一人称占比 {first_ratio:.1%}，"
                    f"第三人称占比 {third_ratio:.1%}），扣 {pov_penalty} 分"
                )

        # ----- 3. 语言风格一致性（检测是否有过于正式/口语化的跳跃） -----
        # 检测过于正式的书面表达
        formal_expressions = [
            "综上所述", "由此可见", "毋庸置疑", "不言而喻",
            "显而易见", "众所周知", "与此同时", "总而言之",
        ]
        formal_count = sum(content.count(expr) for expr in formal_expressions)

        # 检测过于口语化的网络用语
        informal_expressions = [
            "牛逼", "卧槽", "我去", "666", "牛逼哄哄", "绝绝子",
        ]
        informal_count = sum(content.count(expr) for expr in informal_expressions)

        # 同时出现正式和过于口语化的表达说明风格不一致
        if formal_count > 0 and informal_count > 0:
            style_penalty = 15
            score -= style_penalty
            logger.info(f"[风格一致性评估] 语言风格跳跃（正式表达 {formal_count} 处，"
                        f"口语化表达 {informal_count} 处），扣 {style_penalty} 分")

        # 确保分数在 0-100 范围
        score = max(0.0, min(100.0, score))

        logger.info(f"[风格一致性评估] 得分: {score:.1f}")

        return score

    def _calculate_weighted_quality(self, report: AssessmentReport) -> float:
        """
        根据四维度权重计算质量加权分

        维度映射：
        - coherence（连贯性） <- 从 quality_assessor 的 dimensions 中取 "连贯性"
        - literary（文学性）  <- 从 quality_assessor 的 dimensions 中取 "风格"
        - plot_advancement（情节推进） <- 从 quality_assessor 的 dimensions 中取 "情节"
        - style_consistency（风格一致性） <- 来自 _assess_style_consistency

        如果质量评估被禁用或维度缺失，使用 report.quality_score 作为回退。

        Args:
            report: 评估报告

        Returns:
            加权质量分 (0-100)
        """
        dim_scores = report.dimension_scores

        # 维度名映射：内部键 -> quality_assessor 可能使用的中文键
        # quality_assessor 使用 QualityDimension 枚举的 .value（中文）
        coherence = (
            dim_scores.get("coherence", 0.0)
            or dim_scores.get("连贯性", 0.0)
        )
        literary = (
            dim_scores.get("literary", 0.0)
            or dim_scores.get("风格", 0.0)
        )
        plot_advancement = (
            dim_scores.get("plot_advancement", 0.0)
            or dim_scores.get("情节", 0.0)
        )
        style_consistency = report.style_consistency_score

        # 如果所有维度分数都为 0，回退到 report.quality_score
        if coherence == 0.0 and literary == 0.0 and plot_advancement == 0.0:
            return report.quality_score

        weighted = (
            coherence * self.dimension_weights["coherence"]
            + literary * self.dimension_weights["literary"]
            + plot_advancement * self.dimension_weights["plot_advancement"]
            + style_consistency * self.dimension_weights["style_consistency"]
        )
        return weighted

    def _generate_improvement_suggestions(self, report: AssessmentReport) -> Dict[str, str]:
        """
        当某个维度低于阈值时，生成具体的改进建议

        Args:
            report: 评估报告

        Returns:
            维度 -> 改进建议 的字典
        """
        suggestions: Dict[str, str] = {}
        threshold = self.config["quality_min_score"]

        # 连贯性
        coherence_score = (
            report.dimension_scores.get("coherence", 0.0)
            or report.dimension_scores.get("连贯性", 0.0)
        )
        if coherence_score < threshold:
            suggestions["coherence"] = (
                "检查人物位置和状态的连贯性，确保前后文场景衔接自然。"
                "注意时间线的合理性，避免无过渡的场景跳跃。"
            )

        # 文学性
        literary_score = (
            report.dimension_scores.get("literary", 0.0)
            or report.dimension_scores.get("风格", 0.0)
        )
        if literary_score < threshold:
            suggestions["literary"] = (
                "增加感官描写（视觉、听觉、触觉），用具体动作替代抽象形容。"
                "避免空洞的形容词，用生动的细节和画面感来描写。"
            )

        # 情节推进
        plot_score = (
            report.dimension_scores.get("plot_advancement", 0.0)
            or report.dimension_scores.get("情节", 0.0)
        )
        if plot_score < threshold:
            suggestions["plot_advancement"] = (
                "增加角色行动和冲突，确保每章都有明确的情节推进。"
                "检查是否充分覆盖了大纲要点，避免大段静态描写拖慢节奏。"
            )

        # 风格一致性
        if report.style_consistency_score < threshold:
            suggestions["style_consistency"] = (
                "减少AI套话表达（如'眼中闪过一丝''嘴角微微上扬'等），"
                "注意保持叙事视角一致，避免在第一人称和第三人称之间切换。"
            )

        # AI味道过重
        if self.config["ai_taste_level"] != AITasteLevel.DISABLED:
            if report.ai_taste_score < 60:
                suggestions["ai_taste"] = (
                    "文本AI味道过重，存在大量AI化表达。"
                    "建议进行全面改写，去除空洞形容词、机械动作描写和总结性段落。"
                )

        if suggestions:
            logger.info(f"[改进建议] 生成了 {len(suggestions)} 条改进建议: {list(suggestions.keys())}")

        return suggestions

    def _calculate_total_score(self, report: AssessmentReport) -> Tuple[float, str]:
        """
        计算总分

        总分 = AI去味分 * ai_taste_weight + 质量加权分 * quality_weight
        其中质量加权分由四个维度按 dimension_weights 加权得出：
          coherence / literary / plot_advancement / style_consistency

        Args:
            report: 评估报告

        Returns:
            (总分, 等级)
        """
        ai_weight = self.config["ai_taste_weight"]
        quality_weight = self.config["quality_weight"]

        # 计算质量加权分（四维度）
        weighted_quality = self._calculate_weighted_quality(report)

        # 如果禁用了AI去味，只看质量分
        if self.config["ai_taste_level"] == AITasteLevel.DISABLED:
            total_score = weighted_quality
        # 如果禁用了质量评估，只看AI去味分
        elif not self.config["enable_quality_assessment"]:
            total_score = report.ai_taste_score
        # 否则按权重计算
        else:
            total_score = (
                report.ai_taste_score * ai_weight +
                weighted_quality * quality_weight
            )
        
        # 计算等级
        if total_score >= 90:
            grade = "A"
        elif total_score >= 80:
            grade = "B"
        elif total_score >= 70:
            grade = "C"
        elif total_score >= 60:
            grade = "D"
        else:
            grade = "E"
        
        return total_score, grade
    
    def _check_need_rewrite(self, report: AssessmentReport) -> Tuple[bool, str]:
        """
        检查是否需要重写
        
        Args:
            report: 评估报告
            
        Returns:
            (是否需要重写, 原因)
        """
        reasons = []
        
        # 检查总分
        if report.total_score < self.config["total_rewrite_threshold"]:
            reasons.append(f"总分过低 ({report.total_score:.1f} < {self.config['total_rewrite_threshold']})")
        
        # 检查质量分
        if self.config["enable_quality_assessment"]:
            if report.quality_score < self.config["quality_rewrite_threshold"]:
                reasons.append(f"质量分过低 ({report.quality_score:.1f} < {self.config['quality_rewrite_threshold']})")
        
        # 检查AI去味分
        if self.config["ai_taste_level"] != AITasteLevel.DISABLED:
            if report.ai_taste_score < 50:
                reasons.append(f"AI味道过重 ({report.ai_taste_score:.1f} < 50)")
        
        need_rewrite = len(reasons) > 0
        reason = "; ".join(reasons) if reasons else ""
        
        if need_rewrite:
            logger.warning(f"[重写判断] 需要重写: {reason}")
        
        return need_rewrite, reason
    
    def _generate_detailed_report(self, report: AssessmentReport, chapter_num: int) -> str:
        """
        生成详细报告
        
        Args:
            report: 评估报告
            chapter_num: 章节号
            
        Returns:
            详细报告文本
        """
        lines = []
        lines.append(f"=" * 60)
        lines.append(f"第{chapter_num}章 统一评估报告")
        lines.append(f"=" * 60)
        lines.append("")
        
        # 总分
        lines.append(f"【总分】 {report.total_score:.1f} 分 ({report.grade})")
        lines.append("")
        
        # AI去味评分
        if self.config["ai_taste_level"] != AITasteLevel.DISABLED:
            lines.append(f"【AI去味评分】 {report.ai_taste_score:.1f} 分 ({report.ai_taste_grade})")
            if report.ai_taste_issues:
                lines.append(f"  发现 {len(report.ai_taste_issues)} 个问题:")
                for i, issue in enumerate(report.ai_taste_issues[:10], 1):  # 只显示前10个
                    lines.append(f"    {i}. [{issue.severity}] {issue.description}")
                    if issue.suggestion:
                        lines.append(f"       建议: {issue.suggestion}")
            lines.append("")
        
        # 质量评分
        if self.config["enable_quality_assessment"]:
            lines.append(f"【质量评分】 {report.quality_score:.1f} 分 ({report.quality_grade})")
            if report.dimension_scores:
                lines.append(f"  各维度评分:")
                for dim, score in report.dimension_scores.items():
                    lines.append(f"    - {dim}: {score:.1f} 分")
            if report.quality_issues:
                lines.append(f"  发现 {len(report.quality_issues)} 个问题:")
                for i, issue in enumerate(report.quality_issues[:10], 1):  # 只显示前10个
                    lines.append(f"    {i}. [{issue.dimension}] {issue.description}")
                    if issue.suggestion:
                        lines.append(f"       建议: {issue.suggestion}")
            lines.append("")

        # 风格一致性评分
        lines.append(f"【风格一致性】 {report.style_consistency_score:.1f} 分")
        lines.append("")

        # 改进建议
        if report.improvement_suggestions:
            lines.append("【改进建议】")
            dim_labels = {
                "coherence": "连贯性",
                "literary": "文学性",
                "plot_advancement": "情节推进",
                "style_consistency": "风格一致性",
                "ai_taste": "AI味道",
            }
            for dim_key, suggestion in report.improvement_suggestions.items():
                label = dim_labels.get(dim_key, dim_key)
                lines.append(f"  [{label}] {suggestion}")
            lines.append("")

        # 重写建议
        if report.need_rewrite:
            lines.append(f"【重写建议】")
            lines.append(f"  ⚠️ 建议重写本章")
            lines.append(f"  原因: {report.rewrite_reason}")
        else:
            lines.append(f"【重写建议】")
            lines.append(f"  ✅ 质量合格，无需重写")
        
        lines.append("")
        lines.append(f"=" * 60)
        
        return "\n".join(lines)


def create_assessment_prompt(report: AssessmentReport) -> str:
    """
    根据评估报告创建重写提示词
    
    Args:
        report: 评估报告
        
    Returns:
        重写提示词
    """
    prompt_parts = []
    
    prompt_parts.append("【上一版问题总结】")
    prompt_parts.append("")
    
    # AI去味问题
    if report.ai_taste_issues:
        prompt_parts.append("AI味道问题:")
        for i, issue in enumerate(report.ai_taste_issues[:5], 1):
            prompt_parts.append(f"{i}. {issue.description}")
            if issue.suggestion:
                prompt_parts.append(f"   修改建议: {issue.suggestion}")
        prompt_parts.append("")
    
    # 质量问题
    if report.quality_issues:
        prompt_parts.append("质量问题:")
        for i, issue in enumerate(report.quality_issues[:5], 1):
            prompt_parts.append(f"{i}. [{issue.dimension}] {issue.description}")
            if issue.suggestion:
                prompt_parts.append(f"   修改建议: {issue.suggestion}")
        prompt_parts.append("")
    
    # 总体建议
    prompt_parts.append("【改进要求】")
    prompt_parts.append(f"上一版总分: {report.total_score:.1f} 分")
    prompt_parts.append(f"上一版问题: {report.rewrite_reason}")
    prompt_parts.append(f"风格一致性: {report.style_consistency_score:.1f} 分")
    prompt_parts.append("")

    # 添加改进建议
    if report.improvement_suggestions:
        prompt_parts.append("【具体改进建议】")
        dim_labels = {
            "coherence": "连贯性",
            "literary": "文学性",
            "plot_advancement": "情节推进",
            "style_consistency": "风格一致性",
            "ai_taste": "AI味道",
        }
        for dim_key, suggestion in report.improvement_suggestions.items():
            label = dim_labels.get(dim_key, dim_key)
            prompt_parts.append(f"- [{label}] {suggestion}")
        prompt_parts.append("")

    prompt_parts.append("请根据以上问题重新创作本章，注意:")
    prompt_parts.append("1. 避免使用AI化表达")
    prompt_parts.append("2. 提高情节连贯性")
    prompt_parts.append("3. 增强角色刻画")
    prompt_parts.append("4. 丰富细节描写")
    prompt_parts.append("5. 保持风格一致")
    prompt_parts.append("6. 保持叙事视角统一")

    return "\n".join(prompt_parts)
