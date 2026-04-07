from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .errors import ValidationError

_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9._\- ]+$")
_SLUG_SAFE = re.compile(r"[^a-z0-9]+")


class ObsidianStore:
    def __init__(self, vault_root: Path) -> None:
        self.vault_root = vault_root.resolve()
        self.vault_root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, relative_path: str) -> Path:
        normalized = Path(relative_path.replace("\\", "/")).as_posix().strip("/")
        if not normalized:
            raise ValidationError("relative path cannot be empty")
        for segment in normalized.split("/"):
            if segment in {"", ".", ".."} or not _SAFE_SEGMENT.match(segment):
                raise ValidationError(f"invalid vault path segment: {segment!r}")
        candidate = (self.vault_root / normalized).resolve()
        if self.vault_root not in candidate.parents and candidate != self.vault_root:
            raise ValidationError("path escapes vault root")
        return candidate

    @staticmethod
    def _slugify(value: str, fallback: str = "general") -> str:
        normalized = _SLUG_SAFE.sub("-", value.strip().lower()).strip("-")
        return (normalized or fallback)[:80]

    def ensure_project_structure(self, employer: str, project: str) -> str:
        root = f"Employers/{employer}/{project}"
        path = self._resolve(root)
        path.mkdir(parents=True, exist_ok=True)
        return root.replace("\\", "/")

    def upsert_note(self, relative_path: str, content: str, mode: str = "overwrite") -> str:
        if mode not in {"overwrite", "append"}:
            raise ValidationError("mode must be overwrite or append")
        path = self._resolve(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "append" and path.exists():
            with path.open("a", encoding="utf-8") as f:
                f.write("\n" + content)
        else:
            with path.open("w", encoding="utf-8") as f:
                f.write(content)
        return str(path.relative_to(self.vault_root)).replace("\\", "/")

    def get_note(self, relative_path: str) -> dict[str, str | bool]:
        path = self._resolve(relative_path)
        if not path.exists():
            return {"path": relative_path, "exists": False, "content": ""}
        return {
            "path": str(path.relative_to(self.vault_root)).replace("\\", "/"),
            "exists": True,
            "content": path.read_text(encoding="utf-8"),
        }

    @staticmethod
    def canonical_session_path(
        employer: str,
        project: str,
        session_id: str,
        started_at: datetime,
        feature_name: str,
    ) -> str:
        date_part = started_at.strftime("%Y-%m-%d")
        feature_slug = ObsidianStore._slugify(feature_name, fallback="session")
        update_folder = f"{date_part}-update-{feature_slug}"
        return f"Employers/{employer}/{project}/{update_folder}/session-{session_id}.md".replace("\\", "/")

    @staticmethod
    def canonical_meeting_path(
        employer: str,
        project: str,
        meeting_id: str,
        meeting_dt: datetime,
        feature_name: str,
    ) -> str:
        date_part = meeting_dt.strftime("%Y-%m-%d")
        feature_slug = ObsidianStore._slugify(feature_name, fallback="meeting")
        update_folder = f"{date_part}-update-{feature_slug}"
        return f"Employers/{employer}/{project}/{update_folder}/meeting-{meeting_id}.md".replace("\\", "/")

    @staticmethod
    def canonical_decision_path(
        employer: str,
        project: str,
        decision_id: str,
        created_at: datetime,
        feature_name: str,
    ) -> str:
        date_part = created_at.strftime("%Y-%m-%d")
        feature_slug = ObsidianStore._slugify(feature_name, fallback="decision")
        update_folder = f"{date_part}-update-{feature_slug}"
        return f"Employers/{employer}/{project}/{update_folder}/decision-{decision_id}.md".replace("\\", "/")
