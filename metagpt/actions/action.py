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
from metagpt.artifact import Artifact, ArtifactType
from enum import Enum

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


class Action(ABC):
    def __init__(self, name: str = '', context=None, llm: LLM = None):
        self.name: str = name  # TODO action name?
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
        self.multiple_artifacts = False
        self.dest_artifact_type: ArtifactType = None
        self.TASK_CREATE_PROMPT: str = 'TODO'
        self.TASK_UPDATE_PROMPT: str = 'TODO'
        self.DEPENDENCY_CREATE_PROMPT: str = 'TODO'
        self.DEPENDENCY_UPDATE_PROMPT: str = 'TODO'
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
                       system_msgs: Optional[list[str]] = None) -> str:
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
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)

        return content

    def _parse_result(self, content: str, artifact: Artifact):
        logger.debug(content)
        output_class = ActionOutput.create_model_class(self._output_cls_name, self._output_mapping)
        parsed_old_data = OutputParser.parse_data_with_mapping(artifact.new_content(), self._output_mapping) if artifact.content else {}
        parsed_data = OutputParser.parse_data_with_mapping(content, self._output_mapping)
        combined_data = parsed_old_data | parsed_data
        artifact.changes = artifact.changes | parsed_data
        artifact.changes_text = self._parsed_to_str(artifact.changes)

        logger.debug(json.dumps(parsed_data, indent=4, ensure_ascii=False))
        artifact.instruct_content = output_class(**combined_data)
        new_content = self._parsed_to_str(combined_data)
        artifact.pending_content.append(new_content)
        return new_content  # ActionOutput(content, instruct_content)

    def _parsed_to_str(self, parsed):
        str = ''
        for key, value in self._output_mapping.items():
            type = value['type']
            str += f'## {key}\n'
            if type == 'python':
                str += f'```{type}\n'
                str += json.dumps(parsed.get(key,{}), indent=4, ensure_ascii=False)
                str += '\n```\n\n'
            elif type != 'text':
                str += f'```{type}\n'
                str += parsed[key]
                str += '\n```\n\n'
            else:
                str += parsed[key]
                str += '\n\n'
        return str

    async def run(self, *args, **kwargs):
        """Run action"""
        raise NotImplementedError("The run method should be implemented in a subclass.")

    def _get_prompt(self, task: Task, prompt_type: PromptType = PromptType.Default, **kwargs) -> (str, PromptType):
        if prompt_type == PromptType.Comment:
            return self._get_prompt_(PromptType.Comment, **kwargs)
        else:
            if not task.source_artifact:  # task: direct change
                prompt = self.TASK_UPDATE_PROMPT if task.artifact.content else self.TASK_CREATE_PROMPT
                if not prompt:
                    return None, PromptType.No_Action
                return self._get_prompt_(PromptType.Task_Update if task.artifact.content else PromptType.Task_Create, **kwargs)
            else:   # event: upstream change
                if not task.artifact.content:
                    return self._get_prompt_(PromptType.Dependency_Create, **kwargs)
                else:
                    return self._get_prompt_(PromptType.Dependency_Update, **kwargs)

    # @abstractmethod
    def _get_prompt_(self,  prompt_type: PromptType,  **kwargs) -> (str, PromptType):
        task = self.context.task
        if prompt_type == PromptType.Comment:
            return COMMENT_PROMPT.format(comment=kwargs['comment']), PromptType.Comment
        elif prompt_type == PromptType.Task_Update:
            prompt = self.TASK_UPDATE_PROMPT.format(content=task.artifact.content, description=task.description,
                                     format_example=self.FORMAT_EXAMPLE) if self.TASK_UPDATE_PROMPT else None
            return prompt, prompt_type if prompt else PromptType.No_Action
        elif prompt_type == PromptType.Task_Create:
            prompt = self.TASK_CREATE_PROMPT.format(content=task.artifact.content, description=task.description,
                                                    format_example=self.FORMAT_EXAMPLE) if self.TASK_CREATE_PROMPT else None
            return prompt, prompt_type if prompt else PromptType.No_Action
        elif prompt_type == PromptType.Dependency_Create:
            return self.DEPENDENCY_CREATE_PROMPT.format(source=task.source_artifact.content,
                                                 format_example=self.FORMAT_EXAMPLE,
                                                 **kwargs), PromptType.Dependency_Create
        elif prompt_type == PromptType.Dependency_Update:
            return self.DEPENDENCY_UPDATE_PROMPT.format(source=task.source_artifact.previous_content,
                                                                changes=task.source_artifact.changes_text,
                                                                dest=task.artifact.content,
                                                                format_example=self.FORMAT_EXAMPLE), PromptType.Dependency_Update


    async def process_task(self, task: Task) -> str:
        self.context.todo = self
        self.context.task = task
        self.context.artifact = task.artifact
        prompt, prompt_type = self._get_prompt(task)
        if prompt:
            result = await self._aask_v2(prompt, simulate=True,
                                         simulate_name=f'{task.artifact.type.value}_{prompt_type.value}_{task.artifact.name}')
            return self._parse_result(result, task.artifact)
        else:  # use artifact content directly
            if task.description and not task.artifact.content:
                task.artifact.content = task.description
            if not task.artifact.content:
                raise Exception('RAW_REQUIREMENT artifact must exist with content')
            return task.artifact.content

    async def comment(self, comment) -> str:
        prompt, type = self._get_prompt(self.context.task, prompt_type=PromptType.Comment, comment=comment)
        result = await self._aask_v2(prompt)
        return self._parse_result(result, self.context.artifact)

    def commit(self):
        artifact = self.context.artifact
        artifact.save()
        self.context.task = None
        self.context.todo = None
        self.context.artifact = None
        self.context.historyMessages = []
        self.context.env.publish_event(Event(artifact=artifact))
        return artifact

    def create_artifact(self, event):
        artifact = self.context.env.artifact_mgr.create_artifact(self.dest_artifact_type, event.artifact.name, path=event.artifact.path)
        event.artifact.add_watch(artifact)
        return artifact