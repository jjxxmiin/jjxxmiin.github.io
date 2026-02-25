import os
import json
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    OrderBy
)

class GA4Client:
    def __init__(self, property_id=None, credentials_json=None):
        self.property_id = property_id or os.environ.get("GA4_PROPERTY_ID")
        self.credentials_json = credentials_json or os.environ.get("GA4_CREDENTIALS_JSON")
        
        if not self.property_id:
            print("Warning: GA4_PROPERTY_ID not set.")
        
        self.client = None
        if self.credentials_json:
            try:
                # credentials_json can be a path or a JSON string
                if os.path.exists(self.credentials_json):
                    self.client = BetaAnalyticsDataClient.from_service_account_file(self.credentials_json)
                else:
                    info = json.loads(self.credentials_json)
                    self.client = BetaAnalyticsDataClient.from_service_account_info(info)
            except Exception as e:
                print(f"Error initializing GA4 client: {e}")

    def get_weekly_metrics(self):
        """Fetches metrics for the last 7 days."""
        if not self.client or not self.property_id:
            print("GA4 client not fully configured. Returning mock data or empty list.")
            return self._get_mock_data()

        request = RunReportRequest(
            property=f"properties/{self.property_id}",
            dimensions=[Dimension(name="pagePath")],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="userEngagementDuration"),
                Metric(name="activeUsers")
            ],
            date_ranges=[DateRange(start_date="7daysAgo", end_date="yesterday")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)]
        )

        try:
            response = self.client.run_report(request)
            results = []
            for row in response.rows:
                # filter for blog posts usually starting with /posts/ or date patterns
                path = row.dimension_values[0].value
                if not (path.startswith("/posts/") or any(c.isdigit() for c in path[:5])):
                    continue
                    
                views = int(row.metric_values[0].value)
                duration = float(row.metric_values[1].value)
                users = int(row.metric_values[2].value)
                
                avg_engagement = duration / users if users > 0 else 0
                
                results.append({
                    "path": path,
                    "views": views,
                    "avg_engagement_time": avg_engagement
                })
            return results
        except Exception as e:
            print(f"Error running GA4 report: {e}")
            return self._get_mock_data()

    def _get_mock_data(self):
        """Returns mock data for testing purposes."""
        return [
            {"path": "/posts/claude37/", "views": 150, "avg_engagement_time": 120},
            {"path": "/posts/birefnet/", "views": 80, "avg_engagement_time": 45},
            {"path": "/posts/Deepseek/", "views": 20, "avg_engagement_time": 10},
            {"path": "/posts/SWELancer/", "views": 500, "avg_engagement_time": 180}
        ]

if __name__ == "__main__":
    client = GA4Client()
    metrics = client.get_weekly_metrics()
    print(json.dumps(metrics, indent=2))
