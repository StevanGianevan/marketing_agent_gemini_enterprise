import os

import uvicorn

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import (
    create_agent_card_routes,
    create_jsonrpc_routes,
    create_rest_routes,
)
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
)
from agent_executor import (
    HelloWorldAgentExecutor,  # type: ignore[import-untyped]
)
from starlette.applications import Starlette

HOST = os.environ.get('A2A_HOST', '127.0.0.1')
PORT = int(os.environ.get('A2A_PORT', '9999'))
PUBLIC_URL = os.environ.get('A2A_PUBLIC_URL', f'http://{HOST}:{PORT}')

if __name__ == '__main__':
    # --8<-- [start:AgentSkill]
    # Defines the abilities or functions that agent can perform.
    skill = AgentSkill(
        id='marketing_coordinator',
        name='Marketing Coordinator',
        description=(
            'Helps establish a powerful online presence: domain naming, '
            'website creation, marketing campaigns, logo design, and video strategy.'
        ),
        input_modes=['text/plain'],
        output_modes=['text/plain'],
        tags=['marketing', 'adk', 'gemini'],
        examples=['Help me create a brand for my coffee shop', 'I need a domain name for my startup'],
    )
    # --8<-- [end:AgentSkill]
    extended_skill = AgentSkill(
        id='marketing_coordinator_extended',
        name='Marketing Coordinator (Extended)',
        description='Full marketing coordinator with all sub-agents enabled.',
        tags=['marketing', 'adk', 'gemini', 'extended'],
        examples=['Run full marketing setup for my brand'],
    )

    # --8<-- [start:AgentCard]
    # Define a public-facing agent card that allows clients to discover your agent's capabilities.
    public_agent_card = AgentCard(
        # Basic identity information of A2A server
        name='Marketing Coordinator Agent',
        description='AI marketing agent that guides brand creation, domain naming, website, campaigns, and logo design.',
        version='0.0.1',
        # Default Media Types for the agent's interactions
        default_input_modes=['text/plain'],  # Supported media types
        default_output_modes=['text/plain'],
        # Supported A2A features (like streaming or extended config)
        capabilities=AgentCapabilities(streaming=True, extended_agent_card=True),
        # Ordered list of endpoints and protocols where the service can be reached
        supported_interfaces=[
            AgentInterface(
                protocol_binding='HTTP_JSON',
                protocol_version='1.0',
                url=PUBLIC_URL,
            )
        ],
        # The list of AgentSkill objects that this agent offers
        skills=[skill],
        # Optional attributes (omitted here for simplicity):
        # icon_url                         -> A URL to an icon representing the agent
    )
    # --8<-- [end:AgentCard]

    # Defines the authenticated extended agent card with
    # extended skills that are visible only to authenticated users
    extended_agent_card = AgentCard(
        name='Marketing Coordinator Agent - Extended',
        description='Full-featured marketing coordinator with all sub-agents for authenticated users.',
        version='0.0.2',
        default_input_modes=['text/plain'],
        default_output_modes=['text/plain'],
        capabilities=AgentCapabilities(streaming=True, extended_agent_card=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding='HTTP_JSON',
                protocol_version='1.0',
                url=PUBLIC_URL,
            )
        ],
        skills=[
            skill,
            extended_skill,
        ],  # Both skills for the extended card
    )
    # --8<-- [start:RequestHandler]
    # The RequestHandler processes incoming requests and manages tasks
    request_handler = DefaultRequestHandler(
        # Agent executor handles the execution of the client requests
        agent_executor=HelloWorldAgentExecutor(),
        # The task_store is used to store and manage tasks
        task_store=InMemoryTaskStore(),
        # Public agent card for unauthenticated users
        agent_card=public_agent_card,
        # Extended agent card for authenticated users
        extended_agent_card=extended_agent_card,
    )
    # --8<-- [end:RequestHandler]
    # --8<-- [start:ServerRoutes]
    # Creating the routes for the A2A server
    # These routes handle the incoming requests from the clients
    # and the outgoing responses to the clients
    routes = []

    # Create routes for the agent card
    routes.extend(create_agent_card_routes(public_agent_card))

    # v0.3 compat REST routes — REST03Adapter hardcodes /v1/ prefix internally
    routes.extend(create_rest_routes(request_handler, enable_v0_3_compat=True))
    # JSONRPC at / for other A2A clients
    routes.extend(create_jsonrpc_routes(request_handler, '/'))
    # --8<-- [end:ServerRoutes]
    # --8<-- [start:AppServer]

    # Create a web app with the defined routes
    # Here we are using Starlette, a lightweight ASGI web framework to serve the agent
    # Alternatively, you can choose FastAPI or other ASGI frameworks
    app = Starlette(routes=routes)

    # Run the app
    # Uvicorn is a production-ready ASGI HTTP server
    uvicorn.run(app, host=HOST, port=PORT)
    # --8<-- [end:AppServer]
