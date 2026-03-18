# backend/app/services/webhook/handler.py
import hashlib
import hmac
import json
import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.webhook import Webhook, WebhookDelivery


class WebhookHandler:
    """Webhook事件处理器"""

    def __init__(self, db: Session, timeout: int = 10):
        """
        初始化Webhook处理器

        Args:
            db: 数据库会话
            timeout: HTTP请求超时时间（秒）
        """
        self.db = db
        self.timeout = timeout

    def trigger_event(
        self,
        event_type: str,
        payload: Dict[str, Any]
    ) -> List[WebhookDelivery]:
        """
        触发Webhook事件

        Args:
            event_type: 事件类型
            payload: 事件负载

        Returns:
            创建的投递记录列表
        """
        deliveries = []

        # 查找订阅该事件的所有启用的Webhooks
        webhooks = self.db.query(Webhook).filter(
            Webhook.enabled == True
        ).all()

        for webhook in webhooks:
            # 检查Webhook是否订阅该事件
            if event_type not in webhook.events:
                continue

            # 创建投递记录
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                status="pending"
            )
            self.db.add(delivery)

            # 尝试发送
            self._send_webhook(webhook, delivery)

            deliveries.append(delivery)

        self.db.commit()
        return deliveries

    def _send_webhook(self, webhook: Webhook, delivery: WebhookDelivery) -> bool:
        """
        发送Webhook请求

        Args:
            webhook: Webhook配置
            delivery: 投递记录

        Returns:
            是否发送成功
        """
        # Initialize attempt_count if None
        if delivery.attempt_count is None:
            delivery.attempt_count = 0
        delivery.attempt_count += 1

        try:
            # 准备请求
            payload_json = json.dumps(delivery.payload)

            # 生成签名
            signature = self._generate_signature(payload_json, webhook.secret)

            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": delivery.event_type,
                "X-Webhook-Signature": signature,
            }

            # 发送请求
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    webhook.url,
                    content=payload_json,
                    headers=headers
                )

                delivery.response_code = response.status_code
                delivery.response_body = response.text[:1000]  # 限制响应体长度

                if 200 <= response.status_code < 300:
                    delivery.status = "success"
                    delivery.delivered_at = datetime.utcnow()
                    return True
                else:
                    delivery.status = "failed"
                    delivery.error_message = f"HTTP {response.status_code}"
                    self._schedule_retry(delivery)
                    return False

        except httpx.TimeoutException:
            delivery.status = "failed"
            delivery.error_message = "Request timeout"
            self._schedule_retry(delivery)
            return False

        except Exception as e:
            delivery.status = "failed"
            delivery.error_message = str(e)[:500]
            self._schedule_retry(delivery)
            return False

    def _generate_signature(self, payload: str, secret: Optional[str]) -> str:
        """
        生成Webhook签名

        Args:
            payload: 请求体
            secret: 密钥

        Returns:
            签名字符串
        """
        if not secret:
            return ""

        signature = hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"sha256={signature}"

    def _schedule_retry(self, delivery: WebhookDelivery) -> None:
        """
        安排重试

        Args:
            delivery: 投递记录
        """
        if delivery.attempt_count < delivery.max_attempts:
            delivery.status = "retrying"
            # 指数退避：1分钟，5分钟，15分钟
            retry_delays = [1, 5, 15]
            delay_minutes = retry_delays[min(delivery.attempt_count - 1, len(retry_delays) - 1)]
            delivery.next_retry_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

    def can_retry(self, delivery: WebhookDelivery) -> bool:
        """
        检查是否可以重试

        Args:
            delivery: 投递记录

        Returns:
            是否可以重试
        """
        attempt_count = delivery.attempt_count or 0
        max_attempts = delivery.max_attempts or 3
        return (
            delivery.status in ["failed", "retrying"] and
            attempt_count < max_attempts
        )

    def get_pending_deliveries(self) -> List[WebhookDelivery]:
        """
        获取待处理的投递

        Returns:
            待处理的投递列表
        """
        now = datetime.utcnow()

        return self.db.query(WebhookDelivery).filter(
            WebhookDelivery.status.in_(["pending", "retrying"]),
            (WebhookDelivery.next_retry_at == None) | (WebhookDelivery.next_retry_at <= now)
        ).all()

    def process_pending_deliveries(self) -> int:
        """
        处理所有待处理的投递

        Returns:
            处理的投递数量
        """
        pending = self.get_pending_deliveries()
        processed = 0

        for delivery in pending:
            webhook = self.db.query(Webhook).filter(
                Webhook.id == delivery.webhook_id
            ).first()

            if webhook and webhook.enabled:
                self._send_webhook(webhook, delivery)
                processed += 1

        self.db.commit()
        return processed

    def retry_delivery(self, delivery_id: str) -> Optional[WebhookDelivery]:
        """
        手动重试投递

        Args:
            delivery_id: 投递ID

        Returns:
            更新后的投递记录
        """
        delivery = self.db.query(WebhookDelivery).filter(
            WebhookDelivery.id == delivery_id
        ).first()

        if not delivery:
            return None

        webhook = self.db.query(Webhook).filter(
            Webhook.id == delivery.webhook_id
        ).first()

        if not webhook:
            return None

        # 重置状态
        delivery.status = "pending"
        delivery.next_retry_at = None

        self._send_webhook(webhook, delivery)
        self.db.commit()

        return delivery
