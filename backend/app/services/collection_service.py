"""Collect raw source documents (live fetch or replay from snapshots).

Demo mode does not use this service — it loads structured fixtures directly (see
``discovery_service``). Live and replay both produce ``FetchedDocument`` objects
and persist a ``SourceDocument`` row recording status, snapshot URI and any
error, so partial failures are inspectable and never crash the run.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from app.adapters.base import FetchedDocument
from app.config import FIXTURES_DIR, get_settings
from app.errors import AppError, ErrorCode
from app.logging_config import get_logger
from app.models import SourceDocument
from app.models._common import utcnow
from app.security import DomainRateLimiter, assert_safe_url, is_allowed_url
from app.services.storage import save_snapshot

logger = get_logger(__name__)

_CAPTCHA_MARKERS = ("captcha", "are you a robot", "verify you are human", "cf-challenge")
_BLOCK_MARKERS = ("access denied", "403 forbidden", "you have been blocked")


@dataclass
class CollectionResult:
    document: FetchedDocument | None
    source_document: SourceDocument


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()


def _detect_block(text: str) -> ErrorCode | None:
    low = text.lower()
    if any(m in low for m in _CAPTCHA_MARKERS):
        return ErrorCode.CAPTCHA_DETECTED
    if any(m in low for m in _BLOCK_MARKERS):
        return ErrorCode.SOURCE_BLOCKED
    return None


class Collector:
    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.settings = get_settings()
        self.rate_limiter = DomainRateLimiter(
            self.settings.SCAN_PER_DOMAIN_RATE_PER_MINUTE
        )

    def collect(
        self,
        db: Session,
        *,
        discovery_run_id: str,
        source_key: str,
        url: str,
        source_type: str | None,
        market: str | None,
        config: dict | None = None,
        fixture_subdir: str = "global",
    ) -> CollectionResult:
        sd = SourceDocument(
            discovery_run_id=discovery_run_id,
            source_key=source_key,
            source_url=url,
            source_type=source_type,
            market=market,
            mode=self.mode,
            collected_at=utcnow(),
        )
        try:
            if self.mode == "replay":
                text, status = self._read_fixture(source_key, fixture_subdir)
            else:  # live
                text, status = self._fetch_live(url)
            block = _detect_block(text)
            if block is not None:
                raise AppError(block, f"Source appears blocked: {source_key}")
            sd.http_status = status
            sd.content_hash = _content_hash(text)
            sd.snapshot_uri = save_snapshot(
                discovery_run_id, source_key, text, kind=fixture_subdir
            )
            sd.collection_status = "ok"
            doc = FetchedDocument(
                url=url,
                text=text,
                source_key=source_key,
                source_type=source_type,
                market=market,
                config=config or {},
            )
            db.add(sd)
            db.flush()
            return CollectionResult(document=doc, source_document=sd)
        except AppError as exc:
            logger.warning("collection_failed source=%s code=%s", source_key, exc.code)
            sd.collection_status = "failed"
            sd.error_code = exc.code.value
            sd.error_message = exc.message
            db.add(sd)
            db.flush()
            return CollectionResult(document=None, source_document=sd)
        except Exception as exc:  # noqa: BLE001  never let one source kill the run
            logger.exception("collection_error source=%s", source_key)
            sd.collection_status = "failed"
            sd.error_code = ErrorCode.HTTP_ERROR.value
            sd.error_message = str(exc)[:500]
            db.add(sd)
            db.flush()
            return CollectionResult(document=None, source_document=sd)

    def _read_fixture(self, source_key: str, subdir: str) -> tuple[str, int]:
        path = FIXTURES_DIR / subdir / f"{source_key}.html"
        if not path.exists():
            raise AppError(
                ErrorCode.EXTRACTION_FAILED,
                f"No replay fixture for '{source_key}' at {path}",
            )
        return path.read_text(encoding="utf-8"), 200

    def _fetch_live(self, url: str) -> tuple[str, int]:
        if not is_allowed_url(url):
            raise AppError(
                ErrorCode.SOURCE_NOT_ALLOWED,
                f"URL not in configured allowlist: {url}",
            )
        assert_safe_url(url)
        if not self.rate_limiter.acquire(url, timeout=self.settings.SCAN_TIMEOUT_SECONDS):
            raise AppError(ErrorCode.SOURCE_TIMEOUT, "Per-domain rate limit exceeded.")
        headers = {"User-Agent": self.settings.USER_AGENT}
        try:
            with httpx.Client(
                timeout=self.settings.SCAN_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=headers,
            ) as client:
                # Re-validate after redirects by inspecting the final URL.
                resp = client.get(url)
                assert_safe_url(str(resp.url))
                if resp.status_code == 403:
                    raise AppError(ErrorCode.SOURCE_BLOCKED, "HTTP 403 from source.")
                if resp.status_code >= 400:
                    raise AppError(
                        ErrorCode.HTTP_ERROR,
                        f"HTTP {resp.status_code} from source.",
                    )
                content = resp.content[: self.settings.SCAN_MAX_RESPONSE_BYTES]
                return content.decode(resp.encoding or "utf-8", "ignore"), resp.status_code
        except httpx.TimeoutException as exc:
            raise AppError(ErrorCode.SOURCE_TIMEOUT, "Source request timed out.") from exc
        except httpx.HTTPError as exc:
            raise AppError(ErrorCode.HTTP_ERROR, str(exc)[:300]) from exc
