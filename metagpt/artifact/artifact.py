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


class Artifact(BaseModel):
    name: str = ''
    type: ArtifactType
    path: str = ''
    content: str = ''
    full_path: Path = None
    previous_content: str = None
    changes_text: str = ''
    changes: dict = {}
    impact_artifacts: dict = {}  # {'ActionType': list[str]}
    depend_artifacts: dict = {}  # {'ArtifactType': str}
    sub_type: str = None
    parse_mapping: dict = None

    pending_content: list[str] = []
    workspace: Workspace = None
    instruct_content: Any = None

    def new_content(self):
        return self.pending_content[-1] if len(self.pending_content) > 0 else self.content

    def parse(self, content: str):
        if self.parse_mapping:
            parsed_old_data = OutputParser.parse_data_with_mapping(self.new_content(),
                                                                   self.parse_mapping) if self.content else {}
            parsed_data = OutputParser.parse_data_with_mapping(content, self.parse_mapping)
            combined_data = parsed_old_data | parsed_data
            output_class = ActionOutput.create_model_class(self.type.name, self.parse_mapping)
            self.instruct_content = output_class(**combined_data)
            self.changes = self.changes | parsed_data
            self.changes_text = self._parsed_to_str(self.changes)
            logger.debug(json.dumps(parsed_data, indent=4, ensure_ascii=False))
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
            if type == 'python':
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
        if not self.full_path:
            if self.type != ArtifactType.CODE:
                self.full_path = workspace.rootPath / self.path / f'{self.type.value}_{self.name}'
            else:
                self.full_path = workspace.rootPath / self.path / self.name
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
        self.content = self.full_path.read_text()

    def add_watch(self, artifact: 'Artifact', action_type: str):
        artifacts_by_type = self.impact_artifacts.setdefault(action_type, [])
        artifacts_by_type.append(artifact)
        artifact.depend_artifacts[self.type] = self

    def get_dependency_by_type(self, type: ArtifactType, artifact_mgr: 'ArtifactMgr'):
        return artifact_mgr.get(type, self.depend_artifacts[type].name)

    def get_persist_dict(self):
        return {'name': self.name, 'type': self.type.value, 'path': self.path,
                'depend_artifacts': {k.value: v.name for k,v in self.depend_artifacts.items()}}


class ArtifactMgr(BaseModel):
    byType: dict[ArtifactType, dict[str, Artifact]] = {}  #
    workspace: Workspace
    path: Path = None

    @staticmethod
    def create_artifact_mgr(workspace: Workspace, is_load: bool = False):
        artifact_mgr = ArtifactMgr(workspace=workspace)
        artifact_mgr.path = workspace.rootPath / 'artifacts.json'
        if artifact_mgr.path.exists() and is_load:
            json_str = artifact_mgr.path.read_text()
            data_dict = json.loads(json_str)
            for type_name, type_dict in data_dict['artifacts'].items():
                for name, artifact_dict in type_dict.items():
                    artifact_mgr.create_artifact(ArtifactType(type_name), name, path=artifact_dict['path'])
            for type_name, type_dict in data_dict['artifacts'].items():
                for name, artifact_dict in type_dict.items():
                    artifact = artifact_mgr.get(ArtifactType(type_name), name)
                    artifact.depend_artifacts = {ArtifactType(k): artifact_mgr.get(ArtifactType(k), v) for k,v in artifact_dict['depend_artifacts'].items()}
        return artifact_mgr

    def create_artifact(self, artifact_type: ArtifactType, name: str, path: str = '', parse_mapping: dict = None):
        artifact = Artifact(type=artifact_type, name=name, path=path, parse_mapping=parse_mapping)
        artifact.init(self.workspace)

        artifacts_by_type = self.byType.setdefault(artifact_type, {})
        artifacts_by_type[name] = artifact
        return artifact

    def get(self, artifact_type: ArtifactType, name: str=None):
        by_type = self.byType.get(artifact_type, {})
        return list(by_type.values())[0] if not name and len(by_type) == 1 else by_type[name]

    def save(self):
        to_dump = {'workspace': self.workspace.get_persist_dict(), 'artifacts': {k.value: {k1: v1.get_persist_dict() for k1,v1 in v.items()} for k,v in self.byType.items()} }
        self.path.write_text(json.dumps(to_dump, indent=4, ensure_ascii=False))





