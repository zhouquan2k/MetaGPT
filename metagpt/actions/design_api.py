#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/11 19:26
@Author  : alexanderwu
@File    : design_api.py
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

TASK_PROMPT = """
# Origin Version
{content}

# Comment
{description}

# Format example
{format_example}

-----
Role: You are an architect; the goal is to design a SOTA PEP8-compliant python system; make the best use of good open source tools
Requirement: The content below 'Origin Version' section is the design you previously given. now We gave some comments in 'Comment' section.  
please revise the sections as required by these comments, you can only output sections that modified.
Max Output: 8192 chars or 2048 tokens. Try to use them up.
Attention: Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote
"""

PROMPT_TEMPLATE = """
# Context
{context}

## Format example
{format_example}
-----
Role: You are an architect; the goal is to design a SOTA PEP8-compliant python system; make the best use of good open source tools
Requirement: Fill in the following missing information based on the context, note that all sections are response with code form separately
Max Output: 8192 chars or 2048 tokens. Try to use them up.
Attention: Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote.

## Implementation approach: Provide as Plain text. Analyze the difficult points of the requirements, select the appropriate open-source framework.

## Python package name: Provide as Python str with python triple quoto, concise and clear, characters only use a combination of all lowercase and underscores

## File list: Provided as Python list[str], the list of ONLY REQUIRED files needed to write the program(LESS IS MORE!). Only need relative paths, comply with PEP8 standards. ALWAYS write a main.py or app.py here

## Data structures and interface definitions: Use mermaid classDiagram code syntax, including classes (INCLUDING __init__ method) and functions (with type annotations), CLEARLY MARK the RELATIONSHIPS between classes, and comply with PEP8 standards. The data structures SHOULD BE VERY DETAILED and the API should be comprehensive with a complete design. 

## Program call flow: Use sequenceDiagram code syntax, COMPLETE and VERY DETAILED, using CLASSES AND API DEFINED ABOVE accurately, covering the CRUD AND INIT of each object, SYNTAX MUST BE CORRECT.

## Anything UNCLEAR: Provide as Plain text. Make clear here.

"""
FORMAT_EXAMPLE = """
---
## Implementation approach
We will ...

## Python package name
```python
"snake_game"
```

## File list
```python
[
    "main.py",
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
    "Python package name": {'python_type': (str, ...), 'type': 'python'},
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
        self._output_mapping = OUTPUT_MAPPING
        self._output_cls_name = "system_design"

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

    async def run(self, context, simulate=False, prompt=None):
        if not prompt:
            prompt = PROMPT_TEMPLATE.format(context=context, format_example=FORMAT_EXAMPLE)
        else:
            prompt = USER_PROMPT.format(user_prompt=prompt)
        simulate_content = Artifact.load(self.context.env.workspace, 'docs/DESIGN_1.md').content if simulate else None
        # system_design = await self._aask(prompt)
        system_design = await self._aask_v1(prompt, "system_design", OUTPUT_MAPPING, simulate=simulate_content)
        self._save(context, system_design)
        return system_design

    def _get_prompt(self, prompt_type: PromptType, task: Task = None, comment: str = None):
        if prompt_type == PromptType.Task:
            return TASK_PROMPT.format(content=task.artifact.content, description=task.description, format_example=FORMAT_EXAMPLE)
        elif prompt_type == PromptType.Comment:
            return comment

