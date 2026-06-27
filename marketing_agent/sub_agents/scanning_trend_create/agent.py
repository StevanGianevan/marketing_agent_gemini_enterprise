# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Trend_create_agent: for suggesting meanigful DNS domain"""

from google.adk import Agent
# from google.adk.tools import google_search
# from ...tools.bigquery_tools import (
#     get_campaign_performance,
#     analyze_audience_demographics,
#     get_conversion_funnel,
#     insert_campaign_data,
# )
from ...tools.youtube_tools import (
    get_channel_stats,
    # search_videos,
    # get_video_stats,
    # get_channel_videos,
    # get_trending_videos,
    # analyze_video_performance,
    # save_video_performance_to_bigquery,
    # sync_channel_videos_to_bigquery,
)

from . import prompt

MODEL = "gemini-2.5-pro"

trend_create_agent = Agent(
    model=MODEL,
    name="scanner_tren_content",
    instruction=prompt.TREND_CREATE_PROMPT,
    output_key="trend_create_output",
    tools=[
        # google_search,
        # BigQuery analytics tools
        # get_campaign_performance,
        # analyze_audience_demographics,
        # get_conversion_funnel,
        # insert_campaign_data,
        # YouTube tools for trend analysis
        get_channel_stats,
        # search_videos,
        # get_video_stats,
        # get_channel_videos,
        # get_trending_videos,
        # analyze_video_performance,
        # save_video_performance_to_bigquery,
        # sync_channel_videos_to_bigquery,
    ],
)
