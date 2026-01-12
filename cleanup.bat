@echo off
echo 正在清理AI小说生成工具项目...
echo ========================================
echo 版权所有 © 2026 新疆幻城网安科技有限责任公司 (幻城科技)
echo 作者：幻城
echo ========================================

echo 清理缓存目录...
if exist cache rmdir /s /q cache

echo 清理导出文件目录...
if exist exports rmdir /s /q exports

echo 清理日志文件目录...
if exist logs rmdir /s /q logs

echo 清理项目数据目录...
if exist projects rmdir /s /q projects

echo 清理配置备份目录...
if exist config\backups rmdir /s /q config\backups

echo 清理临时配置文件...
if exist config\novel_tool_config.json del /f /q config\novel_tool_config.json

echo 清理开发文档文件...
del /f /q *.md
del /f /q *.txt
del /f /q API_KEY_SETUP.md
del /f /q BUG_ANALYSIS_AND_FIX.md
del /f /q BUG_FIX_REPORT.md
del /f /q CHANGELOG.md
del /f /q COMPLETION_REPORT.md
del /f /q DELIVERY_CHECKLIST.md
del /f /q EXPORT_FEATURE_GUIDE.md
del /f /q EXPORT_FEATURE_PLAN.md
del /f /q EXPORT_IMPLEMENTATION_REPORT.md
del /f /q EXPORT_QUICK_START.md
del /f /q EXPORT_READY.md
del /f /q FINAL_FIX_REPORT.md
del /f /q FIX_COMPLETION_REPORT.md
del /f /q FIX_VERIFICATION_GUIDE.md
del /f /q FIXES_SUMMARY.md
del /f /q HOW_TO_EXPORT.md
del /f /q IMPLEMENTATION_SUMMARY.txt
del /f /q NOVEL_SAVE_FIX.md
del /f /q OPTIMIZATION_SUMMARY.txt
del /f /q PRODUCTION_CHECKLIST.md
del /f /q PRODUCTION_READY.md
del /f /q QUICK_FIX_GUIDE.md
del /f /q QUICK_FIX_REFERENCE.md
del /f /q QUICK_START_WEB_CONFIG.md
del /f /q QUICK_START.md
del /f /q QUICKSTART.md
del /f /q README_UPDATES.md
del /f /q SOLUTION_SUMMARY.md
del /f /q UPGRADE_GUIDE.md
del /f /q VERIFICATION_REPORT.md
del /f /q WEB_CONFIG_GUIDE.md
del /f /q WEB_CONFIG_IMPLEMENTATION.md

echo 清理临时运行文件...
if exist run.bat del /f /q run.bat
if exist run.sh del /f /q run.sh

echo 创建必要的空目录...
mkdir cache 2>nul
mkdir exports 2>nul
mkdir logs 2>nul
mkdir projects 2>nul
mkdir config\backups 2>nul

echo 创建默认配置文件...
echo {} > cache/response_cache.json
echo {"version": "3.0", "created": "2026-01-12"} > config/novel_tool_config.json

echo ========================================
echo 清理完成！
echo 项目已恢复到出厂默认状态。
echo ========================================

pause