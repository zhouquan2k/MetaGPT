#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/9/2
@Author  : quan zhou
@File    : write_prd.py
"""
import shutil
from pathlib import Path
from typing import List

from metagpt.actions.action import Action, ActionOutput
from metagpt.const import WORKSPACE_ROOT
from metagpt.logs import logger
from metagpt.utils.common import CodeParser
from metagpt.utils.mermaid import mermaid_to_file
from metagpt.artifact.artifact import Artifact, ArtifactType
from metagpt.actions.action import USER_PROMPT
from metagpt.schema import Task
from metagpt.actions import PromptType
from pydantic import BaseModel



TASK_UPDATE_PROMPT = '''
Requirement: please revise the design as requests below, you can only output sections that modified. always output 'File List' section with correct file action. files that have action='Updated' indicate that this file need to be updated for this version of design.
Attention: Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote
---
{update_description}
'''

INPUT_PROMPT = """
# Requirement
{PRD}

# System Design
{SYSTEM-DESIGN}

# Format example
{format_example}

-----
Role: You are an architect; the goal is to design a java web application; You must follow the system design under the 'System Design' section. reuse 'public components' in 'system_design' as possible as you can. 
Requirement: Fill in the following missing information based on the context, note that all sections are response with code form separately
Max Output: 8192 chars or 2048 tokens. Try to use them up.
Attention: Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote.

## Package name: Provide as Python str with python triple quoto, concise and clear, characters only use a combination of all lowercase and underscores

## Implementation approach: Provide as Plain text. Analyze the difficult points of the requirements. don't repeat the design from 'System Design' here, just follow it.

## UI Design: detail ui design according to the 'UI Design Draft' in prd, should includes: 
    - 1. ui structure/items description 
    - 2. endpoints needed to contact with backend. you may need to use function call 'get_api' to know the detail endpoints from the specific module.

## File list: the list of ONLY REQUIRED files needed to write the program. You must design according to the relevant content in the System Design.  list all the files needed in the order of: Backend apis, Backend implementations, Frontend files.
Provided as list of json objects including following members:
- path: file relative paths under the package name above and file name 
- type: file type, for backend files, must be one of the values ['Service', 'ServiceImpl', 'DataObject', 'Vue', 'api.js']
- description: a section describing what contents should be placed in this file.
- dependencies: a list of file names that this file has dependency on, like: ServiceImpl and api.js depends on Service, Vue depends on api.js
- action: must be one of the values below: 
    - NoChange: for later design update, if this file need not to be changed
    - Created: all the files will have this action when it's first created
    - Updated: for later design update, if this file need to be updated for this design update
    - Deleted: for later design update, if this file need to be deleted for this design update

## Data structures and interface definitions: Use mermaid classDiagram code syntax, including classes and functions (with type annotations), CLEARLY MARK the RELATIONSHIPS between classes. The data structures SHOULD BE VERY DETAILED and the API should be comprehensive with a complete design. 

## Program call flow: Use sequenceDiagram code syntax, COMPLETE and VERY DETAILED, using CLASSES AND API DEFINED ABOVE accurately, covering the CRUD AND INIT of each object, SYNTAX MUST BE CORRECT.

## Anything UNCLEAR: Provide as Plain text. Make clear here.

"""
FORMAT_EXAMPLE = """
---
## Package name
```python
"account"
```
## Implementation approach
- Challenge 1. ..., approach: ...
- Challenge 2. ..., approach: ...
- Others ...

## File list
```python
[
    {
        "path": "/api/AccountService.java",
        "type": "Service",
        "description": "put account operations prototype in this api interface",
        "dependencies": [],
        "action": "NoChange"
    },
    {
        "path": "/api/Account.java",
        "type": "DataObject",
        "description": "Account data object used by api interface",
        "dependencies": [],
        "action": "Updated"
    },
    {
        "path": "/model/AccountServiceImpl.java",
        "type": "ServiceImpl",
        "description": "account service implemtations. ...",
        "dependencies": ["/api/Account.java", "/api/AccountService.java"],
        "action": "NoChange"
    },
    {
        "path": "/frontend/api/account-api.js",
        "type": "api.js",
        "description": "api of account",
        "dependencies": ["/api/AccountService.java"],
        "action": "NoChange"
    },
    {
        "path": "/frontend/view/AccountTransfer.vue",
        "type": "Vue",
        "description": "ui of account transfer",
        "dependencies": ["/frontend/api/account-api.js"],
        "action": "NoChange"
    },
    ...
]
```

## Data structures and interface definitions
```mermaid
classDiagram
    class Game{
        +int score
    }
    ...
    Game "1" -- "1" Food: has
```

## Program call flow
```mermaid
sequenceDiagram
    participant M as Main
    ...
    G->>M: end game
```

## UI Design
- Transfer Money Dialog
    * ui structure
        - destination account selection: drop down list
        - money need to be transferred: number input field
        - transfer button
    * endpoints called
        - to do the transfer: POST /account/transfer
        - to get the destination accounts constantly used: GET /account/friends
        
## Anything UNCLEAR
The requirement is clear to me.
---
"""


class CodeArtifact(BaseModel):
    path: str
    type: str
    description: str
    dependencies: list[str]
    action: str


OUTPUT_MAPPING = {
    "Implementation approach": {'python_type': (str, ...), 'type': 'text'},
    "Package name": {'python_type': (str, ...), 'type': 'python'},
    "File list": {'python_type': (List[CodeArtifact], ...), 'type': 'python'},
    "Data structures and interface definitions": {'python_type': (str, ...), 'type': 'mermaid'},
    "Program call flow":  {'python_type': (str, ...), 'type': 'mermaid'},
    "UI Design": {'python_type': (str, ...), 'type': 'text'},
    "Anything UNCLEAR": {'python_type': (str, ...), 'type': 'text'}
}


class WriteDesign(Action):
    def __init__(self, name, context=None, llm=None, type=None):
        super().__init__(name, context, llm, type=type)
        self.desc = "Based on the PRD, think about the system design, and design the corresponding APIs, " \
                    "data structures, library tables, processes, and paths. Please provide your design, feedback " \
                    "clearly and in detail."
        self.dest_artifact_type = ArtifactType.DESIGN
        self._output_mapping = OUTPUT_MAPPING
        self._output_cls_name = "design"
        self.INPUT_PROMPT = INPUT_PROMPT
        self.TASK_UPDATE_PROMPT = TASK_UPDATE_PROMPT
        self.FORMAT_EXAMPLE = FORMAT_EXAMPLE

    '''
    def _get_prompt_(self, prompt_type: PromptType, **kwargs) -> (str, PromptType):
        if prompt_type == PromptType.Dependency_Create:
            prd = self.context.artifact.get_dependency_by_type(ArtifactType.PRD, self.context.env.artifact_mgr)
            system_design = self.context.artifact.get_dependency_by_type(ArtifactType.SYSTEM_DESIGN, self.context.env.artifact_mgr)
            return PROMPT_TEMPLATE.format(requirement=prd.content, system_design=system_design.content, format_example=FORMAT_EXAMPLE), PromptType.Dependency_Create
        else:
            return super()._get_prompt_(prompt_type, **kwargs)
    '''

    def recreate_workspace(self, workspace: Path):
        try:
            shutil.rmtree(workspace)
        except FileNotFoundError:
            pass  # 文件夹不存在，但我们不在意
        workspace.mkdir(parents=True, exist_ok=True)

    def _save_prd(self, docs_path, resources_path, prd):
        prd_file = docs_path / 'prd.md'
        # quadrant_chart = CodeParser.parse_code(block="Competitive Quadrant Chart", text=prd)
        # mermaid_to_file(quadrant_chart, resources_path / 'competitive_analysis')
        logger.info(f"Saving PRD to {prd_file}")
        prd_file.write_text(prd)

    def _save_system_design(self, docs_path, resources_path, content):
        data_api_design = CodeParser.parse_code(block="Data structures and interface definitions", text=content)
        seq_flow = CodeParser.parse_code(block="Program call flow", text=content)
        mermaid_to_file(data_api_design, resources_path / 'data_api_design')
        mermaid_to_file(seq_flow, resources_path / 'seq_flow')
        system_design_file = docs_path / 'system_design.md'
        logger.info(f"Saving System Designs to {system_design_file}")
        system_design_file.write_text(content)
        Artifact(ArtifactType.DESIGN, content).save(self.context.env.workspace, 'docs', '1.md')

    def _save(self, context, system_design):
        if isinstance(system_design, ActionOutput):
            content = system_design.content
            ws_name = CodeParser.parse_str(block="Python package name", text=content)
        else:
            content = system_design
            ws_name = CodeParser.parse_str(block="Python package name", text=system_design)
        workspace = WORKSPACE_ROOT / ws_name
        self.recreate_workspace(workspace)
        docs_path = workspace / 'docs'
        resources_path = workspace / 'resources'
        docs_path.mkdir(parents=True, exist_ok=True)
        resources_path.mkdir(parents=True, exist_ok=True)
        self._save_prd(docs_path, resources_path, context[-1].content)
        self._save_system_design(docs_path, resources_path, content)

    def create_artifacts(self, event):  # means a task indicating an upstream artifact change, how to generate/change downstream artifacts by this action
        artifacts = super().create_artifacts(event)
        artifact = artifacts[0]
        system_design = self.context.env.artifact_mgr.get(ArtifactType.SYSTEM_DESIGN)
        system_design.add_watch(artifact, 'DESIGN')
        # artifact.depend_artifacts[ArtifactType.SYSTEM_DESIGN] = system_design
        return artifacts

    def postprocess(self):
        # generate new task to generate code
        artifact = self.context.artifact
        content = artifact.content
        resources_path = self.context.env.workspace.rootPath / 'docs'
        data_api_design = CodeParser.parse_code(block="Data structures and interface definitions", text=content)
        seq_flow = CodeParser.parse_code(block="Program call flow", text=content)
        try:
            mermaid_to_file(data_api_design, resources_path / 'data_api_design')
        except:
            pass
        try:
            mermaid_to_file(seq_flow, resources_path / 'seq_flow')
        except:
            pass
