#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/11 14:43
@Author  : alexanderwu
@File    : action.py
"""
from abc import ABC, abstractmethod
from typing import Optional
import json
from pathlib import Path

from tenacity import retry, stop_after_attempt, wait_fixed

from metagpt.actions.action_output import ActionOutput
from metagpt.llm import LLM
from metagpt.utils.common import OutputParser
from metagpt.schema import Task, Event
from metagpt.logs import logger
from metagpt.artifact import Artifact, ArtifactType
from enum import Enum
from metagpt.utils.common import CodeParser

COMMENT_PROMPT = '''
please revise according to the comment below {comment_supplementary}

COMMENT: ```{comment}
```
'''

COMMENT_SUPPLEMENTARY = ', you can only output modified sections.'

SYSTEM_PROMPT = '''
{action_prefix}
'''

'''
the user question will have a few INPUT sections, one INSTRUCTION section which will reference contents in INPUT sections, 
and one optional EXAMPLE section at the end.
all sections will be divided by '----- <SECTION NAME> ------'.
'''

SECTION_PROMPT = '''
----- {type} -----
{content}

'''

TASK_UPDATE_PROMPT = '''
please revise the sections as required by these comments, you can only output sections that modified.
ATTENTION: Use '##' to SPLIT SECTIONS, not '#'. AND '## <SECTION_NAME>' SHOULD WRITE BEFORE the code and triple quote. Output carefully referenced "Format example" in format.

```
{update_description}
```
'''

DEPENDENCY_UPDATE_PROMPT = '''
One of dependent input '{changed_artifact_name}' has been changed. The Changed version is below after '-----'.
You must compare two versions first, then change {artifact_name_to_change} accordingly. 

----- New Version of '{changed_artifact_name}' -----
{changed_artifact_content}

'''

class PromptType(Enum):
    Default = "default"
    Comment = "comment"
    Task_Update = "task_update"
    Task_Create = "task_create"
    Dependency_Update = "dependency_update"
    Dependency_Create = "dependency_create"
    No_Action = "no_action"


class PromptCategory(Enum):
    EXAMPLE = "EXAMPLE",
    INSTRUCTION = "INSTRUCTION"


def get_api(module_names: list[str] = 'TODO'):
    print(f'get_api: {module_names}')
    ret_text = ''
    for module_name in module_names:
        path = Path(f'/Users/zhouquan/eclipse-workspace-new/Generated-metagpt/HEthics/input-docs/API_{module_name}.json')
        ret_text += SECTION_PROMPT.format(type=module_name, content=path.read_text())
    return ret_text


all_functions = [
    {
        'name': 'get_api',
        'description': 'to get the detail endpoints functionality/specification for public modules listed in "System Design" if you want to call some endpoints of these public modules.',
        'parameters': {
            'type': 'object',
            'properties': {
                'module_names': {
                    'type': 'array',
                    'description': 'name of the modules you want to know more about',
                    'items': {
                        'type': 'string'
                    }
                }
            },
            'required': ['module_names']
        }
    }
]


class Action(ABC):
    def __init__(self, name: str = '', context=None, llm: LLM = None, type: 'ActionType' = None):
        self.name: str = name  # TODO action name?
        self.type: 'ActionType' = type
        if llm is None:
            llm = LLM()
        self.llm = llm
        self.context = context
        self.prefix = ""
        self.profile = ""
        self.desc = ""
        self.content = ""
        self.instruct_content = None
        self._output_mapping = None
        self._output_cls_name = None
        # self.multiple_artifacts = False
        self.dest_artifact_type: ArtifactType = None
        # self.TASK_CREATE_PROMPT: str = 'TODO'  # not used
        self.instruction_prompt: str = 'TODO'
        self.example_prompt: str = None
        self.task_update_prompt: str = TASK_UPDATE_PROMPT
        self.dependency_update_prompt: str = DEPENDENCY_UPDATE_PROMPT

    def set_prefix(self, prefix, profile):
        """Set prefix for later usage"""
        self.prefix = prefix
        self.profile = profile

    def __str__(self):
        return self.__class__.__name__

    def __repr__(self):
        return self.__str__()

    async def _aask(self, prompt: str, system_msgs: Optional[list[str]] = None) -> str:
        """Append default prefix"""
        if not system_msgs:
            system_msgs = []
        system_msgs.append(self.prefix)
        return await self.llm.aask(prompt, system_msgs)

    # @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    async def _aask_v1(self, prompt: str, output_class_name: str,
                       output_data_mapping: dict,
                       simulate: str = None,
                       system_msgs: Optional[list[str]] = None) -> ActionOutput:
        """Append default prefix"""
        if not system_msgs:
            system_msgs = []
        system_msgs.append(self.prefix)
        content = None
        if simulate:
            content = simulate
            self.context.historyMessages.append(self.llm._user_msg(prompt))
            self.context.historyMessages.append(self.llm._assistant_msg(content))
        else:
            logger.debug(system_msgs)
            logger.debug(prompt)
            content = await self.llm.aask(prompt, system_msgs, history=self.context.historyMessages)
        logger.debug(content)
        output_class = ActionOutput.create_model_class(output_class_name, output_data_mapping)
        parsed_data = OutputParser.parse_data_with_mapping(content, output_data_mapping)

        logger.debug(json.dumps(parsed_data, indent=4))
        instruct_content = output_class(**parsed_data)
        return ActionOutput(content, instruct_content)

    async def _aask_v2(self, prompt: str, simulate_name: str = None, simulate: bool = False,
                       system_msgs: Optional[list[str]] = None, functions: list[str]=None) -> str:
        if not system_msgs:
            system_msgs = []
        # system_msgs.append(self.prefix)
        content = None
        path = self.context.env.workspace.rootPath / 'simulate' / simulate_name if simulate_name else None
        if simulate and path and path.exists():
            content = path.read_text()
            self.context.historyMessages.append(self.llm._user_msg(prompt))
            self.context.historyMessages.append(self.llm._assistant_msg(content))
        else:
            content = await self.llm.aask(prompt, system_msgs, history=self.context.historyMessages, functions=functions)
            # to persist for simulate
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
        logger.info(content)
        return content

    async def run(self, *args, **kwargs):
        """Run action"""
        raise NotImplementedError("The run method should be implemented in a subclass.")

    def _get_prompt(self, task: Task, prompt_type: PromptType = PromptType.Default, **kwargs) -> (str, PromptType):
        if prompt_type == PromptType.Comment:
            return self._get_prompt_(PromptType.Comment, **kwargs)
        else:
            if not task.source_artifact:  # task: direct change
                return self._get_prompt_(PromptType.Task_Update if task.artifact.content else PromptType.Task_Create, **kwargs)
            else:   # event: upstream change
                if not task.artifact.content:
                    return self._get_prompt_(PromptType.Dependency_Create, **kwargs)
                else:
                    return self._get_prompt_(PromptType.Dependency_Update, **kwargs)

    def _get_prompt_by_type(self, type: PromptCategory, artifact: Artifact):
        if type == PromptCategory.EXAMPLE:
            return self.example_prompt
        elif type == PromptCategory.INSTRUCTION:
            return self.instruction_prompt

    # @abstractmethod
    def _get_prompt_(self,  prompt_type: PromptType,  **kwargs) -> (str, PromptType):
        task = self.context.task
        logger.debug(f' getting prompt: {prompt_type.value} of artifact: {task.artifact.type.value}:{task.artifact.name}')
        if prompt_type == PromptType.Comment:
            return COMMENT_PROMPT.format(comment=kwargs['comment'], comment_supplementary=COMMENT_SUPPLEMENTARY if task.artifact.type != ArtifactType.CODE else ''), PromptType.Comment
        message_update = None
        message_dependency = ''
        for artifact in task.artifact.depend_artifacts:
            name = f'{artifact.type.value} {artifact.relative_path if artifact.type == ArtifactType.CODE else ""}'
            dependency_prompt = SECTION_PROMPT.format(type=f'INPUT: {name}', content=artifact.content if prompt_type != PromptType.Dependency_Update or artifact != task.source_artifact else artifact.previous_content)
            message_dependency += dependency_prompt
        message_dependency += SECTION_PROMPT.format(type='INSTRUCTION', content=self._get_prompt_by_type(PromptCategory.INSTRUCTION, task.artifact) \
                              + (SECTION_PROMPT.format(type='EXAMPLE',
                                                      content=self._get_prompt_by_type(PromptCategory.EXAMPLE, task.artifact))) if self.example_prompt else '')
        return_message = None
        if prompt_type == PromptType.Task_Update or prompt_type == PromptType.Dependency_Update:
            # message_dependency_prompt = self.INPUT_PROMPT
            # message_dependency = message_dependency_prompt.format(**dependencies)
            # if prompt_type == PromptType.Dependency_Update:
            #     message_dependency += SECTION_PROMPT.format(type=f'ORIGIN {task.source_artifact.get_name()}', content=task.source_artifact.previous_content)
            self.context.historyMessages.append(self.llm._user_msg(message_dependency))
            self.context.historyMessages.append(self.llm._assistant_msg(task.artifact.content))
            if prompt_type == PromptType.Task_Update:
                message_update_prompt = self.task_update_prompt
                message_update = message_update_prompt.format(update_description=task.description,  format_example=self._get_prompt_by_type(PromptCategory.EXAMPLE, task.artifact))
            else:  # Dependency_Update
                message_update_prompt = self.dependency_update_prompt
                message_update = message_update_prompt.format(changed_artifact_name=task.source_artifact.get_name(), artifact_name_to_change=task.artifact.get_name(), changed_artifact_content=task.source_artifact.content)
            return_message = message_update
        else:   # Depdency_Create
            return_message = message_dependency
        return return_message, prompt_type

    def _get_function_list(self, artifact: Artifact):
        return []
    async def process_task(self, task: Task) -> str:
        if not task.artifact:
            return ''

        self.context.todo = self
        self.context.task = task
        self.context.artifact = task.artifact
        prompt, prompt_type = self._get_prompt(task)
        logger.info(f'prompt: {prompt_type}')
        if prompt:
            function_list = self._get_function_list(task.artifact)
            functions = [function for function in all_functions if function['name'] in function_list]
            system_msg = [SYSTEM_PROMPT.format(action_prefix=self.prefix)] if self.prefix else []
            result = await self._aask_v2(prompt, simulate=True, functions=functions, system_msgs=system_msg,
                                         simulate_name=f'{task.artifact.type.value}_{prompt_type.value}_{task.artifact.name}')
            # return self._parse_result(result, task.artifact)
            if task.artifact.type == ArtifactType.CODE:  # TODO
                task.artifact.pending_content.append(CodeParser.parse_code(block="", text=result))
            else:
                task.artifact.parse_mapping = self._output_mapping
                task.artifact.parse(result)
            return result
        else:  # use artifact content directly or do nothing
            if task.description and not task.artifact.content:
                task.artifact.content = task.description
            if task.artifact.content:
                return task.artifact.content
            else:
                return ''

    async def comment(self, comment, use_functions=False) -> str:
        artifact = self.context.task.artifact
        function_list = self._get_function_list(artifact)
        functions = [function for function in all_functions if function['name'] in function_list]
        system_msg = [SYSTEM_PROMPT.format(action_prefix=self.prefix)] if self.prefix else []
        prompt, type = self._get_prompt(self.context.task, prompt_type=PromptType.Comment, comment=comment)
        result = await self._aask_v2(prompt, system_msgs=system_msg, simulate=True, simulate_name=f'comment_{artifact.name}', functions=functions if use_functions else None)
        return artifact.parse(result)

    def commit(self):
        artifact = self.context.artifact
        artifact.save()
        self.postprocess()
        # reset context after postprocess
        self.context.task = None
        self.context.todo = None
        self.context.artifact = None
        self.context.historyMessages = []
        self.context.env.publish_event(Event(artifact=artifact))
        return

    def create_artifacts(self, event):
        name = f'{self.dest_artifact_type.value}_{event.artifact.name.split("_", 1)[1]}'
        artifact = self.context.env.artifact_mgr.create_artifact(self.dest_artifact_type, name, path="docs")
        event.artifact.add_watch(artifact, self.type.name)
        return [artifact]

    def postprocess(self):
        pass