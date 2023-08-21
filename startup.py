#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio

import fire

from metagpt.roles import Architect, Engineer, ProductManager, ProjectManager, QaEngineer
from metagpt.software_company import SoftwareCompany
from init import init_company


async def startup(name: str, idea: str, company: SoftwareCompany, n_round: int = 5):
    """Run a startup. Be a boss."""
    company.start_project(name, idea)
    await company.run(n_round=n_round)


def main(name: str, idea: str = '', investment: float = 3.0, n_round: int = 5, code_review: bool = False, run_tests: bool = False):
    """
    We are a software startup comprised of AI. By investing in us, you are empowering a future filled with limitless possibilities.
    :param name: project name
    :param idea: Your innovative idea, such as "Creating a snake game."
    :param investment: As an investor, you have the opportunity to contribute a certain dollar amount to this AI company.
    :param n_round:
    :param code_review: Whether to use code review.
    :return:
    """
    company = init_company(investment=investment, code_review=code_review, run_tests=run_tests)
    asyncio.run(startup(name, idea, n_round=n_round, company=company))
    # asyncio.run(run(name, 'docs/PRD_1.md', company))
    # asyncio.run(run(name, 'docs/DESIGN_1.md', company))


if __name__ == '__main__':
    fire.Fire(main)
