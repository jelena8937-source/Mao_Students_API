import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger():
    # 1. 確保 logs 資料夾存在
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 2. 定義 Log 的顯示格式 (完美對應你圖片中的格式)
    # 格式：年-月-日 時:分:秒,毫秒 - 模組名 - 等級 - 訊息
    log_format = logging.Formatter(
        '%(asctime)s,%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 3. 建立根日誌記錄器 (Root Logger)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # 設定記錄等級為 INFO 以上

    # 如果已經有 Handler 就不重複加入 (避免重複列印)
    if not root_logger.handlers:
        
        # 建立「檔案」處理器：負責把 Log 寫進 logs/app.log
        # RotatingFileHandler 可以防止檔案無限長大，滿 5MB 會自動切分，最多保留 5 個舊檔
        file_handler = RotatingFileHandler(
            os.path.join(log_dir, "app.log"),
            maxBytes=5 * 1024 * 1024,  # 5 MB
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setFormatter(log_format)
        root_logger.addHandler(file_handler)

        # 建立「終端機」處理器：負責把 Log 顯示在 VS Code 的黑色視窗
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_format)
        root_logger.addHandler(console_handler)

    print("🐾 日誌系統初始化成功，Log 檔案路徑: logs/app.log")