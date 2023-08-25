from metagpt.artifact import Workspace
from metagpt.logs import logger
from pathlib import Path
from enum import Enum


class ArtifactType(Enum):
    RAW_REQUIREMENT = "REQ"
    PRD = "PRD"
    DESIGN = "DESIGN"
    PROJECT = "PROJECT"


class Artifact:
    def __init__(self, type: ArtifactType, name: str, content: str = None, path: str = '', full_path=None):
        self.type: ArtifactType = type
        # self.workspace: Workspace = workspace
        self.name: str = name
        self.path: str = path
        self.content: str = content
        self.full_path: Path = full_path
        self.pending_content: list[str] = []
        self.instruct_content = None
        self.previous_content: str = None

    def new_content(self):
        return self.pending_content[-1] if len(self.pending_content) > 0 else self.content

    def _init(self, workspace: Workspace):
        if not self.full_path:
            self.full_path = workspace.rootPath / self.path / f'{self.type.value}_{self.name}'
            self.full_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, workspace: Workspace):
        self._init(workspace)
        logger.info(f"Saving {self.type.name}_{self.name} to {self.full_path}")
        self.full_path.write_text(self.new_content())
        self.previous_content = self.content
        self.content = self.new_content
        self.pending_content = []


    def load(self, workspace: Workspace):
        self._init(workspace)
        if self.full_path.exists():
            logger.info(f"Loading from {self.full_path}")
            self.content = self.full_path.read_text()

    # TODO
    '''
    @staticmethod
    def load(workspace: Workspace, file_path: str = None) -> 'Artifact':
        logger.info(f"Loading from {file_path}")
        path = workspace.rootPath / file_path
        filename = path.name
        type_str = filename.split("_", 1)[0]
        name_str = filename.split("_", 1)[1]
        content = path.read_text()
        return Artifact(ArtifactType(type_str), name_str, content=content, full_path=path)
    '''




