import time
from io import StringIO
import os
import json
import hashlib

import pandas as pd
import requests
from dotenv import load_dotenv

from db_save import (
	get_pg_conn,
	df_to_spend_fact,
	df_to_conv_long,
	upsert_spend_facts,
	upsert_conv_facts
)


load_dotenv()


CONFIG = {
	"token": os.getenv("YANDEX_TOKEN"),
	"client_login": "mmg-sz",
	"use_sandbox": False,

	"goal_ids": [151735153, 201395020, 282210833, 337720190, 339151905, 465584771, 465723370, 303059688, 258143758],
	"attribution_models": ["AUTO"],

	"max_retries": 30,
	"retry_sleep_seconds": 5,
	"accept_language": "ru",
}


def make_report_name(
	date_from: str,
	date_to: str,
	field_names: list[str],
	goal_ids: list[int],
	attribution_models: list[str],
	include_goals: bool,
) -> str:
	report_key = {
		"date_from": date_from,
		"date_to": date_to,
		"fields": field_names,
		"include_goals": include_goals,
		"goals": goal_ids if include_goals else [],
		"attr": attribution_models if include_goals else [],
	}
	report_hash = hashlib.md5(json.dumps(report_key, sort_keys=True).encode("utf-8")).hexdigest()[:12]
	return f"aiopt_{report_hash}"


def fetch_direct_report_tsv(
	token: str,
	client_login: str,
	date_from: str,
	date_to: str,
	goal_ids: list[int],
	attribution_models: list[str],
	use_sandbox: bool = False,
	max_retries: int = 30,
	retry_sleep_seconds: int = 5,
	include_goals: bool = True,
) -> str:

	base_url = "https://api-sandbox.direct.yandex.com/json/v5/reports" if use_sandbox else "https://api.direct.yandex.com/json/v5/reports"

	headers = {
		"Authorization": f"Bearer {token}",
		"Client-Login": client_login,
		"Accept-Language": CONFIG["accept_language"],
		"Content-Type": "application/json",
		"skipReportHeader": "true",
		"skipColumnHeader": "false",
		"skipReportSummary": "true",
		"Accept-Encoding": "identity",
	}

	field_names = [
		"Date",
		"CampaignId",
		"AdGroupId",
		"CriterionId",
		"Device",
		"AdNetworkType",
		"LocationOfPresenceName",
		"TargetingLocationName",
		"Age",
		"Gender",
		"Impressions",
		"Clicks",
		"Ctr",
		"Cost",
		"Conversions",
	]

	report_name = make_report_name(
		date_from=date_from,
		date_to=date_to,
		field_names=field_names,
		goal_ids=goal_ids,
		attribution_models=attribution_models,
		include_goals=include_goals,
	)

	params = {
		"SelectionCriteria": {
			"DateFrom": date_from,
			"DateTo": date_to
		},
		"FieldNames": field_names,
		"ReportName": report_name,
		"ReportType": "CUSTOM_REPORT",
		"DateRangeType": "CUSTOM_DATE",
		"Format": "TSV",
		"IncludeVAT": "NO",
		"IncludeDiscount": "NO",
	}

	if include_goals:
		params["Goals"] = goal_ids
		params["AttributionModels"] = attribution_models

	body = {"params": params}

	last_status = None
	for attempt in range(1, max_retries + 1):
		r = requests.post(base_url, headers=headers, json=body)

		last_status = r.status_code
		req_id = r.headers.get("RequestId") or r.headers.get("requestid") or r.headers.get("X-Request-Id")

		if r.status_code == 200:
			content_len = len(r.content or b"")
			print(f"REPORT attempt {attempt}: status=200 content_len={content_len} RequestId={req_id}")
			return (r.content or b"").decode("utf-8", errors="replace")

		if r.status_code in (201, 202):
			content_len = len(r.content or b"")
			print(f"REPORT attempt {attempt}: status={r.status_code} content_len={content_len} RequestId={req_id} (waiting...)")
			time.sleep(retry_sleep_seconds)
			continue

		raise RuntimeError(
			"Reports API error\n"
			f"status_code={r.status_code}\n"
			f"request_id={req_id}\n"
			f"response={(r.content or b'').decode('utf-8', errors='replace')}"
		)

	raise TimeoutError(f"Report not ready after {max_retries} retries (last_status={last_status})")


def parse_report_tsv_to_df(
	tsv_text: str,
	goal_ids: list[int],
	attribution_models: list[str],
) -> pd.DataFrame:

	tsv_text = (tsv_text or "").strip()
	if not tsv_text:
		return pd.DataFrame()

	df = pd.read_csv(StringIO(tsv_text), sep="\t")

	# Приводим Cost к числу (на всякий случай, иногда прилетает строкой)
	if "Cost" in df.columns:
		df["Cost"] = pd.to_numeric(df["Cost"], errors="coerce").fillna(0)
		df["cost_rub"] = df["Cost"] / 1_000_000
	else:
		df["cost_rub"] = 0.0

	# Ищем реальные колонки конверсий по нужным goal_id
	all_cols = list(df.columns)
	conversion_cols = []
	for goal_id in goal_ids:
		goal_str = str(goal_id)
		for c in all_cols:
			if c.startswith("Conversions_") and goal_str in c:
				conversion_cols.append(c)

	conversion_cols = sorted(set(conversion_cols))
	print("Conv-like cols (first 30):", conversion_cols[:30])

	# Приводим колонки конверсий к числам (это фикс твоей ошибки)
	for c in conversion_cols:
		# Если вдруг дроби с запятой — заменим на точку
		if df[c].dtype == "object":
			df[c] = df[c].astype(str).str.replace(",", ".", regex=False)
		df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

	df["conversions_selected"] = df[conversion_cols].sum(axis=1) if conversion_cols else 0.0

	# CPA: там где конверсий 0 — NaN
	denom = df["conversions_selected"].where(df["conversions_selected"] != 0)
	df["cpa_selected"] = df["cost_rub"] / denom

	return df


def load_direct_day(date_from: str, date_to: str):
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
	)

	df = parse_report_tsv_to_df(
		tsv_text=tsv,
		goal_ids=CONFIG["goal_ids"],
		attribution_models=CONFIG["attribution_models"],
	)

	if df.empty:
		print(f"[{date_from}] No rows in report.")
		return 0, 0

	conn = get_pg_conn()

	df_spend = df_to_spend_fact(
		df=df,
		account_id=CONFIG["client_login"],
		client_login=CONFIG["client_login"]
	)

	df_conv = df_to_conv_long(
		df=df,
		goal_ids=CONFIG["goal_ids"],
		attribution_models=CONFIG["attribution_models"],
		account_id=CONFIG["client_login"],
		client_login=CONFIG["client_login"]
	)

	inserted_spend = upsert_spend_facts(conn, df_spend)
	inserted_conv = upsert_conv_facts(conn, df_conv)

	conn.close()

	print(f"[{date_from}] spend={inserted_spend}, conv={inserted_conv}")
	return inserted_spend, inserted_conv


if __name__ == "__main__":

	if not CONFIG["token"]:
		raise RuntimeError("YANDEX_TOKEN is empty. Check .env and load_dotenv()")

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
		include_goals=True,
	)

	print("TSV length:", len(tsv))
	print("TSV preview:", repr(tsv[:300]))

	df = parse_report_tsv_to_df(
		tsv_text=tsv,
		goal_ids=CONFIG["goal_ids"],
		attribution_models=CONFIG["attribution_models"],
	)

	print("Rows:", len(df))
	if not df.empty:
		print(df[["Date", "CampaignId", "Clicks", "Cost", "cost_rub", "conversions_selected", "cpa_selected"]].head(10))

	if df.empty:
		print("No rows in report. Stopping before DB step.")
		raise SystemExit(0)

	conn = get_pg_conn()
	print("DB connected successfully")

	from db_save import (
	get_pg_conn,
	df_to_spend_fact,
	df_to_conv_long,
	upsert_spend_facts,
	upsert_conv_facts
	)

	conn = get_pg_conn()

	df_spend = df_to_spend_fact(
		df=df,
		account_id=CONFIG["client_login"],
		client_login=CONFIG["client_login"]
	)

	df_conv = df_to_conv_long(
		df=df,
		goal_ids=CONFIG["goal_ids"],
		attribution_models=CONFIG["attribution_models"],
		account_id=CONFIG["client_login"],
		client_login=CONFIG["client_login"]
	)

	print("Spend rows:", len(df_spend))
	print("Conv rows:", len(df_conv))

	inserted_spend = upsert_spend_facts(conn, df_spend)
	inserted_conv = upsert_conv_facts(conn, df_conv)

	print("Upserted spend:", inserted_spend)
	print("Upserted conv:", inserted_conv)

	conn.close()

	date_from = "2026-03-02"
	date_to = "2026-03-03"
	load_direct_day(date_from, date_to)