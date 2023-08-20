from pathlib import Path
import os


class Workspace:
    def __init__(self, name: str, root_path: str):
        self.name: str = name
        self.rootPath: Path = Path(root_path) / name
        os.makedirs(self.rootPath, exist_ok=True)
        # self.docs_path: Path = Path(root_path) / name / 'doc'

