from metagpt.artifact import Workspace
from metagpt.logs import logger
from pathlib import Path


class Artifact:
    def __init__(self, name: str, workspace: Workspace, content: str = ''):
        self.name: str = name
        self.workspace: Workspace = workspace
        self.content: str = content
        self.file_path: Path = None

    def save(self, file_path):
        self.file_path = self.workspace.rootPath / file_path
        logger.info(f"Saving PRD to {self.file_path}")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(self.content)

    def load(self, file_path: str = None):
        pass
