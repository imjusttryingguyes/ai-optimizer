import os
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()


def get_pg_conn():
	host = os.getenv("DB_HOST")
	port = os.getenv("DB_PORT")
	dbname = os.getenv("DB_NAME")
	user = os.getenv("DB_USER")
	password = os.getenv("DB_PASSWORD")

	print("DB_HOST:", host)
	print("DB_PORT:", port)
	print("DB_NAME:", dbname)
	print("DB_USER:", user)

	return psycopg2.connect(
		host=host,
		port=port,
		dbname=dbname,
		user=user,
		password=password,
	)


def to_int_id(x):
	if x is None:
		return 0
	s = str(x).strip()
	if s in ("", "--", "None", "nan", "NaN"):
		return 0
	try:
		return int(float(s))
	except Exception:
		return 0


# =========================
# SPEND FACT
# =========================

def df_to_spend_fact(df, account_id, client_login):

	df_spend = df.copy()

	df_spend["date"] = pd.to_datetime(df_spend["Date"]).dt.date
	df_spend["account_id"] = account_id
	df_spend["client_login"] = client_login

	df_spend["campaign_id"] = df_spend["CampaignId"].map(to_int_id)
	df_spend["adgroup_id"] = df_spend["AdGroupId"].map(to_int_id)
	df_spend["criterion_id"] = df_spend["CriterionId"].map(to_int_id)

	df_spend["device"] = df_spend["Device"]
	df_spend["ad_network_type"] = df_spend["AdNetworkType"]

	df_spend["location_of_presence_name"] = df_spend["LocationOfPresenceName"]
	df_spend["targeting_location_name"] = df_spend["TargetingLocationName"]

	df_spend["age"] = df_spend["Age"]
	df_spend["gender"] = df_spend["Gender"]

	df_spend["impressions"] = pd.to_numeric(df_spend["Impressions"], errors="coerce").fillna(0).astype(int)
	df_spend["clicks"] = pd.to_numeric(df_spend["Clicks"], errors="coerce").fillna(0).astype(int)
	df_spend["cost_rub"] = df_spend["cost_rub"]

	return df_spend[[
		"date",
		"account_id",
		"client_login",
		"campaign_id",
		"adgroup_id",
		"criterion_id",
		"device",
		"ad_network_type",
		"location_of_presence_name",
		"targeting_location_name",
		"age",
		"gender",
		"impressions",
		"clicks",
		"cost_rub",
	]]


def upsert_spend_facts(conn, df):

	if df.empty:
		return 0

	# Дедуп/агрегация по уникальному ключу spend-таблицы
	pk_cols = [
		"date",
		"account_id",
		"campaign_id",
		"adgroup_id",
		"criterion_id",
		"device",
		"ad_network_type",
		"location_of_presence_name",
		"targeting_location_name",
		"age",
		"gender",
	]

	df = df.groupby(pk_cols, as_index=False).agg({
		"client_login": "first",
		"impressions": "sum",
		"clicks": "sum",
		"cost_rub": "sum",
	})

	print("Spend rows after dedup:", len(df))

	cols = [
		"date",
		"account_id",
		"client_login",
		"campaign_id",
		"adgroup_id",
		"criterion_id",
		"device",
		"ad_network_type",
		"location_of_presence_name",
		"targeting_location_name",
		"age",
		"gender",
		"impressions",
		"clicks",
		"cost_rub",
	]
	df = df[cols]	

	rows = [
		tuple(r)
		for r in df.itertuples(index=False, name=None)
	]

	sql = """
	INSERT INTO direct_daily_spend_fact (
		date,
		account_id,
		client_login,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender,
		impressions,
		clicks,
		cost_rub
	)
	VALUES %s
	ON CONFLICT (
		date,
		account_id,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender
	)
	DO UPDATE SET
		impressions = EXCLUDED.impressions,
		clicks = EXCLUDED.clicks,
		cost_rub = EXCLUDED.cost_rub,
		updated_at = now()
	"""

	with conn.cursor() as cur:
		execute_values(cur, sql, rows, page_size=5000)

	conn.commit()

	return len(rows)

# =========================
# CONVERSIONS FACT
# =========================

def df_to_conv_long(df, goal_ids, attribution_models, account_id, client_login):

	rows = []

	for r in df.itertuples():

		for goal_id in goal_ids:
			for model in attribution_models:

				col = f"Conversions_{goal_id}_{model}"

				if not hasattr(r, col):
					continue

				conversions = getattr(r, col)

				try:
					conversions = float(conversions)
				except Exception:
					conversions = 0.0

				if conversions == 0:
					continue

				rows.append({
					"date": pd.to_datetime(r.Date).date(),
					"account_id": account_id,
					"client_login": client_login,

					"campaign_id": to_int_id(r.CampaignId),
					"adgroup_id": to_int_id(r.AdGroupId),
					"criterion_id": to_int_id(r.CriterionId),

					"device": r.Device,
					"ad_network_type": r.AdNetworkType,

					"location_of_presence_name": r.LocationOfPresenceName,
					"targeting_location_name": r.TargetingLocationName,

					"age": r.Age,
					"gender": r.Gender,

					"goal_id": goal_id,
					"conversions": conversions
				})

	df_long = pd.DataFrame(rows)

	return df_long


def upsert_conv_facts(conn, df):

	if df.empty:
		return 0

	df = df.copy()

	# На всякий: привести типы
	df["campaign_id"] = pd.to_numeric(df["campaign_id"], errors="coerce").fillna(0).astype(int)
	df["adgroup_id"] = pd.to_numeric(df["adgroup_id"], errors="coerce").fillna(0).astype(int)
	df["criterion_id"] = pd.to_numeric(df["criterion_id"], errors="coerce").fillna(0).astype(int)
	df["goal_id"] = pd.to_numeric(df["goal_id"], errors="coerce").fillna(0).astype(int)
	df["conversions"] = pd.to_numeric(df["conversions"], errors="coerce").fillna(0).astype(float)

	df["device"] = df["device"].fillna("UNKNOWN")
	df["ad_network_type"] = df["ad_network_type"].fillna("UNKNOWN")
	df["location_of_presence_name"] = df["location_of_presence_name"].fillna("")
	df["targeting_location_name"] = df["targeting_location_name"].fillna("")
	df["age"] = df["age"].fillna("")
	df["gender"] = df["gender"].fillna("")

	# ✅ Дедуп/агрегация по уникальному ключу conv-таблицы
	pk_cols = [
		"date",
		"account_id",
		"campaign_id",
		"adgroup_id",
		"criterion_id",
		"device",
		"ad_network_type",
		"location_of_presence_name",
		"targeting_location_name",
		"age",
		"gender",
		"goal_id",
	]

	df = df.groupby(pk_cols, as_index=False).agg({
		"client_login": "first",
		"conversions": "sum",
	})

	print("Conv rows after dedup:", len(df))

	# ✅ Жёстко фиксируем порядок колонок под INSERT
	cols = [
		"date",
		"account_id",
		"client_login",
		"campaign_id",
		"adgroup_id",
		"criterion_id",
		"device",
		"ad_network_type",
		"location_of_presence_name",
		"targeting_location_name",
		"age",
		"gender",
		"goal_id",
		"conversions",
	]
	df = df[cols]

	rows = [
		tuple(r)
		for r in df.itertuples(index=False, name=None)
	]

	sql = """
	INSERT INTO direct_daily_goal_conv_fact (
		date,
		account_id,
		client_login,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender,
		goal_id,
		conversions
	)
	VALUES %s
	ON CONFLICT (
		date,
		account_id,
		campaign_id,
		adgroup_id,
		criterion_id,
		device,
		ad_network_type,
		location_of_presence_name,
		targeting_location_name,
		age,
		gender,
		goal_id
	)
	DO UPDATE SET
		conversions = EXCLUDED.conversions,
		updated_at = now()
	"""

	with conn.cursor() as cur:
		execute_values(cur, sql, rows, page_size=5000)

	conn.commit()

	return len(rows)