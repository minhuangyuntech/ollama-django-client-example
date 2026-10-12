"""Small server-side Ollama client. Never send API_KEY to templates."""
from dataclasses import dataclass
import json
import math
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from django.conf import settings


class GatewayError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    """Do not carry a credential header to a redirected URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass
class Answer:
    model: str
    text: str
    elapsed_ms: float
    output_tokens: int | None
    tokens_per_second: float | None
    server_total_ms: float | None
    load_ms: float | None


def _request(path, payload=None):
    key = settings.OLLAMA_GATEWAY_API_KEY
    if not key:
        raise GatewayError("Django 尚未設定 API_KEY。請在啟動網站的終端機設定金鑰，再重新啟動。", 503)
    if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", key):
        raise GatewayError("API_KEY 格式不正確，請確認金鑰沒有空白、換行或多餘引號。", 503)
    base = settings.OLLAMA_GATEWAY_URL.rstrip("/")
    try:
        origin = urlsplit(base)
        valid = (origin.scheme in {"http", "https"} and origin.hostname and not origin.username
                 and not origin.password and origin.path in {"", "/"} and not origin.query
                 and not origin.fragment and (origin.port is None or 1 <= origin.port <= 65535))
    except ValueError:
        valid = False
    if not valid:
        raise GatewayError("OLLAMA_GATEWAY_URL 必須是中介 API 的 HTTP(S) 主機與埠。", 503)
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    started = time.perf_counter()
    try:
        req = Request(base + path, data=body,
                      headers={"Content-Type": "application/json", "X-API-Key": key})
        with build_opener(ProxyHandler({}), NoRedirect()).open(req, timeout=310 if payload is not None else 15) as response:
            raw = response.read(8_388_609)
        if len(raw) > 8_388_608:
            raise GatewayError("API 回應超過大小限制。")
        data = json.loads(raw.decode("utf-8"))
    except HTTPError as exc:
        messages = {
            301: "API 位址發生重新導向（301）。請確認中介服務的直接位址。",
            302: "API 位址發生重新導向（302）。請確認中介服務的直接位址。",
            401: "中介 API 拒絕金鑰（401）。請確認 API_KEY，金鑰更新後需重啟 Django。",
            403: "中介 API 拒絕來源網段（403）。請確認你的 Django 主機位於允許網段。",
            404: "模型或 API 路徑不存在（404）。請重新取得可用模型清單。",
            429: "中介 API 已達同時請求上限（429）。請稍候再送出，不要連續重送。",
            502: "中介 API 無法取得上游回應（502）。請確認 Pi 與 AI 伺服器連線。",
            503: "上游模型服務尚未就緒（503）。請確認模型服務與清單。",
            504: "模型服務等待逾時（504）。請保留錯誤紀錄並稍後再試。",
        }
        message = messages.get(exc.code, f"中介 API 回傳 HTTP {exc.code}。")
        exc.close()
        raise GatewayError(message, exc.code) from exc
    except TimeoutError as exc:
        raise GatewayError("等待中介 API 逾時。", 504) from exc
    except (URLError, OSError, ValueError, UnicodeError) as exc:
        raise GatewayError("無法連線或 API 回應不是有效 JSON。請確認服務位址與網路。") from exc
    if not isinstance(data, dict) or "error" in data:
        raise GatewayError("API 未回傳預期的 JSON 結果。")
    return data, (time.perf_counter() - started) * 1000


def list_models():
    data, _ = _request("/api/tags")
    if not isinstance(data.get("models"), list):
        raise GatewayError("模型清單格式錯誤。")
    names = [item.get("name") for item in data["models"] if isinstance(item, dict)]
    names = list(dict.fromkeys(name for name in names if isinstance(name, str) and name.strip()))
    if not names:
        raise GatewayError("伺服器未提供可用模型，請確認上游模型服務。", 503)
    return names


def _number(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def ask(model, question):
    data, elapsed = _request("/api/chat", {
        "model": model, "messages": [{"role": "user", "content": question}], "stream": False,
    })
    message = data.get("message")
    if (data.get("done") is not True or not isinstance(message, dict)
            or not isinstance(message.get("content"), str) or not message["content"].strip()):
        raise GatewayError("模型未回傳完整的文字回答。請更換可用模型或保留錯誤紀錄。")
    count, duration = _number(data.get("eval_count")), _number(data.get("eval_duration"))
    if not isinstance(count, int):
        count = None
    total, load = _number(data.get("total_duration")), _number(data.get("load_duration"))
    return Answer(
        model=str(data.get("model") or model), text=message["content"], elapsed_ms=elapsed,
        output_tokens=count,
        tokens_per_second=count / (duration / 1e9) if count is not None and duration else None,
        server_total_ms=total / 1e6 if total is not None else None,
        load_ms=load / 1e6 if load is not None else None,
    )
