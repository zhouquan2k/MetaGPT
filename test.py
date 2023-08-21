from init import init_company, run
import asyncio

company = init_company('test')
asyncio.run(run('docs/RAW_1.md', company, simulate=True))
# await run('docs/PRD_1.md', company, simulate=True)
