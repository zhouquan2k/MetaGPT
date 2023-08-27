#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/12 00:30
@Author  : alexanderwu
@File    : software_company.py
"""
from pydantic import BaseModel, Field

from metagpt.actions import BossRequirement
from metagpt.config import CONFIG
from metagpt.environment import Environment
from metagpt.logs import logger
from metagpt.roles import Role, RoleContext
from metagpt.schema import Message, Task
from metagpt.utils.common import NoMoneyException
from metagpt.artifact import Artifact, ArtifactType
from metagpt.actions import ActionType
from metagpt.llm import LLM

ArtifactTypeToAction = {
    ArtifactType.RAW_REQUIREMENT: ActionType.ADD_REQUIREMENT,
    ArtifactType.PRD: ActionType.WRITE_PRD,
    ArtifactType.DESIGN: ActionType.WRITE_DESIGN
}

ArtifactTypeDependency = {
    ArtifactType.RAW_REQUIREMENT: [ActionType.WRITE_PRD],
    ArtifactType.PRD: [ActionType.WRITE_DESIGN],
    ArtifactType.DESIGN: [ActionType.WRITE_TASKS]
}


class SoftwareCompany(BaseModel):
    """
    Software Company: Possesses a team, SOP (Standard Operating Procedures), and a platform for instant messaging,
    dedicated to writing executable code.
    """
    environment: Environment = Field(default_factory=Environment)
    investment: float = Field(default=10.0)
    idea: str = Field(default="")
    name: str = None

    class Config:
        arbitrary_types_allowed = True

    def hire(self, roles: list[Role]):
        """Hire roles to cooperate"""
        self.environment.add_roles(roles)

    def invest(self, investment: float):
        """Invest company. raise NoMoneyException when exceed max_budget."""
        self.investment = investment
        CONFIG.max_budget = investment
        logger.info(f'Investment: ${investment}.')

    def _check_balance(self):
        if CONFIG.total_cost > CONFIG.max_budget:
            raise NoMoneyException(CONFIG.total_cost, f'Insufficient funds: {CONFIG.max_budget}')

    def start_project(self, name, idea):
        """Start a project from publishing boss requirement."""
        self.idea = idea
        self.name = name
        self.environment.init(name)
        self.environment.publish_message(Message(role="BOSS", content=idea, cause_by=BossRequirement))

    # TODO
    async def run_project_one_step(self, new_artifact, prompt=None, simulate=False):
        artifact = self.load_artifact(new_artifact)
        msg = self._get_artifact_msg(artifact, prompt)
        msg.simulate = simulate
        self.environment.single_step = True
        self.environment.publish_message(msg)
        await self.environment.run()

    # TODO
    def _get_artifact_msg(self, artifact, prompt):
        type_action_map = {
            'RAW': ActionType.ADD_REQUIREMENT,
            'PRD': ActionType.WRITE_PRD,
            'DESIGN': ActionType.WRITE_DESIGN,
            'TASK': ActionType.WRITE_TASKS
        }
        return Message(content=prompt if prompt else artifact.content, cause_by=type_action_map[artifact.type].value)

    # TODO
    def load_artifact(self, artifact_path):
        return Artifact.load(self.environment.workspace, artifact_path)

    def add_project_task(self, task: Task):
        if not task.action:
            task.action = ArtifactTypeToAction[task.artifact.type]
        self.environment.task_queue.append(task)

    async def execute_next_task(self) -> RoleContext:
        self._process_events()
        if len(self.environment.task_queue) == 0:
            return None
        task = self.environment.task_queue.pop(0)
        # find role/action to process task
        context = RoleContext()
        context.env = self.environment
        llm = LLM()
        action = task.action.value(f'{task.artifact.type}_{task.artifact.name}', context=context, llm=llm)
        output = await action.process_task(task)
        logger.info(output)
        return context

    def _process_events(self):
        event = self.environment.get_next_event()
        llm = LLM()
        while event:
            actions = ArtifactTypeDependency[event.artifact.type]
            if len(actions) > 0:
                # TODO  to get the singleton of action , not create a new one
                for _action in actions:
                    # TODO get destination artifact, and put it in task, according to artifact dependency
                    context = RoleContext()
                    context.env = self.environment
                    action = _action.value('TODO', context=context, llm=llm)
                    if not action.multiple_artifacts:  # one to one
                        impact_artifacts = event.artifact.impact_artifacts.get(_action, [])
                        count = len(impact_artifacts)
                        dest_artifact = None
                        if count == 0:  # new
                            # TODO action override
                            dest_artifact = self.environment.artifact_mgr.create_artifact(action.dest_artifact_type, event.artifact.name, path=event.artifact.path)
                            event.artifact.add_watch(dest_artifact)
                        elif count == 1:
                            dest_artifact = impact_artifacts[0]
                        else:
                            raise Exception('impact artifacts > 1 for single artifact action?')
                        self.environment.task_queue.append(
                            Task(source_artifact=event.artifact, action=_action, artifact=dest_artifact))
                    else:  # one to many
                        raise NotImplementedError()

            event = self.environment.get_next_event()

    def _save(self):
        logger.info(self.json())

    async def run(self, n_round=3):
        """Run company until target round or no money"""

        while n_round > 0:
            # self._save()
            n_round -= 1
            logger.debug(f"{n_round=}")
            self._check_balance()
            await self.environment.run()
        return self.environment.history
