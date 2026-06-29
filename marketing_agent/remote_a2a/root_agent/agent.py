import os
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from a2a.server.apps import A2AStarletteApplication
from a2a.server.apps.rest.rest_adapter import RESTAdapter
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryPushNotificationConfigStore, InMemoryTaskStore
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from starlette.applications import Starlette
from starlette.routing import Route

from marketing_agent.agent import root_agent

base_url = urlparse(os.getenv("A2A_BASE_URL", f"http://localhost:{os.getenv('A2A_PORT', 8081)}"))

# Ngrok uses standard port 443 for HTTPS traffic
target_port = base_url.port or (443 if base_url.scheme == "https" else 80)

rpc_url = f"{base_url.scheme}://{base_url.hostname}:{target_port}/"


def _create_runner() -> Runner:
    """Lazily build the Runner backing the agent (mirrors to_a2a's default)."""
    return Runner(
        app_name=root_agent.name or "adk_agent",
        agent=root_agent,
        artifact_service=InMemoryArtifactService(),
        session_service=InMemorySessionService(),
        memory_service=InMemoryMemoryService(),
        credential_service=InMemoryCredentialService(),
    )


task_store = InMemoryTaskStore()
push_config_store = InMemoryPushNotificationConfigStore()

request_handler = DefaultRequestHandler(
    agent_executor=A2aAgentExecutor(runner=_create_runner),
    task_store=task_store,
    push_config_store=push_config_store,
)

card_builder = AgentCardBuilder(agent=root_agent, rpc_url=rpc_url)


@asynccontextmanager
async def _lifespan(app: Starlette):
    final_agent_card = await card_builder.build()

    # JSON-RPC transport: registers POST "/" and GET "/.well-known/agent-card.json"
    # (used by ADK's RemoteA2aAgent, e.g. our local test consumer)
    A2AStarletteApplication(
        agent_card=final_agent_card,
        http_handler=request_handler,
    ).add_routes_to_app(app)

    # REST transport: registers "/v1/message:send", "/v1/tasks/{id}", etc.
    # (used by Gemini Enterprise / Agentspace, which calls REST paths directly)
    rest_adapter = RESTAdapter(
        agent_card=final_agent_card,
        http_handler=request_handler,
    )
    for (path, method), callback in rest_adapter.routes().items():
        app.routes.append(Route(path, callback, methods=[method]))

    yield


# Make your agent A2A-compatible over both JSON-RPC and REST transports
a2a_app = Starlette(lifespan=_lifespan)
