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


async def test_new_task():
    company = init_company('test')
    # task may be a new feature, a design refactor, a bug fix
    module_name = 'Strategy_Evaluator'
    '''
    task = Task(artifact=Artifact(ArtifactType.RAW_REQUIREMENT, f'{module_name}.md', path="docs"))
    context = await company.add_project_task(task)
    context.more('review opinions')
    '''
    task = Task(artifact=Artifact(ArtifactType.DESIGN, f'{module_name}.md', path="docs"), description='please use following 3rd party libraries: use backtrade as backtest framework, use tushare to get trading data')
    context = await company.add_project_task(task)
    await context.comment('请将package name改为"strategy_evaluator"')
    print(task.artifact.new_content())
    context.commit()
    # company.process_next_event()
    # will cause downstream artiface change.  artifact dependencies.


asyncio.run(test_new_task())
