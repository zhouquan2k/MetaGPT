#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/11 17:45
@Author  : alexanderwu
@File    : write_prd.py
"""
from typing import List, Tuple

from metagpt.actions import Action, ActionOutput, PromptType
from metagpt.schema import Task
from metagpt.actions.search_and_summarize import SearchAndSummarize
from metagpt.logs import logger
from metagpt.artifact import Artifact, ArtifactType
from metagpt.actions.action import USER_PROMPT

PROMPT_TEMPLATE = """
# Context
## Original Requirements
{source}

## Format example
{format_example}
-----
Role: You are a professional product manager; the goal is to design a concise, usable, efficient product
Requirements: According to the context, fill in the following missing information, note that each sections are returned in Python code triple quote form seperatedly. If the requirements are unclear, ensure minimum viability and avoid excessive design
ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. AND '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote. Output carefully referenced "Format example" in format.

## Original Requirements: Provide as Plain text, place the polished complete original requirements here

## Product Goals: Provided as Python list[str], up to 3 clear, orthogonal product goals. If the requirement itself is simple, the goal should also be simple

## User Stories: Provided as Python list[str], up to 5 scenario-based user stories, If the requirement itself is simple, the user stories should also be less

## Requirement Analysis: Provide as Plain text. Be simple. LESS IS MORE. Make your requirements less dumb. Delete the parts unnessasery.

## Requirement Pool: Provided as Python list[str, str], the parameters are requirement description, priority(P0/P1/P2), respectively, comply with PEP standards; no more than 5 requirements and consider to make its difficulty lower

## UI Design draft: Provide as Plain text. Be simple. Describe the elements and functions, also provide a simple style description and layout description.

## Anything UNCLEAR: Provide as Plain text. Make clear here.
"""

FORMAT_EXAMPLE = """
---
## Original Requirements
The boss ... 

## Product Goals
```python
[
    "Create a ...",
]
```

## User Stories
```python
[
    "As a user, ...",
]
```

## Requirement Analysis
The product should be a ...

## Requirement Pool
```python
[
    ("End game ...", "P0")
]
```

## UI Design draft
Give a basic function description, and a draft

## Anything UNCLEAR
There are no unclear points.
---
"""
OUTPUT_MAPPING = {
    "Original Requirements": {'python_type': (str, ...), 'type': 'text'},
    "Product Goals": {'python_type': (List[str], ...), 'type': 'python'},
    "User Stories": {'python_type': (List[str], ...), 'type': 'python'},
    # "Competitive Analysis": (List[str], ...),
    # "Competitive Quadrant Chart": (str, ...),
    "Requirement Analysis": {'python_type': (str, ...), 'type': 'text'},
    "Requirement Pool": {'python_type': (List[Tuple[str, str]], ...), 'type': 'python'},
    "UI Design draft": {'python_type': (str, ...), 'type': 'text'},
    "Anything UNCLEAR": {'python_type':(str, ...), 'type': 'text'}
}


TASK_UPDATE_PROMPT = '''
# Origin Version
{content}

# Comments
{description}

# Format example
{format_example}

-----
Role: You are a professional product manager; the goal is to design a concise, usable, efficient product
Requirement: The content below 'Origin Version' section is the design you previously given. now We gave some comments in 'Comments' section.  
please revise the sections as required by these comments, you can only output sections that modified.
ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. AND '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote. Output carefully referenced "Format example" in format.

## Original Requirements: Provide as Plain text, place the polished complete original requirements here

## Product Goals: Provided as Python list[str], up to 3 clear, orthogonal product goals. If the requirement itself is simple, the goal should also be simple

## User Stories: Provided as Python list[str], up to 5 scenario-based user stories, If the requirement itself is simple, the user stories should also be less

## Requirement Analysis: Provide as Plain text. Be simple. LESS IS MORE. Make your requirements less dumb. Delete the parts unnessasery.

## Requirement Pool: Provided as Python list[str, str], the parameters are requirement description, priority(P0/P1/P2), respectively, comply with PEP standards; no more than 5 requirements and consider to make its difficulty lower

## UI Design draft: Provide as Plain text. Be simple. Describe the elements and functions, also provide a simple style description and layout description.

## Anything UNCLEAR: Provide as Plain text. Make clear here.
'''

TASK_CREATE_PROMPT = '''
TODO
'''

DEPENDENCY_CREATE_PROMPT = PROMPT_TEMPLATE

DEPENDENCY_UPDATE_PROMPT='''
TODO
'''


class WritePRD(Action):
    def __init__(self, name="", context=None, llm=None):
        super().__init__(name, context, llm)
        self.dest_artifact_type = ArtifactType.PRD
        self.DEPENDENCY_CREATE_PROMPT = DEPENDENCY_CREATE_PROMPT
        self.DEPENDENCY_UPDATE_PROMPT = DEPENDENCY_UPDATE_PROMPT
        self.TASK_UPDATE_PROMPT = TASK_UPDATE_PROMPT
        self.FORMAT_EXAMPLE = FORMAT_EXAMPLE
        self._output_mapping = OUTPUT_MAPPING
        self._output_cls_name = "prd"

    async def run(self, requirements, simulate=False, prompt=None, *args, **kwargs) -> ActionOutput:
        sas = SearchAndSummarize()
        # rsp = await sas.run(context=requirements, system_text=SEARCH_AND_SUMMARIZE_SYSTEM_EN_US)
        rsp = ""
        info = f"### Search Results\n{sas.result}\n\n### Search Summary\n{rsp}"
        if sas.result:
            logger.info(sas.result)
            logger.info(rsp)

        simulate_content = Artifact.load(self.context.env.workspace, 'docs/PRD_1.md').content if simulate else None

        if not prompt:  # first
            prompt = PROMPT_TEMPLATE.format(requirements=requirements, search_information=info,
                                            format_example=FORMAT_EXAMPLE)
        else:
            prompt = USER_PROMPT.format(user_prompt=prompt)
        logger.debug(prompt)
        prd = await self._aask_v1(prompt, "prd", OUTPUT_MAPPING, simulate=simulate_content)
        Artifact(ArtifactType.PRD, prd.content).save(self.context.env.workspace, 'docs', '1.md')
        return prd
