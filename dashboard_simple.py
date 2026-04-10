#!/usr/bin/env python3
"""
Simple HTTP Dashboard - zero dependencies, 100% reliable
No Flask, No Streamlit, no WebSockets - just plain HTTP
"""

import http.server
import json
import urllib.parse
import psycopg2
import os
import sys
from datetime import date, datetime
from dotenv import load_dotenv

# Custom JSON encoder for date objects
class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        from decimal import Decimal
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from analytics.kpi_engine import KPICalculationEngine
from analytics.insights_engine import get_account_cpa, analyze_segment, get_segment_insights, get_segment_campaigns

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'ai_optimizer'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

# Get accounts
def get_accounts():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT account_id 
            FROM (
                SELECT DISTINCT account_id FROM kpi_daily_summary
                UNION
                SELECT DISTINCT account_id FROM kpi_monthly_plan
            ) t
            ORDER BY account_id
        """)
        accounts = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return accounts
    except Exception as e:
        print(f"Error: {e}")
        return []

# Get KPI status
def get_kpi_status(account_id):
    try:
        # Quick check if plan exists
        plan = get_current_plan(account_id)
        if not plan:
            return {"no_plan": True, "error": "No KPI plan found"}
        
        conn = get_db_connection()
        engine = KPICalculationEngine(conn)
        status = engine.calculate_kpi_status(account_id)
        engine.close()
        conn.close()
        
        if isinstance(status, dict) and 'error' in status:
            return {"no_plan": True, "error": status['error']}
        return status
    except Exception as e:
        return {"error": str(e)}

# Get current plan
def get_current_plan(account_id):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        today = date.today()
        # Create first day of current month for date comparison
        month_start = f"{today.year}-{today.month:02d}-01"
        
        cur.execute("""
            SELECT budget_rub, leads_target, cpa_target_rub, roi_target
            FROM kpi_monthly_plan
            WHERE account_id = %s AND date_trunc('month', year_month) = date_trunc('month', %s::date)
        """, (account_id, month_start))
        
        result = cur.fetchone()
        cur.close()
        conn.close()
        
        if result:
            return {
                "budget": result[0],
                "leads": result[1],
                "cpa": result[2],
                "roi": result[3]
            }
        return None
    except Exception as e:
        return None

# Save plan
def save_plan(account_id, year_month, budget, leads, cpa, roi=None):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Convert "2026-04" to dates
        year, month = year_month.split('-')
        year = int(year)
        month = int(month)
        
        # First day of month
        month_start = f"{year}-{month:02d}-01"
        
        # Last day of month
        if month == 12:
            next_month_start = f"{year+1}-01-01"
        else:
            next_month_start = f"{year}-{month+1:02d}-01"
        
        # Last day is day before next month start
        from datetime import datetime, timedelta
        next_date = datetime.strptime(next_month_start, "%Y-%m-%d")
        last_day = (next_date - timedelta(days=1)).strftime("%Y-%m-%d")
        
        cur.execute("""
            INSERT INTO kpi_monthly_plan (account_id, year_month, month_start, month_end, budget_rub, leads_target, cpa_target_rub, roi_target, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (account_id, year_month) DO UPDATE SET
                budget_rub = %s,
                leads_target = %s,
                cpa_target_rub = %s,
                roi_target = %s,
                updated_at = NOW()
        """, (account_id, month_start, month_start, last_day, budget, leads, cpa, roi, budget, leads, cpa, roi))
        
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"Save error: {e}")
        return False

# HTML Template
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KPI Dashboard - AI Optimizer</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .header h1 { color: #333; margin-bottom: 10px; }
        .selector { display: flex; gap: 10px; }
        select { padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        .content { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        .tabs { display: flex; gap: 10px; margin-bottom: 20px; border-bottom: 2px solid #eee; }
        .tab { padding: 10px 20px; cursor: pointer; border: none; background: none; font-size: 14px; color: #666; }
        .tab.active { color: #007bff; border-bottom: 2px solid #007bff; margin-bottom: -2px; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .form-group { margin-bottom: 15px; }
        label { display: block; margin-bottom: 5px; font-weight: 500; color: #333; }
        input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
        button { padding: 10px 20px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 14px; }
        button:hover { background: #0056b3; }
        .metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin-bottom: 20px; }
        .metric { background: #f9f9f9; padding: 15px; border-radius: 4px; border-left: 4px solid #007bff; }
        .metric-label { font-size: 12px; color: #666; margin-bottom: 5px; }
        .metric-value { font-size: 24px; font-weight: bold; color: #333; }
        .metric-small { font-size: 12px; color: #999; margin-top: 5px; }
        .alert { background: #fff3cd; border-left: 4px solid #ffc107; padding: 12px; margin-top: 10px; border-radius: 4px; }
        .error { background: #f8d7da; border-left: 4px solid #dc3545; padding: 12px; margin-top: 10px; border-radius: 4px; color: #721c24; }
        .success { background: #d4edda; border-left: 4px solid #28a745; padding: 12px; margin-top: 10px; border-radius: 4px; color: #155724; }
        .message { margin-top: 10px; padding: 10px; border-radius: 4px; display: none; }
        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .loading { text-align: center; padding: 40px; color: #999; }
        
        /* Insights Styles */
        .insights-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 30px; }
        .insight-section { background: #f9f9f9; padding: 20px; border-radius: 8px; }
        .insight-section h3 { margin-top: 0; padding-bottom: 10px; border-bottom: 2px solid #eee; }
        .insight-item { 
            background: white; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 6px; 
            border-left: 4px solid #dc3545;
            cursor: pointer;
            transition: box-shadow 0.2s;
        }
        .insight-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
        .insight-item.opportunity { border-left-color: #28a745; }
        .insight-item-header { font-weight: 600; margin-bottom: 8px; }
        .insight-item-badge { 
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }
        .insight-item.problem .insight-item-badge { background: #dc3545; color: white; }
        .insight-item.opportunity .insight-item-badge { background: #28a745; color: white; }
        .insight-details { font-size: 13px; color: #666; margin: 5px 0; }
        
        .campaigns-popup {
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 20px;
            width: 90%;
            max-width: 700px;
            max-height: 80vh;
            overflow-y: auto;
            z-index: 1000;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .campaigns-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 999;
            display: none;
        }
        .campaigns-overlay.show { display: block; }
        .popup-close { float: right; font-size: 24px; cursor: pointer; }
        .campaigns-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        .campaigns-table th { 
            background: #f9f9f9;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #ddd;
        }
        .campaigns-table td {
            padding: 10px;
            border-bottom: 1px solid #eee;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 KPI Dashboard</h1>
            <div class="selector">
                <select id="account" onchange="loadAccount()">
                    <option value="">-- Выберите аккаунт --</option>
                </select>
            </div>
        </div>

        <div class="content">
            <div class="tabs">
                <button class="tab active" onclick="showTab('status')">📈 KPI Статус</button>
                <button class="tab" onclick="showTab('insights')">🔍 Инсайты</button>
                <button class="tab" onclick="showTab('form')">⚙️ Установить KPI</button>
            </div>

            <div id="status" class="tab-content active">
                <div id="status-content" class="loading">Выберите аккаунт для просмотра метрик</div>
            </div>

            <div id="insights" class="tab-content">
                <div id="insights-content" class="loading">Выбери аккаунт для просмотра инсайтов</div>
            </div>

            <div id="form" class="tab-content">
                <div class="form-row">
                    <div class="form-group">
                        <label>Месяц</label>
                        <input type="month" id="month">
                    </div>
                    <div class="form-group">
                        <label>Бюджет (₽)</label>
                        <input type="number" id="budget" placeholder="100000" min="0" step="1000">
                    </div>
                </div>
                <div class="form-row">
                    <div class="form-group">
                        <label>Целевое количество лидов</label>
                        <input type="number" id="leads" placeholder="100" min="0">
                    </div>
                    <div class="form-group">
                        <label>Целевой CPA (₽)</label>
                        <input type="number" id="cpa" placeholder="1000" min="0" step="100">
                    </div>
                </div>
                <div class="form-group">
                    <label>ROI Target (% - опционально)</label>
                    <input type="number" id="roi" placeholder="300" min="0" step="10">
                </div>
                <button onclick="savePlan()">💾 Сохранить KPI</button>
                <div id="form-message" class="message"></div>
            </div>
        </div>
    </div>

    <script>
        // Initialize month
        const today = new Date();
        const month = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0');
        document.getElementById('month').value = month;

        // Load accounts
        fetch('/api/accounts').then(r => r.json()).then(data => {
            const sel = document.getElementById('account');
            data.forEach(acc => {
                const opt = document.createElement('option');
                opt.value = acc;
                opt.textContent = acc;
                sel.appendChild(opt);
            });
        });

        function showTab(tab) {
            document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
            document.getElementById(tab).classList.add('active');
            event.target.classList.add('active');
        }

        function loadAccount() {
            const account = document.getElementById('account').value;
            if (!account) return;
            
            // Load plan
            fetch('/api/plan?account=' + account).then(r => r.json()).then(data => {
                if (data) {
                    document.getElementById('budget').value = data.budget || '';
                    document.getElementById('leads').value = data.leads || '';
                    document.getElementById('cpa').value = data.cpa || '';
                    document.getElementById('roi').value = data.roi || '';
                }
            });

            // Load KPI status
            fetch('/api/status?account=' + account).then(r => r.json()).then(data => {
                if (data.no_plan) {
                    document.getElementById('status-content').innerHTML = '<div class="alert">ℹ️ Установите KPI план для просмотра метрик</div>';
                    return;
                }
                
                const html = `
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-label">💰 Бюджет</div>
                            <div class="metric-value">${Math.round(data.budget.spent).toLocaleString('ru-RU')} ₽</div>
                            <div class="metric-small">Темп: ${Math.round(data.budget.pacing_pct)}%</div>
                            <div class="metric-small">План: ${Math.round(data.budget.target).toLocaleString('ru-RU')} ₽</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">📊 Лиды</div>
                            <div class="metric-value">${data.conversions.actual}</div>
                            <div class="metric-small">Темп: ${Math.round(data.conversions.pacing_pct)}%</div>
                            <div class="metric-small">План: ${data.conversions.target}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">💵 CPA</div>
                            <div class="metric-value">${Math.round(data.cpa.actual).toLocaleString('ru-RU')} ₽</div>
                            <div class="metric-small">План: ${Math.round(data.cpa.target).toLocaleString('ru-RU')} ₽</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">✅ Статус</div>
                            <div class="metric-value">${data.summary.overall_status || 'OK'}</div>
                        </div>
                    </div>
                    <h3>🔮 Прогноз на конец месяца</h3>
                    <div class="metrics" style="grid-template-columns: 1fr 1fr 1fr;">
                        <div class="metric">
                            <div class="metric-label">Расход</div>
                            <div class="metric-value">${Math.round(data.forecast.end_month_spend).toLocaleString('ru-RU')} ₽</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Лиды</div>
                            <div class="metric-value">${data.forecast.end_month_conversions}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">CPA</div>
                            <div class="metric-value">${Math.round(data.forecast.end_month_cpa).toLocaleString('ru-RU')} ₽</div>
                        </div>
                    </div>
                `;
                document.getElementById('status-content').innerHTML = html;
            });

            // Load insights
            loadInsights();
        }

        function savePlan() {
            const account = document.getElementById('account').value;
            if (!account) {
                showMessage('Выберите аккаунт', 'error');
                return;
            }

            fetch('/api/plan', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    account: account,
                    month: document.getElementById('month').value,
                    budget: parseFloat(document.getElementById('budget').value),
                    leads: parseInt(document.getElementById('leads').value),
                    cpa: parseFloat(document.getElementById('cpa').value),
                    roi: document.getElementById('roi').value ? parseFloat(document.getElementById('roi').value) : null
                })
            }).then(r => r.json()).then(data => {
                if (data.success) {
                    showMessage('✅ KPI сохранён', 'success');
                    setTimeout(loadAccount, 500);
                } else {
                    showMessage('❌ ' + data.error, 'error');
                }
            });
        }

        function showMessage(text, type) {
            const el = document.getElementById('form-message');
            el.textContent = text;
            el.className = 'message ' + type;
            el.style.display = 'block';
            setTimeout(() => el.style.display = 'none', 3000);
        }

        // Insights Tab
        async function loadInsights() {
            const account = document.getElementById('account').value;
            if (!account) return;

            const content = document.getElementById('insights-content');
            content.innerHTML = '<div class="loading">Загружаем инсайты...</div>';

            try {
                const resp = await fetch(`/api/insights?account=${encodeURIComponent(account)}`);
                const data = await resp.json();

                if (data.error) {
                    content.innerHTML = `<div class="error">Ошибка: ${data.error}</div>`;
                    return;
                }

                // Check if we have conversion data
                if (data.message) {
                    content.innerHTML = `<div class="alert" style="margin-top: 20px;">${data.message}</div>`;
                    return;
                }

                let html = `
                    <div style="margin-bottom: 20px;">
                        <h3>Статус аккаунта (30 дней)</h3>
                        <div class="metrics">
                            <div class="metric">
                                <div class="metric-label">Средний CPA</div>
                                <div class="metric-value">${data.account_cpa > 0 ? data.account_cpa.toLocaleString('ru-RU', {maximumFractionDigits: 0}) + ' ₽' : 'Нет данных'}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Всего расходов</div>
                                <div class="metric-value">${data.account_spend.toLocaleString('ru-RU', {maximumFractionDigits: 0})} ₽</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Всего конверсий</div>
                                <div class="metric-value">${data.account_conversions}</div>
                            </div>
                        </div>
                    </div>

                    <div class="insights-grid">
                        <div class="insight-section">
                            <h3>🚨 Проблемные сегменты (${data.problems.length})</h3>
                `;

                if (data.problems.length === 0) {
                    html += '<p style="color: #999;">Проблемных сегментов не найдено</p>';
                } else {
                    for (const problem of data.problems) {
                        const ratio = problem.cpa_ratio.toFixed(1);
                        html += `
                            <div class="insight-item problem" onclick="showCampaigns('${problem.segment_name}', '${problem.segment_value}', true)">
                                <div class="insight-item-header">
                                    ${problem.segment_name}: ${problem.segment_value}
                                    <span class="insight-item-badge">${ratio}x выше</span>
                                </div>
                                <div class="insight-details">
                                    CPA: ${problem.cpa.toLocaleString('ru-RU', {maximumFractionDigits: 0})} ₽ | 
                                    Расход: ${problem.spend.toLocaleString('ru-RU', {maximumFractionDigits: 0})} ₽ | 
                                    Конверсии: ${problem.conversions}
                                </div>
                            </div>
                        `;
                    }
                }

                html += `
                        </div>

                        <div class="insight-section">
                            <h3>🌟 Точки роста (${data.opportunities.length})</h3>
                `;

                if (data.opportunities.length === 0) {
                    html += '<p style="color: #999;">Точек роста не найдено</p>';
                } else {
                    for (const opp of data.opportunities) {
                        const ratio = opp.cpa_ratio.toFixed(2);
                        html += `
                            <div class="insight-item opportunity" onclick="showCampaigns('${opp.segment_name}', '${opp.segment_value}', false)">
                                <div class="insight-item-header">
                                    ${opp.segment_name}: ${opp.segment_value}
                                    <span class="insight-item-badge">${ratio}x ниже</span>
                                </div>
                                <div class="insight-details">
                                    CPA: ${opp.cpa.toLocaleString('ru-RU', {maximumFractionDigits: 0})} ₽ | 
                                    Расход: ${opp.spend.toLocaleString('ru-RU', {maximumFractionDigits: 0})} ₽ | 
                                    Конверсии: ${opp.conversions}
                                </div>
                            </div>
                        `;
                    }
                }

                html += '</div></div>';
                content.innerHTML = html;

            } catch (err) {
                content.innerHTML = `<div class="error">Ошибка загрузки: ${err.message}</div>`;
            }
        }

        async function showCampaigns(segmentName, segmentValue, isProblem) {
            try {
                const account = document.getElementById('account').value;
                const resp = await fetch(`/api/insights/segment/${segmentName}/${encodeURIComponent(segmentValue)}?account=${encodeURIComponent(account)}&is_problem=${isProblem}`);
                const data = await resp.json();

                const title = isProblem ? 'Кампании с наихудшей СРА' : 'Лучшие кампании';
                const label = isProblem ? 'выше' : 'ниже';

                let html = `
                    <div class="campaigns-popup">
                        <span class="popup-close" onclick="closeCampaigns()">&times;</span>
                        <h3>${title}</h3>
                        <p style="color: #666;">Сегмент: <strong>${segmentName}: ${segmentValue}</strong></p>
                        <table class="campaigns-table">
                            <thead>
                                <tr>
                                    <th>Кампания</th>
                                    <th>Расход</th>
                                    <th>Конверсии</th>
                                    <th>СРА</th>
                                    <th>Клики</th>
                                </tr>
                            </thead>
                            <tbody>
                `;

                for (const camp of data.campaigns) {
                    html += `
                        <tr>
                            <td>ID: ${camp.campaign_id}</td>
                            <td>${camp.spend.toLocaleString('ru-RU', {maximumFractionDigits: 0})} ₽</td>
                            <td>${camp.conversions}</td>
                            <td><strong>${camp.cpa.toLocaleString('ru-RU', {maximumFractionDigits: 0})}</strong> ₽</td>
                            <td>${camp.clicks}</td>
                        </tr>
                    `;
                }

                html += '</tbody></table></div>';

                document.getElementById('campaigns-overlay').innerHTML = html;
                document.getElementById('campaigns-overlay').classList.add('show');

            } catch (err) {
                alert('Ошибка: ' + err.message);
            }
        }

        function closeCampaigns() {
            document.getElementById('campaigns-overlay').classList.remove('show');
        }
    </script>

    <div id="campaigns-overlay" class="campaigns-overlay" onclick="closeCampaigns()"></div>
</body>
</html>
"""

# Insights API functions
def get_insights(client_login=None):
    """Get account-level insights with problems and opportunities"""
    try:
        print(f"[INSIGHTS] Fetching insights for {client_login}...")
        conn = get_db_connection()
        
        # If client_login not provided, use default
        if not client_login:
            client_login = 'mmg-sz'
        
        print(f"[INSIGHTS] Calling get_segment_insights...")
        # Get all insights (problems + opportunities)
        insights = get_segment_insights(conn, client_login, days=30)
        print(f"[INSIGHTS] Got insights, closing connection...")
        
        # No dummy data anymore - show message if no real data available
        if insights.get("note"):
            # No conversion data, add informative message
            insights["message"] = "📊 Инсайты будут доступны когда поступят данные о конверсиях из API Яндекс.Директа"
        
        conn.close()
        print(f"[INSIGHTS] Done")
        
        return insights
    except Exception as e:
        print(f"[INSIGHTS] Error getting insights: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "account_cpa": 0,
            "account_spend": 0,
            "account_conversions": 0,
            "problems": [],
            "opportunities": [],
            "message": "❌ Ошибка при получении инсайтов"
        }

def get_segment_drill_down(client_login, segment_name, segment_value, is_problem=True):
    """Get top 3 campaigns for a segment (worst CPA for problems, best for opportunities)"""
    try:
        print(f"[DRILL] Segment: {segment_name}={segment_value}, is_problem={is_problem}")
        conn = get_db_connection()
        # is_problem=True means show_worst=True (worst CPA first)
        campaigns = get_segment_campaigns(conn, client_login, segment_name, segment_value, limit=3, show_worst=is_problem)
        print(f"[DRILL] Got {len(campaigns)} campaigns")
        conn.close()
        
        return {
            "segment_name": segment_name,
            "segment_value": segment_value,
            "is_problem": is_problem,
            "campaigns": campaigns
        }
    except Exception as e:
        print(f"[DRILL] Error getting segment campaigns: {e}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "campaigns": []
        }

# HTTP Request Handler
class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode())
        
        elif self.path == '/api/accounts':
            accounts = get_accounts()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(accounts, cls=DateTimeEncoder).encode())
        
        elif self.path.startswith('/api/status?'):
            account = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('account', [''])[0]
            status = get_kpi_status(account)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status, cls=DateTimeEncoder).encode())
        
        elif self.path.startswith('/api/plan?'):
            account = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('account', [''])[0]
            plan = get_current_plan(account)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(plan, cls=DateTimeEncoder).encode())
        
        elif self.path.startswith('/api/insights?'):
            account = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('account', [''])[0]
            insights = get_insights(account)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(insights, cls=DateTimeEncoder).encode())
        
        elif self.path.startswith('/api/insights/segment/'):
            # Parse: /api/insights/segment/{segment_name}/{segment_value}?account={account}&is_problem={bool}
            path_parts = self.path.split('/')
            if len(path_parts) >= 5:
                segment_name = path_parts[4]
                segment_value = urllib.parse.unquote(path_parts[5].split('?')[0])
                query_params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                account = query_params.get('account', [''])[0]
                is_problem = query_params.get('is_problem', ['true'])[0].lower() == 'true'
                
                campaigns = get_segment_drill_down(account, segment_name, segment_value, is_problem)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(campaigns, cls=DateTimeEncoder).encode())
            else:
                self.send_response(400)
                self.end_headers()
        
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/plan':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode()
            data = json.loads(body)
            
            success = save_plan(
                data.get('account'),
                data.get('month'),
                data.get('budget'),
                data.get('leads'),
                data.get('cpa'),
                data.get('roi')
            )
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"success": success}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        print(f"[HTTP] {format % args}")

if __name__ == '__main__':
    PORT = 8501
    server = http.server.HTTPServer(('0.0.0.0', PORT), DashboardHandler)
    print(f"✅ Dashboard запущен на http://0.0.0.0:{PORT}")
    print(f"📍 Откройте в браузере: http://127.0.0.1:{PORT}")
    print(f"🌐 Или по внешнему IP: http://43.245.224.117:{PORT}")
    print(f"\nНажмите Ctrl+C для остановки\n")
    server.serve_forever()
