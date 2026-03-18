# backend/tests/test_webhooks.py
import pytest
from sqlalchemy.exc import IntegrityError
from app.models.webhook import Webhook, WebhookDelivery


class TestWebhookModel:
    """测试Webhook模型"""

    def test_webhook_creation(self, test_db):
        """测试Webhook创建"""
        from app.models.webhook import Webhook

        webhook = Webhook(
            name="Project Completion",
            url="https://example.com/webhook",
            events=["project.completed", "project.failed"],
            secret="webhook_secret_key",
            enabled=True
        )
        test_db.add(webhook)
        test_db.commit()

        assert webhook.id is not None
        assert webhook.name == "Project Completion"
        assert len(webhook.events) == 2
        assert webhook.enabled is True

    def test_webhook_url_required(self, test_db):
        """测试Webhook URL必填"""
        from app.models.webhook import Webhook

        webhook = Webhook(name="Test Webhook", events=["test.event"])
        test_db.add(webhook)

        with pytest.raises(IntegrityError):
            test_db.commit()

    def test_webhook_delivery_creation(self, test_db):
        """测试Webhook投递记录"""
        from app.models.webhook import Webhook, WebhookDelivery

        webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["test.event"]
        )
        test_db.add(webhook)
        test_db.commit()

        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test.event",
            payload={"test": "data"},
            status="pending"
        )
        test_db.add(delivery)
        test_db.commit()

        assert delivery.id is not None
        assert delivery.webhook_id == webhook.id
        assert delivery.status == "pending"

    def test_webhook_delivery_status_update(self, test_db):
        """测试投递状态更新"""
        from app.models.webhook import Webhook, WebhookDelivery

        webhook = Webhook(
            name="Test",
            url="https://example.com/webhook",
            events=["test.event"]
        )
        test_db.add(webhook)
        test_db.commit()

        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test.event",
            payload={},
            status="pending"
        )
        test_db.add(delivery)
        test_db.commit()

        # 更新状态
        delivery.status = "success"
        delivery.response_code = 200
        test_db.commit()

        assert delivery.status == "success"
        assert delivery.response_code == 200


class TestWebhookAPI:
    """测试Webhook API"""

    def test_create_webhook(self, client, test_db, admin_token):
        """测试创建Webhook"""
        response = client.post(
            "/api/webhooks",
            json={
                "name": "Test Webhook",
                "url": "https://example.com/webhook",
                "events": ["project.completed"],
                "secret": "test_secret"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Webhook"
        assert data["url"] == "https://example.com/webhook"

    def test_list_webhooks(self, client, test_db, admin_token):
        """测试列出Webhooks"""
        from app.models.webhook import Webhook

        webhook = Webhook(
            name="Test",
            url="https://example.com/webhook",
            events=["test.event"]
        )
        test_db.add(webhook)
        test_db.commit()

        response = client.get(
            "/api/webhooks",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_delete_webhook(self, client, test_db, admin_token):
        """测试删除Webhook"""
        from app.models.webhook import Webhook

        webhook = Webhook(
            name="Test",
            url="https://example.com/webhook",
            events=["test.event"]
        )
        test_db.add(webhook)
        test_db.commit()

        response = client.delete(
            f"/api/webhooks/{webhook.id}",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 204

        # 验证已删除
        deleted = test_db.query(Webhook).filter(Webhook.id == webhook.id).first()
        assert deleted is None

    def test_get_webhook_deliveries(self, client, test_db, admin_token):
        """测试获取Webhook投递记录"""
        from app.models.webhook import Webhook, WebhookDelivery

        webhook = Webhook(
            name="Test",
            url="https://example.com/webhook",
            events=["test.event"]
        )
        test_db.add(webhook)
        test_db.commit()

        # 创建投递记录
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test.event",
            payload={"test": "data"},
            status="success"
        )
        test_db.add(delivery)
        test_db.commit()

        response = client.get(
            f"/api/webhooks/{webhook.id}/deliveries",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["status"] == "success"

    def test_update_webhook(self, client, test_db, admin_token):
        """测试更新Webhook"""
        from app.models.webhook import Webhook

        webhook = Webhook(
            name="Test",
            url="https://example.com/webhook",
            events=["test.event"]
        )
        test_db.add(webhook)
        test_db.commit()

        response = client.put(
            f"/api/webhooks/{webhook.id}",
            json={
                "name": "Updated Webhook",
                "url": "https://example.com/updated-webhook",
                "events": ["project.completed", "project.failed"]
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Webhook"

    def test_webhook_not_found(self, client, admin_token):
        """测试Webhook不存在"""
        response = client.get(
            "/api/webhooks/nonexistent-id",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 404


class TestWebhookTrigger:
    """测试Webhook触发机制"""

    def test_trigger_webhook_event(self, test_db, monkeypatch):
        """测试触发Webhook事件"""
        from app.services.webhook.handler import WebhookHandler

        webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["project.completed"],
            enabled=True
        )
        test_db.add(webhook)
        test_db.commit()

        # Mock the HTTP client
        class MockResponse:
            status_code = 200
            text = "OK"

        class MockClient:
            def __init__(self, timeout=None):
                pass
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def post(self, *args, **kwargs):
                return MockResponse()

        import httpx
        monkeypatch.setattr(httpx, "Client", MockClient)

        handler = WebhookHandler(test_db)

        # 触发事件
        deliveries = handler.trigger_event(
            event_type="project.completed",
            payload={"project_id": "test-123", "status": "completed"}
        )

        assert len(deliveries) >= 1
        assert deliveries[0].event_type == "project.completed"
        assert deliveries[0].status == "success"

    def test_webhook_retry_logic(self, test_db):
        """测试Webhook重试逻辑"""
        from app.services.webhook.handler import WebhookHandler
        from app.models.webhook import WebhookDelivery

        webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["test.event"],
            enabled=True
        )
        test_db.add(webhook)
        test_db.commit()

        # 创建一个失败的投递
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test.event",
            payload={"test": "data"},
            status="failed",
            attempt_count=1
        )
        test_db.add(delivery)
        test_db.commit()

        handler = WebhookHandler(test_db)

        # 检查是否可以重试
        can_retry = handler.can_retry(delivery)
        assert can_retry is True

    def test_webhook_max_retries(self, test_db):
        """测试最大重试次数"""
        from app.services.webhook.handler import WebhookHandler
        from app.models.webhook import WebhookDelivery

        webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["test.event"],
            enabled=True
        )
        test_db.add(webhook)
        test_db.commit()

        # 创建已达到最大重试次数的投递
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test.event",
            payload={"test": "data"},
            status="failed",
            attempt_count=3,
            max_attempts=3
        )
        test_db.add(delivery)
        test_db.commit()

        handler = WebhookHandler(test_db)

        # 检查不能重试
        can_retry = handler.can_retry(delivery)
        assert can_retry is False

    def test_get_pending_deliveries(self, test_db):
        """测试获取待处理的投递"""
        from app.services.webhook.handler import WebhookHandler

        webhook = Webhook(
            name="Test Webhook",
            url="https://example.com/webhook",
            events=["test.event"],
            enabled=True
        )
        test_db.add(webhook)
        test_db.commit()

        # 创建待处理投递
        delivery = WebhookDelivery(
            webhook_id=webhook.id,
            event_type="test.event",
            payload={"test": "data"},
            status="pending"
        )
        test_db.add(delivery)
        test_db.commit()

        handler = WebhookHandler(test_db)
        pending = handler.get_pending_deliveries()

        assert len(pending) >= 1
        assert all(d.status in ["pending", "retrying"] for d in pending)
