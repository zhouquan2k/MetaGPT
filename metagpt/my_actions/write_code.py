#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/9/10
@Author  : quan zhou
@File    : write_prd.py
"""
from metagpt.actions import WriteDesign
from metagpt.actions.action import Action, PromptType, PromptCategory
from metagpt.artifact import ArtifactType, Artifact
from metagpt.const import WORKSPACE_ROOT
from metagpt.logs import logger
from metagpt.schema import Message
from tenacity import retry, stop_after_attempt, wait_fixed
from metagpt.utils.common import CodeParser
from pathlib import Path

ACTION_PREFIX = '''
You are a professional programmer; the main goal is to write elegant, modular, easy to read and maintain code
'''

INSTRUCTION_PROMPT = """
## Code: Based on the following list and inputs above, implement file '{filename}'. Write code with triple quoto.
1. Do your best to implement THIS ONLY ONE FILE. ONLY USE EXISTING API. IF NO API, IMPLEMENT IT.
2. note to return only in code form, your code will be part of the entire project, so please implement complete, reliable, reusable code snippets
3. Attention1: ALWAYS USE STRONG TYPE AND EXPLICIT VARIABLE.
4. Attention2: YOU MUST FOLLOW "Data structures and interface definitions" in DESIGN section above. DONT CHANGE ANY DESIGN.
5. Think before writing: What should be implemented and provided in this document?
6. Do not use public member functions that do not exist in your design.
7. please follow the code example under section 'EXAMPLE' exactly
8. call functions to get module endpoint details only when they're required by this file.
"""

FORMAT_EXAMPLE = """
## Code: {filename}
```code
{example}
```
"""


class WriteCode(Action):
    def __init__(self, name="WriteCode", context: list[Message] = None, llm=None, type=None):
        super().__init__(name, context, llm, type=type)
        self.dest_artifact_type = ArtifactType.CODE
        self.prefix = ACTION_PREFIX
        self.example_prompt = FORMAT_EXAMPLE
        self.instruction_prompt = INSTRUCTION_PROMPT

    # TODO
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    async def write_code(self, prompt):
        code_rsp = await self._aask(prompt)
        code = CodeParser.parse_code(block="", text=code_rsp)
        return code

    # generate example by sub_type
    def _get_prompt_by_type(self, type: PromptCategory, artifact: Artifact):
        if type == PromptCategory.EXAMPLE:
            code_type = artifact.sub_type
            code_ext = artifact.full_path.suffix
            path = self.context.env.workspace.rootPath / 'examples' / f'{code_type}{code_ext}'
            return FORMAT_EXAMPLE.format(example=path.read_text(), filename=artifact.relative_path)
        elif type == PromptCategory.INSTRUCTION:
            return self.instruction_prompt.format(filename=artifact.relative_path)

    # only process action not equals to NoChange
    def _get_prompt_(self, prompt_type: PromptType, **kwargs) -> (str, PromptType):
        artifact = self.context.artifact
        design = artifact.get_dependency_by_type(ArtifactType.DESIGN)

        if prompt_type == PromptType.Dependency_Update:
            file_list = getattr(design.instruct_content, 'File list')
            package_name = getattr(design.instruct_content, 'Package name')
            for file in file_list:
                if f'{package_name}/{file.path}' == f'{artifact.path}/{artifact.name}':
                    if file.action == 'Updated':
                        # TODO Delete and other actions
                        return super()._get_prompt_(prompt_type, **kwargs)
                    else:
                        return None, PromptType.No_Action
        else:
            return super()._get_prompt_(prompt_type, **kwargs)
        return None, PromptType.No_Action

    def _get_function_list(self, artifact: Artifact):
        if artifact.sub_type not in ['DataObject', 'Service']:
            return ['get_api']
        else:
            return []


    def create_artifacts(self, event):
        artifact = event.artifact
        file_list = getattr(artifact.instruct_content, 'File list')
        package_name = getattr(artifact.instruct_content, 'Package name')
        system_design = self.context.env.artifact_mgr.get(ArtifactType.SYSTEM_DESIGN)
        artifacts = []
        for file in file_list:
            if file.path.startswith('/'):
                file.path = file.path[1:]
            path = Path(package_name) / file.path
            print(f'processing actifact {str(path.parent)}/{path.name}...')
            new_artifact = self.context.env.artifact_mgr.create_artifact(ArtifactType.CODE, path.name, str(path.parent))
            new_artifact.sub_type = file.type
            artifact.add_watch(new_artifact, "WRITE_CODE")
            system_design.add_watch(new_artifact, "WRITE_CODE")
            for dependency in file.dependencies:
                if dependency.startswith('/'):
                    dependency = package_name + '/' + dependency[1:]
                dependency_artifact = self.context.env.artifact_mgr.get_by_path(dependency)
                dependency_artifact.add_watch(new_artifact, "WRITE_CODE")
            artifacts.append(new_artifact)
        return artifacts
