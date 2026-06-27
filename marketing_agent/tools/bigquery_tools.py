import os
import google.auth
from google.adk.tools.bigquery import BigQueryToolset, BigQueryCredentialsConfig
from google.adk.tools import ToolContext

# Initialize BigQuery credentials using Application Default Credentials
credentials, project_id = google.auth.default()

# Load BigQuery configuration from environment
BG_LOCATION = os.getenv("BG_LOCATION")  # Default to asia-southeast2 if not set
BQ_DATASET = os.getenv("BQ_DATASET")
BQ_CAMPAIGN_TABLE = os.getenv("BQ_CAMPAIGN_TABLE")
BQ_EVENTS_TABLE = os.getenv("BQ_EVENTS_TABLE")
BQ_USERS_TABLE = os.getenv("BQ_USERS_TABLE")

# Configure BigQuery toolset with your project
bq_config = BigQueryCredentialsConfig(
    credentials=credentials
)

# Create BigQuery toolset instance
bigquery_toolset = BigQueryToolset(credentials_config=bq_config)


# ============ Auto-Initialize BigQuery Tables ============

async def ensure_tables_exist():
    """Create BigQuery tables if they don't exist (auto-initialize)."""

    # Create campaign_analytics table
    campaign_table_ddl = f"""
    CREATE TABLE IF NOT EXISTS `{project_id}.{BQ_DATASET}.{BQ_CAMPAIGN_TABLE}` (
        date DATE,
        campaign_name STRING,
        provider_name STRING,
        impressions INT64,
        clicks INT64,
        conversions INT64,
        spend FLOAT64,
        revenue FLOAT64,
        clicked BOOL,
        converted BOOL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    )
    PARTITION BY date
    CLUSTER BY campaign_name, provider_name;
    """

    # Create events table
    events_table_ddl = f"""
    CREATE TABLE IF NOT EXISTS `{project_id}.{BQ_DATASET}.{BQ_EVENTS_TABLE}` (
        event_id STRING,
        user_id STRING,
        event_type STRING,
        event_timestamp TIMESTAMP,
        campaign_name STRING,
        provider_name STRING,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    )
    PARTITION BY DATE(event_timestamp)
    CLUSTER BY event_type, user_id;
    """

    # Create user_events table
    users_table_ddl = f"""
    CREATE TABLE IF NOT EXISTS `{project_id}.{BQ_DATASET}.{BQ_USERS_TABLE}` (
        user_id STRING,
        age INT64,
        country STRING,
        device_type STRING,
        engagement_score FLOAT64,
        conversion_value FLOAT64,
        event_timestamp TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    )
    PARTITION BY DATE(event_timestamp)
    CLUSTER BY country, device_type;
    """

    # Create YouTube analytics table (compatible with campaign_analytics schema)
    youtube_table_ddl = f"""
    CREATE TABLE IF NOT EXISTS `{project_id}.{BQ_DATASET}.youtube_analytics` (
        date DATE,
        campaign_name STRING,
        provider_name STRING,
        video_id STRING,
        channel_id STRING,
        video_title STRING,
        impressions INT64,
        clicks INT64,
        conversions INT64,
        spend FLOAT64,
        revenue FLOAT64,
        views INT64,
        likes INT64,
        comments INT64,
        engagement_rate FLOAT64,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP()
    )
    PARTITION BY date
    CLUSTER BY channel_id, video_id;
    """

    try:
        # Execute DDL statements
        await bigquery_toolset.execute_sql(campaign_table_ddl)
        await bigquery_toolset.execute_sql(events_table_ddl)
        await bigquery_toolset.execute_sql(users_table_ddl)
        await bigquery_toolset.execute_sql(youtube_table_ddl)
        return {
            "status": "success",
            "message": "BigQuery tables initialized successfully"
        }
    except Exception as e:
        return {
            "status": "failed",
            "message": f"Error initializing tables: {str(e)}"
        }


# ============ Custom BigQuery Tools for Marketing ============

async def get_campaign_performance(
    campaign_name: str,
    provider_name: str = None,
    date_range: str = "last_30_days",
    tool_context: ToolContext = None
) -> dict:
    """Get performance metrics for a specific marketing campaign.

    Args:
        campaign_name: Name of the marketing campaign (e.g., 'summer_sale_2024')
        provider_name: Optional filter by platform (e.g., 'youtube', 'instagram', 'twitter', 'linkedin')
        date_range: Time range to analyze ('last_7_days', 'last_30_days', 'last_quarter')

    Returns:
        dict with metrics like impressions, clicks, conversions, ROI, by provider if specified
    """
    provider_filter = f"AND provider_name = '{provider_name}'" if provider_name else ""

    query = f"""
    SELECT
        campaign_name,
        provider_name,
        COUNT(*) as impressions,
        SUM(CASE WHEN clicked THEN 1 ELSE 0 END) as clicks,
        SUM(CASE WHEN converted THEN 1 ELSE 0 END) as conversions,
        ROUND(SUM(spend), 2) as total_spend,
        ROUND(SUM(revenue), 2) as total_revenue,
        ROUND(SUM(revenue) / SUM(spend), 2) as roi
    FROM `{project_id}.{BQ_DATASET}.{BQ_CAMPAIGN_TABLE}`
    WHERE campaign_name = '{campaign_name}'
        {provider_filter}
        AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY campaign_name, provider_name
    """

    try:
        result = await bigquery_toolset.query(query)
        if result:
            return {
                "status": "success",
                "campaign": campaign_name,
                "provider": provider_name,
                "metrics": result
            }
        else:
            return {
                "status": "no_data",
                "message": f"No data found for campaign '{campaign_name}'{f' from {provider_name}' if provider_name else ''}"
            }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def analyze_audience_demographics(
    dataset: str = "marketing",
    table: str = "user_events",
    tool_context: ToolContext = None
) -> dict:
    """Analyze audience demographics from user engagement data.

    Args:
        dataset: BigQuery dataset name
        table: Table name with user/event data

    Returns:
        dict with age groups, regions, device types, and engagement stats
    """
    query = f"""
    SELECT
        CASE
            WHEN age < 18 THEN '13-17'
            WHEN age < 25 THEN '18-24'
            WHEN age < 35 THEN '25-34'
            WHEN age < 45 THEN '35-44'
            WHEN age < 55 THEN '45-54'
            ELSE '55+'
        END as age_group,
        country as region,
        device_type,
        COUNT(*) as user_count,
        ROUND(AVG(engagement_score), 2) as avg_engagement,
        ROUND(SUM(conversion_value), 2) as total_conversions
    FROM `{project_id}.{dataset or BQ_DATASET}.{table or BQ_USERS_TABLE}`
    WHERE DATE(event_timestamp) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
    GROUP BY age_group, region, device_type
    ORDER BY user_count DESC
    """

    try:
        results = await bigquery_toolset.query(query)
        return {
            "status": "success",
            "demographic_breakdown": results
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def get_conversion_funnel(
    funnel_name: str = "website_purchase",
    tool_context: ToolContext = None
) -> dict:
    """Analyze conversion funnel stages (e.g., view -> click -> purchase).

    Args:
        funnel_name: Name of the conversion funnel to analyze

    Returns:
        dict with funnel stages, drop-off rates, and conversion rates
    """
    query = f"""
    WITH funnel_stages AS (
        SELECT
            user_id,
            'view' as stage,
            COUNT(*) as count
        FROM `{project_id}.{BQ_DATASET}.{BQ_EVENTS_TABLE}`
        WHERE event_type = 'page_view'
        GROUP BY user_id

        UNION ALL

        SELECT
            user_id,
            'click' as stage,
            COUNT(*) as count
        FROM `{project_id}.{BQ_DATASET}.{BQ_EVENTS_TABLE}`
        WHERE event_type = 'click'
        GROUP BY user_id

        UNION ALL

        SELECT
            user_id,
            'purchase' as stage,
            COUNT(*) as count
        FROM `{project_id}.{BQ_DATASET}.{BQ_EVENTS_TABLE}`
        WHERE event_type = 'purchase'
        GROUP BY user_id
    )
    SELECT
        stage,
        COUNT(DISTINCT user_id) as users,
        ROUND(100 * COUNT(DISTINCT user_id) /
            (SELECT COUNT(DISTINCT user_id) FROM funnel_stages WHERE stage = 'view'), 2)
            as conversion_rate_from_view
    FROM funnel_stages
    GROUP BY stage
    ORDER BY
        CASE stage WHEN 'view' THEN 1 WHEN 'click' THEN 2 WHEN 'purchase' THEN 3 END
    """

    try:
        results = await bigquery_toolset.query(query)
        return {
            "status": "success",
            "funnel_stages": results
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def insert_campaign_data(
    campaign_name: str,
    provider_name: str,
    impressions: int,
    clicks: int,
    conversions: int,
    spend: float,
    revenue: float,
    tool_context: ToolContext = None
) -> dict:
    """Insert new campaign performance record into BigQuery with provider tracking.

    Args:
        campaign_name: Name of the campaign (e.g., 'summer_sale_2024')
        provider_name: Social media platform (e.g., 'youtube', 'instagram', 'twitter', 'linkedin')
        impressions: Number of impressions
        clicks: Number of clicks
        conversions: Number of conversions
        spend: Amount spent on campaign
        revenue: Revenue generated

    Returns:
        dict with status of insertion
    """
    rows = [{
        "campaign_name": campaign_name,
        "provider_name": provider_name,
        "date": "CURRENT_DATE()",
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend": spend,
        "revenue": revenue,
    }]

    try:
        await bigquery_toolset.insert_rows(
            table_id=f"{project_id}.{BQ_DATASET}.{BQ_CAMPAIGN_TABLE}",
            rows=rows
        )
        return {
            "status": "success",
            "message": f"Campaign '{campaign_name}' from {provider_name} data inserted successfully"
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}
