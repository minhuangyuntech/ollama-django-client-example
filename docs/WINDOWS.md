# Windows PowerShell

先安裝 Python 3.11–3.14 與 Git，可從 [Python 官方網站](https://www.python.org/downloads/windows/)與 [Git for Windows](https://gitforwindows.org/)下載。也可用 GitHub Download ZIP，解壓後在含 `manage.py` 的資料夾開啟 PowerShell。

## 下載與環境

```powershell
git clone https://github.com/minhuangyuntech/ollama-django-client-example.git
cd ollama-django-client-example
python --version
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe manage.py check
```

若 `python` 命令不可用，已有 Python 3.13 的環境可用 `py -3.13 --version` 與 `py -3.13 -m venv .venv`。後續維持使用 venv 裡的執行器。直接呼叫 `.\.venv\Scripts\python.exe`，不需修改 PowerShell 執行政策或啟用 Activate.ps1。[Python venv 文件](https://docs.python.org/3/library/venv.html)

## 設定 API_KEY 與檢查

在同一個 PowerShell 輸入已取得的 API_KEY；輸入不回顯，不要把真實金鑰寫成程式常數。

```powershell
$taskGatewayKey = Read-Host "API_KEY" -AsSecureString
$env:API_KEY = [System.Net.NetworkCredential]::new("", $taskGatewayKey).Password
$env:OLLAMA_GATEWAY_URL = "http://140.125.35.48:9999"
.\.venv\Scripts\python.exe manage.py check_gateway
```

也可單獨檢查中介的就緒端點。PowerShell 的環境變數寫成 `$env:API_KEY`；使用 `curl.exe` 呼叫實際 curl 執行檔。

```powershell
curl.exe -H "X-API-Key: $env:API_KEY" http://140.125.35.48:9999/readyz
```

## 啟動網站

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

瀏覽器開啟 **http://127.0.0.1:8000/**。選擇清單中的模型並送出問題，終端機用 Ctrl+C 結束。重開 PowerShell 要重新設定環境；只重整網頁不會更新已啟動程序的 API_KEY。

測試不需要真實金鑰：

```powershell
.\.venv\Scripts\python.exe manage.py test chat
```

## 校內其他主機瀏覽開發網站

若需要讓同一網路的其他電腦瀏覽，先查自己的 Django 電腦 IP。以下 `140.125.x.x` 是替換位置，**不是中介 API 的 IP**：

```powershell
$env:DJANGO_ALLOWED_HOSTS = "127.0.0.1,localhost,140.125.x.x"
.\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

另一台瀏覽器開啟 `http://你的Django電腦IP:8000/`，Windows 防火牆需允許該測試連線。`0.0.0.0` 是監聽設定，不是瀏覽器位址。此方式仍是開發測試，預設只使用 localhost 即可。
