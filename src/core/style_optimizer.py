"""
AI味道检测与消除系统

核心功能：
1. 实时检测AI化表达
2. 自动修正AI味道
3. 风格一致性检查
4. 对话自然度优化

版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
作者：幻城
"""

import re
import logging
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class StyleIssue:
    """风格问题"""
    issue_type: str  # 问题类型
    text: str  # 问题文本
    position: int  # 位置
    severity: str  # 严重程度：low/medium/high
    suggestion: str  # 修改建议


class AITasteDetector:
    """AI味道检测器"""

    # 禁用词列表（扩展到100+）
    FORBIDDEN_WORDS = {
        # 程度副词
        "突然", "竟然", "霎时间", "猛然", "蓦然", "刹那间", "瞬间", "顷刻",
        "不由得", "禁不住", "忍不住", "情不自禁", "自然而然", "不知不觉",
        "不由自主地", "情不自禁地", "义无反顾地",
        "心中涌起", "心中升起", "心中产生", "心头涌上", "心潮澎湃",
        # 单独的"一股"
        "一股",
        # AI套路化情绪表达
        "一股暖流涌上心头", "一股寒意涌上心头",
        "眼中闪过一丝", "嘴角微微上扬", "难以言喻的",
        "说不出", "浑身一震", "瞳孔骤缩", "倒吸一口凉气",
        "迈着坚定的步伐", "头也不回地",
        # 比喻性套话
        "宛如", "犹如", "恍如", "恰似", "好似",
        # 空洞形容词
        "美丽的", "壮观的", "惊人的", "震撼的", "绝美的", "惊艳的",
        "不可思议的", "难以置信的", "无法形容的", "无与伦比的",
        # AI常用句式
        "在...的时候", "在...的背景下", "随着...的发展", "伴随着...",
        "不仅...而且...", "既...又...", "一方面...另一方面...",
        # 总结性表达
        "人生感悟", "深刻领悟", "终于明白", "恍然大悟", "醍醐灌顶",
        "这一刻", "此时此刻", "在那一刻",
        # 机械表达
        "点了点头", "摇了摇头", "叹了口气", "皱了皱眉",
    }

    # AI句式模式
    AI_PATTERNS = [
        # 过度使用排比
        r'不仅[^，]{2,10}，而且[^，]{2,10}',
        # 过度使用感叹
        r'[！！]{2,}',
        # 机械动作描写
        r'他(她)?点了点头，[^。]{5,20}。',
        r'他(她)?摇了摇头，[^。]{5,20}。',
        # 空洞描写
        r'那[个只]美丽的[^。]{5,15}',
        r'那[个只]惊人的[^。]{5,15}',
        # 总结段落
        r'这一刻，[^。]{10,30}。',
        r'终于明白[^。]{10,30}。',
        # AI套路化情绪描写
        r'一股[^，。]{2,8}涌上心头',
        r'眼中闪过一丝[^，。]{1,8}',
        r'嘴角微微上扬[^。]{0,15}',
        r'心中涌起[^，。]{2,8}',
        r'浑身一震[^。]{0,15}',
        r'瞳孔骤缩[^。]{0,15}',
        r'倒吸一口凉气',
        r'迈着坚定的步伐',
        r'头也不回地[^。]{2,15}',
        r'义无反顾地[^。]{2,15}',
        r'仿佛[^，。]{2,15}一般',
        r'宛如[^，。]{2,15}似的',
        r'难以言喻的[^，。]{2,8}',
        r'说不出[^，。]{2,8}',
        r'不由自主地[^。]{2,15}',
        r'情不自禁地[^。]{2,15}',
    ]

    # 对话自然度检查
    MECHANICAL_DIALOGUE_PATTERNS = [
        r'"[^"]{20,100}"，[他她它]说道。',
        r'"[^"]{20,100}"，[他她它]说道，"[^"]{20,100}"。',
        r'"[^"]{50,200}"',  # 过长的单句对话
    ]

    def __init__(self):
        self.issues: List[StyleIssue] = []

    def detect_ai_taste(self, text: str) -> List[StyleIssue]:
        """
        检测文本中的AI味道

        Args:
            text: 待检测文本

        Returns:
            问题列表
        """
        self.issues = []

        # 1. 检测禁用词
        self._check_forbidden_words(text)

        # 2. 检测AI句式
        self._check_ai_patterns(text)

        # 3. 检测对话自然度
        self._check_dialogue_naturalness(text)

        # 4. 检测空洞描写
        self._check_empty_descriptions(text)

        # 5. 检测结尾总结
        self._check_ending_summary(text)

        return self.issues

    def _check_forbidden_words(self, text: str) -> None:
        """检查禁用词"""
        for word in self.FORBIDDEN_WORDS:
            if word in text:
                # 找到所有出现位置
                positions = [m.start() for m in re.finditer(re.escape(word), text)]
                for pos in positions:
                    severity = "high" if word in [
                        "突然", "竟然", "心中涌起", "终于明白",
                        "一股暖流涌上心头", "一股寒意涌上心头",
                        "瞳孔骤缩", "浑身一震",
                    ] else "medium"
                    suggestion = self._get_suggestion_for_word(word)
                    self.issues.append(StyleIssue(
                        issue_type="forbidden_word",
                        text=word,
                        position=pos,
                        severity=severity,
                        suggestion=suggestion
                    ))

    def _check_ai_patterns(self, text: str) -> None:
        """检查AI句式模式"""
        for pattern in self.AI_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                self.issues.append(StyleIssue(
                    issue_type="ai_pattern",
                    text=match.group(),
                    position=match.start(),
                    severity="medium",
                    suggestion="请用更自然的表达方式"
                ))

    def _check_dialogue_naturalness(self, text: str) -> None:
        """检查对话自然度"""
        for pattern in self.MECHANICAL_DIALOGUE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                self.issues.append(StyleIssue(
                    issue_type="mechanical_dialogue",
                    text=match.group(),
                    position=match.start(),
                    severity="medium",
                    suggestion="对话要口语化，像真人说话"
                ))

    def _check_empty_descriptions(self, text: str) -> None:
        """检查空洞描写"""
        # 检测连续使用空洞形容词
        empty_adj_pattern = r'(?:美丽的|壮观的|惊人的|震撼的|绝美的){2,}'
        matches = re.finditer(empty_adj_pattern, text)
        for match in matches:
            self.issues.append(StyleIssue(
                issue_type="empty_description",
                text=match.group(),
                position=match.start(),
                severity="low",
                suggestion="请用具体细节代替空洞形容词"
            ))

    def _check_ending_summary(self, text: str) -> None:
        """检查结尾总结"""
        # 检测最后一段是否有总结性表达
        paragraphs = text.split('\n\n')
        if paragraphs:
            last_para = paragraphs[-1]
            summary_patterns = [
                r'这一刻，.*',
                r'终于明白.*',
                r'深刻领悟.*',
                r'人生感悟.*',
            ]
            for pattern in summary_patterns:
                if re.search(pattern, last_para):
                    self.issues.append(StyleIssue(
                        issue_type="ending_summary",
                        text=last_para[:50] + "...",
                        position=len(text) - len(last_para),
                        severity="high",
                        suggestion="去掉结尾的人生感悟，让情节自然结束"
                    ))
                    break

    def _get_suggestion_for_word(self, word: str) -> str:
        """获取禁用词的修改建议"""
        suggestions = {
            "突然": "去掉，直接描述动作",
            "竟然": "去掉，直接描述反应",
            "霎时间": "去掉，直接描写变化",
            "不由得": "去掉，直接描述行为",
            "心中涌起": "改为具体动作或表情",
            "终于明白": "去掉，让读者自己体会",
            "美丽的": "改为具体描写",
            "壮观的": "改为具体画面",
            "点了点头": "简化为点头，或配合具体动作",
            "摇了摇头": "简化为摇头，或配合具体动作",
            "不由自主地": "去掉或改为更具体的动作描写",
            "情不自禁地": "去掉或改为更具体的动作描写",
            "义无反顾地": "去掉，用行动本身展现决心",
            "一股暖流涌上心头": "改为具体的身体感受或动作",
            "一股寒意涌上心头": "改为具体的身体感受或动作",
            "眼中闪过一丝": "改为具体的眼神变化描写",
            "嘴角微微上扬": "改为更自然的笑容描写",
            "难以言喻的": "用具体感受替代抽象形容",
            "说不出": "用具体感受替代模糊表达",
            "浑身一震": "去掉或改为更具体的身体反应",
            "瞳孔骤缩": "去掉或改为更自然的惊讶描写",
            "倒吸一口凉气": "去掉或改为更自然的惊讶反应",
            "迈着坚定的步伐": "去掉，用具体行动展现",
            "头也不回地": "去掉或改为更自然的离开描写",
        }
        return suggestions.get(word, "请用更自然的表达")


class AITasteCorrector:
    """AI味道修正器"""

    def __init__(self):
        self.detector = AITasteDetector()

    def correct_text(self, text: str, issues: List[StyleIssue]) -> str:
        """
        修正文本中的AI味道

        Args:
            text: 原文本
            issues: 问题列表

        Returns:
            修正后的文本
        """
        corrected = text

        # 按位置倒序处理，避免位置偏移
        issues_sorted = sorted(issues, key=lambda x: x.position, reverse=True)

        for issue in issues_sorted:
            if issue.issue_type == "forbidden_word":
                corrected = self._correct_forbidden_word(corrected, issue)
            elif issue.issue_type == "ai_pattern":
                corrected = self._correct_ai_pattern(corrected, issue)
            elif issue.issue_type == "ending_summary":
                corrected = self._correct_ending_summary(corrected, issue)

        return corrected

    def _correct_forbidden_word(self, text: str, issue: StyleIssue) -> str:
        """修正禁用词"""
        word = issue.text
        position = issue.position

        # 获取上下文
        context_start = max(0, position - 20)
        context_end = min(len(text), position + len(word) + 20)
        context = text[context_start:context_end]

        # 简单的修正策略
        if word in ["突然", "竟然", "霎时间", "猛然"]:
            # 直接删除
            return text[:position] + text[position + len(word):]
        elif word in ["心中涌起", "心中升起", "心中产生"]:
            # 改为具体动作
            return text[:position] + text[position + len(word):]
        elif word in ["不由得", "禁不住", "忍不住"]:
            # 改为直接动作
            return text[:position] + text[position + len(word):]
        else:
            # 其他情况，简单删除
            return text[:position] + text[position + len(word):]

    def _correct_ai_pattern(self, text: str, issue: StyleIssue) -> str:
        """修正AI句式"""
        # 简单处理：标记为需要人工修改
        return text

    def _correct_ending_summary(self, text: str, issue: StyleIssue) -> str:
        """修正结尾总结"""
        # 删除最后一段
        paragraphs = text.split('\n\n')
        if len(paragraphs) > 1:
            return '\n\n'.join(paragraphs[:-1])
        return text

    def get_quality_score(self, text: str) -> Tuple[float, str]:
        """
        获取文本质量评分

        Args:
            text: 文本

        Returns:
            (分数, 评级) 分数0-100，评级A/B/C/D
        """
        issues = self.detector.detect_ai_taste(text)

        # 计算基础分数
        base_score = 100

        # 统计问题数量
        high_count = 0
        medium_count = 0
        low_count = 0

        # 根据问题扣分
        for issue in issues:
            if issue.severity == "high":
                base_score -= 10
                high_count += 1
            elif issue.severity == "medium":
                base_score -= 5
                medium_count += 1
            elif issue.severity == "low":
                base_score -= 2
                low_count += 1

        # 确保分数在0-100之间
        score = max(0, min(100, base_score))

        # 评级
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 60:
            grade = "C"
        else:
            grade = "D"

        # 添加调试日志
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"[AI去味评分] 检测到 {len(issues)} 个问题: 高={high_count}, 中={medium_count}, 低={low_count}")
        logger.info(f"[AI去味评分] 基础分100, 扣分={100-base_score}, 最终得分={score} ({grade})")

        return score, grade


class StyleOptimizer:
    """风格优化器（整合检测和修正）"""

    def __init__(self, api_client=None):
        self.detector = AITasteDetector()
        self.corrector = AITasteCorrector()
        self.api_client = api_client

    def optimize_chapter(
        self,
        content: str,
        auto_correct: bool = True
    ) -> Tuple[str, Dict]:
        """
        优化章节风格

        Args:
            content: 章节内容
            auto_correct: 是否自动修正

        Returns:
            (优化后的内容, 优化报告)
        """
        # 1. 检测问题
        issues = self.detector.detect_ai_taste(content)

        # 2. 获取质量评分
        score, grade = self.corrector.get_quality_score(content)

        # 3. 自动修正
        if auto_correct and issues:
            corrected_content = self.corrector.correct_text(content, issues)
        else:
            corrected_content = content

        # 4. 构建报告
        report = {
            "original_score": score,
            "original_grade": grade,
            "issues_count": len(issues),
            "issues_by_type": self._group_issues_by_type(issues),
            "issues_by_severity": self._group_issues_by_severity(issues),
            "auto_corrected": auto_correct,
        }

        if auto_correct:
            # 重新评分
            new_score, new_grade = self.corrector.get_quality_score(corrected_content)
            report["optimized_score"] = new_score
            report["optimized_grade"] = new_grade
            report["score_improvement"] = new_score - score
        else:
            report["optimized_content"] = None

        return corrected_content, report

    def _group_issues_by_type(self, issues: List[StyleIssue]) -> Dict[str, int]:
        """按类型分组问题"""
        groups = {}
        for issue in issues:
            groups[issue.issue_type] = groups.get(issue.issue_type, 0) + 1
        return groups

    def _group_issues_by_severity(self, issues: List[StyleIssue]) -> Dict[str, int]:
        """按严重程度分组问题"""
        groups = {}
        for issue in issues:
            groups[issue.severity] = groups.get(issue.severity, 0) + 1
        return groups

    def optimize_with_ai(
        self,
        content: str,
        max_retries: int = 2
    ) -> Tuple[str, Dict]:
        """
        使用AI辅助优化

        Args:
            content: 章节内容
            max_retries: 最大重试次数

        Returns:
            (优化后的内容, 优化报告)
        """
        if not self.api_client:
            logger.warning("API客户端未初始化，使用本地优化")
            return self.optimize_chapter(content, auto_correct=True)

        # 1. 本地检测
        issues = self.detector.detect_ai_taste(content)
        score, grade = self.corrector.get_quality_score(content)

        # 如果质量已经很好，直接返回
        if score >= 85:
            return content, {
                "original_score": score,
                "original_grade": grade,
                "optimized_score": score,
                "optimized_grade": grade,
                "score_improvement": 0,
                "issues_count": len(issues),
                "method": "local_only"
            }

        # 2. 构建AI优化提示词
        prompt = self._build_optimization_prompt(content, issues)

        # 3. 调用AI优化
        for retry in range(max_retries):
            try:
                response = self.api_client.generate([
                    {"role": "system", "content": "你是一位专业的小说编辑，擅长去除AI味道，让文字更像真人写作。"},
                    {"role": "user", "content": prompt}
                ], temperature=0.7)

                if response:
                    # 4. 验证优化结果
                    new_score, new_grade = self.corrector.get_quality_score(response)
                    improvement = new_score - score

                    report = {
                        "original_score": score,
                        "original_grade": grade,
                        "optimized_score": new_score,
                        "optimized_grade": new_grade,
                        "score_improvement": improvement,
                        "issues_count": len(issues),
                        "method": "ai_assisted",
                        "retry_count": retry + 1
                    }

                    return response, report

            except Exception as e:
                logger.warning(f"AI优化失败 (第{retry + 1}次尝试): {e}")
                continue

        # 如果AI优化失败，回退到本地优化
        logger.warning("AI优化失败，使用本地优化")
        return self.optimize_chapter(content, auto_correct=True)

    def _build_optimization_prompt(self, content: str, issues: List[StyleIssue]) -> str:
        """构建AI优化提示词"""
        # 提取主要问题
        main_issues = [issue for issue in issues if issue.severity in ["high", "medium"]][:5]

        issues_desc = "\n".join([
            f"- {issue.text}: {issue.suggestion}"
            for issue in main_issues
        ])

        prompt = f"""请优化以下小说章节，去除AI味道，让文字更自然。

【主要问题】
{issues_desc}

【优化要求】
1. 去掉AI化的表达（突然、竟然、心中涌起等）
2. 对话要口语化，像真人说话
3. 描写要具体，用细节代替空洞形容词
4. 去掉结尾的人生感悟
5. 保持原意和情节不变
6. 字数保持相近

【原文】
{content}

【优化后的文本】"""

        return prompt


# 便捷函数
def detect_and_optimize(
    content: str,
    api_client=None,
    use_ai: bool = False
) -> Tuple[str, Dict]:
    """
    检测并优化文本风格

    Args:
        content: 文本内容
        api_client: API客户端（可选）
        use_ai: 是否使用AI辅助优化

    Returns:
        (优化后的文本, 优化报告)
    """
    optimizer = StyleOptimizer(api_client)

    if use_ai and api_client:
        return optimizer.optimize_with_ai(content)
    else:
        return optimizer.optimize_chapter(content, auto_correct=True)


def get_style_score(content: str) -> Tuple[float, str]:
    """
    获取文本风格评分

    Args:
        content: 文本内容

    Returns:
        (分数, 评级)
    """
    corrector = AITasteCorrector()
    return corrector.get_quality_score(content)
