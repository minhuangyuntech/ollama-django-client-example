"""Authenticated reachability checks with no credential output."""
from django.core.management.base import BaseCommand, CommandError

from chat.gateway import GatewayError, _request, list_models


class Command(BaseCommand):
    help = "檢查中介 API、上游模型清單與金鑰設定；不執行模型推論。"

    def handle(self, *args, **options):
        path = "/healthz"
        try:
            health, _ = _request(path)
            if health.get("status") != "ok":
                raise GatewayError("中介程序尚未就緒。", 503)
            self.stdout.write("/healthz：中介程序正常")
            path = "/readyz"
            ready, _ = _request(path)
            if ready.get("status") != "ready":
                raise GatewayError("上游服務尚未就緒。", 503)
            self.stdout.write("/readyz：可取得上游模型清單")
            path = "/api/tags"
            models = list_models()
            self.stdout.write("/api/tags：" + "、".join(models))
        except GatewayError as exc:
            raise CommandError(f"{path}：{exc}") from None
