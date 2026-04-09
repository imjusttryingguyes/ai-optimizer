import os
import psycopg2
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')

# Register custom filters
@app.template_filter('currency')
def currency_filter(value):
	"""Format number as currency"""
	try:
		return f"₽ {int(value):,}".replace(',', ' ')
	except (ValueError, TypeError):
		return "₽ 0"

@app.template_filter('thousands')
def thousands_filter(value):
	"""Format number with thousands separator"""
	try:
		return f"{int(value):,}".replace(',', ' ')
	except (ValueError, TypeError):
		return "0"

@app.template_filter('decimal1')
def decimal1_filter(value):
	"""Format number with 1 decimal place"""
	try:
		return f"{float(value):.1f}"
	except (ValueError, TypeError):
		return "0"

# Database connection
def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)

# Insight type classification
GROWTH_TYPES = {
	'ACCOUNT_CPA_TREND_GOOD',
	'SEGMENT_LADDER_TREND_GOOD',
	'SEGMENT_LADDER_WINNER'
}

DECLINE_TYPES = {
	'ACCOUNT_LEADS_TREND_BAD',
	'SEGMENT_COMBINATION_CPA_BAD',
	'SEGMENT_COMBINATION_TREND_BAD',
	'SEGMENT_LADDER_CPA_BAD',
	'SEGMENT_LADDER_TREND_BAD',
	'RSYA_WASTE',
	'SEGMENT_LADDER_WASTE'
}

def classify_insight_type(insight_type):
	"""Classify insight as growth or decline"""
	if insight_type in GROWTH_TYPES:
		return 'growth'
	elif insight_type in DECLINE_TYPES:
		return 'decline'
	return 'other'

def get_insights_by_period(days=7, account_id=None, severity_min=0):
	"""Get aggregated insights data by period"""
	conn = get_conn()
	cur = conn.cursor()
	
	where_clauses = [
		f"created_at >= CURRENT_DATE - INTERVAL '{days} days'",
		"severity >= %s" % severity_min
	]
	
	if account_id:
		where_clauses.append(f"account_id = '{account_id}'")
	
	where_sql = " AND ".join(where_clauses)
	
	cur.execute(f"""
		SELECT 
			id, account_id, type, entity_type, entity_id,
			severity, impact_rub, title, description, recommendation, created_at
		FROM insights
		WHERE {where_sql}
		ORDER BY severity DESC, impact_rub DESC, created_at DESC
	""")
	
	insights = cur.fetchall()
	cur.close()
	conn.close()
	return insights

def get_trend_data(account_id=None, severity_min=0):
	"""Calculate trend metrics comparing 7d vs 30d"""
	conn = get_conn()
	cur = conn.cursor()
	
	account_filter = f"AND account_id = '{account_id}'" if account_id else ""
	
	# Get 7-day impact per entity
	cur.execute(f"""
		SELECT 
			COALESCE(account_id, '') as entity,
			COALESCE(entity_type, '') as etype,
			COALESCE(entity_id, '') as eid,
			SUM(impact_rub) as impact_7d,
			AVG(severity) as avg_severity_7d
		FROM insights
		WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
			AND severity >= {severity_min}
			{account_filter}
		GROUP BY account_id, entity_type, entity_id
	""")
	data_7d = {(r[0], r[1], r[2]): (r[3] or 0, r[4] or 0) for r in cur.fetchall()}
	
	# Get 30-day impact per entity
	cur.execute(f"""
		SELECT 
			COALESCE(account_id, '') as entity,
			COALESCE(entity_type, '') as etype,
			COALESCE(entity_id, '') as eid,
			SUM(impact_rub) as impact_30d,
			AVG(severity) as avg_severity_30d,
			id, type, title, description, recommendation, created_at
		FROM insights
		WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'
			AND severity >= {severity_min}
			{account_filter}
		GROUP BY account_id, entity_type, entity_id, id, type, title, description, recommendation, created_at
	""")
	
	trends = []
	for row in cur.fetchall():
		entity = (row[0], row[1], row[2])
		impact_30d = row[3] or 0
		avg_severity_30d = row[4] or 0
		
		impact_7d, avg_severity_7d = data_7d.get(entity, (0, 0))
		
		# Determine if improving or declining
		if impact_7d > impact_30d:
			trend = 'improvement'
		else:
			trend = 'decline'
		
		trends.append({
			'entity': row[0],
			'entity_type': row[1],
			'entity_id': row[2],
			'trend': trend,
			'impact_7d': impact_7d,
			'impact_30d': impact_30d,
			'severity_7d': avg_severity_7d,
			'severity_30d': avg_severity_30d,
			'id': row[5],
			'type': row[6],
			'title': row[7],
			'description': row[8],
			'recommendation': row[9],
			'created_at': row[10]
		})
	
	cur.close()
	conn.close()
	
	return trends

# Get all insight types for filter
def get_insight_types():
	conn = get_conn()
	cur = conn.cursor()
	cur.execute("SELECT DISTINCT type FROM insights ORDER BY type")
	types = [row[0] for row in cur.fetchall()]
	cur.close()
	conn.close()
	return types

# Get all entity types for filter
def get_entity_types():
	conn = get_conn()
	cur = conn.cursor()
	cur.execute("SELECT DISTINCT entity_type FROM insights ORDER BY entity_type")
	entity_types = [row[0] for row in cur.fetchall() if row[0] is not None]
	cur.close()
	conn.close()
	return entity_types

# Get insights with filters
def get_insights(days=7, insight_type=None, account_id=None, severity_min=0, entity_type=None):
	conn = get_conn()
	cur = conn.cursor()
	
	where_clauses = [
		"created_at >= CURRENT_DATE - INTERVAL '%d days'" % days,
		"severity >= %s" % severity_min
	]
	
	if insight_type:
		where_clauses.append(f"type = '{insight_type}'")
	
	if account_id:
		where_clauses.append(f"account_id = '{account_id}'")

	if entity_type:
		where_clauses.append(f"entity_type = '{entity_type}'")
	
	where_sql = " AND ".join(where_clauses)
	
	query = f"""
		SELECT
			id,
			account_id,
			type,
			entity_type,
			entity_id,
			severity,
			impact_rub,
			title,
			description,
			recommendation,
			created_at
		FROM insights
		WHERE {where_sql}
		ORDER BY severity DESC, impact_rub DESC, created_at DESC
		LIMIT 500
	"""
	
	cur.execute(query)
	insights = cur.fetchall()
	cur.close()
	conn.close()
	return insights

# Get insights statistics
def get_statistics(days=7):
	try:
		conn = get_conn()
		cur = conn.cursor()
		
		cur.execute(f"""
			SELECT 
				COUNT(*) as total_insights,
				COUNT(DISTINCT account_id) as accounts_affected,
				SUM(impact_rub) as total_impact,
				AVG(severity) as avg_severity,
				MAX(created_at) as last_update
			FROM insights
			WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
		""")
		
		row = cur.fetchone()
		cur.close()
		conn.close()
		
		return {
			'total_insights': row[0] or 0,
			'accounts_affected': row[1] or 0,
			'total_impact': float(row[2] or 0),
			'avg_severity': float(row[3] or 0) if row[3] else 0,
			'last_update': row[4].isoformat() if row[4] else None
		}
	except Exception as e:
		print(f"Error getting statistics: {e}")
		return {
			'total_insights': 0,
			'accounts_affected': 0,
			'total_impact': 0,
			'avg_severity': 0,
			'last_update': None,
			'error': str(e)
		}

# Get insights by type for chart
def get_insights_by_type(days=7):
	try:
		conn = get_conn()
		cur = conn.cursor()
		
		cur.execute(f"""
			SELECT 
				type,
				COUNT(*) as count,
				SUM(impact_rub) as total_impact
			FROM insights
			WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
			GROUP BY type
			ORDER BY count DESC
		""")
		
		data = cur.fetchall()
		cur.close()
		conn.close()
		
		return [{
			'type': row[0],
			'count': row[1],
			'impact': float(row[2] or 0)
		} for row in data]
	except Exception as e:
		print(f"Error getting insights by type: {e}")
		return []

# Get severity distribution
def get_severity_distribution(days=7):
	try:
		conn = get_conn()
		cur = conn.cursor()
		
		cur.execute(f"""
			WITH severity_levels AS (
				SELECT 
					CASE 
						WHEN severity >= 80 THEN 'Critical'
						WHEN severity >= 60 THEN 'High'
						WHEN severity >= 40 THEN 'Medium'
						ELSE 'Low'
					END as level
				FROM insights
				WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
			)
			SELECT 
				level,
				COUNT(*) as count
			FROM severity_levels
			GROUP BY level
			ORDER BY CASE 
				WHEN level = 'Critical' THEN 1
				WHEN level = 'High' THEN 2
				WHEN level = 'Medium' THEN 3
				ELSE 4
			END
		""")
		
		data = cur.fetchall()
		cur.close()
		conn.close()
		
		return [{
			'level': row[0],
			'count': row[1]
		} for row in data]
	except Exception as e:
		print(f"Error getting severity distribution: {e}")
		return []

# Routes
@app.route('/')
def index():
	try:
		days = request.args.get('days', 7, type=int)
		stats = get_statistics(days)
		insights_by_type = get_insights_by_type(days)
		severity_dist = get_severity_distribution(days)
		
		return render_template('index.html',
			stats=stats,
			insights_by_type=insights_by_type,
			severity_dist=severity_dist,
			days=days
		)
	except Exception as e:
		print(f"Error in index route: {e}")
		return render_template('error.html', error=str(e)), 500

@app.route('/insights')
def insights():
	try:
		mode = request.args.get('mode', '7days')
		insight_category = request.args.get('category', 'growth')
		account_id = request.args.get('account_id', None)
		severity_min = request.args.get('severity_min', 0, type=int)
		
		insights_list = []
		page_title = "Инсайты"
		
		if mode == 'trends':
			page_title = "Тренды инсайтов"
			trend_data = get_trend_data(account_id, severity_min)
			
			if insight_category == 'improvement':
				trend_data = [t for t in trend_data if t['trend'] == 'improvement']
			else:
				trend_data = [t for t in trend_data if t['trend'] == 'decline']
			
			insights_list = [{
				'id': t['id'],
				'account_id': t['entity'],
				'type': t['type'],
				'entity_type': t['entity_type'],
				'entity_id': t['entity_id'],
				'severity': t['severity_7d'],
				'impact_rub': float(t['impact_7d']),
				'title': t['title'],
				'description': t['description'],
				'recommendation': t['recommendation'],
				'created_at': t['created_at'].isoformat() if t['created_at'] else None,
				'date_formatted': t['created_at'].strftime('%Y-%m-%d %H:%M') if t['created_at'] else 'N/A',
				'trend': t['trend'],
				'impact_7d': float(t['impact_7d']),
				'impact_30d': float(t['impact_30d']),
				'change_percent': round(((t['impact_7d'] - t['impact_30d']) / t['impact_30d'] * 100) if t['impact_30d'] > 0 else 0, 1)
			} for t in trend_data]
		else:
			days = 7 if mode == '7days' else 30
			page_title = f"Инсайты ({days} дней)"
			data = get_insights_by_period(days, account_id, severity_min)
			
			insights_list = []
			for row in data:
				classification = classify_insight_type(row[2])
				if (insight_category == 'growth' and classification == 'growth') or (insight_category == 'decline' and classification == 'decline'):
					insights_list.append({
						'id': row[0],
						'account_id': row[1],
						'type': row[2],
						'entity_type': row[3],
						'entity_id': row[4],
						'severity': row[5],
						'impact_rub': float(row[6] or 0),
						'title': row[7],
						'description': row[8],
						'recommendation': row[9],
						'created_at': row[10].isoformat() if row[10] else None,
						'date_formatted': row[10].strftime('%Y-%m-%d %H:%M') if row[10] else 'N/A'
					})
		
		conn = get_conn()
		cur = conn.cursor()
		cur.execute("SELECT DISTINCT account_id FROM insights ORDER BY account_id")
		accounts = [row[0] for row in cur.fetchall()]
		cur.close()
		conn.close()
		
		return render_template('insights.html',
			insights=insights_list,
			accounts=accounts,
			selected_account=account_id,
			selected_severity=severity_min,
			selected_mode=mode,
			selected_category=insight_category,
			page_title=page_title
		)
	except Exception as e:
		print(f"Error in insights route: {e}")
		import traceback
		traceback.print_exc()
		return render_template('error.html', error=str(e)), 500

@app.route('/segment-combinations')
def segment_combinations():
	days = request.args.get('days', 30, type=int)
	severity_min = request.args.get('severity_min', 0, type=int)
	data = get_insights(days, None, None, severity_min, 'segment_combination')
	insight_types = get_insight_types()
	entity_types = get_entity_types()
	insights_list = [{
		'id': row[0],
		'account_id': row[1],
		'type': row[2],
		'entity_type': row[3],
		'entity_id': row[4],
		'severity': row[5],
		'impact_rub': float(row[6] or 0),
		'title': row[7],
		'description': row[8],
		'recommendation': row[9],
		'created_at': row[10].isoformat() if row[10] else None,
		'date_formatted': row[10].strftime('%Y-%m-%d %H:%M') if row[10] else 'N/A'
	} for row in data]

	return render_template('insights.html',
		insights=insights_list,
		insight_types=insight_types,
		entity_types=entity_types,
		selected_type=None,
		selected_entity='segment_combination',
		selected_account=None,
		selected_severity=severity_min,
		days=days
	)

@app.route('/api/insights-timeline')
def insights_timeline():
	days = request.args.get('days', 30, type=int)
	conn = get_conn()
	cur = conn.cursor()
	
	cur.execute(f"""
		SELECT 
			DATE(created_at) as date,
			COUNT(*) as count,
			SUM(impact_rub) as total_impact
		FROM insights
		WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
		GROUP BY DATE(created_at)
		ORDER BY date
	""")
	
	data = cur.fetchall()
	cur.close()
	conn.close()
	
	return jsonify({
		'dates': [row[0].isoformat() for row in data],
		'counts': [row[1] for row in data],
		'impacts': [float(row[2] or 0) for row in data]
	})

@app.route('/api/top-accounts')
def top_accounts():
	days = request.args.get('days', 7, type=int)
	conn = get_conn()
	cur = conn.cursor()
	
	cur.execute(f"""
		SELECT 
			account_id,
			COUNT(*) as insight_count,
			SUM(impact_rub) as total_impact,
			AVG(severity) as avg_severity
		FROM insights
		WHERE created_at >= CURRENT_DATE - INTERVAL '{days} days'
		GROUP BY account_id
		ORDER BY total_impact DESC, insight_count DESC
		LIMIT 10
	""")
	
	data = cur.fetchall()
	cur.close()
	conn.close()
	
	return jsonify({
		'accounts': [row[0] for row in data],
		'insight_counts': [row[1] for row in data],
		'impacts': [float(row[2] or 0) for row in data],
		'avg_severities': [float(row[3] or 0) if row[3] else 0 for row in data]
	})

if __name__ == '__main__':
	app.run(debug=True, host='0.0.0.0', port=5000)
