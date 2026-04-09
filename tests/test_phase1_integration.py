#!/usr/bin/env python
"""
Integration tests for Phase 1a KPI system components
Tests KPI engine, sync task, and Telegram notifier
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_kpi_engine_imports():
    """Test KPI engine imports"""
    try:
        from analytics.kpi_engine import KPICalculationEngine, create_kpi_engine
        print("✅ KPI Engine imports OK")
        return True
    except Exception as e:
        print(f"❌ KPI Engine import failed: {e}")
        return False

def test_sync_task_imports():
    """Test sync task imports"""
    try:
        from analytics.kpi_sync_task import KPIDailySync, create_kpi_sync_task
        print("✅ KPI Sync Task imports OK")
        return True
    except Exception as e:
        print(f"❌ KPI Sync Task import failed: {e}")
        return False

def test_telegram_notifier_imports():
    """Test Telegram notifier imports"""
    try:
        from analytics.telegram_notifier import TelegramNotifier, create_telegram_notifier
        print("✅ Telegram Notifier imports OK")
        return True
    except Exception as e:
        print(f"❌ Telegram Notifier import failed: {e}")
        return False

def test_yandex_api_imports():
    """Test Yandex API imports"""
    try:
        from analytics.yandex_api import YandexDirectAPIClient
        print("✅ Yandex API imports OK")
        return True
    except Exception as e:
        print(f"❌ Yandex API import failed: {e}")
        return False

def test_scheduler_imports():
    """Test scheduler imports"""
    try:
        from analytics.kpi_scheduler import KPIScheduler, init_scheduler
        print("✅ KPI Scheduler imports OK")
        return True
    except Exception as e:
        print(f"❌ KPI Scheduler import failed: {e}")
        return False

def test_flask_app_imports():
    """Test Flask app imports"""
    try:
        from web.app import app
        print("✅ Flask app imports OK")
        return True
    except Exception as e:
        print(f"❌ Flask app import failed: {e}")
        return False

def test_kpi_engine_methods():
    """Test KPI engine has required methods"""
    try:
        from analytics.kpi_engine import KPICalculationEngine
        
        required_methods = [
            'get_current_month_plan',
            'get_month_actual_metrics',
            'calculate_kpi_status',
            'close'
        ]
        
        for method in required_methods:
            if not hasattr(KPICalculationEngine, method):
                print(f"❌ KPI Engine missing method: {method}")
                return False
        
        print("✅ KPI Engine has all required methods")
        return True
    except Exception as e:
        print(f"❌ KPI Engine method check failed: {e}")
        return False

def test_telegram_notifier_methods():
    """Test Telegram notifier has required methods"""
    try:
        from analytics.telegram_notifier import TelegramNotifier
        
        required_methods = [
            'send_message',
            'format_kpi_report',
            'send_kpi_report',
            'send_error_alert'
        ]
        
        for method in required_methods:
            if not hasattr(TelegramNotifier, method):
                print(f"❌ Telegram Notifier missing method: {method}")
                return False
        
        print("✅ Telegram Notifier has all required methods")
        return True
    except Exception as e:
        print(f"❌ Telegram Notifier method check failed: {e}")
        return False

def test_telegram_message_formatting():
    """Test Telegram message formatting"""
    try:
        from analytics.telegram_notifier import TelegramNotifier
        
        notifier = TelegramNotifier("test_token")
        
        # Mock KPI status
        kpi_status = {
            "account_id": "test_account",
            "plan": {"budget_rub": 100000, "leads_target": 100, "cpa_target_rub": 1000},
            "budget": {
                "spent": 50000,
                "target": 100000,
                "pacing_pct": 75,
                "status": "on_track",
                "severity": "ok"
            },
            "conversions": {
                "actual": 45,
                "target": 100,
                "pacing_pct": 45,
                "status": "behind",
                "severity": "warning"
            },
            "cpa": {
                "actual": 1111,
                "target": 1000,
                "deviation_pct": 11,
                "status": "warning"
            },
            "pacing": {
                "days_elapsed": 15,
                "total_days": 30
            },
            "summary": {
                "overall_status": "warning",
                "key_alerts": ["Budget pacing +75% - spending ahead of plan"]
            }
        }
        
        message = notifier.format_kpi_report(kpi_status, "http://localhost:5000")
        
        if not message or len(message) < 50:
            print(f"❌ Telegram message format invalid: {message}")
            return False
        
        if "test_account" not in message:
            print(f"❌ Account ID not in message")
            return False
        
        print("✅ Telegram message formatting OK")
        return True
    except Exception as e:
        print(f"❌ Telegram message format test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=" * 60)
    print("Phase 1 Integration Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Import Tests", [
            test_kpi_engine_imports,
            test_sync_task_imports,
            test_telegram_notifier_imports,
            test_yandex_api_imports,
            test_scheduler_imports,
            test_flask_app_imports,
        ]),
        ("Method Tests", [
            test_kpi_engine_methods,
            test_telegram_notifier_methods,
        ]),
        ("Functionality Tests", [
            test_telegram_message_formatting,
        ])
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for section_name, test_list in tests:
        print(f"\n{section_name}:")
        print("-" * 40)
        
        for test_func in test_list:
            total_tests += 1
            if test_func():
                passed_tests += 1
    
    print()
    print("=" * 60)
    print(f"Results: {passed_tests}/{total_tests} tests passed")
    print("=" * 60)
    
    return 0 if passed_tests == total_tests else 1

if __name__ == '__main__':
    sys.exit(main())
