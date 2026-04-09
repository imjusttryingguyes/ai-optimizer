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

MAX_RISKS = 5
MAX_OPPORTUNITIES = 5
MAX_CHANGES = 5

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
)

CHANGE_TYPES = (
	"SEGMENT_COMBINATION_TREND_BAD",
	"SEGMENT_COMBINATION_TREND_GOOD",
	"SEGMENT_LADDER_TREND_BAD",
	"SEGMENT_LADDER_TREND_GOOD",
)


def send_message(text: str):
	url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
	payload = {
		"chat_id": CHAT_ID,
		"text": text,
		"parse_mode": "Markdown",
		"disable_web_page_preview": True,
	}
	r = requests.post(url, json=payload, timeout=30)
	r.raise_for_status()


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

def build_section(title: str, rows) -> str:
	if not rows:
		return ""

	lines = [title]
	for r in rows:
		_id, _type, _etype, entity_id, impact, conf, priority, insight_title, rec = r
		impact = float(impact or 0)
		conf = float(conf or 1)
		priority = float(priority or 0)

		lines.append(f"• *{insight_title}*")
		lines.append(
			f"  `{entity_id}` | impact `{fmt_money(impact)} ₽` | "
			f"conf `{fmt_num(conf,2)}` | priority `{fmt_money(priority)}`"
		)
		lines.append(f"  {rec}")

	return "\n".join(lines) + "\n"


def build_digest_blocks(cur, account_id: str) -> str:
	risk_rows = fetch_insights_by_types(cur, account_id, RISK_TYPES, MAX_RISKS)
	opportunity_rows = fetch_insights_by_types(cur, account_id, OPPORTUNITY_TYPES, MAX_OPPORTUNITIES)
	change_rows = fetch_insights_by_types(cur, account_id, CHANGE_TYPES, MAX_CHANGES)

	parts = []

	if risk_rows:
		parts.append(build_section("⚠ *Top Risks*", risk_rows))

	if opportunity_rows:
		parts.append(build_section("🚀 *Opportunities*", opportunity_rows))

	if change_rows:
		parts.append(build_section("📈 *Recent Changes*", change_rows))

	if not parts:
		return "✅ *Новых инсайтов за сегодня нет.*\n"

	return "\n".join(parts)


def mark_sent(cur, account_id: str):
	cur.execute(
		"""
		UPDATE insights
		SET status='sent', updated_at=now()
		WHERE status='new'
		AND insight_date = CURRENT_DATE
		AND account_id = %s
		""",
		(account_id,),
	)


def main():
	if not BOT_TOKEN or not CHAT_ID:
		raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID is missing in .env")

	account_id = os.getenv("AI_ACCOUNT_ID") or os.getenv("DIRECT_CLIENT_LOGIN") or "mmg-sz"

	conn = get_conn()
	cur = conn.cursor()

	msg = "🤖 *AI Optimizer — Daily Digest*\n\n"
	msg += build_kpi_block(cur, account_id) + "\n"
	msg += build_digest_blocks(cur, account_id)

	send_message(msg)

	mark_sent(cur, account_id)
	conn.commit()

	cur.close()
	conn.close()

	print("Digest sent.")


if __name__ == "__main__":
	main()