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

from metagpt.actions import Action, ActionOutput
from metagpt.const import WORKSPACE_ROOT
from metagpt.logs import logger
from metagpt.utils.common import CodeParser
from metagpt.utils.mermaid import mermaid_to_file
from metagpt.artifact.artifact import Artifact, ArtifactType
from metagpt.actions.action import USER_PROMPT
from metagpt.schema import Task
from metagpt.actions import PromptType

DEPENDENCY_PROMPT = """
TODO
"""

TASK_PROMPT = """
# Origin Version
{content}

# Comment
{description}

# Format example
{format_example}

-----
Role: You are an architect; the goal is to design a SOTA PEP8-compliant python system; make the best use of good open source tools
Requirement: The content under 'Origin Version' section is the design you previously given. now We gave some comments in 'Comment' section.  
please revise the sections as required by these comments, only output sections that modified.
Max Output: 8192 chars or 2048 tokens. Try to use them up.
Attention: Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote
"""

PROMPT_TEMPLATE = """
# Requirement
{requirement}

# System Design
{system_design}

# Format example
{format_example}

-----
Role: You are an architect; the goal is to design a java web application; You must follow the system design under the 'System Design' section. reuse 'public components' in 'system_design' as possible as you can. 
Requirement: Fill in the following missing information based on the context, note that all sections are response with code form separately
Max Output: 8192 chars or 2048 tokens. Try to use them up.
Attention: Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote.

## Implementation approach: Provide as Plain text. Analyze the difficult points of the requirements, select the appropriate open-source framework.

## Package name: Provide as Python str with python triple quoto, concise and clear, characters only use a combination of all lowercase and underscores

## File list: Provided as Python list[str], the list of ONLY REQUIRED files needed to write the program(LESS IS MORE!). Only need relative paths under the packege name above.

## Data structures and interface definitions: Use mermaid classDiagram code syntax, including classes and functions (with type annotations), CLEARLY MARK the RELATIONSHIPS between classes. The data structures SHOULD BE VERY DETAILED and the API should be comprehensive with a complete design. 

## Program call flow: Use sequenceDiagram code syntax, COMPLETE and VERY DETAILED, using CLASSES AND API DEFINED ABOVE accurately, covering the CRUD AND INIT of each object, SYNTAX MUST BE CORRECT.

## Anything UNCLEAR: Provide as Plain text. Make clear here.

"""
FORMAT_EXAMPLE = """
---
## Implementation approach
- Challenge 1. ..., approach: ...
- Challenge 2. ..., approach: ...
- Others ...

## Package name
```python
"snake_game"
```

## File list
```python
[
    "main.java",
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

## Anything UNCLEAR
The requirement is clear to me.
---
"""

OUTPUT_MAPPING = {
    "Implementation approach": {'python_type': (str, ...), 'type': 'text'},
    "Package name": {'python_type': (str, ...), 'type': 'python'},
    "File list": {'python_type': (List[str], ...), 'type': 'python'},
    "Data structures and interface definitions": {'python_type': (str, ...), 'type': 'mermaid'},
    "Program call flow":  {'python_type': (str, ...), 'type': 'mermaid'},
    "Anything UNCLEAR": {'python_type': (str, ...), 'type': 'text'}
}


class WriteDesign(Action):
    def __init__(self, name, context=None, llm=None):
        super().__init__(name, context, llm)
        self.desc = "Based on the PRD, think about the system design, and design the corresponding APIs, " \
                    "data structures, library tables, processes, and paths. Please provide your design, feedback " \
                    "clearly and in detail."
        self.dest_artifact_type = ArtifactType.DESIGN
        self._output_mapping = OUTPUT_MAPPING
        self._output_cls_name = "design"
        self.DEPENDENCY_CREATE_PROMPT = PROMPT_TEMPLATE
        self.FORMAT_EXAMPLE = FORMAT_EXAMPLE

    def _get_prompt_(self, prompt_type: PromptType, **kwargs) -> (str, PromptType):
        if prompt_type == PromptType.Dependency_Create:
            prd = self.context.artifact.get_dependency_by_type(ArtifactType.PRD, self.context.env.artifact_mgr)
            system_design = self.context.artifact.get_dependency_by_type(ArtifactType.SYSTEM_DESIGN, self.context.env.artifact_mgr)
            return PROMPT_TEMPLATE.format(requirement=prd.content, system_design=system_design.content, format_example=FORMAT_EXAMPLE), PromptType.Dependency_Create
        else:
            return super()._get_prompt_(prompt_type, **kwargs)

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

    def commit(self):
        artifact = super().commit()
        content = artifact.content
        resources_path = self.context.env.workspace.rootPath / 'docs'
        data_api_design = CodeParser.parse_code(block="Data structures and interface definitions", text=content)
        seq_flow = CodeParser.parse_code(block="Program call flow", text=content)
        mermaid_to_file(data_api_design, resources_path / 'data_api_design')
        mermaid_to_file(seq_flow, resources_path / 'seq_flow')

    def create_artifact(self, event):
        artifact = super().create_artifact(event)
        system_design = self.context.env.artifact_mgr.get(ArtifactType.SYSTEM_DESIGN)
        artifact.depend_artifacts[ArtifactType.SYSTEM_DESIGN.value]=system_design.name
        return artifact



