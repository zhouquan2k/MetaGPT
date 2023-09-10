#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/20 17:46
@Author  : alexanderwu
@File    : add_requirement.py
"""
from metagpt.actions import Action


class BossRequirement(Action):
    """Boss Requirement without any implementation details"""
    def __init__(self, name = "", context = None, llm = None):
        super().__init__(name, context, llm)
        self.DEPENDENCY_CREATE_PROMPT = None
        self.DEPENDENCY_UPDATE_PROMPT = None
        self.TASK_UPDATE_PROMPT = None
        self.FORMAT_EXAMPLE = None

    async def run(self, *args, **kwargs):
        raise NotImplementedError
