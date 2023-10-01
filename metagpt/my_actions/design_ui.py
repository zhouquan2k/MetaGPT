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
from pydantic import BaseModel


FORMAT_EXAMPLE = """
## Package name
```python
"account"
```

## UI Design
- Transfer Money Dialog
    * ui structure
       ...
    * endpoints referenced and implemented in this module.
        - to do the transfer: POST /account/transfer
        - to get the destination accounts constantly used: GET /account/friends
    * endpoints refencenced implemented by external modules.
        ...

## Endpoints to implement
```yaml
openapi: 3.0.0
info:
  title: Account API
paths:
  ...
components:
  ...
```

## File list
```python
[
    {
        "path": "/frontend/api/account_api_mock.js",
        "type": "api-mock.js",
        "description": "api of account",
        "dependencies": [],
        "action": "Created"
    },
    {
        "path": "/frontend/view/AccountTransfer.vue",
        "type": "Vue",
        "description": "ui of account transfer",
        "dependencies": ["/frontend/api/account_api_mock.js"],
        "action": "NoChange"
    },
    ...
]
```
        
## Anything UNCLEAR
The requirement is clear to me.
"""


ACTION_PREFIX = '''
You are an architect; the goal is to design a frontend part of a web application. 
'''

INSTRUCTION = '''
Requirement: Fill in the following missing information of 'Design Document' based on the contents of all INPUT sections. Output strictly according to the 'EXAMPLE' section above.

Attention: 
- Max Output: 8192 chars or 2048 tokens. Try to use them up.
- Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote.
- you can call 'get-api' function to know more about endpoints of modules if necessary. 
- the '...' in examples means content need you to fill in. you must supplement them. don't leave any '...' in code your generated.

Below is the format of 'Design Document' including description of each paragraph:
```
## Package name: Provide as Python str with python triple quoto, concise and clear, characters only use a combination of all lowercase and underscores

## UI Design: detail ui design according to the 'UI需求' in REQ, should includes: 
    - 1. describe structure/position/layout of ui element like form/table
        - list all form input items，their types for forms.
        - list all column names for tables.   
        - event handlers for ui elements 
        - don't lose any detail information from section 'UI需求' in REQ.
    - 2. endpoints referenced and implemented in this module. 
    - 3. endpoints referenced but in implemented in other modules which can be understood by calling function 'get_api' to know the detail of endpoints.
NOTICE: 
    - output in Chinese.
    - must include every detail information in section 'UI需求' in REQ.

## File list: the list of ONLY REQUIRED files needed to write the program. You must design according to the relevant content in the System Design.  list all the files needed in the order of: Backend api data objects, Backend api services, Backend implementations, Frontend files, Depended files should be listed first.
Provided as list of json objects including following members:
- path: file relative paths under the package name above and file name 
- type: file type, for backend files, must be one of the values ['Vue', 'api-mock.js']
- description: a section describing what contents should be placed in this file.
- dependencies: a list of file names that this file has dependency on, like: Vue depends on api-mock.js
- action: must be one of the values below: 
    - NoChange: for later design update, if this file need not to be changed
    - Created: all the files will have this action when it's first created
    - Updated: for later design update, if this file need to be updated for this design update
    - Deleted: for later design update, if this file need to be deleted for this design update

## Endpoints to implement: use openai 3.0.0 specification to list all the endpoints we should implement in this module. 
NOTICE: you must declare all the data objects referenced in this module under node 'components'.
the properties of each component can be derived from the ui description. eg table columns/form items if not specified explicitly. 

## Anything UNCLEAR: Provide as Plain text. Make clear here.
```
'''


class CodeArtifact(BaseModel):
    path: str
    type: str
    description: str
    dependencies: list[str]
    action: str


OUTPUT_MAPPING = {
    "Package name": {'python_type': (str, ...), 'type': 'python'},
    "File list": {'python_type': (List[CodeArtifact], ...), 'type': 'python'},
    "Endpoints to implement": {'python_type': (str, ...), 'type': 'text'},
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
        self.prefix = ACTION_PREFIX
        self.instruction_prompt = INSTRUCTION
        self.example_prompt = FORMAT_EXAMPLE
        self._output_mapping = OUTPUT_MAPPING
        self._output_cls_name = "design"

    def create_artifacts(self, event):  # means a task indicating an upstream artifact change, how to generate/change downstream artifacts by this action
        artifacts = super().create_artifacts(event)
        artifact = artifacts[0]
        system_design = self.context.env.artifact_mgr.get(ArtifactType.SYSTEM_DESIGN)
        system_design.add_watch(artifact, 'DESIGN')
        # prd = artifact.get_dependency_by_type(ArtifactType.PRD)
        # req = prd.get_dependency_by_type(ArtifactType.RAW_REQUIREMENT)
        # req.add_watch(artifact, 'DESIGN')
        return artifacts

    def _get_function_list(self, artifact: Artifact):
        return ['get_api']
