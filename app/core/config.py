#MYSQL地端資料庫再改開這個
# from pydantic_settings import BaseSettings
# from typing import List
# from urllib.parse import quote_plus


# class Settings(BaseSettings):
#     # 資料庫
#     DB_HOST: str = "localhost"
#     DB_PORT: int = 3306
#     DB_USER: str = "root"
#     DB_PASSWORD: str = ""
#     DB_NAME: str = "mao_students_db"

#     # JWT
#     SECRET_KEY: str = "change-this-in-production"
#     ALGORITHM: str = "HS256"
#     ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
#     REFRESH_TOKEN_EXPIRE_DAYS: int = 7

#     # 應用程式
#     APP_NAME: str = "毛同學後端 API"
#     APP_VERSION: str = "1.0.0"
#     DEBUG: bool = False
#     ALLOWED_ORIGINS: str = "http://localhost:5173"
#     FRONTEND_URL: str = "http://127.0.0.1:5173"
#     GOOGLE_CLIENT_ID: str = ""
#     GOOGLE_CLIENT_SECRET: str = ""
#     GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/auth/google/callback"

#     # 管理員預設帳號
#     ADMIN_EMAIL: str = "admin@maosmain.com"
#     ADMIN_PASSWORD: str = "ChangeThisPassword123!"

#     @property
#     def DATABASE_URL(self) -> str:
#         return (
#             f"mysql+pymysql://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}"  # ← quote_plus 在這
#             f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
#         )

#     @property
#     def ORIGINS_LIST(self) -> List[str]:
#         return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

#     class Config:
#         env_file = ".env"
#         case_sensitive = True


# settings = Settings()


from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # 資料庫（直接讀取完整連線字串）
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/postgres"

    # JWT
    SECRET_KEY: str = "change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 應用程式
    APP_NAME: str = "毛同學後端 API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:5173"
    FRONTEND_URL: str = "http://127.0.0.1:5173"
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/v1/auth/google/callback"

    # 管理員預設帳號
    ADMIN_EMAIL: str = "maostudents3@gmail.com"
    ADMIN_PASSWORD: str = "maomaomaostudents0826"

    @property
    def ORIGINS_LIST(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()