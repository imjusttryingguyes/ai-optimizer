import os
import psycopg2
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

load_dotenv()


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


def fmt_money(x):
	try:
		return f"{float(x):,.0f}".replace(",", " ")
	except Exception:
		return str(x)


def fmt_num(x):
	try:
		return f"{float(x):,.2f}".replace(",", " ")
	except Exception:
		return str(x)


def main():
	# Пороги (потом вынесем в таблицу настроек)
	min_cost_for_analysis = 1000.0
	waste_cost_threshold = 5000.0
	worst_multiplier = 1.5
	best_multiplier = 0.7

	conn = get_conn()
	cur = conn.cursor()

	cur.execute("""
		SELECT
			account_id,
			campaign_id,
			spend_rub,
			conversions,
			cpa,
			AVG(cpa) OVER (PARTITION BY account_id) as cpa_account
		FROM kpi_campaign_vs_account
		WHERE spend_rub >= %s
		ORDER BY spend_rub DESC
	""", (min_cost_for_analysis,))

	rows = cur.fetchall()

	worst = []
	best = []
	waste = []

	for r in rows:
		account_id, campaign_id, spend_rub, conv, cpa_c, cpa_a = r

		spend_rub = float(spend_rub or 0)
		conv = float(conv or 0)
		cpa_a = float(cpa_a) if cpa_a is not None else None
		cpa_c = float(cpa_c) if cpa_c is not None else None

		# Слив: есть расход, нет конверсий
		if conv == 0 and spend_rub >= waste_cost_threshold:
			waste.append((campaign_id, spend_rub))
			continue

		if cpa_a is None or cpa_c is None:
			continue

		# Плохие/хорошие относительно CPA аккаунта
		if cpa_c > cpa_a * worst_multiplier:
			worst.append((campaign_id, spend_rub, conv, cpa_c, cpa_a))
		elif cpa_c < cpa_a * best_multiplier:
			best.append((campaign_id, spend_rub, conv, cpa_c, cpa_a))

	print("===== CAMPAIGN ANALYSIS (7d window, or available days) =====\n")

	if worst:
		print("⚠ WORST CAMPAIGNS (CPA > account * 1.5)")
		for cid, spend_rub, conv, cpa_c, cpa_a in worst[:10]:
			print(f"- {cid}: spend {fmt_money(spend_rub)} | conv {fmt_num(conv)} | CPA {fmt_num(cpa_c)} (acct {fmt_num(cpa_a)})")
		print("")
	else:
		print("✅ No WORST campaigns by threshold\n")

	if waste:
		print("💸 SPEND WITHOUT CONVERSIONS (conv=0 and spend>=5000)")
		for cid, spend_rub in waste[:10]:
			print(f"- {cid}: spend {fmt_money(spend_rub)}")
		print("")
	else:
		print("✅ No big spend-without-conv cases\n")

	if best:
		print("🚀 BEST CAMPAIGNS (CPA < account * 0.7)")
		for cid, spend_rub, conv, cpa_c, cpa_a in best[:10]:
			print(f"- {cid}: spend {fmt_money(spend_rub)} | conv {fmt_num(conv)} | CPA {fmt_num(cpa_c)} (acct {fmt_num(cpa_a)})")
		print("")
	else:
		print("ℹ No BEST campaigns by threshold\n")

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()
