from google.adk.a2a.utils.agent_to_a2a import to_a2a
from marketing_agent.agent import root_agent
from urllib.parse import urlparse
import os

base_url = urlparse(os.getenv("A2A_BASE_URL", f"http://localhost:{os.getenv("A2A_PORT", 8081)}"))

# Ngrok uses standard port 443 for HTTPS traffic
target_port = base_url.port or (443 if base_url.scheme == "https" else 80)

# Make your agent A2A-compatible
a2a_app = to_a2a(
    root_agent,
    host=base_url.hostname,       # Extracts: ngrok url if available
    port=target_port,           # Extracts: 443
    protocol=base_url.scheme      # Extracts: https
)