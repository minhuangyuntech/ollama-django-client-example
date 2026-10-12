# Raspberry Pi／Linux（Bash）

此處在 Pi 上執行的是 **Django 網站**。它呼叫已存在的 `140.125.35.48:9999` 中介服務，無需在 Pi 安裝模型或 GPU 套件。Django 使用 8000 埠，中介使用 9999 埠；即使在同一台 Pi，也分屬不同程序。

## 系統與專案

在 Pi 的 Bash 或 SSH 終端機執行。Python 需為 3.11–3.14；先確認系統版本符合要求。

```bash
sudo apt-get update
sudo apt-get install -y git python3-venv python3-pip curl
python3 --version
git clone https://github.com/minhuangyuntech/ollama-django-client-example.git
cd ollama-django-client-example
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py check
```

若系統 Python 太舊，先使用支援版本的 Python 建立 venv。套件安裝到 venv，不使用 `sudo pip`，也不需要 `--break-system-packages`。[Python venv 文件](https://docs.python.org/3/library/venv.html)

## 金鑰與服務檢查

```bash
read -r -s -p "API_KEY: " API_KEY
printf '\n'
export API_KEY
export OLLAMA_GATEWAY_URL="http://140.125.35.48:9999"
.venv/bin/python manage.py check_gateway
```

可另用 curl：

```bash
curl -H "X-API-Key: $API_KEY" http://140.125.35.48:9999/readyz
```

此網站使用既有中介金鑰，不會生成、輪替或讀取 `/etc/ollama-gateway.env`。金鑰更新後，重啟 Django 才會讀取新的環境。

## 本機開啟

```bash
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

Pi 有桌面環境時，瀏覽器開啟 **http://127.0.0.1:8000/**。保持終端機運作，Ctrl+C 結束。

## 沒有桌面的 Pi：SSH 轉送

Pi 上維持上述 Django 程序。在自己的 Windows PowerShell 或 macOS Terminal 另開終端機，使用實際 SSH 帳號與 **執行 Django 的 Pi IP**：

```text
ssh -L 8000:127.0.0.1:8000 帳號@Pi的IP
```

在自己電腦的瀏覽器開啟 **http://127.0.0.1:8000/**。瀏覽器流量透過 SSH 到 Pi 的 Django；API 呼叫來源仍是 Pi。自己的 8000 埠若已占用，可用 `-L 8001:127.0.0.1:8000`，瀏覽器改開 `http://127.0.0.1:8001/`。

## 同一網路直接瀏覽

若需要讓其他主機直接瀏覽 Pi 的開發網站，將下方的 `140.125.x.x` 替換為 **Django Pi 的實際 IP**：

```bash
export DJANGO_ALLOWED_HOSTS="127.0.0.1,localhost,140.125.x.x"
.venv/bin/python manage.py runserver 0.0.0.0:8000
```

另一台瀏覽器開啟 `http://Django的PiIP:8000/`。網路與防火牆須允許測試連線。中介位址仍是 `140.125.35.48:9999`；修改網站監聽位址不會改變 API 位址。

以上為開發練習方式；正式長期公開網站需採用適當的 WSGI／ASGI 部署。[Django runserver 文件](https://docs.djangoproject.com/en/5.2/ref/django-admin/#runserver)

測試不需校內模型服務：

```bash
.venv/bin/python manage.py test chat
```
