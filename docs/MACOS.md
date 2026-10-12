# macOS

使用 Python 3.11–3.14，Apple Silicon 與 Intel Mac 均以同樣的 Python 專案運作。可安裝 [Python 官方 macOS 套件](https://www.python.org/downloads/macos/)；已有 Homebrew 時，也可使用受支援的版本：

```zsh
brew install python@3.13
```

下列命令以 `python3.13` 建立環境。若已有支援版本的 `python3`，確認版本後替換建立 venv 的執行器即可。[Homebrew python@3.13](https://formulae.brew.sh/formula/python@3.13)

## 下載與環境

```zsh
git clone https://github.com/minhuangyuntech/ollama-django-client-example.git
cd ollama-django-client-example
python3.13 --version
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py check
```

也可使用 GitHub Download ZIP，解壓後在 Terminal 進入含 `manage.py` 的資料夾。直接使用 `.venv/bin/python`，不需要 `source activate`。

## 預設 zsh 的 API_KEY 設定

macOS Terminal 通常使用 zsh。輸入金鑰不回顯：

```zsh
read -r -s "API_KEY?API_KEY: "
printf '\n'
export API_KEY
export OLLAMA_GATEWAY_URL="http://140.125.35.48:9999"
.venv/bin/python manage.py check_gateway
```

zsh 的提示字串是 `變數名?提示文字`；Bash 的 `read -p` 在 zsh 代表不同用途，不能混用。[zsh read 文件](https://zsh.sourceforge.io/Doc/Release/Shell-Builtin-Commands.html#index-read)

## 若使用 Bash

若終端機是 Bash，使用以下寫法，其他安裝及啟動命令相同：

```bash
read -r -s -p "API_KEY: " API_KEY
printf '\n'
export API_KEY
export OLLAMA_GATEWAY_URL="http://140.125.35.48:9999"
.venv/bin/python manage.py check_gateway
```

## 啟動與驗證

```zsh
.venv/bin/python manage.py runserver 127.0.0.1:8000
```

瀏覽器開啟 **http://127.0.0.1:8000/**。Ctrl+C 結束網站；金鑰變更或新開 Terminal 時，需要重新設定環境並啟動。網站的模型下拉選單使用 `/api/tags` 的實際名稱。

單獨檢查就緒端點：

```zsh
curl -H "X-API-Key: $API_KEY" http://140.125.35.48:9999/readyz
```

測試不需真實 API_KEY：

```zsh
.venv/bin/python manage.py test chat
```

macOS 不會因為有 Python 就能從任意網路呼叫校內中介；Django 主機仍需位於允許的校內來源網段或具備合適的網路連線。
