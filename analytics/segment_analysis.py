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
	return f"{float(x):,.0f}".replace(",", " ")


def fmt_num(x):
	return f"{float(x):,.2f}".replace(",", " ")


def main():
	min_cost = 1000.0
	waste_cost_no_conv = 5000.0
	worst_mult = 1.5
	best_mult = 0.7

	conn = get_conn()
	cur = conn.cursor()

	cur.execute("""
		SELECT
			account_id,
			device,
			ad_network_type,
			spend_rub,
			conversions,
			cpa_segment,
			cpa_account
		FROM kpi_segment_device_network
		WHERE spend_rub >= %s
		ORDER BY spend_rub DESC
	""", (min_cost,))

	rows = cur.fetchall()

	worst = []
	best = []
	waste = []

	for account_id, device, net, spend_rub, conv, cpa_s, cpa_a in rows:
		spend_rub = float(spend_rub or 0)
		conv = float(conv or 0)

		if conv == 0 and spend_rub >= waste_cost_no_conv:
			waste.append((device, net, spend_rub))
			continue

		if cpa_s is None or cpa_a is None:
			continue

		cpa_s = float(cpa_s)
		cpa_a = float(cpa_a)

		if cpa_s > cpa_a * worst_mult:
			worst.append((device, net, spend_rub, conv, cpa_s, cpa_a))
		elif cpa_s < cpa_a * best_mult:
			best.append((device, net, spend_rub, conv, cpa_s, cpa_a))

	print("===== SEGMENT ANALYSIS: DEVICE x NETWORK (7d window, or available days) =====\n")

	if worst:
		print("⚠ WORST SEGMENTS (CPA > account * 1.5)")
		for device, net, spend_rub, conv, cpa_s, cpa_a in worst[:10]:
			print(f"- {device} / {net}: spend {fmt_money(spend_rub)} | conv {fmt_num(conv)} | CPA {fmt_num(cpa_s)} (acct {fmt_num(cpa_a)})")
		print("")
	else:
		print("✅ No WORST segments by threshold\n")

	if waste:
		print("💸 SPEND WITHOUT CONVERSIONS (conv=0 and spend>=5000)")
		for device, net, spend_rub in waste[:10]:
			print(f"- {device} / {net}: spend {fmt_money(spend_rub)}")
		print("")
	else:
		print("✅ No big spend-without-conv segments\n")

	if best:
		print("🚀 BEST SEGMENTS (CPA < account * 0.7)")
		for device, net, spend_rub, conv, cpa_s, cpa_a in best[:10]:
			print(f"- {device} / {net}: spend {fmt_money(spend_rub)} | conv {fmt_num(conv)} | CPA {fmt_num(cpa_s)} (acct {fmt_num(cpa_a)})")
		print("")
	else:
		print("ℹ No BEST segments by threshold\n")

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()
