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
"refund"
```

## UI Design
- 退费页面
    * UI结构
        - 用户搜索栏：包含姓名、诊疗卡号、身份证号输入框和搜索按钮。 在同一行放置所有搜索输入框和按钮。
        - 用户信息显示区域：显示用户信息表格，包括诊疗卡号、姓名、电话、身份证号、地址、病人ID
        - 挂号信息显示区域：显示挂号信息表格，包括挂号日期、挂号科室、挂号医生、挂号类型、状态（待诊、已就诊、已退费）、已支付金额。每行有一个控制区域，仅当状态为‘待诊’时，显示‘退费’按钮
    * UI布局：
    	- ‘用户搜索栏’在页面顶部占用一行。
    	- ‘用户信息显示区域’和‘挂号信息显示区域'位于页面主体部分，上下排列，表格为固定高度，各占页面主体部分50%。即使没有数据也显示固定高度。
    * 事件响应：
    	- 点击’用户搜索栏‘的搜索按钮: 查询并填入’用户信息显示区域‘表格
    	- 选中‘用户信息显示区域’表格的一行: 查询并填入‘挂号信息显示区域’表格，对于状态为’待诊‘的’挂号信息‘显示’退费‘按钮。
    	- 点击’退费‘按钮: 弹出’确认退费对话框‘, 显示退费信息，有‘确认退费’和‘取消’两个按钮
    	- 点击’确认退费‘按钮: 执行退费操作，并将退费结果显示在对话框中。 
    	- 点击’关闭‘按钮: 刷新’挂号信息显示区域‘的表格。
    * 本模块实现和引用的端点
        - 搜索病人：GET /api/patients
        - 搜索某个病人的挂号：GET /api/patients/{patentId}/visits
        - 执行退费：POST /api/refund
    * 引用但由外部模块实现的端点
        - 无

## Endpoints to implement
```yaml
openapi: 3.0.0
info:
  title: Refund API
paths:
  /api/patients:
    get:
      summary: Search patients
      parameters:
      - name: "name"
          in: "query"
          required: false
          description: "姓名"
          schema:
            type: "string"
    `responses:
        '200':
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Patient'
components:
  schemas:
    Patient:
      type: object
      properties:
        patientId:
          type: string
        cardNumber:
          type: string
        name:
          type: string
        ...
```

## File list
```python
[
    {
        "path": "/refund_api_mock.js",
        "type": "api-mock.js",
        "description": "mock data for api of refund",
        "dependencies": [],
        "action": "Created"
    },
    {
        "path": "/refund.vue",
        "type": "Vue",
        "description": "ui of refund",
        "dependencies": ["/refund_api_mock.js"],
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
Requirement: Fill in the following missing information of 'Design Document' based on the contents of all INPUT sections. Try to use the same pattern as 'EXAMPLE' section above. 

Attention: 
- Use '##' to split sections, not '#', and '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote.
- you can call 'get-api' function to know more about endpoints of modules if necessary. 
- don't leave any '...' in code your generated.

Below is the format of 'Design Document' including description of each paragraph:
```
## Package name: Provide as Python str with python triple quoto, concise and clear, characters only use a combination of all lowercase and underscores

## UI Design: detail ui design according to REQ, should includes: 
    - 1. UI structure: describe each part of ui elements in page. for forms: describe their inputs, component should be used. for tables: describe their column names.
    - 2. UI layout: describe the layout/position of elements above. eg: row/column layout
    - 3. Event Handling: what should do when something user action happened.
    - 4.  endpoints referenced and implemented in this module.
    - 5. endpoints referenced but in implemented in other modules which can be understood by calling function 'get_api' to know the detail of endpoints.
NOTICE: 
    - output in Chinese.

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
    def __init__(self, name='', context=None, llm=None, type=None):
        super().__init__(name, context, llm, type=type)
        self.desc = "Based on the PRD, think about the system design, and design the corresponding APIs, " \
                    "data structures, library tables, processes, and paths. Please provide your design, feedback " \
                    "clearly and in detail."
        self.dest_artifact_type = ArtifactType.DESIGN
        self.prefix = ACTION_PREFIX
        self.instruction_prompt = INSTRUCTION
        self.example_prompt = FORMAT_EXAMPLE
        self.output_mapping = OUTPUT_MAPPING
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
