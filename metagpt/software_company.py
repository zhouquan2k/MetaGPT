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

    def load_artifact(self, artifact_path):
        return Artifact.load(self.environment.workspace, artifact_path)

    async def add_project_task(self, task: Task) -> RoleContext:
        # find role/action to process task
        action_cls = ArtifactTypeToAction[task.artifact.type].value
        context = RoleContext()
        context.env = self.environment
        llm = LLM()
        action = action_cls(f'{task.artifact.type}_{task.artifact.name}', context=context, llm=llm)
        output = await action.process_task(task)
        logger.info(output)
        return context

    async def process_next_event(self):
        # pick one event from queue
        # find role/action to process event
        # action.process_event(event)
        event = self.environment.get_next_event()
        if event:





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
