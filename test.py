from init import init_company, run
import asyncio
from metagpt.artifact import Artifact, ArtifactType
from metagpt.schema import Task


async def test_prd():
    company = init_company('test')
    await run('docs/RAW_1.md', company, simulate=True)
    await run('docs/RAW_1.md', company, prompt='''
    add detail trading data properties as in requirement into the UserStory and Requirement pool of PRD.
    add detail indicators needed to evaluate strategy as in requirement into the UserStory and Requirement pool of the PRD.
    all configurations are put in one configuration file. no gui for configuration needed.
    for the ui design draft: The only UI we needed here is the console output text, no gui needed. we should output the output indicators.
''')


async def test_design():
    company = init_company('test')
    await run('docs/PRD_1.md', company, simulate=True)
    await run('docs/PRD_1.md', company, prompt='''
        design a standalone abstract class for trading strategy to be evaluated  
    ''')


async def test_coding():
    company = init_company('test')
    await run('docs/TASK_1.md', company)


module_name = 'Strategy_Evaluator'
company = init_company('test')


# 新生成原型场景，输入原始需求文档
async def test_new_requirement_task():
    req = company.environment.artifact_mgr.create_artifact(ArtifactType.RAW_REQUIREMENT, f'{module_name}.md', path="docs")
    task = Task(artifact=req)
    company.add_project_task(task)
    # loop until no more new tasks, created all necessary artifacts
    context = await company.execute_next_task()
    context.commit()
    # PRD
    context = await company.execute_next_task()
    context.commit()
    # DESIGN
    context = await company.execute_next_task()
    context.commit()
    company.environment.artifact_mgr.save()


async def test_update_prd_task():
    prd = company.environment.artifact_mgr.get(ArtifactType.PRD, f'{module_name}.md')
    task = Task(artifact=prd, description='''
- all configurations are put in one configuration file. no gui for configuration needed.
- for the ui design draft: The only UI we needed here is the console output text, no gui needed. we should output the output indicators.
    ''')
    company.add_project_task(task)
    # PRD Change
    context = await company.execute_next_task()
    context.commit()
    # DESIGN Update
    context = await company.execute_next_task()
    context.commit()
    company.environment.artifact_mgr.save()



async def test_update_design_task():
    # task may be a new feature, a design refactor, a bug fix
    task = Task(artifact=Artifact(ArtifactType.DESIGN, f'{module_name}.md', path="docs"), description='please use following 3rd party libraries: use backtrade as backtest framework, use tushare to get trading data')
    company.add_project_task(task)
    context = await company.execute_next_task()
    await context.comment('请将package name改为"strategy_evaluator"')
    print(task.artifact.new_content())
    # will cause downstream artiface change.  artifact dependencies.
    context.commit()


asyncio.run(test_update_prd_task())
