from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class GuardianModelManifest:
    manifest_version: str
    model_id: str
    base_model: str
    fine_tune_profile: str
    artifact_path: str
    artifact_sha256: str
    training_data_version: str
    intended_roles: tuple[str, ...]
    notes: str = ""

    @classmethod
    def load(cls, path: str | Path) -> "GuardianModelManifest":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        data["intended_roles"] = tuple(data.get("intended_roles") or ())
        return cls(**data)

    @property
    def configured(self) -> bool:
        return bool(
            self.model_id.strip()
            and self.base_model.strip()
            and self.fine_tune_profile.strip()
            and self.artifact_path.strip()
            and self.artifact_sha256.strip()
        )

    def verify_artifact(self, *, root: str | Path = ".") -> bool:
        if not self.configured:
            return False
        path = Path(self.artifact_path)
        if not path.is_absolute():
            path = Path(root) / path
        if not path.exists() or not path.is_file():
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest().lower() == self.artifact_sha256.lower()

    def assert_primary_ready(self, *, root: str | Path = ".") -> None:
        if not self.configured:
            raise ValueError("clinical B guardian manifest is not fully configured")
        required = {"clinical_context_broadening","adversarial_claim_audit","privacy_oversight"}
        missing = required - set(self.intended_roles)
        if missing:
            raise ValueError(f"guardian manifest missing intended roles: {sorted(missing)}")
        if not self.verify_artifact(root=root):
            raise ValueError("clinical B guardian artifact hash/path verification failed")
