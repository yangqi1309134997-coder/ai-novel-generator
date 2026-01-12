#!/bin/bash

echo "正在清理AI小说生成工具项目..."
echo "========================================"
echo "版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)"
echo "作者：幻城"
echo "========================================"

# 清理缓存目录
if [ -d "cache" ]; then
    rm -rf cache
    echo "清理缓存目录完成"
fi

# 清理导出文件目录
if [ -d "exports" ]; then
    rm -rf exports
    echo "清理导出文件目录完成"
fi

# 清理日志文件目录
if [ -d "logs" ]; then
    rm -rf logs
    echo "清理日志文件目录完成"
fi

# 清理项目数据目录
if [ -d "projects" ]; then
    rm -rf projects
    echo "清理项目数据目录完成"
fi

# 清理配置备份目录
if [ -d "config/backups" ]; then
    rm -rf config/backups
    echo "清理配置备份目录完成"
fi

# 清理临时配置文件
if [ -f "config/novel_tool_config.json" ]; then
    rm -f config/novel_tool_config.json
    echo "清理临时配置文件完成"
fi

# 清理开发文档文件
rm -f *.md
rm -f *.txt
rm -f API_KEY_SETUP.md
rm -f BUG_ANALYSIS_AND_FIX.md
rm -f BUG_FIX_REPORT.md
rm -f CHANGELOG.md
rm -f COMPLETION_REPORT.md
rm -f DELIVERY_CHECKLIST.md
rm -f EXPORT_FEATURE_GUIDE.md
rm -f EXPORT_FEATURE_PLAN.md
rm -f EXPORT_IMPLEMENTATION_REPORT.md
rm -f EXPORT_QUICK_START.md
rm -f EXPORT_READY.md
rm -f FINAL_FIX_REPORT.md
rm -f FIX_COMPLETION_REPORT.md
rm -f FIX_VERIFICATION_GUIDE.md
rm -f FIXES_SUMMARY.md
rm -f HOW_TO_EXPORT.md
rm -f IMPLEMENTATION_SUMMARY.txt
rm -f NOVEL_SAVE_FIX.md
rm -f OPTIMIZATION_SUMMARY.txt
rm -f PRODUCTION_CHECKLIST.md
rm -f PRODUCTION_READY.md
rm -f QUICK_FIX_GUIDE.md
rm -f QUICK_FIX_REFERENCE.md
rm -f QUICK_START_WEB_CONFIG.md
rm -f QUICK_START.md
rm -f QUICKSTART.md
rm -f README_UPDATES.md
rm -f SOLUTION_SUMMARY.md
rm -f UPGRADE_GUIDE.md
rm -f VERIFICATION_REPORT.md
rm -f WEB_CONFIG_GUIDE.md
rm -f WEB_CONFIG_IMPLEMENTATION.md

# 清理临时运行文件
rm -f run.bat
rm -f run.sh

# 创建必要的空目录
mkdir -p cache
mkdir -p exports
mkdir -p logs
mkdir -p projects
mkdir -p config/backups

# 创建默认配置文件
echo "{}" > cache/response_cache.json
echo '{"version": "3.0", "created": "2026-01-12"}' > config/novel_tool_config.json

echo "========================================"
echo "清理完成！"
echo "项目已恢复到出厂默认状态。"
echo "========================================"