#!/usr/bin/env python3
"""Initialize Phase 4 database schema."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('/opt/ai-optimizer/.env')

DB_HOST = os.getenv('DB_HOST')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

conn = psycopg2.connect(
    host=DB_HOST,
    port=DB_PORT,
    user=DB_USER,
    password=DB_PASSWORD,
    database=DB_NAME
)

with open('/opt/phase4/storage/schema.sql', 'r') as f:
    schema = f.read()

try:
    with conn.cursor() as cur:
        cur.execute(schema)
        conn.commit()
    print("✅ Database schema initialized successfully")
except Exception as e:
    print(f"❌ Schema initialization failed: {e}")
    conn.rollback()
finally:
    conn.close()
