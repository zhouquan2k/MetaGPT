#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/9/10
@Author  : quan zhou
@File    : write_prd.py
"""
from metagpt.actions import WriteDesign
from metagpt.actions.action import Action, PromptType
from metagpt.artifact import ArtifactType
from metagpt.const import WORKSPACE_ROOT
from metagpt.logs import logger
from metagpt.schema import Message
from tenacity import retry, stop_after_attempt, wait_fixed
from metagpt.utils.common import CodeParser

PROMPT_TEMPLATE = """
NOTICE
Role: You are a professional programmer; the main goal is to write elegant, modular, easy to read and maintain code 
ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. Output format carefully referenced "Format example".

## Code: {filename} Write code with triple quoto, based on the following list and context.
1. Do your best to implement THIS ONLY ONE FILE. ONLY USE EXISTING API. IF NO API, IMPLEMENT IT.
2. Requirement: Based on the context, implement one following code file, note to return only in code form, your code will be part of the entire project, so please implement complete, reliable, reusable code snippets
3. Attention1: ALWAYS USE STRONG TYPE AND EXPLICIT VARIABLE.
4. Attention2: YOU MUST FOLLOW "Data structures and interface definitions". DONT CHANGE ANY DESIGN.
5. Think before writing: What should be implemented and provided in this document?
6. Do not use public member functions that do not exist in your design.
7. please follow the code example under section 'Format example' exactly

-----
# Design
{design}
-----
# System_Design
{system_design}
-----
# Format example
## Code: {filename}
```java
{example}
```
-----
"""


class WriteCode(Action):
    def __init__(self, name="WriteCode", context: list[Message] = None, llm=None, type=None):
        super().__init__(name, context, llm, type=type)
        self.dest_artifact_type = ArtifactType.CODE

    # TODO
    @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    async def write_code(self, prompt):
        code_rsp = await self._aask(prompt)
        code = CodeParser.parse_code(block="", text=code_rsp)
        return code

    def _get_prompt_(self, prompt_type: PromptType, **kwargs) -> (str, PromptType):
        artifact = self.context.artifact
        design = artifact.get_dependency_by_type(ArtifactType.DESIGN, self.context.env.artifact_mgr)
        if prompt_type == PromptType.Dependency_Create:
            system_design = self.context.env.artifact_mgr.get(ArtifactType.SYSTEM_DESIGN)
            code_type = artifact.sub_type
            code_ext = artifact.full_path.suffix
            path = self.context.env.workspace.rootPath / 'examples' / f'{code_type}{code_ext}'
            example = path.read_text()
            return PROMPT_TEMPLATE.format(design=design.content, system_design=system_design.content, filename=self.context.artifact.full_path, example=example), PromptType.Dependency_Create
        elif prompt_type == PromptType.Dependency_Update:
            file_list = getattr(design.instruct_content, 'File list')
            for file in file_list:
                if file.path == f'/{artifact.path}/{artifact.name}':
                    if file.action == 'Update':
                    # TODO Delete
                        return super()._get_prompt_(prompt_type, **kwargs)
                    else:
                        return None, PromptType.No_Action
        else:
            return super()._get_prompt_(prompt_type, **kwargs)


    def create_artifacts(self, event):
        artifact = event.artifact
        file_list = getattr(artifact.instruct_content, 'File list')
        package_name = getattr(artifact.instruct_content, 'Package name')
        system_design = self.context.env.artifact_mgr.get(ArtifactType.SYSTEM_DESIGN)
        artifacts = []
        for file in file_list:
            path = self.context.env.workspace.rootPath / f'src/main/java/{package_name}' / file.path
            new_artifact = self.context.env.artifact_mgr.create_artifact(ArtifactType.CODE, path.name, path.parent.name)
            new_artifact.sub_type = file.type
            # TODO assign task to write_code
            artifact.add_watch(new_artifact, "WRITE_CODE")
            system_design.add_watch(new_artifact, "WRITE_CODE")
            artifacts.append(new_artifact)

        return artifacts
