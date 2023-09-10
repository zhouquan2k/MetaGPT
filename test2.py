from init import init_company
from metagpt.artifact import Artifact, ArtifactType
from metagpt.schema import Task
import asyncio

company = init_company('HEthics')

# module_name = 'CreateProject'
module_name = 'MeetingApproval'

# 新生成原型场景，输入原始需求文档
async def test_new_requirement_task():
    (company.environment.workspace.rootPath / f'docs/PRD_{module_name}.md').unlink(True)
    (company.environment.workspace.rootPath / f'docs/DESIGN_{module_name}.md').unlink(True)
    req = company.environment.artifact_mgr.create_artifact(ArtifactType.RAW_REQUIREMENT, f'{module_name}.md', path="docs")
    company.environment.artifact_mgr.create_artifact(ArtifactType.SYSTEM_DESIGN, 'system_design.md', path="docs")
    company.add_artifact_event(req)
    # PRD
    context = await company.execute_next_task()
    await context.comment('以上子用户故事应该都可以在一个界面中完成，因此应该在用户故事中描述，而不是子用户故事，此外，请提供UI描述')
    context.commit()
    # DESIGN
    context = await company.execute_next_task()
    context.commit()
    company.environment.artifact_mgr.save()


async def test_design():
    prd = company.environment.artifact_mgr.create_artifact(ArtifactType.PRD, f'{module_name}.md', path="docs")
    company.environment.artifact_mgr.create_artifact(ArtifactType.SYSTEM_DESIGN, 'system_design.md', path="docs")
    company.add_artifact_event(prd)
    context = await company.execute_next_task()
    await context.comment('''- Reviewer和Attendee应该都是Meeting的属性，都是在可登录的用户/特定角色中选择，可以使用User类，不需要创建单独的实体。
-File List中的文件命名没有按照System Design的规范''')


asyncio.run(test_design())