#!/usr/bin/env python
# -*- coding: utf-8 -*-
import asyncio

import fire

from metagpt.roles import Architect, Engineer, ProductManager, ProjectManager, QaEngineer
from metagpt.software_company import SoftwareCompany


async def startup(name: str, idea: str, investment: float = 3.0, n_round: int = 5,
                  code_review: bool = False, run_tests: bool = False):
    """Run a startup. Be a boss."""
    company = SoftwareCompany()
    company.hire([ProductManager(),
                  Architect(),
                  ProjectManager(),
                  Engineer(n_borg=5, use_code_review=code_review)])
    if run_tests:
        # developing features: run tests on the spot and identify bugs (bug fixing capability comes soon!)
        company.hire([QaEngineer()])
    company.invest(investment)
    company.start_project(name, idea)
    await company.run(n_round=n_round)


def main(idea: str = '', investment: float = 3.0, n_round: int = 5, code_review: bool = False, run_tests: bool = False):
    """
    We are a software startup comprised of AI. By investing in us, you are empowering a future filled with limitless possibilities.
    :param idea: Your innovative idea, such as "Creating a snake game."
    :param investment: As an investor, you have the opportunity to contribute a certain dollar amount to this AI company.
    :param n_round:
    :param code_review: Whether to use code review.
    :return:
    """
    idea = '''
    # 功能描述文档\n\n## 1. 概述\n本程序旨在实现择时回测功能，用户可以配置多个时段进行回测，随机选择n个品种的交易对象（股票）并获取交易对象在指定时段的交易数据，对于每个待评估的交易策略：为每个交易对象的所有配置的交易时段计算交易策略的各项指标，并可配置各指标权重，按权重合成最终的唯一输出指标。\n\n## 2. 功能描述\n\n### 2.1 配置回测时段\n用户可以配置多个时段进行回测，每个时段包括开始日期和结束日期。程序将根据这些时段获取交易数据进行回测。\n\n### 2.2 随机选择交易对象\n用户可以指定需要随机选择的交易对象（股票）的数量n。程序将从所有可用的交易对象中随机选择n个进行回测。\n\n### 2.3 获取交易数据\n程序将获取所选交易对象在指定时段的交易数据，包括以下内容：\n\n1. 开盘价：每个交易日开始时的股票价格。\n2. 收盘价：每个交易日结束时的股票价格。\n3. 最高价：每个交易日中股票价格的最高点。\n4. 最低价：每个交易日中股票价格的最低点。\n5. 成交量：每个交易日中股票的交易数量。\n6. 成交额：每个交易日中股票的交易总金额。\n\n### 2.4 计算交易策略的各项指标\n对于每个待评估的交易策略，程序将为每个交易对象的所有配置的交易时段计算交易策略的各项指标，包括：\n\n1. 收益率：投资回报的百分比。\n2. 最大回撤：投资过程中资产价值下降的最大幅度。\n3. 夏普比率：衡量每单位总风险所带来的超额回报。\n4. 资产波动率：衡量资产价格变动的不确定性或风险水平。\n5. 信息比率：衡量超额回报相对于活动风险的比率。\n6. 索提诺比率：衡量每单位下行风险所带来的超额回报。\n7. 胜率：交易策略盈利的交易次数占总交易次数的比例。\n8. 盈亏比：平均盈利交易的收益与平均亏损交易的损失之比。\n9. 策略表现标准差：计算策略在所有测试交易对象上的表现（如收益率）的标准差。\n10. 策略表现离散系数：计算策略在所有测试交易对象上的表现（如收益率）的标准差与平均值的比值。\n\n### 2.5 配置指标权重\n用户可以为每个交易指标配置权重，权重的总和必须为1。程序将根据这些权重合成最终的唯一输出指标。\n\n### 2.6 输出唯一指标\n程序将根据各项交易指标和其对应的权重，计算出一个唯一的输出指标。这个指标将用于评估交易策略的效果。\n\n## 3. 使用方法\n用户需要提供回测时段、交易对象数量、交易策略和指标权重。程序将自动进行回测，并输出唯一的评估指标。\n\n## 4. 注意事项\n- 所有的日期都应该是有效的交易日。\n- 交易对象数量应该是一个正整数。\n- 指标权重应该是一个非负数，且所有权重的总和应该为1。\n- 交易策略应该是有效的，且能够根据交易数据计算出各项交易指标。\n\n## 5. 期望结果\n程序能够根据用户的配置，自动进行择时回测，并输出唯一的评估指标。
    '''
    name = 'strategy_eval'
    asyncio.run(startup(name, idea, investment, n_round, code_review, run_tests))


if __name__ == '__main__':
    fire.Fire(main)
