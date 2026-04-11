#!/usr/bin/env python3
"""
Phase 4 Analytics API
======================
REST API to expose Level 1-3 analytics.

Endpoints:
- GET /api/account/kpi           → Account daily metrics + CPA trend
- GET /api/insights               → All good/bad segments (L2)
- GET /api/insights/{type}/{val}  → Campaign drill-down for segment
"""

import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import psycopg2
from flask import Flask, jsonify, request

load_dotenv('/opt/ai-optimizer/.env')

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

app = Flask(__name__)

def get_db_conn():
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, database=DB_NAME
    )

# ============================================================================
# Level 1: Account KPI
# ============================================================================

@app.route('/api/account/kpi')
def get_account_kpi():
    """Get last 30 days of daily KPI + summary statistics."""
    
    conn = get_db_conn()
    with conn.cursor() as cur:
        # Daily breakdown
        cur.execute("""
            SELECT date, cost, conversions, cpa
            FROM account_kpi
            ORDER BY date DESC
            LIMIT 30
        """)
        
        daily = []
        for date, cost, conversions, cpa in cur.fetchall():
            daily.append({
                'date': date.isoformat(),
                'cost': float(cost),
                'conversions': int(conversions),
                'cpa': float(cpa) if cpa else None
            })
        
        # Summary
        cur.execute("""
            SELECT 
                SUM(cost) as total_cost,
                SUM(conversions) as total_conv,
                AVG(cpa) as avg_cpa
            FROM account_kpi
        """)
        
        total_cost, total_conv, avg_cpa = cur.fetchone()
        total_cost = float(total_cost or 0)
        total_conv = int(total_conv or 0)
        account_cpa = total_cost / total_conv if total_conv > 0 else 0
    
    conn.close()
    
    return jsonify({
        'summary': {
            'total_cost': total_cost,
            'total_conversions': total_conv,
            'account_cpa': account_cpa,
            'avg_daily_cpa': float(avg_cpa) if avg_cpa else None
        },
        'daily': daily
    })

# ============================================================================
# Level 2: 30-Day Trends
# ============================================================================

@app.route('/api/insights')
def get_insights():
    """Get all good and bad segments (Level 2)."""
    
    classification = request.args.get('classification', 'all')  # 'good', 'bad', 'all'
    
    conn = get_db_conn()
    with conn.cursor() as cur:
        if classification == 'all':
            query = """
                SELECT segment_type, segment_value, classification,
                       cost, conversions, cpa, ratio_to_account
                FROM segment_trends_30d
                ORDER BY classification DESC, ratio_to_account DESC
            """
            cur.execute(query)
        else:
            query = """
                SELECT segment_type, segment_value, classification,
                       cost, conversions, cpa, ratio_to_account
                FROM segment_trends_30d
                WHERE classification = %s
                ORDER BY ratio_to_account DESC
            """
            cur.execute(query, (classification,))
        
        insights = []
        for row in cur.fetchall():
            segment_type, segment_value, class_, cost, conversions, cpa, ratio = row
            insights.append({
                'segment_type': segment_type,
                'segment_value': segment_value,
                'classification': class_,
                'cost': float(cost),
                'conversions': int(conversions),
                'cpa': float(cpa),
                'ratio_to_account_cpa': float(ratio)
            })
    
    conn.close()
    
    return jsonify({'insights': insights, 'count': len(insights)})

# ============================================================================
# Level 3: Campaign Drill-Down
# ============================================================================

@app.route('/api/insights/<segment_type>/<segment_value>')
def get_campaign_drill_down(segment_type, segment_value):
    """Get campaign-level breakdown for a specific segment."""
    
    conn = get_db_conn()
    with conn.cursor() as cur:
        # Get campaigns for this segment from Level 3
        cur.execute("""
            SELECT campaign_id, campaign_type, cost, conversions, cpa, 
                   classification, ratio_to_account
            FROM campaign_insights_30d
            WHERE segment_type = %s AND segment_value = %s
            ORDER BY cost DESC
            LIMIT 10
        """, (segment_type, segment_value))
        
        campaigns = []
        for row in cur.fetchall():
            campaign_id, campaign_type, cost, conversions, cpa, classification, ratio = row
            campaigns.append({
                'campaign_id': int(campaign_id),
                'campaign_type': campaign_type,
                'cost': float(cost),
                'conversions': int(conversions),
                'cpa': float(cpa),
                'classification': classification,
                'ratio_to_account_cpa': float(ratio)
            })
    
    conn.close()
    
    return jsonify({
        'segment': {
            'type': segment_type,
            'value': segment_value
        },
        'campaigns': campaigns,
        'count': len(campaigns)
    })

# ============================================================================
# Health Check
# ============================================================================

@app.route('/health')
def health():
    """Health check endpoint."""
    try:
        conn = get_db_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM account_kpi")
            count = cur.fetchone()[0]
        conn.close()
        
        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'account_kpi_rows': count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# ============================================================================
# Main
# ============================================================================

if __name__ == '__main__':
    print("🚀 Phase 4 Analytics API")
    print("   Endpoints:")
    print("   - GET /api/account/kpi          → Account KPI + daily breakdown")
    print("   - GET /api/insights             → All segments (L2)")
    print("   - GET /api/insights/TYPE/VALUE  → Campaign drill-down")
    print("   - GET /health                   → Health check")
    print()
    
    app.run(host='127.0.0.1', port=5555, debug=False)
