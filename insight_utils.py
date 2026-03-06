import os
import json
import hashlib

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
	insight_date: str | None = None,
):
	conn = get_conn()
	cur = conn.cursor()

	impact_val = float(impact_rub) if impact_rub is not None else 0.0
	conf_val = float(confidence) if confidence is not None else 0.0
	freshness_score = 1.0

	evidence_json = json.dumps(evidence or {}, ensure_ascii=False, sort_keys=True)

	fingerprint_source = json.dumps({
		"type": type,
		"entity_type": entity_type,
		"entity_id": entity_id,
		"impact_rub": round(impact_val, 2),
		"confidence": round(conf_val, 4),
		"evidence": json.loads(evidence_json),
	}, ensure_ascii=False, sort_keys=True)

	fingerprint = hashlib.sha256(fingerprint_source.encode("utf-8")).hexdigest()

	WEIGHTS = {
	"RSYA_WASTE": 1.0,
	"CAMPAIGN_WASTE": 1.2,
	"SEGMENT_BAD_CR": 0.8,
	"BEST_PLACEMENT": 0.6,
	}

	business_weight = WEIGHTS.get(type, 1.0)

	priority = impact_val * conf_val * business_weight

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
			business_weight,
			priority,
			fingerprint,
			freshness_score,
			title,
			description,
			recommendation,
			evidence,
			insight_date,
			status,
			updated_at
		)
		VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,COALESCE(%s::date, CURRENT_DATE),'new',now())
		ON CONFLICT (account_id, type, entity_type, entity_id, insight_date)
		DO UPDATE SET
			severity = EXCLUDED.severity,
			impact_rub = EXCLUDED.impact_rub,
			confidence = EXCLUDED.confidence,
			business_weight = EXCLUDED.business_weight,
			priority = EXCLUDED.priority,
			fingerprint = EXCLUDED.fingerprint,
			freshness_score = EXCLUDED.freshness_score,
			title = EXCLUDED.title,
			description = EXCLUDED.description,
			recommendation = EXCLUDED.recommendation,
			evidence = EXCLUDED.evidence,
			status = CASE
				WHEN insights.fingerprint IS DISTINCT FROM EXCLUDED.fingerprint THEN 'new'
				ELSE insights.status
			END,
			updated_at = now()
		""",
		(
			account_id,
			type,
			entity_type,
			entity_id,
			float(severity) if severity is not None else None,
			impact_val,
			conf_val,
			business_weight,
			priority,
			fingerprint,
			freshness_score,
			title,
			description,
			recommendation,
			evidence_json,
			insight_date,
		),
	)

	conn.commit()
	cur.close()
	conn.close()