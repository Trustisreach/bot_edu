# app/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    
    # Database
    DATABASE_URL: str
    
    # S3
    S3_ENDPOINT_URL: str
    S3_ACCESS_KEY: str
    S3_SECRET_KEY: str
    S3_BUCKET_FREE: str
    S3_BUCKET_PREMIUM: str
    
    # Robokassa
    ROBOKASSA_LOGIN: str
    ROBOKASSA_PASSWORD1: str
    ROBOKASSA_PASSWORD2: str
    ROBOKASSA_TEST_MODE: bool = True
    
    # Polling interval (секунды)
    PAYMENT_CHECK_INTERVAL: int = 30
    PAYMENT_MAX_AGE_HOURS: int = 1       # максимальный возраст платежа
    PAYMENT_MAX_CHECKS: int = 120        # максимум проверок (120 * 30сек = 1 час)


    # # Webhook
    # WEBHOOK_HOST: str  # https://your-domain.com
    # WEBHOOK_PORT: int = 8080

    class Config:
        env_file = ".env"


settings = Settings()