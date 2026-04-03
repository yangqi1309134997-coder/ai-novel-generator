# AI 小说工坊 API 参考

更新时间：2026-04-03

## 说明

本文档描述的是当前仓库商业版 `frontend-web + backend` 的真实 HTTP API 基线。

- 后端入口：`backend.main:app`
- 默认地址：`http://127.0.0.1:8000`
- 在线文档：`http://127.0.0.1:8000/docs`

如果你要查看早期 4.5 本地写作引擎内部模块用法，请直接参考源码；不要再把它们当成当前商业版对外 API 基线。

## 基础接口

### `GET /`

- 作用：服务根信息
- 认证：无

### `GET /health`

- 作用：健康检查
- 认证：无
- 关键返回：
  - `status`
  - `version`

## 认证与平台策略

### `GET /api/auth/policy`

- 作用：读取公开平台策略
- 认证：无
- 关键返回：
  - `commercial_mode`
  - `generation_mode`
  - `allow_registration`
  - `customer_can_manage_api`
  - `customer_can_manage_prompts`

### `POST /api/auth/register`

- 作用：注册账号
- 认证：无
- 请求体：
  - `email`
  - `password`
  - `username`

### `POST /api/auth/login`

- 作用：登录
- 认证：无
- 请求体：
  - `email`
  - `password`
- 关键返回：
  - `user`
  - `access_token`
  - `refresh_token`
  - `token_type`

### `POST /api/auth/refresh`

- 作用：刷新访问令牌
- 认证：无
- 请求体：
  - `refresh_token`

### `GET /api/auth/me`

- 作用：读取当前账号信息
- 认证：`Bearer`
- 关键返回：
  - `id`
  - `email`
  - `role`
  - `role_name`
  - `permissions`
  - `subscription_tier`
  - `subscription_name`
  - `remaining_quota`
  - `can_generate`
  - `generation_message`

### `GET /api/auth/me/quota`

- 作用：读取当前配额与生成权限
- 认证：`Bearer`

### `POST /api/auth/me/api-key`

- 作用：为专业会员生成 API Key
- 认证：`Bearer`

## 管理后台 API

以下接口都要求后台权限，具体由角色矩阵决定。

### `GET /api/auth/admin/policy`

- 作用：读取完整平台策略
- 权限：`policy.view`

### `PUT /api/auth/admin/policy`

- 作用：更新平台策略
- 权限：`policy.edit`
- 请求体：
  - `allow_registration`
  - `generation_mode`
  - `member_tiers_allowed`
  - `default_subscription_tier`
  - `customer_can_manage_api`
  - `customer_can_manage_prompts`

### `GET /api/auth/admin/users`

- 作用：读取账号列表
- 权限：`users.view`

### `PUT /api/auth/admin/users/{user_id}/membership`

- 作用：调整客户会员等级和启用状态
- 权限：`users.membership.edit`
- 请求体：
  - `subscription_tier`
  - `is_active`

### `PUT /api/auth/admin/users/{user_id}/role`

- 作用：调整后台角色
- 权限：`users.role.edit`
- 请求体：
  - `role`

### `GET /api/auth/admin/roles`

- 作用：读取可用角色与权限矩阵
- 权限：`users.view`

### `GET /api/auth/admin/audit-logs`

- 作用：读取后台审计日志
- 权限：`audit.view`
- 查询参数：
  - `limit`
  - `actor_role`
  - `action_prefix`

## 接口配置与提示词

### `GET /api/providers`

- 作用：读取可选模型提供商
- 权限：`api_config.view`

### `GET /api/settings/api-config`

- 作用：读取当前接口配置
- 认证：`Bearer`
- 说明：
  - 后台角色会拿到完整脱敏配置
  - 客户只拿到是否已配置等最小运行态

### `POST /api/settings/api-config`

- 作用：保存当前接口配置
- 权限：`api_config.edit`

### `POST /api/test-api`

- 作用：测试接口连通性
- 权限：`api_config.test`

### `GET /api/prompts/templates`

- 作用：读取提示词列表
- 权限：`prompts.view`

### `GET /api/prompts/template`

- 作用：读取单个提示词模板
- 权限：`prompts.view`
- 查询参数：
  - `category`
  - `name`

### `POST /api/prompts/template`

- 作用：保存提示词模板
- 权限：`prompts.edit`

### `POST /api/prompts/reset`

- 作用：重置提示词为预设
- 权限：`prompts.edit`

## 支付、账单与会员升级

### `GET /api/billing/plans`

- 作用：读取可升级方案和支付通道
- 认证：`Bearer`
- 关键返回：
  - `plans`
  - `payment_channels`
  - `current_tier`

### `GET /api/billing/orders`

- 作用：读取升级订单
- 认证：`Bearer`
- 说明：
  - 客户只看到自己的订单
  - 后台团队可按权限看到全部订单
- 关键返回：
  - `checkout_session`

### `GET /api/billing/orders/{order_id}/checkout-session`

- 作用：读取单笔订单的统一 checkout session
- 认证：`Bearer`

### `GET /api/billing/invoices`

- 作用：读取账单
- 认证：`Bearer`

### `POST /api/billing/orders`

- 作用：创建升级订单
- 权限：`billing.create`
- 请求体：
  - `target_tier`
  - `payment_channel`
  - `note`

### `POST /api/billing/orders/{order_id}/submit-payment`

- 作用：人工转账订单提交付款备注
- 认证：`Bearer`
- 请求体：
  - `payment_reference`

### `POST /api/billing/orders/{order_id}/sandbox-pay`

- 作用：本地沙盒支付立即完成支付
- 认证：`Bearer`
- 请求体：
  - `payment_reference`

### `POST /api/billing/orders/{order_id}/approve`

- 作用：后台确认人工转账到账并升级会员
- 权限：`billing.manage`
- 请求体：
  - `payment_reference`

### `POST /api/billing/orders/{order_id}/cancel`

- 作用：取消订单
- 认证：`Bearer`
- 请求体：
  - `note`

### `POST /api/billing/webhooks/payment`

- 作用：支付回调
- 认证：签名校验，不走用户令牌
- 请求头：
  - `X-Payment-Timestamp`
  - `X-Payment-Signature`
- 请求体：
  - `event_id`
  - `event_type`
  - `order_id`
  - `status`
  - `amount`
  - `currency`
  - `payment_reference`
- 当前规则：
  - 签名算法为 `HMAC-SHA256(secret, "{timestamp}.{raw_body}")`
  - 支持时间戳有效期校验
  - 支持订单金额与币种校验
  - 支持 `event_id` 幂等处理

## 项目与任务

### `GET /api/projects`

- 作用：读取项目列表
- 认证：`Bearer`
- 说明：
  - 客户只看到自己的项目
  - 后台管理员可看到全部项目

### `POST /api/projects`

- 作用：创建项目
- 认证：`Bearer`
- 请求体：
  - `title`
  - `genre`
  - `character_setting`
  - `world_setting`
  - `plot_idea`
  - `chapter_count`

### `GET /api/projects/{project_id}`

- 作用：读取项目详情
- 认证：`Bearer`

### `POST /api/projects/{project_id}/chapters`

- 作用：向项目追加章节
- 认证：`Bearer`

### `PUT /api/projects/{project_id}/content`

- 作用：替换项目正文并重解析章节
- 认证：`Bearer`

### `DELETE /api/projects/{project_id}`

- 作用：删除项目
- 认证：`Bearer`

### `GET /api/projects/{project_id}/export`

- 作用：导出项目
- 认证：`Bearer`
- 查询参数：
  - `format`

### `GET /api/jobs`

- 作用：读取任务列表
- 认证：`Bearer`

### `GET /api/jobs/{job_id}`

- 作用：读取任务详情
- 认证：`Bearer`

### `DELETE /api/jobs/{job_id}`

- 作用：删除任务记录
- 认证：`Bearer`

### `POST /api/jobs/full-generate`

- 作用：提交整本后台生成任务
- 认证：`Bearer`

### `POST /api/jobs/{job_id}/retry`

- 作用：重试失败任务
- 认证：`Bearer`

## 生成与工具

### `POST /api/quick/outline`

- 作用：快速模式生成大纲并创建项目
- 认证：`Bearer`

### `POST /api/snowflake/architecture`

- 作用：生成雪花写作法架构
- 认证：`Bearer`

### `POST /api/snowflake/blueprint`

- 作用：生成章节蓝图
- 认证：`Bearer`

### `POST /api/parse-blueprint`

- 作用：解析章节蓝图
- 认证：无

### `POST /api/tools/polish`

- 作用：文本润色
- 认证：`Bearer`

### `POST /api/tools/polish-suggestions`

- 作用：润色并返回修改建议
- 认证：`Bearer`

### `POST /api/tools/continuation/analyze`

- 作用：续写分析
- 认证：`Bearer`

### `POST /api/tools/continuation/generate`

- 作用：续写生成
- 认证：`Bearer`

## 验证建议

商业版接口改动后，至少执行：

```bash
python scripts/commercial_api_regression.py
```

整体验收执行：

```bash
python scripts/commercial_release_check.py
```

## 相关文档

- `docs/COMMERCIAL_WEB.md`
- `docs/PROJECT_PROGRESS.md`
- `task.md`
