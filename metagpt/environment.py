#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/11 22:12
@Author  : alexanderwu
@File    : environment.py
"""
import asyncio
from typing import Iterable

from pydantic import BaseModel, Field

from metagpt.memory import Memory
from metagpt.roles import Role
from metagpt.schema import Message, Event, Task
from metagpt.artifact import Workspace, ArtifactMgr
from metagpt.config import CONFIG


class Environment(BaseModel):
    """环境，承载一批角色，角色可以向环境发布消息，可以被其他角色观察到
       Environment, hosting a batch of roles, roles can publish messages to the environment, and can be observed by other roles
    
    """

    roles: dict[str, Role] = Field(default_factory=dict)
    memory: Memory = Field(default_factory=Memory)
    history: str = Field(default='')
    workspace: Workspace = None
    single_step: bool = False

    task_queue: list[Task] = []
    event_queue: list[Event] = []
    artifact_mgr: ArtifactMgr = None


    class Config:
        arbitrary_types_allowed = True

    def init(self, project_name):
        self.workspace = Workspace.init_workspace(project_name, CONFIG.workspace_root_path)
        path = self.workspace.rootPath / 'artifacts.json'
        if path.exists():
            self.artifact_mgr = ArtifactMgr.parse_raw(path.read_text())
        else:
            self.artifact_mgr = ArtifactMgr.create_artifact_mgr(workspace=self.workspace)

    def add_role(self, role: Role):
        """增加一个在当前环境的角色
           Add a role in the current environment
        """
        role.set_env(self)
        self.roles[role.profile] = role

    def add_roles(self, roles: Iterable[Role]):
        """增加一批在当前环境的角色
            Add a batch of characters in the current environment
        """
        for role in roles:
            self.add_role(role)

    def publish_message(self, message: Message):
        """向当前环境发布信息
          Post information to the current environment
        """
        # self.message_queue.put(message)
        self.memory.add(message)
        self.history += f"\n{message}"

    async def run(self, k=1):
        """处理一次所有信息的运行
        Process all Role runs at once
        """
        # while not self.message_queue.empty():
        # message = self.message_queue.get()
        # rsp = await self.manager.handle(message, self)
        # self.message_queue.put(rsp)
        for _ in range(k):
            futures = []
            for role in self.roles.values():
                future = role.run()
                futures.append(future)

            await asyncio.gather(*futures)

    # env根据订阅负责dispatch event，而不是每个role运行一遍

    def get_roles(self) -> dict[str, Role]:
        """获得环境内的所有角色
           Process all Role runs at once
        """
        return self.roles

    def get_role(self, name: str) -> Role:
        """获得环境内的指定角色
           get all the environment roles
        """
        return self.roles.get(name, None)

    def publish_event(self, event: Event):
        self.event_queue.append(event)

    def get_next_event(self) -> Event:
        return self.event_queue.pop(0) if len(self.event_queue) > 0 else None