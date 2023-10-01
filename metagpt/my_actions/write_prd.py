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
from pydantic import BaseModel


ACTION_PREFIX = '''
You are a professional product manager; the goal is to design a concise, usable, efficient product
'''
'''
## 子用户故事: provide as a list of json structure described above. 
You can break down a large user story into some smaller user stories that can be developed and tested separately. 
There are 2 main scenario that you can break down this story into sub user stories:
1. this story includes more than 1 ui page/screen/dialog, each should be 1 sub story.
2. some function can be implemented and tested separately and has a lower priority. 

Only Provide this section when no sub user story exist in '子用户故事' section. 
'''
INSTRUCTION = '''
Requirements: According to the requirement listed in 'REQ' section of input, fill in the following missing information. If the requirements are unclear, ensure minimum viability and avoid excessive design
ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. Output carefully referenced "Format example" in format. Output all the content in Chinese.

## 用户故事: Provide as a json structure including following members
- User: This is the role of the user who wants to use this user story, e.g., bank customer, administrator, etc.
- Action: This is the action that the user wants the system to perform, e.g., online money transfer, view account balance, etc.
- Goal: This is the effect or goal the user hopes to achieve by completing the action, e.g., not having to go to the bank, being able to check the account balance at any time, etc.
- Priority: output P0 if it's mandatory for the higher-level user story. else output P1 ~ P3 accordingly 

## 不清楚的点: Provide as Plain text as multiple short sentences. The unclear things which not mentioned in context and you want to make them clear, ask questions here.
'''

'''
## 原始需求: Provide as markdown text, place the polished COMPLETE original requirements under 'REQ' section in input here
## UI描述: Provide as Plain text using multiple short sentences. Describe each element or group of elements and their functions in one line, also provide a simple style description and layout description.
'''

FORMAT_EXAMPLE = """
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

## 不清楚的点
...
"""

'''
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

## UI描述
- 转账金额: 输入框
- 目标账户选择: 从历史保存的收款人中选择
- 转账按钮
'''

class UserStory(BaseModel):
    User: str
    Action: str
    Goal: str


OUTPUT_MAPPING = {
    # "原始需求": {'python_type': (str, ...), 'type': 'text'},
    "用户故事": {'python_type': (UserStory, ...), 'type': 'python'},
    # "UI描述": {'python_type': (List[str], []), 'type': 'python'},
    "子用户故事": {'python_type': (List[UserStory], []), 'type': 'python'},
    "不清楚的点": {'python_type':(str, ...), 'type': 'text'}
}


class WritePRD(Action):
    def __init__(self, name="", context=None, llm=None, type=None):
        super().__init__(name, context, llm, type=type)
        self.dest_artifact_type = ArtifactType.PRD
        self._output_mapping = OUTPUT_MAPPING
        self._output_cls_name = "prd"
        self.prefix = ACTION_PREFIX
        self.instruction_prompt = INSTRUCTION
        self.example_prompt = FORMAT_EXAMPLE
