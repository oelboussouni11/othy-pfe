from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    critical = "critical"
    warning = "warning"
    info = "info"
    ok = "ok"


@dataclass(frozen=True)
class CrawledPage:
    url: str
    status_code: int
    html: str
    response_time_ms: int


@dataclass(frozen=True)
class Issue:
    page_url: str
    type: str
    severity: Severity
    message: str
    recommendation: str = ""
    status_code: int | None = None
