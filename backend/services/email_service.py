"""
邮件发送服务

从 AdminConfig 表读取 SMTP 配置，使用 aiosmtplib 异步发送邮件。
支持：验证码邮件、生成完成通知、会员到期提醒。

版权所有 (c) 2026 新疆幻城网安科技有限责任公司 (幻城科技)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.core.database import SessionLocal
from backend.models.orm_models import AdminConfig, EmailLog

logger = logging.getLogger(__name__)


class EmailService:
    """异步邮件发送服务。"""

    def __init__(self) -> None:
        self._config: Dict[str, Any] = self._get_smtp_config()

    # ------------------------------------------------------------------
    # SMTP 配置
    # ------------------------------------------------------------------

    def _get_smtp_config(self) -> Dict[str, Any]:
        """从 AdminConfig 表获取 SMTP 配置，未配置时提供默认值。"""
        defaults: Dict[str, Any] = {
            "host": "",
            "port": 465,
            "username": "",
            "password": "",
            "sender": "noreply@example.com",
            "use_tls": True,
        }

        db: Optional[Session] = None
        try:
            db = SessionLocal()
            keys = [
                "smtp_host",
                "smtp_port",
                "smtp_username",
                "smtp_password",
                "smtp_sender",
                "smtp_use_tls",
            ]
            rows = (
                db.query(AdminConfig)
                .filter(AdminConfig.config_key.in_(keys))
                .all()
            )
            config_map = {row.config_key: row for row in rows}

            def _val(key: str) -> Optional[str]:
                row = config_map.get(key)
                return row.config_value if row else None

            host = _val("smtp_host")
            if host:
                defaults["host"] = host

            port_str = _val("smtp_port")
            if port_str:
                try:
                    defaults["port"] = int(port_str)
                except (ValueError, TypeError):
                    pass

            username = _val("smtp_username")
            if username:
                defaults["username"] = username

            password = _val("smtp_password")
            if password:
                defaults["password"] = password

            sender = _val("smtp_sender")
            if sender:
                defaults["sender"] = sender

            use_tls_str = _val("smtp_use_tls")
            if use_tls_str is not None:
                defaults["use_tls"] = use_tls_str.lower() in ("true", "1", "yes")
        except Exception as exc:
            logger.warning("读取 SMTP 配置失败，使用默认值: %s", exc)
        finally:
            if db:
                db.close()

        return defaults

    def reload_config(self) -> None:
        """重新加载 SMTP 配置（管理员修改配置后可调用）。"""
        self._config = self._get_smtp_config()

    # ------------------------------------------------------------------
    # 邮件构建
    # ------------------------------------------------------------------

    def _build_smtp_message(
        self, to: str, subject: str, html_body: str
    ) -> MIMEMultipart:
        """构建 MIME 邮件消息。"""
        msg = MIMEMultipart("alternative")
        msg["From"] = self._config["sender"]
        msg["To"] = to
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html", "utf-8"))
        return msg

    # ------------------------------------------------------------------
    # 内部发送
    # ------------------------------------------------------------------

    async def _send(self, to: str, subject: str, html_body: str) -> bool:
        """底层发送方法，使用 aiosmtplib。

        如果 SMTP 未配置（host 为空），则打印日志并返回 True（开发模式容错）。
        """
        if not self._config.get("host"):
            logger.info(
                "[DEV] SMTP 未配置，跳过发送邮件 -> %s, 主题: %s", to, subject
            )
            logger.debug("[DEV] 邮件内容:\n%s", html_body[:500])
            return True

        try:
            import aiosmtplib

            msg = self._build_smtp_message(to, subject, html_body)

            if self._config.get("use_tls", True):
                await aiosmtplib.send(
                    msg,
                    hostname=self._config["host"],
                    port=self._config["port"],
                    username=self._config.get("username"),
                    password=self._config.get("password"),
                    use_tls=True,
                )
            else:
                await aiosmtplib.send(
                    msg,
                    hostname=self._config["host"],
                    port=self._config["port"],
                    username=self._config.get("username"),
                    password=self._config.get("password"),
                    start_tls=True,
                )

            logger.info("邮件已发送 -> %s, 主题: %s", to, subject)
            return True
        except Exception as exc:
            logger.error("发送邮件失败 -> %s: %s", to, exc)
            return False

    # ------------------------------------------------------------------
    # 邮件日志
    # ------------------------------------------------------------------

    def _log_email(
        self,
        to_email: str,
        email_type: str,
        status: str,
        content_summary: Optional[str] = None,
    ) -> None:
        """将邮件发送记录写入 EmailLog 表。"""
        db: Optional[Session] = None
        try:
            db = SessionLocal()
            log_entry = EmailLog(
                to_email=to_email,
                email_type=email_type,
                status=status,
                content_summary=content_summary,
                created_at=datetime.now(timezone.utc),
            )
            db.add(log_entry)
            db.commit()
        except Exception as exc:
            logger.warning("写入邮件日志失败: %s", exc)
            if db:
                db.rollback()
        finally:
            if db:
                db.close()

    # ------------------------------------------------------------------
    # 公开接口
    # ------------------------------------------------------------------

    async def send_verification_code(self, to_email: str, code: str) -> bool:
        """发送验证码邮件。

        Args:
            to_email: 收件人邮箱。
            code: 验证码字符串。

        Returns:
            发送是否成功。
        """
        html_body = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f4f6f9; font-family:'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f6f9; padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="520" cellspacing="0" cellpadding="0" style="background-color:#ffffff; border-radius:12px; box-shadow:0 4px 24px rgba(0,0,0,0.08); overflow:hidden;">
          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding:32px 40px; text-align:center;">
              <h1 style="margin:0; color:#ffffff; font-size:22px; font-weight:600; letter-spacing:1px;">
                AI Novel Generator
              </h1>
              <p style="margin:8px 0 0; color:rgba(255,255,255,0.85); font-size:14px;">
                邮箱验证码
              </p>
            </td>
          </tr>
          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 20px;">
              <p style="margin:0 0 8px; color:#333333; font-size:16px; line-height:1.6;">
                您好，
              </p>
              <p style="margin:0 0 24px; color:#555555; font-size:14px; line-height:1.6;">
                您正在进行身份验证，请使用以下验证码完成操作。验证码有效期为 5 分钟。
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center" style="padding:20px 0;">
                    <div style="display:inline-block; background:linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%); border:2px dashed #667eea; border-radius:8px; padding:16px 48px;">
                      <span style="font-size:36px; font-weight:700; color:#667eea; letter-spacing:8px; font-family:'Courier New',monospace;">
                        {code}
                      </span>
                    </div>
                  </td>
                </tr>
              </table>
              <p style="margin:24px 0 0; color:#999999; font-size:12px; line-height:1.6;">
                如果这不是您的操作，请忽略此邮件。
              </p>
            </td>
          </tr>
          <!-- Footer -->
          <tr>
            <td style="padding:20px 40px 32px; border-top:1px solid #eeeeee;">
              <p style="margin:0; color:#aaaaaa; font-size:12px; text-align:center; line-height:1.5;">
                此邮件由系统自动发送，请勿直接回复。<br>
                &copy; 2026 AI Novel Generator &mdash; 新疆幻城网安科技有限责任公司
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        success = await self._send(to_email, "【AI Novel Generator】您的验证码", html_body)
        self._log_email(
            to_email=to_email,
            email_type="verification_code",
            status="sent" if success else "failed",
            content_summary=f"验证码: {code[:2]}****",
        )
        return success

    async def send_generation_complete(
        self, to_email: str, title: str, project_id: str
    ) -> bool:
        """发送小说生成完成通知邮件。"""
        html_body = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f4f6f9; font-family:'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f6f9; padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="520" cellspacing="0" cellpadding="0" style="background-color:#ffffff; border-radius:12px; box-shadow:0 4px 24px rgba(0,0,0,0.08); overflow:hidden;">
          <tr>
            <td style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%); padding:32px 40px; text-align:center;">
              <h1 style="margin:0; color:#ffffff; font-size:22px; font-weight:600;">
                &#10004; 生成完成
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:40px;">
              <p style="margin:0 0 16px; color:#333333; font-size:16px; line-height:1.6;">
                您的小说已经生成完毕！
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f9fafb; border-radius:8px; padding:16px 20px;">
                <tr>
                  <td style="padding:8px 0;">
                    <span style="color:#888888; font-size:13px;">作品名称</span><br>
                    <span style="color:#333333; font-size:15px; font-weight:600;">{title}</span>
                  </td>
                </tr>
                <tr>
                  <td style="padding:8px 0; border-top:1px solid #eeeeee;">
                    <span style="color:#888888; font-size:13px;">项目编号</span><br>
                    <span style="color:#666666; font-size:14px; font-family:monospace;">{project_id}</span>
                  </td>
                </tr>
              </table>
              <p style="margin:24px 0 0; color:#555555; font-size:14px; line-height:1.6;">
                请登录平台查看并下载您的作品。
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 40px 32px; border-top:1px solid #eeeeee;">
              <p style="margin:0; color:#aaaaaa; font-size:12px; text-align:center;">
                此邮件由系统自动发送，请勿直接回复。<br>
                &copy; 2026 AI Novel Generator &mdash; 新疆幻城网安科技有限责任公司
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        success = await self._send(to_email, f"【AI Novel Generator】小说生成完成 - {title}", html_body)
        self._log_email(
            to_email=to_email,
            email_type="generation_complete",
            status="sent" if success else "failed",
            content_summary=f"项目: {title} ({project_id})",
        )
        return success

    async def send_membership_reminder(
        self, to_email: str, days_left: int
    ) -> bool:
        """发送会员到期提醒邮件。"""
        urgency = "明天" if days_left <= 1 else f"{days_left} 天后"
        color = "#e74c3c" if days_left <= 3 else "#f39c12" if days_left <= 7 else "#3498db"
        html_body = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin:0; padding:0; background-color:#f4f6f9; font-family:'Helvetica Neue',Arial,'PingFang SC','Microsoft YaHei',sans-serif;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color:#f4f6f9; padding:40px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="520" cellspacing="0" cellpadding="0" style="background-color:#ffffff; border-radius:12px; box-shadow:0 4px 24px rgba(0,0,0,0.08); overflow:hidden;">
          <tr>
            <td style="background: linear-gradient(135deg, {color} 0%, #2c3e50 100%); padding:32px 40px; text-align:center;">
              <h1 style="margin:0; color:#ffffff; font-size:22px; font-weight:600;">
                会员即将到期
              </h1>
            </td>
          </tr>
          <tr>
            <td style="padding:40px;">
              <p style="margin:0 0 16px; color:#333333; font-size:16px; line-height:1.6;">
                您的会员资格将在 <strong style="color:{color};">{urgency}</strong> 到期。
              </p>
              <p style="margin:0 0 24px; color:#555555; font-size:14px; line-height:1.6;">
                为避免影响您的正常使用，建议您尽快续费。续费后可继续享受不限量生成、优先处理等专属权益。
              </p>
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                  <td align="center">
                    <div style="display:inline-block; background:{color}; color:#ffffff; font-size:16px; font-weight:600; padding:12px 40px; border-radius:6px; text-decoration:none;">
                      立即续费
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
          <tr>
            <td style="padding:20px 40px 32px; border-top:1px solid #eeeeee;">
              <p style="margin:0; color:#aaaaaa; font-size:12px; text-align:center;">
                此邮件由系统自动发送，请勿直接回复。<br>
                &copy; 2026 AI Novel Generator &mdash; 新疆幻城网安科技有限责任公司
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""
        success = await self._send(
            to_email,
            f"【AI Novel Generator】会员将在{urgency}到期",
            html_body,
        )
        self._log_email(
            to_email=to_email,
            email_type="membership_reminder",
            status="sent" if success else "failed",
            content_summary=f"剩余 {days_left} 天",
        )
        return success


# 全局单例
email_service = EmailService()
