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

	_, client_login, data_days_week, cpa_week, cpa_plan, cpa_30d, conv_day_week, conv_day_plan, conv_day_30d = row

	lines = []
	lines.append(f"*KPI ({client_login})*  _(данных дней: {int(data_days_week)})_")
	lines.append(f"• CPA: week `{fmt_money(cpa_week)}` / plan `{fmt_money(cpa_plan)}` / 30d `{fmt_money(cpa_30d)}`")
	lines.append(f"• Leads/day: week `{fmt_num(conv_day_week,1)}` / plan `{fmt_num(conv_day_plan,1)}` / 30d `{fmt_num(conv_day_30d,1)}`")
	return "\n".join(lines) + "\n"


def build_insights_block(cur, account_id: str) -> str:
	cur.execute(
		"""
		SELECT
			id,
			type,
			entity_type,
			entity_id,
			impact_rub,
			confidence,
			title,
			recommendation
		FROM insights
		WHERE status='new'
		AND insight_date = CURRENT_DATE
		AND account_id = %s
		ORDER BY (impact_rub * COALESCE(confidence,1)) DESC NULLS LAST
		LIMIT 10
		""",
		(account_id,),
	)
	rows = cur.fetchall()
	if not rows:
		return "✅ *Инсайтов за сегодня нет.*\n"

	lines = []
	lines.append("⚠ *Top инсайты (сегодня)*")
	for r in rows:
		_id, _type, _etype, entity_id, impact, conf, title, rec = r
		impact = float(impact or 0)
		conf = float(conf or 1)
		lines.append(f"• *{title}*")
		lines.append(f"  `{entity_id}` | impact `{fmt_money(impact)} ₽` | conf `{fmt_num(conf,2)}`")
		lines.append(f"  {rec}")
	return "\n".join(lines) + "\n"


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
	msg += build_insights_block(cur, account_id)

	send_message(msg)

	mark_sent(cur, account_id)
	conn.commit()

	cur.close()
	conn.close()

	print("Digest sent.")


if __name__ == "__main__":
	main()