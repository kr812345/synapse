import asyncio
from kernel.kernel import Kernel
from memory.memory_engine import MemoryEngine
from agents.registry import AgentRegistry
from models.model_router import ModelRouter
from scheduler.scheduler import Scheduler
from departments.research.manager import ResearchManager
from departments.engineering.manager import EngineeringManager
from departments.marketing.manager import MarketingManager
from departments.personal.manager import PersonalManager
from departments.base import BaseDepartmentModule
from shared.models import AgentContract

from tools.tool_registry import ToolRegistry
from tools.library.github_tool import GitHubTool
from tools.library.reddit_tool import RedditTool
from tools.library.browser_tool import BrowserTool
from tools.library.email_tool import EmailTool
from tools.library.pdf_tool import PDFTool
from tools.library.ppt_tool import PPTTool
from tools.library.file_tools import FileRead, FileWrite, FileEdit

async def boot_os():
    kernel = Kernel()
    memory = MemoryEngine(db_url="dbname=synapse user=root")
    registry = AgentRegistry()
    router = ModelRouter()
    scheduler = Scheduler()
    
    tool_registry = ToolRegistry()
    tool_registry.register(GitHubTool())
    tool_registry.register(RedditTool())
    tool_registry.register(BrowserTool())
    tool_registry.register(EmailTool())
    tool_registry.register(PDFTool())
    tool_registry.register(PPTTool())
    tool_registry.register(FileRead())
    tool_registry.register(FileWrite())
    tool_registry.register(FileEdit())
    
    kernel.register_module(memory)
    kernel.register_module(registry)
    kernel.register_module(router)
    kernel.register_module(scheduler)
    
    # Instantiate managers
    rm = ResearchManager("rm_1", "Research Manager")
    eng = EngineeringManager("eng_1", "Engineering Manager")
    mkt = MarketingManager("mkt_1", "Marketing Manager")
    per = PersonalManager("per_1", "Personal Manager")

    # Register as Kernel Modules
    kernel.register_module(BaseDepartmentModule(rm))
    kernel.register_module(BaseDepartmentModule(eng))
    kernel.register_module(BaseDepartmentModule(mkt))
    kernel.register_module(BaseDepartmentModule(per))

    # Register their Contracts
    def make_contract(agent):
        return AgentContract(
            identity=agent.id,
            department=agent.department,
            goal=f"Manage {agent.department}",
            responsibilities=["execute", "delegate"],
            forbidden_actions=agent.forbidden_actions(),
            allowed_tools=agent.allowed_tools(),
            memory_access=agent.memory_access_level(),
            output_schema={},
            confidence_score=agent.confidence_score
        )

    registry.register_agent(make_contract(rm))
    registry.register_agent(make_contract(eng))
    registry.register_agent(make_contract(mkt))
    registry.register_agent(make_contract(per))
    
    print("[SYSTEM] Synapse OS Booted Successfully.")
    return kernel, registry, scheduler
