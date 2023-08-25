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

from tenacity import retry, stop_after_attempt, wait_fixed

from metagpt.actions.action_output import ActionOutput
from metagpt.llm import LLM
from metagpt.utils.common import OutputParser
from metagpt.schema import Task, Event
from metagpt.logs import logger
from metagpt.artifact import Artifact
from enum import Enum


USER_PROMPT = '''
{user_prompt} 

REMEMBER: Always output the full PRD even when part of it need to be modified.   
'''


class PromptType(Enum):
    Task = "task"
    Comment = "comment"


class Action(ABC):
    def __init__(self, name: str = '', context=None, llm: LLM = None):
        self.name: str = name
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

    async def _aask_v2(self, prompt, simulate_name: str = None, simulate: bool = False, system_msgs: Optional[list[str]] = None) -> str:
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
            content = await self.llm.aask(prompt, system_msgs, history=self.context.historyMessages)
            if path:
                path.write_text(content)

        return content

    def _parse_result(self, content: str, artifact: Artifact):
        logger.debug(content)
        output_class = ActionOutput.create_model_class(self._output_cls_name, self._output_mapping)
        parsed_old_data = OutputParser.parse_data_with_mapping(artifact.new_content(), self._output_mapping)
        parsed_data = OutputParser.parse_data_with_mapping(content, self._output_mapping)
        combined_data = parsed_old_data | parsed_data

        logger.debug(json.dumps(parsed_data, indent=4))
        artifact.instruct_content = output_class(**combined_data)
        new_content = self._parsed_to_str(combined_data)
        artifact.pending_content.append(new_content)
        return new_content  # ActionOutput(content, instruct_content)

    def _parsed_to_str(self, parsed):
        str = ''
        for key, value in self._output_mapping.items():
            type = value['type']
            str += f'## {key}\n'
            if type != 'text':
                str += f'```{type}\n'
            str += f'{parsed[key]}'
            if type != 'text':
                str += '```\n\n'
            else:
                str += '\n\n'
        return str

    async def run(self, *args, **kwargs):
        """Run action"""
        raise NotImplementedError("The run method should be implemented in a subclass.")

    # @abstractmethod
    async def _get_prompt(self, prompt_type: PromptType, **vargs) -> str:
        return ''

    async def process_task(self, task: Task) -> str:
        self.context.todo = self
        self.context.task = task
        self.context.artifact = task.artifact
        task.artifact.load(self.context.env.workspace)
        if task.description:
            prompt = self._get_prompt(PromptType.Task, task=task)
            result = await self._aask_v2(prompt, simulate=True, simulate_name=f'{task.artifact.type.value}_{task.artifact.name}')
            return self._parse_result(result, task.artifact)
        else:
            return task.artifact.content

    async def comment(self, comment) -> str:
        prompt = self._get_prompt(PromptType.Comment, comment=comment)
        result = await self._aask_v2(prompt)
        return self._parse_result(result, self.context.artifact)

    def commit(self):
        artifact = self.context.artifact
        artifact.save(self.context.env.workspace)
        self.context.task = None
        self.context.todo = None
        self.context.artifact = None
        self.context.env.publish_event(Event(artifact=artifact))



