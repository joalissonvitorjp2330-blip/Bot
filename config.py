import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

@dataclass(frozen=True)
class Settings:
    discord_token: str = os.getenv("DISCORD_TOKEN", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    guild_id: int = int(os.getenv("GUILD_ID", "0") or 0)
    admin_role_id: int = int(os.getenv("ADMIN_ROLE_ID", "0") or 0)
    pix_key: str = os.getenv("PIX_KEY", "")
    pix_receiver: str = os.getenv("PIX_RECEIVER", "")
    minimum_age: int = int(os.getenv("MINIMUM_AGE", "18") or 18)

settings = Settings()

def validate_settings():
    missing = [k for k, v in (("DISCORD_TOKEN", settings.discord_token), ("DATABASE_URL", settings.database_url)) if not v]
    if missing:
        raise RuntimeError("Variáveis obrigatórias ausentes: " + ", ".join(missing))
