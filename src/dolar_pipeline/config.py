from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_base_url: str = "https://dolarapi.com"
    dollars_endpoint: str = "/v1/dolares"
    status_endpoint: str = "/v1/estado"
    source_name: str = "dolarapi"
    timeout_seconds: int = 15
    default_db_path: Path = Path("data/dolar_rates.sqlite")
    default_log_path: Path = Path("logs/runs.ndjson")
    default_csv_path: Path = Path("data/latest_rates.csv")
    default_report_path: Path = Path("data/latest_report.html")


SETTINGS = Settings()

