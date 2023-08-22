from init import init_company, run
import asyncio


async def test():
    company = init_company('test')
    await run('docs/RAW_1.md', company, simulate=True)
    await run('docs/RAW_1.md', company, prompt='''
    add detail trading data properties as in requirement into the UserStory and Requirement pool of PRD.
    add detail indicators needed to evaluate strategy as in requirement into the UserStory and Requirement pool of the PRD.
    all configurtations are put in one configuration file. no gui for configuration needed.
    for the ui design draft: The only UI we needed here is the console output text, no gui needed. we should output the output indicators.
    
    REMEMBER: Always output the full PRD even when part of it need to be modified.   
''')

asyncio.run(test())
# await run('docs/PRD_1.md', company, simulate=True)
