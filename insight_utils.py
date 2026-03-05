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
	account_id: str,
	type: str,
	entity_type: str,
	entity_id: str | None,
	severity: float | None,
	impact_rub: float | None,
	title: str | None,
	description: str | None,
	recommendation: str | None,
	evidence: dict | None,
	confidence: float = 1.0,
):
	conn = get_conn()
	cur = conn.cursor()

	cur.execute(
		"""
		INSERT INTO insights (
			account_id,
			type,
			entity_type,
			entity_id,
			severity,
			impact_rub,
			confidence,
			title,
			description,
			recommendation,
			evidence
		)
		VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
		""",
		(
			account_id,
			type,
			entity_type,
			entity_id,
			float(severity) if severity is not None else None,
			float(impact_rub) if impact_rub is not None else None,
			float(confidence) if confidence is not None else None,
			title,
			description,
			recommendation,
			json.dumps(evidence or {}, ensure_ascii=False),
		),
	)

	conn.commit()
	cur.close()
	conn.close()