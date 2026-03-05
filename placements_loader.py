import os
import time
from io import StringIO
from datetime import datetime

import pandas as pd
import requests
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()


CONFIG = {
	"token": os.getenv("YANDEX_TOKEN"),
	"client_login": os.getenv("YANDEX_CLIENT_LOGIN") or "mmg-sz",
	"use_sandbox": False,

	"goal_ids": [151735153, 201395020, 282210833, 337720190, 339151905, 465584771, 465723370, 303059688, 258143758],
	"attribution_models": ["AUTO"],

	"max_retries": 20,
	"retry_sleep_seconds": 5,
	"accept_language": "ru",

	# ВАЖНО: Placement имеет смысл почти всегда только в РСЯ/сетях
	"only_ad_network": True,
}


def get_conn():
	return psycopg2.connect(
		host=os.getenv("DB_HOST"),
		port=os.getenv("DB_PORT"),
		dbname=os.getenv("DB_NAME"),
		user=os.getenv("DB_USER"),
		password=os.getenv("DB_PASSWORD"),
	)


def fetch_direct_report_tsv(
	token: str,
	client_login: str,
	date_from: str,
	date_to: str,
	goal_ids: list[int],
	attribution_models: list[str],
	use_sandbox: bool = False,
	max_retries: int = 40,
	retry_sleep_seconds: int = 5,
	only_ad_network: bool = True,
) -> str:

	base_url = "https://api-sandbox.direct.yandex.com/json/v5/reports" if use_sandbox else "https://api.direct.yandex.com/json/v5/reports"

	headers = {
		"Authorization": f"Bearer {token}",
		"Client-Login": client_login,
		"Accept-Language": CONFIG["accept_language"],
		"Content-Type": "application/json",
		"Accept-Encoding": "identity",
		"skipReportHeader": "true",
		"skipColumnHeader": "false",
		"skipReportSummary": "true",
		# помогает Директу выбрать режим генерации
		"processingMode": "auto",
	}

	field_names = [
		"Date",
		"CampaignId",
		"AdNetworkType",
		"Placement",
		"Impressions",
		"Clicks",
		"Cost",
	]

	selection = {
		"DateFrom": date_from,
		"DateTo": date_to,
	}

	if only_ad_network:
		selection["Filter"] = [{
			"Field": "AdNetworkType",
			"Operator": "EQUALS",
			"Values": ["AD_NETWORK"]
		}]

	params = {
		"SelectionCriteria": selection,
		"FieldNames": field_names,
		"ReportName": f"aiopt_placements_{date_from}_{date_to}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
		"ReportType": "CUSTOM_REPORT",
		"DateRangeType": "CUSTOM_DATE",
		"Format": "TSV",
		"IncludeVAT": "NO",
		"IncludeDiscount": "NO",
		"Goals": goal_ids,
		"AttributionModels": attribution_models,
	}

	body = {"params": params}

	for attempt in range(1, max_retries + 1):
		r = requests.post(base_url, headers=headers, json=body)

		if r.status_code in (200, 201):
			text = (r.content or b"").decode("utf-8", errors="replace")
			req_id = r.headers.get("RequestId") or r.headers.get("X-Request-Id") or ""
			print(f"REPORT attempt {attempt}: status={r.status_code} len={len(text)} RequestId={req_id}")

			# КЛЮЧЕВОЙ ФИКС:
			# иногда Директ отдаёт 200/201 с пустым телом, хотя отчёт ещё "доготавливается"
			if len(text.strip()) == 0:
				time.sleep(retry_sleep_seconds)
				continue

			print("TSV head:", repr(text[:250]))
			return text

		if r.status_code == 202:
			req_id = r.headers.get("RequestId") or r.headers.get("X-Request-Id") or ""
			print(f"REPORT attempt {attempt}: status=202 RequestId={req_id} (waiting...)")
			time.sleep(retry_sleep_seconds)
			continue

		raise RuntimeError(
			"Reports API error\n"
			f"status_code={r.status_code}\n"
			f"response={r.content.decode('utf-8', errors='replace')}"
		)

	raise TimeoutError(f"Report was not ready after {max_retries} retries")



def parse_tsv(tsv_text: str, goal_ids: list[int], attribution_models: list[str]) -> pd.DataFrame:
	tsv_text = (tsv_text or "").strip()
	if not tsv_text:
		return pd.DataFrame()

	df = pd.read_csv(StringIO(tsv_text), sep="\t")

	# Если пришёл только заголовок
	if df.empty:
		print("Parsed DF is empty. Columns:", list(df.columns))
		return df

	# Money
	df["cost_rub"] = pd.to_numeric(df.get("Cost", 0), errors="coerce").fillna(0) / 1_000_000

	# Conversions_* -> conversions_selected
	conv_cols = []
	for gid in goal_ids:
		for model in attribution_models:
			col = f"Conversions_{gid}_{model}"
			if col in df.columns:
				conv_cols.append(col)

	if conv_cols:
		for c in conv_cols:
			df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
		df["conversions_selected"] = df[conv_cols].sum(axis=1)
	else:
		df["conversions_selected"] = 0.0

	# Normalize
	df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
	df["CampaignId"] = pd.to_numeric(df["CampaignId"], errors="coerce").fillna(0).astype("int64")

	df["Placement"] = df.get("Placement", "").astype(str).fillna("")
	df["Placement"] = df["Placement"].str.strip()
	# В отчётах Директа часто пустые значения выглядят как '--'
	df.loc[df["Placement"].isin(["", "--", "—"]), "Placement"] = "UNKNOWN"

	df["AdNetworkType"] = df.get("AdNetworkType", "").astype(str).fillna("").str.strip()

	df["Impressions"] = pd.to_numeric(df.get("Impressions", 0), errors="coerce").fillna(0).astype("int64")
	df["Clicks"] = pd.to_numeric(df.get("Clicks", 0), errors="coerce").fillna(0).astype("int64")

	# Группируем на всякий
	df = df.groupby(["Date", "CampaignId", "AdNetworkType", "Placement"], as_index=False).agg({
		"Impressions": "sum",
		"Clicks": "sum",
		"cost_rub": "sum",
		"conversions_selected": "sum",
	})

	print("Unique AdNetworkType:", df["AdNetworkType"].unique()[:10])
	print("Top placements sample:", df["Placement"].value_counts().head(10).to_dict())

	return df


def upsert_placement_fact(conn, df: pd.DataFrame, account_id: str, client_login: str) -> int:
	if df.empty:
		return 0

	df2 = df.copy()
	df2["account_id"] = account_id
	df2["client_login"] = client_login

	# Dedup on PK
	df2 = df2.drop_duplicates(subset=["Date", "account_id", "CampaignId", "Placement"], keep="last")

	rows = []
	for _, r in df2.iterrows():
		rows.append((
			r["Date"],
			r["account_id"],
			r["client_login"],
			int(r["CampaignId"]),
			str(r["Placement"]),
			int(r["Impressions"]),
			int(r["Clicks"]),
			float(r["cost_rub"]),
			float(r["conversions_selected"]),
		))

	sql = """
	INSERT INTO direct_daily_placement_fact (
		date, account_id, client_login,
		campaign_id, placement,
		impressions, clicks, cost_rub, conversions_selected
	)
	VALUES %s
	ON CONFLICT (date, account_id, campaign_id, placement)
	DO UPDATE SET
		impressions = EXCLUDED.impressions,
		clicks = EXCLUDED.clicks,
		cost_rub = EXCLUDED.cost_rub,
		conversions_selected = EXCLUDED.conversions_selected,
		updated_at = now()
	"""

	with conn.cursor() as cur:
		execute_values(cur, sql, rows, page_size=5000)

	conn.commit()
	return len(rows)


def main():
	if not CONFIG["token"]:
		raise RuntimeError("YANDEX_TOKEN is empty. Check .env")

	# Для теста: вчера/сегодня — руками через env, либо дефолт
	date_from = os.getenv("PLACEMENTS_DATE_FROM") or "2026-03-03"
	date_to = os.getenv("PLACEMENTS_DATE_TO") or "2026-03-03"

	tsv = fetch_direct_report_tsv(
		token=CONFIG["token"],
		client_login=CONFIG["client_login"],
		date_from=date_from,
		date_to=date_to,
		goal_ids=CONFIG["goal_ids"],
		attribution_models=CONFIG["attribution_models"],
		use_sandbox=CONFIG["use_sandbox"],
		max_retries=CONFIG["max_retries"],
		retry_sleep_seconds=CONFIG["retry_sleep_seconds"],
		only_ad_network=CONFIG["only_ad_network"],
	)

	df = parse_tsv(tsv, CONFIG["goal_ids"], CONFIG["attribution_models"])
	print("Placement rows:", len(df))

	conn = get_conn()
	inserted = upsert_placement_fact(conn, df, account_id=CONFIG["client_login"], client_login=CONFIG["client_login"])
	conn.close()

	print("Upserted placement rows:", inserted)


if __name__ == "__main__":
	main()
