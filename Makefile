-include .env
export

run-a2a-server:
	@uv run uvicorn marketing_agent.remote_a2a.root_agent.agent:a2a_app --port $(A2A_PORT)

run-adk-web:
	@uv run adk web --port $(ADK_PORT)

run-both:
	@echo running adk web and a2a for adk
	@uv run adk web --port $(ADK_PORT) & uv run uvicorn marketing_agent.remote_a2a.root_agent.agent:a2a_app --port ${A2A_PORT}

run-test-a2a-adk:
	uv run adk web test/ --port $(A2A_CONSUMER_PORT)