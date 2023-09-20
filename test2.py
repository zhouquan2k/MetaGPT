from init import init_company
from metagpt.artifact import Artifact, ArtifactType
from metagpt.my_actions.design import OUTPUT_MAPPING as Design_Output_Mapping
from metagpt.schema import Task
import asyncio



# module_name = 'CreateProject'
module_name = 'MeetingApproval'

# 新生成原型场景，输入原始需求文档
async def test_new_requirement_task():
    company = init_company('HEthics')
    (company.environment.workspace.rootPath / f'docs/PRD_{module_name}.md').unlink(True)
    (company.environment.workspace.rootPath / f'docs/DESIGN_{module_name}.md').unlink(True)
    req = company.environment.artifact_mgr.create_artifact(ArtifactType.RAW_REQUIREMENT, f'{module_name}.md', path="docs")
    # company.environment.artifact_mgr.create_artifact(ArtifactType.SYSTEM_DESIGN, 'system_design.md', path="docs")
    company.add_artifact_event(req)
    # PRD
    context = await company.execute_next_task()
    '''
    await context.comment('以上子用户故事应该都可以在一个界面中完成，因此应该在用户故事中描述，而不是子用户故事，此外，请提供UI描述')
    context.commit()
    # DESIGN
    context = await company.execute_next_task()
    context.commit()
    company.environment.artifact_mgr.save()
    '''


async def test_design():
    company = init_company('HEthics')
    (company.environment.workspace.rootPath / f'docs/DESIGN_{module_name}.md').unlink(True)
    prd = company.environment.artifact_mgr.create_artifact(ArtifactType.PRD, f'{module_name}.md', path="docs")
    company.environment.artifact_mgr.create_artifact(ArtifactType.SYSTEM_DESIGN, 'system_design.md', path="docs")
    company.add_artifact_event(prd)
    # design
    context = await company.execute_next_task()
    context.commit()
    '''
    # first code
    context = await company.execute_next_task()
    context.commit()
    company.environment.artifact_mgr.save()

    # await company.execute_remain_tasks()

    # company.environment.artifact_mgr.save()
    # await context.comment('- Reviewer和Attendee应该都是Meeting的属性，都是在可登录的用户/特定角色中选择，可以使用User类，不需要创建单独的实体。
    # -File List中的文件命名没有按照System Design的规范')
    '''


async def test_code():
    company = init_company('HEthics')
    design = company.environment.artifact_mgr.create_artifact(ArtifactType.DESIGN, f'{module_name}.md', path="docs", parse_mapping=Design_Output_Mapping)
    # TODO parse_mapping use protected attr
    company.environment.artifact_mgr.create_artifact(ArtifactType.SYSTEM_DESIGN, 'system_design.md', path="input-docs")
    company.add_artifact_event(design)
    # Service
    context = await company.execute_next_task()
    context.commit()
    # Data Object
    context = await company.execute_next_task()
    context.commit()
    # ServiceImpl
    context = await company.execute_next_task()
    context.commit()
    # Vue
    context = await company.execute_next_task()
    context.commit()
    # js
    context = await company.execute_next_task()
    context.commit()



async def test_modify_design():
    company = init_company('HEthics', is_load_artifacts=True)
    design = company.environment.artifact_mgr.get(ArtifactType.DESIGN, f'{module_name}.md')
    # task = Task(artifact=design, description='''
    #- you didn't consider about api js files which used to call backend endpoints in the 'File List'.
    #- For selecting meeting participants, we'll use 'get all users' endpoint from 'User' module to get the users in the dropdown select
    #''')
    task = Task(artifact=design, description='''
        - For selecting meeting participants/reviewers, we'll use 'get all users' endpoint from 'User' module to get the users in the dropdown select
        ''')

    company.add_project_task(task)
    # Design
    context = await company.execute_next_task()
    context.commit()

    '''
    # code
    context = await company.execute_next_task()
    context.commit()

    context = await company.execute_next_task()
    context.commit()

    context = await company.execute_next_task()
    context.commit()

    context = await company.execute_next_task()
    context.commit()
    '''


asyncio.run(test_modify_design())