"""Load and validate the repository-wide connectome source registry.

The registry deliberately stores source identity and provenance separately from
the data payload. A FlyWire root ID and a MaleCNS body ID are different
namespaces; a cross-match artifact is not permission to silently rewrite one
into the other.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping


class RegistryError(ValueError):
    """Raised when a connectome registry violates the integration contract."""


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,64}$")
_REQUIRED_STAGES = {
    "annotation_audit",
    "target_selection",
    "checkpoint_preparation",
    "rollout",
}


@dataclass(frozen=True)
class RepositoryRecord:
    name: str
    url: str
    path: str
    commit: str
    role: str
    tier: str
    status: str
    license_note: str

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "RepositoryRecord":
        required = ("name", "url", "path", "commit", "role", "tier", "status")
        missing = [key for key in required if not str(value.get(key, "")).strip()]
        if missing:
            raise RegistryError(f"Repository record thieu truong: {', '.join(missing)}")
        commit = str(value["commit"]).lower()
        if not _COMMIT.fullmatch(commit):
            raise RegistryError(f"Commit khong hop le cho repo {value['name']}: {commit}")
        return cls(
            name=str(value["name"]),
            url=str(value["url"]),
            path=str(value["path"]),
            commit=commit,
            role=str(value["role"]),
            tier=str(value["tier"]),
            status=str(value["status"]),
            license_note=str(value.get("license_note", "")),
        )


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    source_repo: str
    path: str
    source_dataset: str
    id_namespace: str
    role: str
    promotion_status: str
    sha256: str | None = None
    notes: str = ""

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ArtifactRecord":
        required = (
            "artifact_id",
            "source_repo",
            "path",
            "source_dataset",
            "id_namespace",
            "role",
            "promotion_status",
        )
        missing = [key for key in required if not str(value.get(key, "")).strip()]
        if missing:
            raise RegistryError(f"Artifact record thieu truong: {', '.join(missing)}")
        sha256 = value.get("sha256")
        if sha256 is not None:
            sha256 = str(sha256).lower()
            if not _SHA256.fullmatch(sha256):
                raise RegistryError(f"SHA-256 khong hop le cho artifact {value['artifact_id']}")
        return cls(
            artifact_id=str(value["artifact_id"]),
            source_repo=str(value["source_repo"]),
            path=str(value["path"]),
            source_dataset=str(value["source_dataset"]),
            id_namespace=str(value["id_namespace"]),
            role=str(value["role"]),
            promotion_status=str(value["promotion_status"]),
            sha256=sha256,
            notes=str(value.get("notes", "")),
        )


@dataclass(frozen=True)
class ConnectomeRegistry:
    schema_version: str
    reviewed_at: str
    repositories: tuple[RepositoryRecord, ...]
    artifacts: tuple[ArtifactRecord, ...]
    primary_datasets: tuple[Mapping[str, Any], ...]
    policies: Mapping[str, Any]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "ConnectomeRegistry":
        schema_version = str(value.get("schema_version", "")).strip()
        if schema_version != "connectome-source-registry-1":
            raise RegistryError(f"schema_version khong duoc ho tro: {schema_version!r}")
        repositories = tuple(
            RepositoryRecord.from_mapping(item) for item in value.get("repositories", [])
        )
        artifacts = tuple(ArtifactRecord.from_mapping(item) for item in value.get("artifacts", []))
        registry = cls(
            schema_version=schema_version,
            reviewed_at=str(value.get("reviewed_at", "")),
            repositories=repositories,
            artifacts=artifacts,
            primary_datasets=tuple(value.get("primary_datasets", [])),
            policies=value.get("policies", {}),
        )
        registry.validate()
        return registry

    def validate(self, *, workspace_root: str | Path | None = None) -> None:
        repo_names = [repo.name for repo in self.repositories]
        if len(repo_names) != len(set(repo_names)):
            raise RegistryError("Ten repository bi trung trong registry")
        artifact_ids = [artifact.artifact_id for artifact in self.artifacts]
        if len(artifact_ids) != len(set(artifact_ids)):
            raise RegistryError("artifact_id bi trung trong registry")
        known_repos = set(repo_names)
        for artifact in self.artifacts:
            if artifact.source_repo not in known_repos and artifact.source_repo != "primary_source":
                raise RegistryError(
                    f"Artifact {artifact.artifact_id} tham chieu repo khong co trong registry: "
                    f"{artifact.source_repo}"
                )
            if artifact.promotion_status not in {"audit_only", "target_candidate", "verified"}:
                raise RegistryError(
                    f"promotion_status khong hop le cho {artifact.artifact_id}: "
                    f"{artifact.promotion_status}"
                )
        if workspace_root is not None:
            root = Path(workspace_root)
            for repo in self.repositories:
                repo_path = root / repo.path
                if not repo_path.exists():
                    raise RegistryError(f"Khong tim thay repo {repo.name}: {repo_path}")
            for artifact in self.artifacts:
                artifact_path = root / artifact.path
                if not artifact_path.exists():
                    raise RegistryError(f"Khong tim thay artifact {artifact.artifact_id}: {artifact_path}")
        stages = set(self.policies.get("promotion_stages", []))
        if stages != _REQUIRED_STAGES:
            raise RegistryError(
                "promotion_stages phai gom dung: " + ", ".join(sorted(_REQUIRED_STAGES))
            )

    def to_report(
        self,
        *,
        workspace_root: str | Path | None = None,
        verify_git: bool = False,
        verify_checksums: bool = False,
    ) -> dict[str, Any]:
        """Return a machine-readable report, optionally verifying pinned inputs."""

        self.validate(workspace_root=workspace_root)
        root = Path(workspace_root) if workspace_root is not None else None
        repo_report = []
        verification_failures: list[str] = []
        for repo in self.repositories:
            path = root / repo.path if root is not None else None
            row = {
                "name": repo.name,
                "path": repo.path,
                "commit": repo.commit,
                "exists": bool(path and path.exists()) if path else None,
                "role": repo.role,
                "tier": repo.tier,
                "status": repo.status,
            }
            if verify_git and path is not None and path.exists():
                try:
                    completed = subprocess.run(
                        [
                            "git",
                            f"-c",
                            f"safe.directory={path.resolve()}",
                            "-C",
                            str(path),
                            "rev-parse",
                            "HEAD",
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    observed = completed.stdout.strip().lower()
                    row["git_head"] = observed
                    row["git_head_matches"] = observed == repo.commit
                    if observed != repo.commit:
                        verification_failures.append(
                            f"repo {repo.name}: expected {repo.commit}, observed {observed}"
                        )
                except (OSError, subprocess.CalledProcessError) as exc:
                    row["git_head"] = None
                    row["git_head_matches"] = False
                    row["git_error"] = str(exc)
                    verification_failures.append(f"repo {repo.name}: git verification failed")
            repo_report.append(row)
        artifact_report = []
        for artifact in self.artifacts:
            path = root / artifact.path if root is not None else None
            row = {
                "artifact_id": artifact.artifact_id,
                "source_repo": artifact.source_repo,
                "source_dataset": artifact.source_dataset,
                "id_namespace": artifact.id_namespace,
                "role": artifact.role,
                "promotion_status": artifact.promotion_status,
                "exists": bool(path and path.exists()) if path else None,
                "size_bytes": path.stat().st_size if path and path.exists() else None,
                "sha256": artifact.sha256,
            }
            if verify_checksums and path is not None and path.exists() and artifact.sha256:
                digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        digest.update(chunk)
                observed = digest.hexdigest()
                row["sha256_observed"] = observed
                row["sha256_matches"] = observed == artifact.sha256
                if observed != artifact.sha256:
                    verification_failures.append(
                        f"artifact {artifact.artifact_id}: expected {artifact.sha256}, observed {observed}"
                    )
            artifact_report.append(row)
        return {
            "schema_version": self.schema_version,
            "reviewed_at": self.reviewed_at,
            "repository_count": len(repo_report),
            "artifact_count": len(artifact_report),
            "repositories": repo_report,
            "artifacts": artifact_report,
            "policies": dict(self.policies),
            "verification": {
                "git_checked": verify_git,
                "checksums_checked": verify_checksums,
                "failures": verification_failures,
            },
        }


def load_registry(path: str | Path) -> ConnectomeRegistry:
    source = Path(path)
    with source.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, Mapping):
        raise RegistryError("Registry root phai la JSON object")
    return ConnectomeRegistry.from_mapping(value)
