# AI 小说工坊 更新日志

---

## v6.0.0 (2026-04-03)

### 安全加固

- **统一 JWT 密钥管理**：后端 `core/security.py` 与 `auth_service.py` 共用同一持久化密钥，重启不再导致已颁发 Token 失效
- **密码哈希兼容**：`CryptContext` 同时支持 `pbkdf2_sha256` 和 `bcrypt`，旧密码无需重置
- **CORS 收紧**：`allow_methods` 和 `allow_headers` 从通配改为白名单
- **Webhook 密钥**：支付回调签名密钥默认为空，部署时必须显式配置
- **输入边界校验**：所有用户输入添加 `ge/le/max_length` 约束（章节数 1-500、文本 50000 字符上限等）

### 性能优化

- **数据库索引**：`GenerationJob.status`、`Order.status`、`CardCode.status` 三张表的状态字段添加索引
- **异步 SQLite**：`state_store` 新增 `async_get_json` / `async_set_json`，避免阻塞事件循环

### 代码质量

- **FastAPI lifespan**：从已废弃的 `@app.on_event("startup")` 迁移到 `lifespan` context manager
- **前端工具函数**：提取 `formatDate`、`displayTitle` 到 `utils/format.js`，12+ 视图共享
- **Gradio 去重**：提取 `read_uploaded_file` 到 `file_utils.py`，polish/rewrite 共用

### Bug 修复

- **提示词管理分类不匹配**：前端 Tab 分类键与后端实际分类对齐，所有提示词模板可正常编辑
- **NaiveUI 选择器**：确认 `.n-tabs-tab`、`.n-base-selection`、`.n-base-select-option` 为正确 CSS 类名

### 测试

- 深度浏览器测试通过率 **98.0%**（48 PASS / 0 FAIL / 1 WARN）
- Gradio 深度测试通过率 **86.7%**（26 PASS / 0 FAIL）
- API 回归测试通过率 **92.3%**（60 PASS / 0 FAIL）

---

## v5.0.0 (2026-03-28)

### 商业版主线完成

- 仓库正式拆分为本地版（Gradio）和商业版（Vue 3 + FastAPI）
- 登录 / 注册、管理后台、客户账号中心、项目 owner 隔离
- 后台团队角色分层（管理员 / 运营 / 客服）
- 后台审计日志
- 升级订单 / 账单 / 会员升级闭环
- 支付回调签名校验与幂等处理
- 统一支付网关适配层（sandbox_gateway / manual_transfer）
- SQLite 持久化层
- 商业版 API 回归脚本、浏览器回归脚本、一键验收

---

## v4.5.0 (2026-03-08)

- 全新 Gradio UI 界面设计
- 文档系统完善，版本号统一到 4.5

---

## v4.0.0 (2026-02-07)

- 智能连贯性系统（角色跟踪、剧情管理、世界观数据库、分层摘要）
- 统一评估系统（AI 去味、质量评估、评估报告）
- 22+ 主流 API 提供商支持
- 提示词管理系统（可视化编辑、模板变量、版本管理、导入导出）
- 完整项目管理（暂停/恢复、实时进度、自动缓存）

---

## v3.0.0 (2025-12-15)

- 基础小说生成功能
- OpenAI / Claude API 支持
- WebUI 界面（Gradio）

---

*版权所有 &copy; 2026 新疆幻城网安科技有限责任公司（幻城科技）*
