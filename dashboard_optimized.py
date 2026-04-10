#!/usr/bin/env python3
"""
Phase 3 Dashboard - Campaign Drill-Down Analytics
"""
import sys
sys.path.insert(0, '/opt/ai-optimizer')

from flask import Flask, jsonify, request, render_template_string
from db_save import get_pg_conn
from datetime import datetime
import json

app = Flask(__name__)

# HTML Template for Phase 3 Dashboard
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phase 3 Analytics Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f7fa;
            color: #333;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .header h1 {
            font-size: 28px;
            margin-bottom: 10px;
        }
        
        .header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .controls {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            gap: 15px;
            align-items: center;
        }
        
        .controls select {
            padding: 10px 15px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 14px;
            cursor: pointer;
        }
        
        .controls button {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
        }
        
        .controls button:hover {
            background: #764ba2;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-card .label {
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 8px;
        }
        
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        
        .insights-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .insights-section {
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        
        .insights-section h2 {
            font-size: 20px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .insights-section h2 .count {
            background: #f0f0f0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 14px;
            color: #666;
        }
        
        .segment-card {
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 12px;
            cursor: pointer;
            transition: all 0.2s;
            border-left: 4px solid;
        }
        
        .segment-card.problem {
            background: #fff5f5;
            border-left-color: #f56565;
        }
        
        .segment-card.problem:hover {
            background: #fed7d7;
            transform: translateX(5px);
        }
        
        .segment-card.opportunity {
            background: #f0fff4;
            border-left-color: #48bb78;
        }
        
        .segment-card.opportunity:hover {
            background: #c6f6d5;
            transform: translateX(5px);
        }
        
        .segment-card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 8px;
            font-weight: 600;
        }
        
        .segment-card-header .name {
            font-size: 14px;
        }
        
        .segment-card-header .badge {
            font-size: 12px;
            padding: 3px 8px;
            border-radius: 3px;
            font-weight: bold;
        }
        
        .segment-card.problem .badge {
            background: #f56565;
            color: white;
        }
        
        .segment-card.opportunity .badge {
            background: #48bb78;
            color: white;
        }
        
        .segment-card-details {
            font-size: 12px;
            color: #666;
            display: flex;
            gap: 15px;
        }
        
        .segment-card-details span {
            display: flex;
            flex-direction: column;
        }
        
        .segment-card-details .label {
            color: #999;
            font-size: 11px;
        }
        
        .segment-card-details .value {
            font-weight: 600;
            color: #333;
        }
        
        .empty-state {
            text-align: center;
            padding: 40px;
            color: #999;
        }
        
        .empty-state p {
            font-size: 14px;
        }
        
        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .modal.show {
            display: flex;
        }
        
        .modal-content {
            background: white;
            border-radius: 8px;
            padding: 30px;
            max-width: 600px;
            width: 90%;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }
        
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }
        
        .modal-header h3 {
            font-size: 18px;
        }
        
        .modal-header .close {
            font-size: 28px;
            cursor: pointer;
            color: #999;
            border: none;
            background: none;
            padding: 0;
        }
        
        .modal-header .close:hover {
            color: #333;
        }
        
        .modal-section {
            margin-bottom: 20px;
        }
        
        .modal-section h4 {
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 1px;
        }
        
        .campaigns-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
        }
        
        .campaigns-table th {
            background: #f5f7fa;
            padding: 10px;
            text-align: left;
            font-weight: 600;
            color: #666;
            border-bottom: 1px solid #ddd;
        }
        
        .campaigns-table td {
            padding: 12px 10px;
            border-bottom: 1px solid #eee;
        }
        
        .campaigns-table tr:hover {
            background: #f9fafb;
        }
        
        .loading {
            text-align: center;
            padding: 20px;
            color: #999;
        }
        
        @media (max-width: 768px) {
            .insights-container {
                grid-template-columns: 1fr;
            }
            
            .stats-grid {
                grid-template-columns: 1fr 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Phase 3 Analytics Dashboard</h1>
        <p>Campaign Drill-Down Analytics - Problems & Opportunities</p>
    </div>
    
    <div class="container">
        <div class="controls">
            <label for="account-select">Аккаунт:</label>
            <select id="account-select">
                <option value="">Выбери аккаунт...</option>
            </select>
            <button onclick="loadDashboard()">Загрузить</button>
        </div>
        
        <div id="stats-section" style="display: none;">
            <div class="stats-grid" id="stats-grid"></div>
        </div>
        
        <div class="insights-container" id="insights-container" style="display: none;">
            <div class="insights-section">
                <h2>🚨 Проблемные сегменты <span class="count" id="problems-count">0</span></h2>
                <div id="problems-list"></div>
            </div>
            
            <div class="insights-section">
                <h2>🌟 Точки роста <span class="count" id="opportunities-count">0</span></h2>
                <div id="opportunities-list"></div>
            </div>
        </div>
    </div>
    
    <!-- Modal for drill-down -->
    <div class="modal" id="drill-down-modal">
        <div class="modal-content">
            <div class="modal-header">
                <h3 id="modal-title"></h3>
                <button class="close" onclick="closeDrillDown()">&times;</button>
            </div>
            
            <div class="modal-section">
                <h4>Top-3 кампании</h4>
                <table class="campaigns-table">
                    <thead>
                        <tr>
                            <th>Кампания</th>
                            <th>Расход</th>
                            <th>Конверсии</th>
                            <th>СРА</th>
                        </tr>
                    </thead>
                    <tbody id="campaigns-tbody">
                        <tr>
                            <td colspan="4" class="loading">Загрузка...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <script>
        const API_BASE = window.location.origin;
        
        // Load accounts on page load
        document.addEventListener('DOMContentLoaded', () => {
            loadAccounts();
        });
        
        async function loadAccounts() {
            try {
                const response = await fetch(`${API_BASE}/api/accounts`);
                const data = await response.json();
                
                const select = document.getElementById('account-select');
                data.accounts.forEach(account => {
                    const option = document.createElement('option');
                    option.value = account;
                    option.textContent = account;
                    select.appendChild(option);
                });
                
                // Auto-select first account if available
                if (data.accounts.length > 0) {
                    select.value = data.accounts[0];
                }
            } catch (err) {
                console.error('Failed to load accounts:', err);
            }
        }
        
        async function loadDashboard() {
            const account = document.getElementById('account-select').value;
            if (!account) {
                alert('Выбери аккаунт!');
                return;
            }
            
            try {
                // Load insights
                const response = await fetch(`${API_BASE}/api/insights?account=${encodeURIComponent(account)}`);
                const data = await response.json();
                
                // Show stats
                const statsGrid = document.getElementById('stats-grid');
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <div class="label">Средний СРА</div>
                        <div class="value">${Math.round(data.account_cpa).toLocaleString('ru-RU')} ₽</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Расход (30 дней)</div>
                        <div class="value">${Math.round(data.account_cost).toLocaleString('ru-RU')} ₽</div>
                    </div>
                    <div class="stat-card">
                        <div class="label">Конверсии</div>
                        <div class="value">${Math.round(data.account_conversions).toLocaleString('ru-RU')}</div>
                    </div>
                `;
                document.getElementById('stats-section').style.display = 'block';
                
                // Show problems
                const problemsList = document.getElementById('problems-list');
                if (data.problems.length > 0) {
                    problemsList.innerHTML = data.problems.map(p => `
                        <div class="segment-card problem" onclick="openDrillDown('${p.segment_name}', '${p.segment_value}', true)">
                            <div class="segment-card-header">
                                <span class="name">${p.segment_name}: <strong>${p.segment_value}</strong></span>
                                <span class="badge">${p.cpa_ratio.toFixed(1)}x выше</span>
                            </div>
                            <div class="segment-card-details">
                                <span><span class="label">Расход</span><span class="value">${Math.round(p.spend).toLocaleString('ru-RU')} ₽</span></span>
                                <span><span class="label">Конверсии</span><span class="value">${p.conversions}</span></span>
                                <span><span class="label">СРА</span><span class="value">${Math.round(p.cpa).toLocaleString('ru-RU')} ₽</span></span>
                            </div>
                        </div>
                    `).join('');
                } else {
                    problemsList.innerHTML = '<div class="empty-state"><p>Проблемных сегментов не найдено</p></div>';
                }
                document.getElementById('problems-count').textContent = data.problems.length;
                
                // Show opportunities
                const oppsList = document.getElementById('opportunities-list');
                if (data.opportunities.length > 0) {
                    oppsList.innerHTML = data.opportunities.map(o => `
                        <div class="segment-card opportunity" onclick="openDrillDown('${o.segment_name}', '${o.segment_value}', false)">
                            <div class="segment-card-header">
                                <span class="name">${o.segment_name}: <strong>${o.segment_value}</strong></span>
                                <span class="badge">${o.cpa_ratio.toFixed(2)}x ниже</span>
                            </div>
                            <div class="segment-card-details">
                                <span><span class="label">Расход</span><span class="value">${Math.round(o.spend).toLocaleString('ru-RU')} ₽</span></span>
                                <span><span class="label">Конверсии</span><span class="value">${o.conversions}</span></span>
                                <span><span class="label">СРА</span><span class="value">${Math.round(o.cpa).toLocaleString('ru-RU')} ₽</span></span>
                            </div>
                        </div>
                    `).join('');
                } else {
                    oppsList.innerHTML = '<div class="empty-state"><p>Точек роста не найдено</p></div>';
                }
                document.getElementById('opportunities-count').textContent = data.opportunities.length;
                
                document.getElementById('insights-container').style.display = 'grid';
            } catch (err) {
                console.error('Error loading dashboard:', err);
                alert('Ошибка загрузки данных');
            }
        }
        
        async function openDrillDown(segmentType, segmentValue, isProblem) {
            const modal = document.getElementById('drill-down-modal');
            document.getElementById('modal-title').textContent = 
                `${segmentType}: ${segmentValue} ${isProblem ? '(проблема)' : '(возможность)'}`;
            
            try {
                const response = await fetch(
                    `${API_BASE}/api/insights/segment/${segmentType}/${encodeURIComponent(segmentValue)}?is_problem=${isProblem}`
                );
                const data = await response.json();
                
                const tbody = document.getElementById('campaigns-tbody');
                if (data.campaigns && data.campaigns.length > 0) {
                    tbody.innerHTML = data.campaigns.map(c => `
                        <tr>
                            <td>${c.campaign_name || 'ID: ' + c.campaign_id}</td>
                            <td>${Math.round(c.cost).toLocaleString('ru-RU')} ₽</td>
                            <td>${c.conversions}</td>
                            <td><strong>${Math.round(c.cpa).toLocaleString('ru-RU')} ₽</strong></td>
                        </tr>
                    `).join('');
                } else {
                    tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #999;">Нет данных</td></tr>';
                }
            } catch (err) {
                console.error('Error loading drill-down:', err);
                tbody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: #f56565;">Ошибка загрузки</td></tr>';
            }
            
            modal.classList.add('show');
        }
        
        function closeDrillDown() {
            document.getElementById('drill-down-modal').classList.remove('show');
        }
        
        // Close modal on outside click
        document.getElementById('drill-down-modal').addEventListener('click', (e) => {
            if (e.target === document.getElementById('drill-down-modal')) {
                closeDrillDown();
            }
        });
    </script>
</body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    """Serve main dashboard page"""
    return render_template_string(HTML_TEMPLATE)


@app.route('/api/accounts', methods=['GET'])
def get_accounts():
    """Get list of all available accounts"""
    conn = get_pg_conn()
    cur = conn.cursor()
    
    cur.execute("""
    SELECT DISTINCT client_login 
    FROM account_daily_metrics 
    ORDER BY client_login
    """)
    
    accounts = [row[0] for row in cur.fetchall()]
    cur.close()
    conn.close()
    
    return jsonify({
        "status": "ok",
        "accounts": accounts
    })


@app.route('/api/kpi', methods=['GET'])
def get_kpi():
    """Get KPI for dashboard first tab"""
    account = request.args.get('account', 'mmg-sz')
    
    conn = get_pg_conn()
    cur = conn.cursor()
    
    # Get daily metrics
    cur.execute("""
    SELECT 
        date,
        SUM(impressions) as impressions,
        SUM(clicks) as clicks,
        SUM(cost) as cost,
        SUM(conversions) as conversions,
        SUM(cost) / NULLIF(SUM(conversions), 0) as cpa
    FROM account_daily_metrics
    WHERE client_login = %s
    GROUP BY date
    ORDER BY date DESC
    LIMIT 30
    """, (account,))
    
    metrics = []
    for row in cur.fetchall():
        metrics.append({
            "date": row[0].isoformat(),
            "impressions": row[1],
            "clicks": row[2],
            "cost": row[3],
            "conversions": row[4],
            "cpa": row[5]
        })
    
    cur.close()
    conn.close()
    
    return jsonify({
        "status": "ok",
        "data": metrics,
        "count": len(metrics)
    })


@app.route('/api/insights', methods=['GET'])
def get_insights():
    """Get insights for problems and opportunities with details"""
    account = request.args.get('account', 'mmg-sz')
    
    conn = get_pg_conn()
    cur = conn.cursor()
    
    # Get account stats
    cur.execute("""
    SELECT account_cpa, total_cost, total_conversions
    FROM account_stats
    WHERE client_login = %s
    LIMIT 1
    """, (account,))
    
    stats = cur.fetchone()
    account_cpa = stats[0] if stats else 0
    account_cost = stats[1] if stats else 0
    account_conversions = stats[2] if stats else 0
    
    # Get problems with full details
    cur.execute("""
    SELECT 
        segment_type,
        segment_value,
        cost,
        conversions,
        cpa,
        ratio_to_account
    FROM segment_insights
    WHERE classification = 'problem'
    ORDER BY ratio_to_account DESC, cost DESC
    """)
    
    problems = []
    for row in cur.fetchall():
        problems.append({
            "segment_name": row[0],
            "segment_value": row[1],
            "spend": row[2],
            "conversions": row[3],
            "cpa": row[4],
            "cpa_ratio": row[5]
        })
    
    # Get opportunities with full details
    cur.execute("""
    SELECT 
        segment_type,
        segment_value,
        cost,
        conversions,
        cpa,
        ratio_to_account
    FROM segment_insights
    WHERE classification = 'opportunity'
    ORDER BY ratio_to_account ASC, cost DESC
    """)
    
    opportunities = []
    for row in cur.fetchall():
        opportunities.append({
            "segment_name": row[0],
            "segment_value": row[1],
            "spend": row[2],
            "conversions": row[3],
            "cpa": row[4],
            "cpa_ratio": row[5]
        })
    
    cur.close()
    conn.close()
    
    return jsonify({
        "status": "ok",
        "account_cpa": account_cpa,
        "account_cost": account_cost,
        "account_conversions": account_conversions,
        "problems": problems,
        "opportunities": opportunities
    })



@app.route('/api/insights/segment/<segment_type>/<segment_value>', methods=['GET'])
def get_segment_drilldown(segment_type, segment_value):
    """Get drilldown for specific segment - shows top 3 campaigns"""
    is_problem = request.args.get('is_problem', 'false').lower() == 'true'
    
    conn = get_pg_conn()
    cur = conn.cursor()
    
    # Get top 3 campaigns for this segment
    # For problems: sort by CPA DESC (worst first)
    # For opportunities: sort by CPA ASC (best first)
    sort_order = "DESC" if is_problem else "ASC"
    
    cur.execute(f"""
    SELECT 
        campaign_id,
        campaign_name,
        cost,
        conversions,
        cpa
    FROM segment_campaign_analysis
    WHERE segment_type = %s
        AND segment_value = %s
    ORDER BY cpa {sort_order}
    LIMIT 3
    """, (segment_type, segment_value))
    
    campaigns = []
    for row in cur.fetchall():
        campaigns.append({
            "campaign_id": row[0],
            "campaign_name": row[1],
            "cost": round(row[2], 2),
            "conversions": int(row[3]),
            "cpa": round(row[4], 2)
        })
    
    cur.close()
    conn.close()
    
    return jsonify({
        "status": "ok",
        "segment_type": segment_type,
        "segment_value": segment_value,
        "is_problem": is_problem,
        "campaigns": campaigns
    })



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8502, debug=False)
