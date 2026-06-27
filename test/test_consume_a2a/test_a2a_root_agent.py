from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent
import os
from urllib.parse import urlparse

A2A_BASE_URL = urlparse(os.getenv("A2A_BASE_URL", f"http://localhost:{os.getenv("A2A_PORT", 8081)}"))

marketing_remote_agent = RemoteA2aAgent(
    name="marketing_agent",
    description="a marketing agent",
    agent_card=(
        f"{A2A_BASE_URL.scheme}://{A2A_BASE_URL.hostname}{AGENT_CARD_WELL_KNOWN_PATH}"
        # f""
    ),
)

root_agent = marketing_remote_agent

