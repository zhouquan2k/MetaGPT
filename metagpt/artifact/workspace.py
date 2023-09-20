from pathlib import Path
import os
from pydantic import BaseModel


class Workspace(BaseModel):
    name: str
    rootPath_: str = None
    rootPath: Path = None

    @staticmethod
    def init_workspace(name: str, root_path: str) -> 'Workspace':
        workspace = Workspace(name=name)
        workspace.rootPath = Path(root_path) / name
        workspace.rootPath_ = str(workspace.rootPath.resolve())
        os.makedirs(workspace.rootPath, exist_ok=True)
        return workspace

    def get_persist_dict(self):
        return {'name': self.name, 'root_path': self.rootPath_}
