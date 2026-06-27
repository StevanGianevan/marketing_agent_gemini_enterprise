import google.auth
from google.adk.tools.bigquery import BigQueryToolset, BigQueryCredentialsConfig
from google.adk.tools import ToolContext

# Initialize BigQuery credentials using Application Default Credentials
credentials, project_id = google.auth.default()

# Configure BigQuery toolset with your project
bq_config = BigQueryCredentialsConfig(
    credentials=credentials,
    project_id=project_id,
)

# Create BigQuery toolset instance
bigquery_toolset = BigQueryToolset(
    credentials_config=bq_config,
    description="Query and analyze marketing campaign data from BigQuery datasets"
)


# ============ Custom BigQuery Tools for Marketing ============

async def get_campaign_performance(
    campaign_name: str,
    date_range: str = "last_30_days",
    tool_context: ToolContext = None
) -> dict:
    """Get performance metrics for a specific marketing campaign.

    Args:
        campaign_name: Name of the marketing campaign (e.g., 'summer_sale_2024')
        date_range: Time range to analyze ('last_7_days', 'last_30_days', 'last_quarter')

    Returns:
        dict with metrics like impressions, clicks, conversions, ROI, CPC, CTR
    """
    query = f"""
    SELECT
        campaign_name,
        COUNT(*) as impressions,
        SUM(CASE WHEN clicked THEN 1 ELSE 0 END) as clicks,
        SUM(CASE WHEN converted THEN 1 ELSE 0 END) as conversions,
        ROUND(SUM(spend), 2) as total_spend,
        ROUND(SUM(revenue), 2) as total_revenue,
        ROUND(SUM(revenue) / SUM(spend), 2) as roi
    FROM `{project_id}.marketing.campaign_analytics`
    WHERE campaign_name = '{campaign_name}'
        AND date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
    GROUP BY campaign_name
    """

    try:
        result = await bigquery_toolset.query(query)
        if result:
            return {
                "status": "success",
                "campaign": campaign_name,
                "metrics": result[0] if result else {}
            }
        else:
            return {
                "status": "no_data",
                "message": f"No data found for campaign '{campaign_name}'"
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
    FROM `{project_id}.{dataset}.{table}`
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
        FROM `{project_id}.marketing.events`
        WHERE event_type = 'page_view'
        GROUP BY user_id

        UNION ALL

        SELECT
            user_id,
            'click' as stage,
            COUNT(*) as count
        FROM `{project_id}.marketing.events`
        WHERE event_type = 'click'
        GROUP BY user_id

        UNION ALL

        SELECT
            user_id,
            'purchase' as stage,
            COUNT(*) as count
        FROM `{project_id}.marketing.events`
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
    impressions: int,
    clicks: int,
    conversions: int,
    spend: float,
    revenue: float,
    tool_context: ToolContext = None
) -> dict:
    """Insert new campaign performance record into BigQuery.

    Args:
        campaign_name: Name of the campaign
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
        "date": "CURRENT_DATE()",
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "spend": spend,
        "revenue": revenue,
    }]

    try:
        await bigquery_toolset.insert_rows(
            table_id=f"{project_id}.marketing.campaign_analytics",
            rows=rows
        )
        return {
            "status": "success",
            "message": f"Campaign '{campaign_name}' data inserted successfully"
        }
    except Exception as e:
        return {"status": "failed", "error": str(e)}
