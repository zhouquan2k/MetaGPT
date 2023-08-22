#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Time    : 2023/5/11 14:43
@Author  : alexanderwu
@File    : product_manager.py
"""
from metagpt.actions import BossRequirement, WritePRD
from metagpt.roles import Role


class ProductManager(Role):
    def __init__(self, name="Alice", profile="Product Manager", goal="Efficiently create a successful product",
                 etc="REMEMBER: Always output the full PRD even when part of it need to be modified."):
        super().__init__(name, profile, goal, etc=etc)
        self._init_actions([WritePRD])
        self._watch([BossRequirement])
