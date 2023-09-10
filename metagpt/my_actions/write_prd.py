#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/9/2
@Author  : quan zhou
@File    : write_prd.py
"""
from typing import List, Tuple

from metagpt.actions import Action, ActionOutput, PromptType
from metagpt.schema import Task
from metagpt.actions.search_and_summarize import SearchAndSummarize
from metagpt.logs import logger
from metagpt.artifact import Artifact, ArtifactType
from metagpt.actions.action import USER_PROMPT
from metagpt.schema import UserStory

PROMPT_TEMPLATE = """
# Context
## Original Requirements
{source}

## Format example
{format_example}
-----
Role: You are a professional product manager; the goal is to write a user story in agile development and Scrum.
Requirements: According to the 'Original Requirements' of context, fill in the following missing information. If the requirements are unclear, ensure minimum viability and avoid excessive design
note that the section '** 项目背景' is the background of the whole project. you only need to describe the requirements about the content in '** 场景xxx' here
ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. Output carefully referenced "Format example" in format. Output all the content in Chinese.

## 原始需求: Provide as markdown text, place the polished COMPLETE original requirements under 'Original Requirements - 场景' in context here

## 用户故事: Provide as a json structure including following members
- User: This is the role of the user who wants to use this user story, e.g., bank customer, administrator, etc.
- Action: This is the action that the user wants the system to perform, e.g., online money transfer, view account balance, etc.
- Goal: This is the effect or goal the user hopes to achieve by completing the action, e.g., not having to go to the bank, being able to check the account balance at any time, etc.
- Priority: output P0 if it's mandatory for the higher-level user story. else output P1 ~ P3 accordingly 

## 子用户故事: provide as a list of json structure described above. You can break down a large user story into some smaller user stories that can be developed and tested separately. especially for some optional functions can be provided later.
Please list the sub-user stories as comprehensively as possible. as a reference you can treat a single UI page/dialog as an user story that needn't be broke down.  

## UI描述: Only Provided when no sub user story in '子用户故事' section. Provide as Plain text using multiple short sentences. Be simple. Describe each element or group of elements and their functions in one line, also provide a simple style description and layout description.

## 不清楚的点: Provide as Plain text as multiple short sentences. The unclear things which not mentioned in context and you want to make them clear, ask questions here.
"""

FORMAT_EXAMPLE = """
---
## 原始需求
在线完成转账业务

## 用户故事
```python
{
    "User": "银行客户",
    "Action: "在线转账",
    "Goal": "可以随时随地不用去银行就可以转账、查看余额"
}
```

## UI描述
- 转账金额: 输入框
- 目标账户选择: 从历史保存的收款人中选择
- 转账按钮

## 子用户故事
```python
[
    {
        "User": "银行客户",
        "Action": "从已记录的历史转账收款人中选择收款人",
        "Goal": "快速准确的输入收款人",
        "Priority": "P1"
    },
    {
        "User": "银行客户",
        "Action": "在转账后能收到确认信息",
        "Goal": "确保转账成功",
        "Priority": "P0"
    }
    ...
]
```

## 不清楚的点
...
---
"""
OUTPUT_MAPPING = {
    "原始需求": {'python_type': (str, ...), 'type': 'text'},
    "用户故事": {'python_type': (UserStory, ...), 'type': 'python'},
    "UI描述": {'python_type': (List[str], []), 'type': 'python'},
    "子用户故事": {'python_type': (List[UserStory], []), 'type': 'python'},
    "不清楚的点": {'python_type':(str, ...), 'type': 'text'}
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
