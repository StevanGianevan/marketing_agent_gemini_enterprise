"""YouTube integration tools for marketing agent."""

import os
from datetime import datetime
from google.adk.tools import ToolContext
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Initialize YouTube API client
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# BigQuery config for YouTube analytics
try:
    from .bigquery_tools import bigquery_toolset
    HAS_BIGQUERY = True
except ImportError:
    HAS_BIGQUERY = False


def get_youtube_client():
    """Initialize and return YouTube API client."""
    if not YOUTUBE_API_KEY:
        raise ValueError("YOUTUBE_API_KEY not found in environment variables")
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


async def get_channel_stats(
    channel_id: str = None,
    username: str = None,
    tool_context: ToolContext = None
) -> dict:
    """Get YouTube channel statistics (subscribers, views, video count).

    Args:
        channel_id: YouTube channel ID (starts with 'UC')
        username: YouTube username (if channel_id not provided)

    Returns:
        dict with channel stats: subscribers, total_views, video_count, description
    """
    try:
        youtube = get_youtube_client()

        # Get channel ID from username if needed
        if not channel_id and username:
            request = youtube.channels().list(
                part="id",
                forUsername=username
            )
            response = request.execute()
            if not response.get("items"):
                return {
                    "status": "failed",
                    "error": f"Channel not found for username: {username}"
                }
            channel_id = response["items"][0]["id"]

        # Get channel statistics
        request = youtube.channels().list(
            part="statistics,snippet",
            id=channel_id
        )
        response = request.execute()

        if not response.get("items"):
            return {
                "status": "failed",
                "error": f"Channel not found: {channel_id}"
            }

        channel = response["items"][0]
        stats = channel["statistics"]
        snippet = channel["snippet"]

        return {
            "status": "success",
            "channel_id": channel_id,
            "channel_name": snippet["title"],
            "description": snippet["description"],
            "subscribers": stats.get("subscriberCount", "Not disclosed"),
            "total_views": stats.get("viewCount", 0),
            "video_count": stats.get("videoCount", 0),
        }
    except HttpError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def search_videos(
    query: str,
    max_results: int = 10,
    order: str = "relevance",
    tool_context: ToolContext = None
) -> dict:
    """Search YouTube videos by keyword.

    Args:
        query: Search query string
        max_results: Maximum number of results (default: 10, max: 50)
        order: Order results by 'relevance', 'viewCount', 'uploadDate', 'rating'

    Returns:
        dict with list of videos (video_id, title, channel, upload_date)
    """
    try:
        if max_results > 50:
            max_results = 50

        youtube = get_youtube_client()
        request = youtube.search().list(
            part="snippet",
            q=query,
            type="video",
            maxResults=max_results,
            order=order
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "video_id": item["id"]["videoId"],
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "upload_date": snippet["publishedAt"],
                "thumbnail": snippet["thumbnails"]["default"]["url"],
            })

        return {
            "status": "success",
            "query": query,
            "results_count": len(videos),
            "videos": videos
        }
    except HttpError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def get_video_stats(
    video_id: str,
    tool_context: ToolContext = None
) -> dict:
    """Get video statistics (views, likes, comments).

    Args:
        video_id: YouTube video ID

    Returns:
        dict with video stats: views, likes, comments, duration, title
    """
    try:
        youtube = get_youtube_client()
        request = youtube.videos().list(
            part="statistics,snippet,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get("items"):
            return {
                "status": "failed",
                "error": f"Video not found: {video_id}"
            }

        video = response["items"][0]
        stats = video["statistics"]
        snippet = video["snippet"]
        details = video["contentDetails"]

        return {
            "status": "success",
            "video_id": video_id,
            "title": snippet["title"],
            "channel": snippet["channelTitle"],
            "views": stats.get("viewCount", 0),
            "likes": stats.get("likeCount", "Not available"),
            "comments": stats.get("commentCount", 0),
            "duration": details["duration"],
            "upload_date": snippet["publishedAt"],
            "description": snippet["description"],
        }
    except HttpError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def get_channel_videos(
    channel_id: str = None,
    username: str = None,
    max_results: int = 10,
    order: str = "date",
    tool_context: ToolContext = None
) -> dict:
    """Get recent/popular videos from a YouTube channel.

    Args:
        channel_id: YouTube channel ID
        username: YouTube username (if channel_id not provided)
        max_results: Maximum videos to fetch (default: 10, max: 50)
        order: Sort by 'date', 'viewCount', or 'rating'

    Returns:
        dict with list of channel videos
    """
    try:
        if max_results > 50:
            max_results = 50

        youtube = get_youtube_client()

        # Get channel ID from username if needed
        if not channel_id and username:
            request = youtube.channels().list(
                part="id",
                forUsername=username
            )
            response = request.execute()
            if not response.get("items"):
                return {
                    "status": "failed",
                    "error": f"Channel not found: {username}"
                }
            channel_id = response["items"][0]["id"]

        # Get uploads playlist ID
        request = youtube.channels().list(
            part="contentDetails",
            id=channel_id
        )
        response = request.execute()

        if not response.get("items"):
            return {
                "status": "failed",
                "error": f"Channel not found: {channel_id}"
            }

        uploads_id = response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        # Get videos from uploads playlist
        request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_id,
            maxResults=max_results,
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            videos.append({
                "video_id": snippet["resourceId"]["videoId"],
                "title": snippet["title"],
                "upload_date": snippet["publishedAt"],
                "thumbnail": snippet["thumbnails"]["default"]["url"],
            })

        return {
            "status": "success",
            "channel_id": channel_id,
            "videos_count": len(videos),
            "videos": videos
        }
    except HttpError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def get_trending_videos(
    region_code: str = "US",
    category_id: str = None,
    max_results: int = 10,
    tool_context: ToolContext = None
) -> dict:
    """Get trending/popular videos on YouTube.

    Args:
        region_code: Region code (e.g., 'US', 'ID', 'JP') - default US
        category_id: YouTube category ID (10=music, 20=gaming, etc.)
        max_results: Max videos to return (default: 10, max: 50)

    Returns:
        dict with list of trending videos
    """
    try:
        if max_results > 50:
            max_results = 50

        youtube = get_youtube_client()
        request = youtube.videos().list(
            part="snippet,statistics",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=max_results,
            videoCategoryId=category_id
        )
        response = request.execute()

        videos = []
        for item in response.get("items", []):
            snippet = item["snippet"]
            stats = item["statistics"]
            videos.append({
                "video_id": item["id"],
                "title": snippet["title"],
                "channel": snippet["channelTitle"],
                "views": stats.get("viewCount", 0),
                "likes": stats.get("likeCount", 0),
                "upload_date": snippet["publishedAt"],
                "thumbnail": snippet["thumbnails"]["default"]["url"],
            })

        return {
            "status": "success",
            "region": region_code,
            "videos_count": len(videos),
            "videos": videos
        }
    except HttpError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def analyze_video_performance(
    video_id: str,
    tool_context: ToolContext = None
) -> dict:
    """Analyze video performance and engagement metrics.

    Args:
        video_id: YouTube video ID

    Returns:
        dict with engagement analysis: engagement_rate, likes_per_view, etc.
    """
    try:
        youtube = get_youtube_client()
        request = youtube.videos().list(
            part="statistics,snippet,contentDetails",
            id=video_id
        )
        response = request.execute()

        if not response.get("items"):
            return {
                "status": "failed",
                "error": f"Video not found: {video_id}"
            }

        video = response["items"][0]
        stats = video["statistics"]
        snippet = video["snippet"]

        views = int(stats.get("viewCount", 0)) or 1
        likes = int(stats.get("likeCount", 0))
        comments = int(stats.get("commentCount", 0))

        engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0
        likes_per_view = (likes / views) if views > 0 else 0

        return {
            "status": "success",
            "video_id": video_id,
            "title": snippet["title"],
            "total_views": views,
            "total_likes": likes,
            "total_comments": comments,
            "engagement_rate": round(engagement_rate, 2),
            "likes_per_view": round(likes_per_view, 4),
            "upload_date": snippet["publishedAt"],
        }
    except HttpError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def save_video_performance_to_bigquery(
    campaign_name: str,
    video_id: str,
    channel_id: str,
    video_title: str,
    views: int,
    likes: int,
    comments: int,
    spend: float = 0.0,
    revenue: float = 0.0,
    tool_context: ToolContext = None
) -> dict:
    """Save YouTube video performance data to BigQuery.

    Args:
        campaign_name: Marketing campaign name
        video_id: YouTube video ID
        channel_id: YouTube channel ID
        video_title: Video title
        views: Number of views
        likes: Number of likes
        comments: Number of comments
        spend: Amount spent on this video (optional)
        revenue: Revenue generated (optional)

    Returns:
        dict with save status
    """
    if not HAS_BIGQUERY:
        return {
            "status": "failed",
            "error": "BigQuery tools not available"
        }

    try:
        from .bigquery_tools import project_id, BQ_DATASET

        # Calculate engagement rate
        engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0

        # Prepare data for BigQuery
        rows = [{
            "date": datetime.now().date().isoformat(),
            "campaign_name": campaign_name,
            "provider_name": "youtube",
            "video_id": video_id,
            "channel_id": channel_id,
            "video_title": video_title,
            "impressions": views,
            "clicks": 0,
            "conversions": 0,
            "spend": spend,
            "revenue": revenue,
            "views": views,
            "likes": likes,
            "comments": comments,
            "engagement_rate": round(engagement_rate, 2),
        }]

        # Insert to BigQuery
        await bigquery_toolset.insert_rows(
            table_id=f"{project_id}.{BQ_DATASET}.youtube_analytics",
            rows=rows
        )

        return {
            "status": "success",
            "message": f"YouTube video '{video_title}' performance saved to BigQuery",
            "data_saved": {
                "video_id": video_id,
                "views": views,
                "engagement_rate": round(engagement_rate, 2)
            }
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def sync_channel_videos_to_bigquery(
    channel_id: str,
    campaign_name: str,
    spend: float = 0.0,
    tool_context: ToolContext = None
) -> dict:
    """Sync all videos from a YouTube channel to BigQuery with performance metrics.

    Args:
        channel_id: YouTube channel ID
        campaign_name: Marketing campaign name
        spend: Total spend for this campaign

    Returns:
        dict with sync status and number of videos saved
    """
    if not HAS_BIGQUERY:
        return {
            "status": "failed",
            "error": "BigQuery tools not available"
        }

    try:
        from .bigquery_tools import project_id, BQ_DATASET

        youtube = get_youtube_client()

        # Get uploads playlist
        request = youtube.channels().list(
            part="contentDetails,snippet",
            id=channel_id
        )
        response = request.execute()

        if not response.get("items"):
            return {
                "status": "failed",
                "error": f"Channel not found: {channel_id}"
            }

        channel = response["items"][0]
        uploads_id = channel["contentDetails"]["relatedPlaylists"]["uploads"]
        channel_title = channel["snippet"]["title"]

        # Get all videos from uploads playlist
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_id,
            maxResults=50
        )

        all_videos = []
        videos_saved = 0

        while request and videos_saved < 50:
            response = request.execute()

            for item in response.get("items", []):
                video_id = item["contentDetails"]["videoId"]
                video_title = item["snippet"]["title"]

                # Get video stats
                stats_request = youtube.videos().list(
                    part="statistics",
                    id=video_id
                )
                stats_response = stats_request.execute()

                if stats_response.get("items"):
                    stats = stats_response["items"][0]["statistics"]
                    views = int(stats.get("viewCount", 0))
                    likes = int(stats.get("likeCount", 0))
                    comments = int(stats.get("commentCount", 0))

                    # Calculate engagement
                    engagement_rate = ((likes + comments) / views * 100) if views > 0 else 0

                    all_videos.append({
                        "date": datetime.now().date().isoformat(),
                        "campaign_name": campaign_name,
                        "provider_name": "youtube",
                        "video_id": video_id,
                        "channel_id": channel_id,
                        "video_title": video_title,
                        "impressions": views,
                        "clicks": 0,
                        "conversions": 0,
                        "spend": spend / max(len(response.get("items", [])), 1),
                        "revenue": 0,
                        "views": views,
                        "likes": likes,
                        "comments": comments,
                        "engagement_rate": round(engagement_rate, 2),
                    })
                    videos_saved += 1

            # Get next page
            request = youtube.playlistItems().list_next(request, response)

        # Insert all videos to BigQuery
        if all_videos:
            await bigquery_toolset.insert_rows(
                table_id=f"{project_id}.{BQ_DATASET}.youtube_analytics",
                rows=all_videos
            )

        return {
            "status": "success",
            "message": f"Synced {videos_saved} videos from '{channel_title}' to BigQuery",
            "videos_synced": videos_saved,
            "campaign": campaign_name
        }
    except HttpError as e:
        return {"status": "failed", "error": str(e)}
    except Exception as e:
        return {"status": "failed", "error": str(e)}
