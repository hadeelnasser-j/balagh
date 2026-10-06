"""Media storage.

Working files always live on local disk under STORAGE_DIR (FFmpeg needs paths).
When SUPABASE_STORAGE_ENABLED=true, every saved file is also uploaded to the
matching Supabase Storage bucket, and missing local files are restored from it.

Stored paths are relative keys such as "projects/<id>/video/original.mp4".
"""
from __future__ import annotations

import logging
import mimetypes
import shutil
from pathlib import Path
from typing import Any, BinaryIO

logger = logging.getLogger(__name__)


class StorageError(RuntimeError):
    pass


class StorageService:
    def __init__(self, root: Path, supabase_client: Any | None = None,
                 buckets: dict[str, str] | None = None) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.supabase = supabase_client
        self.buckets = buckets or {}

    # Keys ------------------------------------------------------------------
    @staticmethod
    def project_key(project_id: str, *parts: str) -> str:
        return "/".join(["projects", str(project_id), *parts])

    def path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        if self.root not in candidate.parents and candidate != self.root:
            raise StorageError("Invalid storage key")
        return candidate

    def _bucket_for(self, key: str) -> str | None:
        kind = key.split("/")[2] if key.count("/") >= 2 else ""
        return self.buckets.get(kind)

    # Write -----------------------------------------------------------------
    def save_stream(self, key: str, stream: BinaryIO, max_bytes: int | None = None) -> int:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        written = 0
        with open(target, "wb") as out:
            while chunk := stream.read(1024 * 1024):
                written += len(chunk)
                if max_bytes is not None and written > max_bytes:
                    out.close()
                    target.unlink(missing_ok=True)
                    raise StorageError("FILE_TOO_LARGE")
                out.write(chunk)
        self.mirror(key)
        return written

    def register(self, key: str) -> str:
        """Call after a file was written directly at path(key)."""
        if not self.path(key).is_file():
            raise StorageError(f"Missing file for {key}")
        self.mirror(key)
        return key

    def mirror(self, key: str) -> None:
        bucket = self._bucket_for(key)
        if not self.supabase or not bucket:
            return
        local = self.path(key)
        content_type = mimetypes.guess_type(local.name)[0] or "application/octet-stream"
        try:
            with open(local, "rb") as fh:
                self.supabase.storage.from_(bucket).upload(
                    key, fh.read(), {"content-type": content_type, "upsert": "true"})
        except Exception as exc:  # noqa: BLE001 - mirroring must not break processing
            logger.warning("Supabase storage upload failed for %s: %s", key, exc)

    # Read ------------------------------------------------------------------
    def ensure_local(self, key: str | None) -> Path | None:
        if not key:
            return None
        local = self.path(key)
        if local.is_file():
            return local
        bucket = self._bucket_for(key)
        if self.supabase and bucket:
            try:
                data = self.supabase.storage.from_(bucket).download(key)
                local.parent.mkdir(parents=True, exist_ok=True)
                local.write_bytes(data)
                return local
            except Exception as exc:  # noqa: BLE001
                logger.warning("Supabase storage download failed for %s: %s", key, exc)
        return None

    def delete_prefix(self, key_prefix: str) -> None:
        target = self.path(key_prefix)
        if target.is_dir():
            shutil.rmtree(target, ignore_errors=True)
