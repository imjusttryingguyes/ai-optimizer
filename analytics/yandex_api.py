"""
Yandex Direct API Client for fetching campaign performance data and conversions
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

logger = logging.getLogger(__name__)


class YandexDirectAPIClient:
    """Client for Yandex Direct API v5"""
    
    BASE_URL = "https://api.direct.yandex.com/json/v5"
    
    def __init__(self, access_token: str, login: str):
        """
        Initialize Yandex Direct API client
        
        Args:
            access_token: OAuth token for Yandex Direct API
            login: Client login for API requests
        """
        self.access_token = access_token
        self.login = login
        self.session = requests.Session()
        self.rate_limit_reset = 0
        self._setup_headers()
    
    def _setup_headers(self):
        """Setup request headers for API calls"""
        self.session.headers.update({
            "Authorization": f"Bearer {self.access_token}",
            "Client-Login": self.login,
            "Accept-Language": "ru",
        })
    
    def _check_rate_limit(self):
        """Check and respect API rate limits"""
        if time.time() < self.rate_limit_reset:
            wait_time = self.rate_limit_reset - time.time()
            logger.warning(f"Rate limited. Waiting {wait_time:.1f}s")
            time.sleep(wait_time + 1)
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """
        Make authenticated request to Yandex Direct API
        
        Args:
            method: HTTP method (GET, POST)
            endpoint: API endpoint path
            data: Request body data
            
        Returns:
            API response as dict
            
        Raises:
            Exception: If API returns error
        """
        self._check_rate_limit()
        
        url = f"{self.BASE_URL}/{endpoint}"
        
        try:
            if method == "GET":
                response = self.session.get(url)
            elif method == "POST":
                response = self.session.post(
                    url,
                    data=json.dumps(data),
                    headers={"Content-Type": "application/json"}
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            # Handle rate limiting
            if "x-ratelimit-reset" in response.headers:
                self.rate_limit_reset = float(response.headers["x-ratelimit-reset"])
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 400:
                logger.error(f"Bad request: {response.text}")
                raise ValueError(f"API Error 400: {response.text}")
            elif response.status_code == 401:
                logger.error("Unauthorized - check access token")
                raise ValueError("Unauthorized - invalid token")
            elif response.status_code == 429:
                logger.warning("Rate limited, retrying...")
                time.sleep(60)
                return self._make_request(method, endpoint, data)
            else:
                logger.error(f"API Error {response.status_code}: {response.text}")
                raise Exception(f"API Error {response.status_code}: {response.text}")
                
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def get_campaigns(self) -> List[Dict]:
        """
        Get list of campaigns
        
        Returns:
            List of campaigns with structure:
            {
                "Id": 123456,
                "Name": "Campaign Name",
                "Status": "ENABLED",
                "Type": "TEXT_CAMPAIGN"
            }
        """
        request_body = {
            "method": "get",
            "params": {
                "SelectionCriteria": {},
                "FieldNames": ["Id", "Name", "Status", "Type"]
            }
        }
        
        response = self._make_request("POST", "campaigns", request_body)
        
        if "result" in response and "Campaigns" in response["result"]:
            return response["result"]["Campaigns"]
        return []
    
    def get_ads(self, campaign_ids: List[int]) -> List[Dict]:
        """
        Get ads for campaigns
        
        Args:
            campaign_ids: List of campaign IDs
            
        Returns:
            List of ads with basic info
        """
        request_body = {
            "method": "get",
            "params": {
                "SelectionCriteria": {
                    "CampaignIds": campaign_ids
                },
                "FieldNames": ["Id", "CampaignId", "AdGroupId", "Status"]
            }
        }
        
        response = self._make_request("POST", "ads", request_body)
        
        if "result" in response and "Ads" in response["result"]:
            return response["result"]["Ads"]
        return []
    
    def get_report(self, date_range: Tuple[str, str], metrics: List[str]) -> List[Dict]:
        """
        Get statistics report for date range
        
        Args:
            date_range: Tuple of (start_date, end_date) in format 'YYYY-MM-DD'
            metrics: List of metrics (e.g., ['Impressions', 'Clicks', 'Cost', 'Conversions'])
            
        Returns:
            List of statistics by campaign/ad group/etc
        """
        start_date, end_date = date_range
        
        request_body = {
            "method": "get",
            "params": {
                "SelectionCriteria": {
                    "DateFrom": start_date,
                    "DateTo": end_date
                },
                "FieldNames": ["CampaignId", "CampaignName", "Date"],
                "OrderBy": [{"Field": "Date", "SortOrder": "DESCENDING"}],
                "ReportName": "Performance Report",
                "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                "Format": "TSV",
                "IncludeVAT": "NO",
                "IncludeDiscount": "NO"
            }
        }
        
        # Add requested metrics
        request_body["params"]["FieldNames"].extend(metrics)
        
        response = self._make_request("POST", "reports", request_body)
        
        # Reports API returns raw data, parse it
        if "result" in response:
            return self._parse_report(response["result"])
        return []
    
    def get_daily_stats(self, date: str) -> Dict:
        """
        Get daily statistics for a specific date
        
        Args:
            date: Date in format 'YYYY-MM-DD'
            
        Returns:
            Dict with daily metrics:
            {
                "cost_rub": 1000.50,
                "impressions": 5000,
                "clicks": 250,
                "conversions": 10
            }
        """
        try:
            request_body = {
                "method": "get",
                "params": {
                    "SelectionCriteria": {
                        "DateFrom": date,
                        "DateTo": date
                    },
                    "FieldNames": ["Date", "Impressions", "Clicks", "Cost", "Conversions"],
                    "ReportName": f"Daily Stats {date}",
                    "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                    "Format": "JSON",
                    "IncludeVAT": "NO",
                    "IncludeDiscount": "NO"
                }
            }
            
            response = self._make_request("POST", "reports", request_body)
            
            if "result" in response and "data" in response["result"]:
                # Aggregate all rows
                total_cost = 0
                total_impressions = 0
                total_clicks = 0
                total_conversions = 0
                
                for row in response["result"]["data"]:
                    total_cost += float(row.get("Cost", 0)) / 1_000_000  # API returns in units
                    total_impressions += int(row.get("Impressions", 0))
                    total_clicks += int(row.get("Clicks", 0))
                    total_conversions += int(row.get("Conversions", 0))
                
                return {
                    "date": date,
                    "cost_rub": round(total_cost, 2),
                    "impressions": total_impressions,
                    "clicks": total_clicks,
                    "conversions": total_conversions
                }
            return None
            
        except Exception as e:
            logger.error(f"Failed to get daily stats for {date}: {e}")
            return None
    
    def get_date_range_stats(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Get statistics for date range aggregated by day
        
        Args:
            start_date: Start date 'YYYY-MM-DD'
            end_date: End date 'YYYY-MM-DD'
            
        Returns:
            List of daily stats dicts
        """
        try:
            request_body = {
                "method": "get",
                "params": {
                    "SelectionCriteria": {
                        "DateFrom": start_date,
                        "DateTo": end_date
                    },
                    "FieldNames": ["Date", "Impressions", "Clicks", "Cost", "Conversions"],
                    "ReportName": f"Range Stats {start_date} to {end_date}",
                    "ReportType": "CAMPAIGN_PERFORMANCE_REPORT",
                    "Format": "JSON",
                    "IncludeVAT": "NO",
                    "IncludeDiscount": "NO"
                }
            }
            
            response = self._make_request("POST", "reports", request_body)
            
            if "result" in response and "data" in response["result"]:
                # Group by date
                date_stats = {}
                
                for row in response["result"]["data"]:
                    date = row.get("Date", "").split()[0]  # Extract just the date part
                    
                    if date not in date_stats:
                        date_stats[date] = {
                            "date": date,
                            "cost_rub": 0,
                            "impressions": 0,
                            "clicks": 0,
                            "conversions": 0
                        }
                    
                    date_stats[date]["cost_rub"] += float(row.get("Cost", 0)) / 1_000_000
                    date_stats[date]["impressions"] += int(row.get("Impressions", 0))
                    date_stats[date]["clicks"] += int(row.get("Clicks", 0))
                    date_stats[date]["conversions"] += int(row.get("Conversions", 0))
                
                # Round costs
                for stats in date_stats.values():
                    stats["cost_rub"] = round(stats["cost_rub"], 2)
                
                return sorted(date_stats.values(), key=lambda x: x["date"])
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get range stats {start_date}-{end_date}: {e}")
            return []
    
    @staticmethod
    def _parse_report(report_data: Dict) -> List[Dict]:
        """Parse report response data"""
        # Implementation depends on report format
        # For now, return raw data
        return report_data.get("data", [])


def create_yandex_client(access_token: str, login: str) -> YandexDirectAPIClient:
    """
    Factory function to create Yandex Direct API client
    
    Args:
        access_token: OAuth token
        login: Client login
        
    Returns:
        YandexDirectAPIClient instance
    """
    return YandexDirectAPIClient(access_token, login)
