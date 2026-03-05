import os
import requests
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


BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_message(text):

	url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

	payload = {
		"chat_id": CHAT_ID,
		"text": text,
		"parse_mode": "Markdown"
	}

	requests.post(url, json=payload)


def main():

	conn = get_conn()
	cur = conn.cursor()

	cur.execute("""
	SELECT
		id,
		type,
		entity_type,
		entity_id,
		impact_rub,
		title,
		recommendation
	FROM insights
	WHERE status='new'
	ORDER BY impact_rub DESC
	LIMIT 20
	""")

	rows = cur.fetchall()

	if not rows:
		print("No new insights")
		return

	message = "🤖 *AI Optimizer Report*\n\n"

	for r in rows:

		id, type, entity_type, entity_id, impact, title, rec = r

		message += f"⚠ *{title}*\n"
		message += f"Entity: `{entity_id}`\n"
		message += f"Impact: {impact:.0f} ₽\n"
		message += f"{rec}\n\n"

	send_message(message)

	ids = [r[0] for r in rows]

	cur.execute("""
	UPDATE insights
	SET status='sent'
	WHERE id = ANY(%s)
	""", (ids,))

	conn.commit()

	cur.close()
	conn.close()


if __name__ == "__main__":
	main()