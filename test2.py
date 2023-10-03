from init import init_company
from metagpt.artifact import Artifact, ArtifactType
from metagpt.my_actions.design_ui import OUTPUT_MAPPING as Design_Output_Mapping
from metagpt.schema import Task
import asyncio



# module_name = 'CreateProject'
module_name = 'MeetingApproval'

# 新生成原型场景，输入原始需求文档
async def test_new_requirement_task():
    company = init_company('HEthics')
    module_name = 'Refund'
    (company.environment.workspace.rootPath / f'docs/PRD_{module_name}.md').unlink(True)
    (company.environment.workspace.rootPath / f'docs/DESIGN_{module_name}.md').unlink(True)
    req = company.environment.artifact_mgr.create_artifact(ArtifactType.RAW_REQUIREMENT, f'REQ_{module_name}.md', path="input-docs")
    company.environment.artifact_mgr.create_artifact(ArtifactType.SYSTEM_DESIGN, 'SYSTEM-DESIGN_system_design_ui.md', path="input-docs")
    company.add_artifact_event(req)
    # PRD
    context = await company.execute_next_task()
    # await context.comment('以上子用户故事应该都可以在一个界面中完成，因此应该在用户故事中描述，而不是子用户故事，此外，请提供UI描述')
    context.commit()
    # DESIGN
    context = await company.execute_next_task()
    '''
    context.commit()
    company.environment.artifact_mgr.save()
    '''


async def test_design():
    company = init_company('')
    module_name = 'pay'
    (company.environment.workspace.rootPath / f'docs/DESIGN_{module_name}.md').unlink(True)
    req = company.environment.artifact_mgr.create_artifact(ArtifactType.RAW_REQUIREMENT, f'REQ_{module_name}.md', path="docs")
    # prd = company.environment.artifact_mgr.create_artifact(ArtifactType.PRD, f'PRD_{module_name}.md', path="docs")
    # req.add_watch(prd, 'WRITE_PRD')
    company.environment.artifact_mgr.create_artifact(ArtifactType.SYSTEM_DESIGN, 'SYSTEM-DESIGN_system_design_ui.md', path="input-docs")
    company.add_artifact_event(req)
    # design
    context = await company.execute_next_task()
    context.commit()

    #await context.comment('''
    #    - "/user/reviewers", "/user/participants" 应属于User module提供的endpoint，不要在"Endpoints to implement"中描述
    #    - "/file/list" 修改为 "/meeting/file/list"
    #''')
    #context.commit()
    company.environment.artifact_mgr.save()

async def test_code():
    company = init_company('', is_load_artifacts=True)
    design = company.environment.artifact_mgr.get_by_path('docs/DESIGN_pay.md')

    company.add_artifact_event(design)
    #  api mock js
    context = await company.execute_next_task()
    context.commit()

    context = await company.execute_next_task()
    context.commit()

    '''
    await context.comment('please check the consistency to "Data structures and interface definitions" of DESIGN')
    '''

    '''
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
    '''


async def test_modify_design():
    await test_design()
    company = init_company('HEthics', is_load_artifacts=True)
    design = company.environment.artifact_mgr.get_by_path(f'docs/DESIGN_{module_name}.md')
    task = Task(artifact=design, description='''
        - you didn't consider about the endpoints: 
        ''')

    company.add_project_task(task)
    # Design
    context = await company.execute_next_task()
    context.commit()

    # code - DataObject
    context = await company.execute_next_task()
    context.commit()

    # code - Service
    context = await company.execute_next_task()
    context.commit()

    # code -ServiceImpl
    context = await company.execute_next_task()
    context.commit()

    # code - api.js
    context = await company.execute_next_task()
    context.commit()

    # code - vue
    context = await company.execute_next_task()
    context.commit()

async def test_modify_code():
    company = init_company('HEthics', is_load_artifacts=True)
    vue = company.environment.artifact_mgr.get_by_path('refund/frontend/views/Refund.vue')
    task = Task(artifact=vue, description='''
            - 请将‘用户搜索栏’的所有输入框和按钮放在同一行
            - 即使没有数据 请将‘用户信息显示区域‘ 和 ‘挂号信息显示区域’ 显示为固定高度，并占满显示区域（各50%）
            ''')
    company.add_project_task(task)
    # vue
    context = await company.execute_next_task()

asyncio.run(test_code())