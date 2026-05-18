import os
from dataclasses import dataclass


@dataclass
class AgentSettings:
    server_url: str = os.getenv("SERVER_URL", "http://127.0.0.1:8000")
    api_key: str = os.getenv("SERVER_API_KEY", "change-me")
    interval_seconds: int = int(os.getenv("AGENT_INTERVAL_SECONDS", "60"))
    client_id_file: str = os.getenv("CLIENT_ID_FILE", ".client_id")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))


settings = AgentSettings()
