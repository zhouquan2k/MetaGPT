from metagpt.artifact import Workspace
from metagpt.logs import logger
from pathlib import Path
from enum import Enum
from pydantic import BaseModel
from typing import Any
from metagpt.actions.action_output import ActionOutput
from metagpt.utils.common import OutputParser
import json


class ArtifactType(Enum):
    RAW_REQUIREMENT = "REQ"
    SYSTEM_DESIGN = "SYSTEM-DESIGN"
    PRD = "PRD"
    DESIGN = "DESIGN"
    PROJECT = "PROJECT"  # USELESS
    CODE = "CODE"


class Artifact():
    def __init__(self, type: ArtifactType, name: str, path: str = None, parse_mapping=None):
        self.name: str = name
        self.type: ArtifactType = type
        self.path: str = path
        self.content: str = ''
        self.full_path: Path = None
        self.relative_path: str = None
        self.previous_content: str = None
        self.changes_text: str = ''
        self.changes: dict = {}
        self.impact_artifacts: dict = {}  # {ActionType: list[Artifact]}
        self.depend_artifacts: list['Artifact'] = []  # artifacts
        self.depend_artifacts_by_type: dict = {}  # {type: Artifact} , only one allowed
        self.sub_type: str = None
        self.parse_mapping: dict = parse_mapping

        self.pending_content: list[str] = []
        self.workspace: Workspace = None
        self.instruct_content: Any = None

    def get_name(self):
        return f'{self.name}'

    def new_content(self):
        return self.pending_content[-1] if len(self.pending_content) > 0 else self.content

    def parse(self, content: str):
        if self.parse_mapping:
            parsed_old_data = OutputParser.parse_data_with_mapping(self.new_content(), self.parse_mapping)
            parsed_data = OutputParser.parse_data_with_mapping(content, self.parse_mapping)
            combined_data = parsed_old_data | parsed_data
            output_class = ActionOutput.create_model_class(self.type.name, self.parse_mapping)
            self.instruct_content = output_class(**combined_data)
            self.changes = self.changes | parsed_data
            self.changes_text = self._parsed_to_str(self.changes)
            # logger.debug(json.dumps(parsed_data, indent=4, ensure_ascii=False))
            self.pending_content.append(self._parsed_to_str(combined_data))
        else:
            self.pending_content.append(content)

    def _parsed_to_str(self, parsed):
        str = ''
        for key, value in self.parse_mapping.items():
            if not key in parsed:
                continue
            type = value['type']
            str += f'## {key}\n'
            if type == 'python':  # TODO change to json?
                str += f'```{type}\n'
                str += json.dumps(parsed.get(key,{}), indent=4, ensure_ascii=False)
                str += '\n```\n\n'
            elif type != 'text':
                str += f'```{type}\n'
                str += parsed.get(key, '')
                str += '\n```\n\n'
            else:
                str += parsed.get(key, '')
                str += '\n\n'
        return str

    def init(self, workspace: Workspace):
        self.workspace = workspace
        self.relative_path = f'{self.path}/{self.name}'
        if not self.full_path:
            self.full_path = workspace.rootPath / self.relative_path
            self.full_path.parent.mkdir(parents=True, exist_ok=True)
        if self.full_path.exists() and not self.content:
            self._load()
            self.parse(self.content)

    def save(self):
        #if not self.changes:
        #    return
        logger.info(f"Saving {self.type.name}_{self.name} to {self.full_path}")
        self.full_path.write_text(self.new_content())
        self.previous_content = self.content
        self.content = self.new_content()
        self.pending_content = []

    def _load(self):
        logger.info(f"Loading from {self.full_path}")
        self.previous_content = self.content = self.full_path.read_text()

    def add_watch(self, artifact: 'Artifact', action_type: str):
        artifacts_by_type = self.impact_artifacts.setdefault(action_type, [])
        artifacts_by_type.append(artifact)
        artifact.depend_artifacts.append(self)
        artifact.depend_artifacts_by_type[self.type] = self

    def get_dependency_by_type(self, type: ArtifactType):
        return self.depend_artifacts_by_type[type]

    def get_persist_dict(self):
        return {'name': self.name, 'type': self.type.value, 'path': self.path,
                'sub_type': self.sub_type,
                'depend_artifacts': [artifact.relative_path for artifact in self.depend_artifacts]
                }


class ArtifactMgr():
    def __init__(self, workspace):
        self.byType: dict[ArtifactType, dict[str, Artifact]] = {}
        self.byPath: dict[str, Artifact] = {}
        self.workspace: Workspace = workspace
        self.path: Path = None

    @staticmethod
    def create_artifact_mgr(workspace: Workspace, is_load: bool = False):
        artifact_mgr = ArtifactMgr(workspace=workspace)
        artifact_mgr.path = workspace.rootPath / 'artifacts.json'
        # load from file
        if artifact_mgr.path.exists() and is_load:
            json_str = artifact_mgr.path.read_text()
            data_dict = json.loads(json_str)
            for type_name, type_dict in data_dict['artifacts'].items():
                for path, artifact_dict in type_dict.items():
                    artifact = artifact_mgr.create_artifact(ArtifactType(type_name), artifact_dict['name'], path=artifact_dict['path'])
                    if artifact_dict['sub_type']:
                        artifact.sub_type = artifact_dict['sub_type']
            for type_name, type_dict in data_dict['artifacts'].items():
                for path, artifact_dict in type_dict.items():
                    artifact = artifact_mgr.get_by_path(path)
                    artifact.depend_artifacts = [artifact_mgr.get_by_path(path) for path in artifact_dict['depend_artifacts']]
                    artifact.depend_artifacts_by_type = {artifact_mgr.get_by_path(path).type: artifact_mgr.get_by_path(path) for path in artifact_dict['depend_artifacts']}
        return artifact_mgr

    def create_artifact(self, artifact_type: ArtifactType, name: str, path: str = '', parse_mapping: dict = None):
        artifact = Artifact(type=artifact_type, name=name, path=path, parse_mapping=parse_mapping)
        artifact.init(self.workspace)

        artifacts_by_type = self.byType.setdefault(artifact_type, {})
        artifacts_by_type[artifact.relative_path] = artifact
        self.byPath[artifact.relative_path] = artifact
        return artifact

    def get(self, artifact_type: ArtifactType, name: str=None):
        by_type = self.byType.get(artifact_type, {})
        return list(by_type.values())[0] if not name and len(by_type) == 1 else by_type[name]

    def get_by_path(self, path: str):
        return self.byPath[path]

    def save(self):
        to_dump = {'workspace': self.workspace.get_persist_dict(), 'artifacts': {k.value: {k1: v1.get_persist_dict() for k1,v1 in v.items()} for k,v in self.byType.items()} }
        self.path.write_text(json.dumps(to_dump, indent=4, ensure_ascii=False))





