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

USER_PROMPT = '''
{user_prompt} 

REMEMBER: Always output the full PRD even when part of it need to be modified.   
'''

COMMENT_PROMPT = '''
please revise according to the comment below:

COMMENT: ```{comment}
```
'''


class PromptType(Enum):
    Default = "default"
    Comment = "comment"
    Task_Update = "task_update"
    Task_Create = "task_create"
    Dependency_Update = "dependency_update"
    Dependency_Create = "dependency_create"
    No_Action = "no_action"


def get_api(module_name: str = 'TODO'):
    print('get_api: ' + module_name)
    path = Path(f'/Users/zhouquan/Workspace/Generated-metagpt/HEthics/input-docs/API_{module_name}.json')
    return path.read_text()


code_functions = [
    {
        'name': 'get_api',
        'description': 'to get the detail endpoints functionality/specification for an public module listed in "System Design" if you want to call one of the endpoints of these public modules.',
        'parameters': {
            'type': 'object',
            'properties': {
                'module_name': {
                    'type': 'string',
                    'description': 'name of the module you want to know more about'
                }
            }
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
        self.INPUT_PROMPT: str = 'TODO'
        self.TASK_UPDATE_PROMPT: str = 'TODO'

        self.DEPENDENCY_UPDATE_INPUT_PROMPT: str = 'TODO'
        self.DEPENDENCY_UPDATE_PROMPT: str = 'TODO'
        self.DEPENDENCY_CREATE_PROMPT: str = 'TODO'
        self.FORMAT_EXAMPLE: str = 'TODO'

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

    async def _aask_v2(self, prompt, simulate_name: str = None, simulate: bool = False,
                       system_msgs: Optional[list[str]] = None, functions: list[str]=None) -> str:
        if not system_msgs:
            system_msgs = []
        system_msgs.append(self.prefix)
        content = None
        path = self.context.env.workspace.rootPath / 'simulate' / simulate_name if simulate_name else None
        if simulate and path and path.exists():
            content = path.read_text()
            self.context.historyMessages.append(self.llm._user_msg(prompt))
            self.context.historyMessages.append(self.llm._assistant_msg(content))
        else:
            logger.debug(system_msgs)
            logger.debug(prompt)
            content = await self.llm.aask(prompt, system_msgs, history=self.context.historyMessages, functions=functions)
            # to persist for simulate
            if path:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
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

    # @abstractmethod
    def _get_prompt_(self,  prompt_type: PromptType,  **kwargs) -> (str, PromptType):
        task = self.context.task
        logger.debug(f' getting format: {prompt_type.value} of artifact: {task.artifact.type.value}:{task.artifact.name}')
        if prompt_type == PromptType.Comment:
            return COMMENT_PROMPT.format(comment=kwargs['comment']), PromptType.Comment
        message_update = None
        dependencies = {artifactType.value: artifact.content for artifactType, artifact in
                        task.artifact.depend_artifacts.items()}
        dependencies['format_example'] = self.FORMAT_EXAMPLE
        if prompt_type == PromptType.Task_Update or prompt_type == PromptType.Dependency_Update:
            # message_dependency_prompt = self.TASK_UPDATE_INPUT_PROMPT if prompt_type == PromptType.Task_Update else self.DEPENDENCY_UPDATE_INPUT_PROMPT
            message_dependency_prompt = self.INPUT_PROMPT
            message_dependency = message_dependency_prompt.format(**dependencies)
            self.context.historyMessages.append(self.llm._user_msg(message_dependency))
            self.context.historyMessages.append(self.llm._assistant_msg(task.artifact.content))
            message_update_prompt = self.TASK_UPDATE_PROMPT if prompt_type == PromptType.Task_Update else self.DEPENDENCY_UPDATE_PROMPT
            message_update = message_update_prompt.format(update_description=task.description if prompt_type == PromptType.Task_Update else 'TODO',
                                                          format_example=self.FORMAT_EXAMPLE)
        else:   # Depdency_Create
            message_update_prompt = self.INPUT_PROMPT
            message_update = message_update_prompt.format(**dependencies)
        return message_update, prompt_type

    async def process_task(self, task: Task) -> str:
        if not task.artifact:
            return ''

        self.context.todo = self
        self.context.task = task
        self.context.artifact = task.artifact
        prompt, prompt_type = self._get_prompt(task)
        if prompt:
            functions = code_functions if task.artifact.type in [ArtifactType.DESIGN, ArtifactType.CODE] else None
            result = await self._aask_v2(prompt, simulate=True, functions=functions,
                                         simulate_name=f'{task.artifact.type.value}_{prompt_type.value}_{task.artifact.name}')
            # return self._parse_result(result, task.artifact)
            if task.artifact.type == ArtifactType.CODE:  # TODO
                task.artifact.content = CodeParser.parse_code(block="", text=result)
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

    async def comment(self, comment) -> str:
        prompt, type = self._get_prompt(self.context.task, prompt_type=PromptType.Comment, comment=comment)
        result = await self._aask_v2(prompt)
        return self._parse_result(result, self.context.artifact)

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
        return artifact

    def create_artifacts(self, event):
        artifact = self.context.env.artifact_mgr.create_artifact(self.dest_artifact_type, event.artifact.name, path=event.artifact.path)
        event.artifact.add_watch(artifact, self.type.name)
        return [artifact]

    def postprocess(self):
        pass