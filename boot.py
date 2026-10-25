import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
root_env = Path(__file__).resolve().parents[2] / ".env"
if root_env.exists():
    load_dotenv(root_env, override=False)

from kernel.kernel import Kernel
from memory.memory_engine import MemoryEngine
from agents.registry import AgentRegistry
from models.model_router import ModelRouter
from scheduler.scheduler import Scheduler
from scheduler.jobs import install_default_jobs
from departments.base import BaseDepartmentModule
from shared.models import AgentContract
from assistants.pip_assistant import PipAssistant

from tools.tool_registry import ToolRegistry
from tools.library.github_tool import GitHubTool
from tools.library.browser_tool import BrowserTool
from tools.library.pdf_tool import PDFTool
from tools.library.ppt_tool import PPTTool
from tools.library.file_tools import FileRead, FileWrite, FileEdit
from tools.library.desktop import (
    BrowserClick,
    BrowserFillLogin,
    BrowserOpen,
    BrowserSnapshot,
    BrowserType,
)
from tools.library.model_tools import ModelsInstall, ModelsList, ModelsUse
from tools.library.job_tools import JobsCreate, JobsList
from tools.library.vault_tool import VaultList, VaultPut


async def boot_os():
    """Boot the brain with one assistant: Pip.

    Marketing, sales, research, and engineering stay in the tree and are not wired.
    Reddit and email tools stay unwired too.
    """
    kernel = Kernel()
    db_url = os.environ.get("DATABASE_URL", "dbname=synapse user=root")
    memory = MemoryEngine(db_url=db_url)
    registry = AgentRegistry()
    router = ModelRouter()
    scheduler = Scheduler()

    tool_registry = ToolRegistry()
    for tool in (
        GitHubTool(),
        BrowserTool(),
        PDFTool(),
        PPTTool(),
        FileRead(),
        FileWrite(),
        FileEdit(),
        BrowserOpen(),
        BrowserSnapshot(),
        BrowserClick(),
        BrowserType(),
        BrowserFillLogin(),
        VaultPut(),
        VaultList(),
        ModelsList(),
        ModelsUse(),
        ModelsInstall(),
        JobsList(),
        JobsCreate(),
    ):
        tool_registry.register(tool)

    kernel.register_module(memory)
    kernel.register_module(registry)
    kernel.register_module(router)
    kernel.register_module(scheduler)
    kernel.register_module(tool_registry)

    pip = PipAssistant()
    kernel.register_module(BaseDepartmentModule(pip))
    registry.register_agent(
        AgentContract(
            identity=pip.id,
            department=pip.department,
            goal="Help with the computer, the vault, and the schedule",
            responsibilities=["execute", "ask before sensitive actions"],
            forbidden_actions=pip.forbidden_actions(),
            allowed_tools=pip.allowed_tools(),
            memory_access=pip.memory_access_level(),
            output_schema={},
            confidence_score=pip.confidence_score,
        )
    )

    install_default_jobs()
    print("[SYSTEM] Pip booted. One assistant, workspace jail on.")
    return kernel, registry, scheduler
