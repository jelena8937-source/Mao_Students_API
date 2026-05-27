@echo off
chcp 65001 > nul
echo 🐾 正在啟動「毛同學」後端開發伺服器...

:: 1. 檢查並自動啟用虛擬環境 (.venv)
if exist .venv\Scripts\activate.bat (
    echo 📦 偵測到虛擬環境，正在自動啟用...
    call .venv\Scripts\activate.bat
) else (
    echo ⚠️ 警告：找不到 .venv 虛擬環境，將使用系統全域 Python 執行。
)

:: 2. 啟動 Uvicorn 伺服器
echo 🚀 FastAPI 服務正在啟動，請稍候...
echo 💡 提示：開啟瀏覽器前往 http://127.0.0.1:8000/docs 查看 API 文件
echo --------------------------------------------------

set PYTHONIOENCODING=utf-8
uvicorn main:app --reload --host 127.0.0.1 --port 8000

pause