import os
import math
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


def wilson_interval(successes: float, trials: float, z: float = 1.96):
	# Wilson score interval for proportion
	# returns (low, high)
	if trials <= 0:
		return (0.0, 0.0)
	p = successes / trials
	den = 1.0 + (z * z) / trials
	center = (p + (z * z) / (2.0 * trials)) / den
	half = (z / den) * math.sqrt((p * (1.0 - p) / trials) + (z * z) / (4.0 * trials * trials))
	low = max(0.0, center - half)
	high = min(1.0, center + half)
	return (low, high)


def main():
	# Пороги (можно потом вынести в account_targets / settings)
	min_cost = 500.0					# чтобы не шуметь на копейках
	waste_cost_no_conv = 2000.0			# “слив без конверсий”
	min_clicks_for_significance = 30	# минимум кликов, чтобы сравнивать CR

	conn = get_conn()
	cur = conn.cursor()

	cur.execute("""
		SELECT
			account_id,
			placement,
			cost_rub,
			clicks,
			impressions,
			conversions,
			acct_cost_rub,
			acct_clicks,
			acct_impressions,
			acct_conversions
		FROM kpi_rsy_placements_7d
		WHERE cost_rub >= %s
		ORDER BY cost_rub DESC
	""", (min_cost,))

	rows = cur.fetchall()
	cur.close()
	conn.close()

	if not rows:
		print("No placement rows found (check loader + view refresh).")
		return

	# Baseline per account
	# (в рамках 1 аккаунта; на будущее можно делать по client_login)
	acct_id = rows[0][0]
	acct_clicks = float(rows[0][7] or 0)
	acct_conversions = float(rows[0][9] or 0)

	acct_cr = (acct_conversions / acct_clicks) if acct_clicks > 0 else 0.0
	acct_low, acct_high = wilson_interval(acct_conversions, acct_clicks)

	waste = []
	worst_sig = []
	best_sig = []
	top_spend = []

	for r in rows:
		account_id, placement, cost, clicks, impr, conv, acct_cost, acct_clk, acct_impr, acct_conv = r
		cost = float(cost or 0)
		clicks = float(clicks or 0)
		conv = float(conv or 0)

		top_spend.append((placement, cost, clicks, conv))

		# Слив без конверсий
		if conv <= 0 and cost >= waste_cost_no_conv:
			waste.append((placement, cost, clicks))
			continue

		# Значимость по CR
		if clicks < min_clicks_for_significance:
			continue

		seg_low, seg_high = wilson_interval(conv, clicks)

		# Площадка статистически хуже аккаунта: её upper < account lower
		if seg_high < acct_low:
			# приоритет = “переплата” относительно baseline CPA аккаунта (грубо)
			# если baseline CR есть: ожидаемые конверсии = clicks * acct_cr
			exp_conv = clicks * acct_cr
			waste_rub = cost  # fallback
			if exp_conv > 0:
				# ожидаемая стоимость конверсии на аккаунте приблизительно = acct_cost/acct_conv, но у нас тут только CR,
				# поэтому упрощаем приоритетом через cost и дефицит конверсий:
				waste_rub = max(0.0, cost * (1.0 - (conv / exp_conv)))
			worst_sig.append((placement, cost, clicks, conv, seg_low, seg_high, waste_rub))

		# Площадка статистически лучше: её lower > account upper
		elif seg_low > acct_high:
			best_sig.append((placement, cost, clicks, conv, seg_low, seg_high))

	print("===== RSYA PLACEMENTS ANALYSIS (7d window, or available days) =====")
	print(f"Account: {acct_id}")
	print(f"Baseline CR (conv/click): {fmt_num(acct_cr * 100)}% (Wilson {fmt_num(acct_low * 100)}%..{fmt_num(acct_high * 100)}%)\n")

	# TOP spend overview (helpful always)
	print("📌 TOP SPEND PLACEMENTS")
	for placement, cost, clicks, conv in top_spend[:10]:
		cr = (conv / clicks) if clicks > 0 else 0.0
		print(f"- {placement}: spend {fmt_money(cost)} | clicks {int(clicks)} | conv {fmt_num(conv)} | CR {fmt_num(cr * 100)}%")
	print("")

	if waste:
		print(f"💸 SPEND WITHOUT CONVERSIONS (cost >= {fmt_money(waste_cost_no_conv)})")
		for placement, cost, clicks in waste[:15]:
			print(f"- {placement}: spend {fmt_money(cost)} | clicks {int(clicks)} | conv 0")
		print("")
	else:
		print("✅ No big spend-without-conv placements\n")

	if worst_sig:
		print(f"⚠ STATISTICALLY WORSE THAN ACCOUNT (clicks >= {min_clicks_for_significance})")
		# сортируем по “потенциальной переплате”
		worst_sig.sort(key=lambda x: x[6], reverse=True)
		for placement, cost, clicks, conv, lo, hi, waste_rub in worst_sig[:15]:
			cr = (conv / clicks) if clicks > 0 else 0.0
			print(f"- {placement}: spend {fmt_money(cost)} | clicks {int(clicks)} | conv {fmt_num(conv)} | CR {fmt_num(cr * 100)}% (Wilson {fmt_num(lo * 100)}%..{fmt_num(hi * 100)}%) | priority≈{fmt_money(waste_rub)}")
		print("")
	else:
		print("✅ No statistically worse placements by threshold\n")

	if best_sig:
		print(f"🚀 STATISTICALLY BETTER THAN ACCOUNT (clicks >= {min_clicks_for_significance})")
		best_sig.sort(key=lambda x: x[1], reverse=True)
		for placement, cost, clicks, conv, lo, hi in best_sig[:15]:
			cr = (conv / clicks) if clicks > 0 else 0.0
			print(f"- {placement}: spend {fmt_money(cost)} | clicks {int(clicks)} | conv {fmt_num(conv)} | CR {fmt_num(cr * 100)}% (Wilson {fmt_num(lo * 100)}%..{fmt_num(hi * 100)}%)")
		print("")
	else:
		print("ℹ No statistically better placements by threshold\n")


if __name__ == "__main__":
	main()