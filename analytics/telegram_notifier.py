"""
Telegram Notifications for KPI alerts
"""

import requests
import logging
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send KPI alerts to Telegram"""
    
    BASE_URL = "https://api.telegram.org"
    
    def __init__(self, bot_token: str):
        """
        Initialize Telegram notifier
        
        Args:
            bot_token: Telegram bot token
        """
        self.bot_token = bot_token
        self.api_url = f"{self.BASE_URL}/bot{bot_token}"
    
    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send message to Telegram chat
        
        Args:
            chat_id: Telegram chat ID
            text: Message text
            parse_mode: Text formatting (HTML, Markdown, etc)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Telegram message sent to {chat_id}")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram API error: {e}")
            return False
    
    def format_kpi_report(self, kpi_status: Dict, dashboard_url: str = None) -> str:
        """
        Format KPI status as Telegram message
        
        Args:
            kpi_status: Dict from KPI calculation engine
            dashboard_url: URL to dashboard for link
            
        Returns:
            Formatted message text
        """
        account_id = kpi_status["account_id"]
        plan = kpi_status["plan"]
        budget = kpi_status["budget"]
        conversions = kpi_status["conversions"]
        cpa = kpi_status["cpa"]
        pacing = kpi_status["pacing"]
        summary = kpi_status["summary"]
        
        # Status emoji
        status_emoji = "✅" if summary["overall_status"] == "ok" else (
            "⚠️" if summary["overall_status"] == "warning" else "🚨"
        )
        
        # Build message
        lines = [
            f"📊 <b>KPI Report - {account_id}</b>",
            f"📅 {pacing['days_elapsed']}/{pacing['total_days']} дней месяца",
            "",
            f"<b>💰 Бюджет:</b> {status_emoji}",
            f"  ₽{budget['spent']:,.0f} / ₽{budget['target']:,.0f}",
            f"  Pace: <b>{budget['pacing_pct']:.0f}%</b> ({'↑ +' if budget['pacing_pct'] > 100 else '↓ '}{abs(budget['pacing_pct']-100):.0f}%)",
            f"  {'✅ On Track' if budget['status'] == 'on_track' else ('⬆ Ahead' if budget['status'] == 'ahead' else '⬇ Behind')}",
            "",
            f"<b>📈 Конверсии:</b>",
            f"  {conversions['actual']} / {conversions['target']} лидов",
            f"  Pace: <b>{conversions['pacing_pct']:.0f}%</b>",
            f"  {'✅ On Track' if conversions['status'] == 'on_track' else ('⬆ Ahead' if conversions['status'] == 'ahead' else '⬇ Behind')}",
            "",
            f"<b>💵 CPA:</b>",
            f"  ₽{cpa['actual']:,.0f} vs ₽{cpa['target']:,.0f} (target)",
            f"  {'✅ On target' if abs(cpa['deviation_pct']) < 10 else ('⚠️ +' if cpa['deviation_pct'] > 0 else '')}{cpa['deviation_pct']:+.0f}%",
        ]
        
        # Add alerts if any
        if summary["key_alerts"]:
            lines.extend(["", "⚠️ <b>Alerts:</b>"])
            for alert in summary["key_alerts"]:
                lines.append(f"  • {alert}")
        
        # Add dashboard link if provided
        if dashboard_url:
            lines.extend(["", f"<a href='{dashboard_url}'>📱 View in Dashboard</a>"])
        
        lines.append(f"\n🕐 {datetime.now().strftime('%H:%M:%S')}")
        
        return "\n".join(lines)
    
    def send_kpi_report(self, chat_id: str, kpi_status: Dict, 
                       dashboard_url: str = None) -> bool:
        """
        Send KPI report to Telegram
        
        Args:
            chat_id: Telegram chat ID
            kpi_status: Dict from KPI calculation engine
            dashboard_url: Optional dashboard URL
            
        Returns:
            True if sent successfully
        """
        try:
            message = self.format_kpi_report(kpi_status, dashboard_url)
            return self.send_message(chat_id, message, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to format KPI report: {e}")
            return False
    
    def send_error_alert(self, chat_id: str, error_message: str) -> bool:
        """
        Send error alert to Telegram
        
        Args:
            chat_id: Telegram chat ID
            error_message: Error description
            
        Returns:
            True if sent successfully
        """
        text = f"""🚨 <b>System Error</b>

{error_message}

⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        return self.send_message(chat_id, text, parse_mode="HTML")


def create_telegram_notifier(bot_token: str) -> TelegramNotifier:
    """Factory function to create Telegram notifier"""
    return TelegramNotifier(bot_token)
