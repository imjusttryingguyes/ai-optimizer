import os
import requests
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Section limits - risks are most important, then opportunities, then changes
MAX_RISKS = 8
MAX_OPPORTUNITIES = 4
MAX_CHANGES = 3

RISK_TYPES = (
	"ACCOUNT_CPA_TREND_BAD",
	"ACCOUNT_LEADS_TREND_BAD",
	"RSYA_WASTE",
	"SEGMENT_COMBINATION_WASTE",
	"SEGMENT_COMBINATION_CPA_BAD",
	"SEGMENT_LADDER_WASTE",
	"SEGMENT_LADDER_CPA_BAD",
	"SEGMENT_LADDER_TREND_BAD",
)

OPPORTUNITY_TYPES = (
	"SEGMENT_COMBINATION_WINNER",
	"SEGMENT_LADDER_WINNER",
	"ACCOUNT_CPA_TREND_GOOD",
	"ACCOUNT_LEADS_TREND_GOOD",
)

CHANGE_TYPES = (
	"SEGMENT_COMBINATION_TREND_BAD",
	"SEGMENT_COMBINATION_TREND_GOOD",
	"SEGMENT_LADDER_TREND_BAD",
	"SEGMENT_LADDER_TREND_GOOD",
	"ACCOUNT_CPA_TREND_BAD",
	"ACCOUNT_CPA_TREND_GOOD",
	"ACCOUNT_LEADS_TREND_BAD",
	"ACCOUNT_LEADS_TREND_GOOD",
)


def send_message(text: str):
	url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
	payload = {
		"chat_id": CHAT_ID,
		"text": text,
		"disable_web_page_preview": True,
	}
	r = requests.post(url, json=payload, timeout=30)

	if not r.ok:
		raise RuntimeError(f"Telegram sendMessage failed: {r.status_code} | {r.text}")


def fmt_money(x):
	try:
		return f"{float(x):,.0f}".replace(",", " ")
	except Exception:
		return str(x)


def fmt_num(x, digits=2):
	try:
		return f"{float(x):.{digits}f}"
	except Exception:
		return str(x)


def build_kpi_block(cur, account_id: str) -> str:
	cur.execute(
		"""
		SELECT
			account_id,
			COALESCE(client_login, account_id) AS client_login,
			COALESCE(data_days_week, 0) AS data_days_week,
			COALESCE(data_days_30d, 0) AS data_days_30d,

			COALESCE(cpa_week, 0) AS cpa_week,
			COALESCE(cpa_plan, 0) AS cpa_plan,
			COALESCE(cpa_30d, 0) AS cpa_30d,

			COALESCE(conversions_per_day_week, 0) AS conv_day_week,
			COALESCE(conversions_plan_daily, 0) AS conv_day_plan,
			COALESCE(conversions_per_day_30d, 0) AS conv_day_30d
		FROM kpi_account_vs_plan
		WHERE account_id = %s
		LIMIT 1
		""",
		(account_id,),
	)

	row = cur.fetchone()
	if not row:
		return f"*KPI:* нет данных по {account_id}\n"

	(
		_,
		client_login,
		data_days_week,
		data_days_30d,
		cpa_week,
		cpa_plan,
		cpa_30d,
		conv_day_week,
		conv_day_plan,
		conv_day_30d,
	) = row

	lines = []
	lines.append(f"*KPI ({client_login})*")
	lines.append(f"_данных дней: 7d={int(data_days_week)}, 30d={int(data_days_30d)}_")
	lines.append(f"• CPA: week `{fmt_money(cpa_week)}` / plan `{fmt_money(cpa_plan)}` / 30d `{fmt_money(cpa_30d)}`")
	lines.append(f"• Leads/day: week `{fmt_num(conv_day_week,1)}` / plan `{fmt_num(conv_day_plan,1)}` / 30d `{fmt_num(conv_day_30d,1)}`")
	return "\n".join(lines) + "\n"

def build_data_health_block(cur, account_id: str) -> str:
	"""Build data quality block with indicators."""
	cur.execute(
		"""
		SELECT
			COALESCE(data_days_week, 0) AS data_days_week,
			COALESCE(data_days_30d, 0) AS data_days_30d
		FROM kpi_account_vs_plan
		WHERE account_id = %s
		LIMIT 1
		""",
		(account_id,),
	)
	
	row = cur.fetchone()
	if not row:
		return ""

	data_days_week, data_days_30d = row
	
	lines = []
	lines.append(f"_📊 Data Health_")
	
	# Week health indicator
	if data_days_week >= 6:
		week_indicator = "✅"
	elif data_days_week >= 3:
		week_indicator = "⚠️"
	else:
		week_indicator = "❌"
	
	# 30d health indicator
	if data_days_30d >= 25:
		month_indicator = "✅"
	elif data_days_30d >= 15:
		month_indicator = "⚠️"
	else:
		month_indicator = "❌"
	
	lines.append(f"• Week: {week_indicator} {int(data_days_week)}/7 days")
	lines.append(f"• Month: {month_indicator} {int(data_days_30d)}/30 days")
	
	return "\n".join(lines) + "\n"


def fetch_insights_by_types(cur, account_id: str, insight_types: tuple[str, ...], limit: int):
	cur.execute(
		"""
		SELECT
			id,
			type,
			entity_type,
			entity_id,
			impact_rub,
			confidence,
			priority,
			title,
			recommendation
		FROM insights
		WHERE status = 'new'
			AND insight_date = CURRENT_DATE
			AND account_id = %s
			AND type = ANY(%s)
		ORDER BY priority DESC NULLS LAST
		LIMIT %s
		""",
		(account_id, list(insight_types), limit),
	)
	return cur.fetchall()

def format_insight_line(row) -> str:
	(
		insight_id,
		insight_type,
		entity_type,
		entity_id,
		impact,
		confidence,
		priority,
		title,
		recommendation,
	) = row

	entity_id = str(entity_id or "n/a").strip()
	title = str(title or insight_type).strip()
	recommendation = str(recommendation or "").strip()
	impact = float(impact or 0)
	confidence = float(confidence or 0)
	priority = float(priority or 0)

	# Format impact cleanly
	impact_str = f"{impact:,.0f}".replace(",", " ")
	conf_str = f"{confidence:.2f}"
	priority_str = f"{priority:,.0f}".replace(",", " ")

	line = f"• {title}\n"
	line += f"  💰 {impact_str} ₽ | ⭐ {conf_str} | 🎯 {priority_str}"
	
	if entity_id and entity_id != "n/a":
		line += f" | {entity_type or 'Entity'}: {entity_id}"

	if recommendation:
		line += f"\n  → {recommendation}"

	return line

def build_section(title: str, rows: list, limit: int | None = None) -> tuple[str, list[int]]:
	if not rows:
		return "", []

	if limit is not None:
		rows = rows[:limit]

	lines = [title]
	insight_ids = []
	for row in rows:
		lines.append(format_insight_line(row))
		insight_ids.append(row[0])

	return "\n".join(lines) + "\n", insight_ids


def build_digest_blocks(cur, account_id: str) -> list[tuple[str, list[int]]]:
	"""Returns list of (section_text, insight_ids) tuples for each section."""
	risk_rows = fetch_insights_by_types(cur, account_id, RISK_TYPES, MAX_RISKS)
	opportunity_rows = fetch_insights_by_types(cur, account_id, OPPORTUNITY_TYPES, MAX_OPPORTUNITIES)
	change_rows = fetch_insights_by_types(cur, account_id, CHANGE_TYPES, MAX_CHANGES)

	sections = []

	if risk_rows:
		text, ids = build_section("⚠ *Top Risks*", risk_rows, limit=5)
		sections.append((text, ids))

	if opportunity_rows:
		text, ids = build_section("🚀 *Opportunities*", opportunity_rows, limit=3)
		sections.append((text, ids))

	if change_rows:
		text, ids = build_section("📈 *Recent Changes*", change_rows, limit=2)
		sections.append((text, ids))

	return sections


def mark_sent(cur, insight_ids: list[int]):
	if not insight_ids:
		return
	cur.execute(
		"""
		UPDATE insights
		SET status='sent', updated_at=now()
		WHERE id = ANY(%s)
		""",
		(insight_ids,),
	)


def main():
	if not BOT_TOKEN or not CHAT_ID:
		raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID is missing in .env")

	account_id = os.getenv("AI_ACCOUNT_ID") or os.getenv("DIRECT_CLIENT_LOGIN") or "mmg-sz"

	conn = get_conn()
	cur = conn.cursor()

	MAX_TG_MESSAGE_LEN = 3800

	msg = "🤖 *AI Optimizer — Daily Digest*\n\n"
	msg += build_kpi_block(cur, account_id) + "\n"
	msg += build_data_health_block(cur, account_id) + "\n"
	
	sections = build_digest_blocks(cur, account_id)
	sent_ids = []

	if not sections:
		msg += "✅ *Новых инсайтов за сегодня нет.*\n"
	else:
		for section_text, section_ids in sections:
			msg_with_section = msg + section_text
			
			if len(msg_with_section) <= MAX_TG_MESSAGE_LEN:
				msg = msg_with_section
				sent_ids.extend(section_ids)
			else:
				# Section doesn't fit - add truncation notice and stop
				msg += "\n⏸ _Остальные инсайты завтра_"
				break

	send_message(msg)

	mark_sent(cur, sent_ids)
	conn.commit()

	cur.close()
	conn.close()

	print("Digest sent.")


if __name__ == "__main__":
	main()