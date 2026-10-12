# Django 如何呼叫中介 API

一次提問的路徑：瀏覽器表單 → Django view → API client → Pi 中介 → Ollama → Answer → template。

## 環境與認證

`course_site/settings.py` 從環境讀取服務位址及金鑰：

```python
OLLAMA_GATEWAY_URL = os.environ.get(
    "OLLAMA_GATEWAY_URL", "http://140.125.35.48:9999"
)
OLLAMA_GATEWAY_API_KEY = os.environ.get("API_KEY", "")
```

Base URL 不包含 `/api/chat`、query 或帳號密碼。`chat/gateway.py` 建立 HTTP header，API_KEY 不交給 template。client 不使用系統代理，也不跟隨重新導向，避免認證資料被帶到另一個服務。

## 模型清單與表單

`list_models()` GET `/api/tags`，解析 `models[*].name`。`AskForm` 以清單建立 ChoiceField，並用 CharField 驗證必填、空白與 4000 字元上限。模型值及問題內容先通過 `form.is_valid()`，再使用 `cleaned_data` 呼叫模型。

## 問答與 JSON

`ask()` 發送 POST `/api/chat`：

```python
{
    "model": model,
    "messages": [{"role": "user", "content": question}],
    "stream": False,
}
```

JSON 以 UTF-8 傳送，header 包含 `Content-Type: application/json` 與 `X-API-Key`。GET 逾時 15 秒，問答逾時 310 秒；此值配合中介目前的 300 秒總期限。client 限制回應大小 8 MiB，將 HTTP、網路、JSON 及不完整回答轉成 GatewayError。

成功回應必須包含 `done:true` 與非空的 `message.content`。網站目前每題獨立，不會自動將先前問答當成歷史送給模型。[Ollama chat 文件](https://docs.ollama.com/api/chat)

## 呈現與量測

view 將 `form`、`answer`、`error` 傳給 template。表單保留 `{% csrf_token %}`；回答使用 `{{ answer.text }}` 的預設 escape，避免將模型文字執行成 HTML。[Django CSRF](https://docs.djangoproject.com/en/5.2/howto/csrf/)、[Templates](https://docs.djangoproject.com/en/5.2/topics/templates/)

| 網站資訊 | 來源 |
|---|---|
| API 呼叫時間 | `_request` 使用 `perf_counter` |
| 輸出 token | Ollama 的 `eval_count` |
| 生成速度 | `eval_count / (eval_duration / 10^9)` |
| 伺服器總時間 | `total_duration / 10^6`，單位 ms |
| 模型載入時間 | `load_duration / 10^6`，單位 ms |

缺少、無效或分母為 0 的欄位顯示「未回報」，不補造數字。API 呼叫時間包含網路及服務等待，與純生成速度或 GPU 運算時間不同。

## 測試

`chat/tests.py` 用 mock 驗證資料格式、金鑰處理、CSRF、escape、表單與錯誤。重新導向測試使用 localhost HTTP 服務確認不跟隨 Location；測試金鑰無法用於實際服務。`check_gateway` 則用啟動環境中的真實設定檢查既有中介，兩種用途不同。
