"""Object storage helpers for filing/transcript raw bytes.

Uses S3 if ``S3_BUCKET`` is configured, otherwise falls back to local disk
under ``backend-ai/storage/`` so the pipeline runs in development without
cloud credentials. Returns URI strings (``s3://...`` or ``file://...``)
that we persist on Filing/Transcript rows.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from src.config import get_settings

logger = logging.getLogger(__name__)


_LOCAL_ROOT = Path(__file__).resolve().parents[2] / "storage"


def _ensure_local_root() -> None:
    _LOCAL_ROOT.mkdir(parents=True, exist_ok=True)


def store_bytes(prefix: str, key: str, data: bytes, content_type: Optional[str] = None) -> str:
    """Persist ``data`` and return a URI suitable for later retrieval.

    Args:
        prefix: Folder prefix (e.g. "filings/<company_id>/").
        key: Final filename, typically "<sha256>.<ext>".
        data: Raw bytes.
        content_type: Optional MIME type for S3.
    """
    settings = get_settings()
    full_key = f"{prefix.rstrip('/')}/{key}"

    if settings.s3_bucket and settings.aws_access_key_id:
        try:
            import boto3  # type: ignore

            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
            extra = {"ContentType": content_type} if content_type else {}
            s3.put_object(Bucket=settings.s3_bucket, Key=full_key, Body=data, **extra)
            return f"s3://{settings.s3_bucket}/{full_key}"
        except Exception as exc:
            logger.warning("S3 store failed, falling back to local: %s", exc)

    _ensure_local_root()
    target = _LOCAL_ROOT / full_key
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return f"file://{target.resolve()}"


def load_bytes(uri: str) -> Optional[bytes]:
    """Load bytes from a URI returned by ``store_bytes``."""
    if uri.startswith("file://"):
        path = Path(uri.replace("file://", ""))
        if path.exists():
            return path.read_bytes()
        return None
    if uri.startswith("s3://"):
        try:
            import boto3  # type: ignore

            settings = get_settings()
            s3 = boto3.client(
                "s3",
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region,
            )
            without_scheme = uri.replace("s3://", "")
            bucket, _, key = without_scheme.partition("/")
            obj = s3.get_object(Bucket=bucket, Key=key)
            return obj["Body"].read()
        except Exception as exc:
            logger.error("S3 load failed for %s: %s", uri, exc)
            return None
    return None


def store_text(prefix: str, key: str, text: str) -> str:
    """Convenience wrapper for text payloads (parsed transcripts/JSON)."""
    return store_bytes(prefix, key, text.encode("utf-8"), content_type="text/plain")


def split_uri(uri: str) -> Tuple[str, str]:
    """Return (scheme, path)."""
    scheme, _, rest = uri.partition("://")
    return scheme, rest
