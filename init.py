from metagpt.roles import Architect, Engineer, ProductManager, ProjectManager, QaEngineer
from metagpt.software_company import SoftwareCompany


def init_company(project_name, investment: float = 3.0, code_review: bool = False, run_tests: bool = False):
    company = SoftwareCompany()
    company.environment.init(project_name)
    company.hire([ProductManager(),
                  Architect(),
                  ProjectManager(),
                  Engineer(n_borg=5, use_code_review=code_review)])
    if run_tests:
        # developing features: run tests on the spot and identify bugs (bug fixing capability comes soon!)
        company.hire([QaEngineer()])
    company.invest(investment)
    return company


async def run(new_artifact: str, company: SoftwareCompany, prompt=None, simulate=False):
    await company.run_project_one_step(new_artifact, prompt=prompt, simulate=simulate)
