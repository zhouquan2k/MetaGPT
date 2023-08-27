from pathlib import Path
import os
from pydantic import BaseModel


class Workspace(BaseModel):
    name: str
    rootPath: Path = None

    @staticmethod
    def init_workspace(name: str, root_path: str) -> 'Workspace':
        workspace = Workspace(name=name)
        workspace.rootPath = Path(root_path) / name
        os.makedirs(workspace.rootPath, exist_ok=True)
        return workspace
