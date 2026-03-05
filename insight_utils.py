import os
import json
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


def insert_insight(
	account_id,
	type,
	entity_type,
	entity_id,
	severity,
	impact_rub,
	title,
	description,
	recommendation,
	evidence
):
	conn = get_conn()
	cur = conn.cursor()

	cur.execute("""
	INSERT INTO insights (
		account_id,
		type,
		entity_type,
		entity_id,
		severity,
		impact_rub,
		title,
		description,
		recommendation,
		evidence
	)
	VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
	""", (
		account_id,
		type,
		entity_type,
		entity_id,
		severity,
		impact_rub,
		title,
		description,
		recommendation,
		json.dumps(evidence)
	))

	conn.commit()
	cur.close()
	conn.close()