from metagpt.artifact import Workspace
from metagpt.logs import logger
from pathlib import Path


class Artifact:
    def __init__(self, type: str, workspace: Workspace, content: str = ''):
        self.type: str = type
        self.workspace: Workspace = workspace
        self.content: str = content
        self.file_path: Path = None

    def save(self, path, name):
        self.file_path = self.workspace.rootPath / path / f'{self.type}_{name}'
        logger.info(f"Saving {self.type} to {self.file_path}")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(self.content)

    @staticmethod
    def load(workspace: Workspace, file_path: str = None) -> 'Artifact':
        logger.info(f"Loading from {file_path}")
        path = workspace.rootPath / file_path
        filename = path.name
        type = filename.split("_", 1)[0]
        content = path.read_text()
        return Artifact(type, workspace, content)





