from metagpt.artifact import Workspace
from metagpt.logs import logger
from pathlib import Path
from enum import Enum
from pydantic import BaseModel
from typing import Any


class ArtifactType(Enum):
    RAW_REQUIREMENT = "REQ"
    PRD = "PRD"
    DESIGN = "DESIGN"
    PROJECT = "PROJECT"


class Artifact(BaseModel):
    name: str = ''
    type: ArtifactType
    name: str
    path: str = ''
    content: str = ''
    full_path: Path = None
    previous_content: str = None
    changes_text: str = ''
    changes: dict = {}
    impact_artifacts: dict = {}  # ['ActionType': list[str]]

    pending_content: list[str] = []
    workspace: Workspace = None
    instruct_content: Any = None

    def new_content(self):
        return self.pending_content[-1] if len(self.pending_content) > 0 else self.content

    def init(self, workspace: Workspace):
        self.workspace = workspace
        if not self.full_path:
            self.full_path = workspace.rootPath / self.path / f'{self.type.value}_{self.name}'
            self.full_path.parent.mkdir(parents=True, exist_ok=True)
        if self.full_path.exists() and not self.content:
            self._load()

    def save(self):
        if not self.changes:
            return
        logger.info(f"Saving {self.type.name}_{self.name} to {self.full_path}")
        self.full_path.write_text(self.new_content())
        self.previous_content = self.content
        self.content = self.new_content()
        self.pending_content = []

    def _load(self):
        logger.info(f"Loading from {self.full_path}")
        self.content = self.full_path.read_text()

    def add_watch(self, artifact: 'Artifact'):
        artifacts_by_type = self.impact_artifacts.setdefault(artifact.type.value, [])
        artifacts_by_type.append(artifact.name)


class ArtifactMgr(BaseModel):
    byType: dict[str, dict[str, Artifact]] = {}  #
    workspace: Workspace
    path: Path = None

    @staticmethod
    def create_artifact_mgr(workspace: Workspace):
        artifact_mgr = ArtifactMgr(workspace=workspace)
        artifact_mgr.path = workspace.rootPath / 'artifacts.json'
        return artifact_mgr

    def create_artifact(self, artifact_type: ArtifactType, name: str, path: str = ''):
        artifact = Artifact(type=artifact_type, name=name, path=path)
        artifact.init(self.workspace)

        artifacts_by_type = self.byType.setdefault(artifact_type.value, {})
        artifacts_by_type[name] = artifact
        return artifact

    def get(self, artifact_type: ArtifactType, name: str):
        return self.byType.get(artifact_type.value, {})[name]

    def save(self):
        self.path.write_text(self.json(indent=4))



