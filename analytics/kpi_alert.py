import os
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


def main():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
		SELECT
			account_id,
			client_login,
			cpa_plan,
			conversions_plan_daily,
			spend_rub_week,
			conversions_week,
			data_days_week,
			cpa_week,
			conversions_per_day_week,
			cpa_30d,
			conversions_per_day_30d
		FROM kpi_account_vs_plan
		WHERE account_id IS NOT NULL
		ORDER BY account_id
	"""
    )

    rows = cur.fetchall()

    for r in rows:
        (
            account_id,
            client_login,
            cpa_plan,
            conv_plan_daily,
            spend_week,
            conv_week,
            data_days_week,
            cpa_week,
            conv_week_per_day,
            cpa_30d,
            conv_30d_per_day,
        ) = r

        coverage_note = f"(данных дней: {int(data_days_week)})"

        status = []
        if cpa_week is not None and float(cpa_week) > float(cpa_plan):
            status.append("CPA выше плана")
        if float(conv_week_per_day) < float(conv_plan_daily):
            status.append("Лидов/день ниже плана")

        if not status:
            level = "OK"
            status_txt = "всё в норме"
        else:
            level = "ALERT"
            status_txt = "; ".join(status)

        print(f"[{level}] {account_id} {coverage_note}")
        print(f"  CPA: week={cpa_week} plan={cpa_plan} 30d={cpa_30d}")
        print(
            f"  Leads/day: week={conv_week_per_day} plan={conv_plan_daily} 30d={conv_30d_per_day}"
        )
        print("")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
