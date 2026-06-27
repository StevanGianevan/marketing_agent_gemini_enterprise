from google.adk import Agent
from ...tools.youtube_tools import (
    get_channel_stats,
    search_videos,
    get_video_stats,
    analyze_video_performance,
)

from . import prompt

MODEL = "gemini-2.5-flash"

youtube_analyser = Agent(
    model=MODEL,
    name="youtube_analyser",
    instruction=prompt.YOUTUBE_ANALYSER,
    output_key="youtube_analyser_output",
    tools=[
        get_channel_stats,
        search_videos,
        get_video_stats,
        analyze_video_performance,
    ]
)
