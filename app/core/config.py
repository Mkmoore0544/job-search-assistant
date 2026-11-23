from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "AI Job Search Assistant"
    database_url: str = "sqlite:///./data/jobs.db"
    host: str = "127.0.0.1"
    port: int = 8000
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    usajobs_api_key: str = ""
    usajobs_user_agent: str = ""
    greenhouse_boards: str = ""
    lever_boards: str = ""
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    adzuna_country: str = "us"
    ashby_boards: str = ""
    remotive_enabled: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from: str = ""
    notify_email: str = ""
    search_interval_hours: float = 4
    min_match_score: int = 70
    ai_max_requests_per_day: int = 100
    ai_estimated_cost_per_1k: float = 0.00015


settings = Settings()
