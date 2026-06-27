import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from a2a.helpers import (
    get_message_text,
    new_task_from_user_message,
    new_text_message,
    new_text_part,
)
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types.a2a_pb2 import TaskState

from marketing_agent.agent import root_agent


class MarketingAgentExecutor(AgentExecutor):
    """AgentExecutor backed by the ADK marketing_coordinator agent."""

    def __init__(self) -> None:
        self._session_service = InMemorySessionService()
        self._runner = Runner(
            agent=root_agent,
            app_name='marketing_agent',
            session_service=self._session_service,
        )

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        if context.current_task:
            task = context.current_task
        else:
            task = new_task_from_user_message(context.message)
            await event_queue.enqueue_event(task)

        task_updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task.id,
            context_id=task.context_id,
        )
        await task_updater.update_status(
            state=TaskState.TASK_STATE_WORKING,
            message=new_text_message('Processing request...'),
        )

        query = get_message_text(context.message)
        if not query:
            result = 'No text input provided.'
        else:
            session_id = task.context_id or task.id
            user_id = 'a2a_user'

            await self._session_service.create_session(
                app_name='marketing_agent',
                user_id=user_id,
                session_id=session_id,
            )

            result_parts = []
            async for event in self._runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=Content(parts=[Part(text=query)]),
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            result_parts.append(part.text)

            result = '\n'.join(result_parts) if result_parts else 'No response generated.'

        await task_updater.add_artifact(
            parts=[new_text_part(text=result, media_type='text/plain')]
        )

        await task_updater.update_status(
            state=TaskState.TASK_STATE_COMPLETED,
            message=new_text_message('Request completed.'),
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise NotImplementedError('Cancel is not supported.')


# Keep old name as alias so __main__.py import still works
HelloWorldAgentExecutor = MarketingAgentExecutor
