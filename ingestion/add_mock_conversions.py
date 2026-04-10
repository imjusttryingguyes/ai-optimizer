"""
Add synthetic/mock conversion data to direct_api_detail

Uses realistic conversion rates (2-5% from clicks) for testing purposes.
When real conversion data arrives from API, this can be replaced.
"""

import psycopg2
import random
import json
from datetime import datetime

CONFIG = {
    "goal_ids": [151735153, 201395020, 282210833, 337720190, 339151905, 465584771, 465723370, 303059688, 258143758],
    "conversion_rate_range": (0.02, 0.05),  # 2-5% of clicks
    "db_host": "localhost",
    "db_port": 5432,
    "db_name": "aiopt",
    "db_user": "aiopt",
    "db_password": "strongpassword123",
}


def generate_mock_conversions(clicks: int, goal_ids: list, rate_range=(0.02, 0.05)) -> dict:
    """
    Generate realistic mock conversions
    
    Args:
        clicks: Number of clicks for this record
        goal_ids: List of goal IDs
        rate_range: Tuple of (min_rate, max_rate) for conversion
    
    Returns:
        Dict with structure: {"151735153": {"AUTO": 5}, ...}
    """
    conversions = {}
    
    for goal_id in goal_ids:
        # Random conversion rate between 2-5%
        rate = random.uniform(rate_range[0], rate_range[1])
        
        # Calculate conversions (ensure at least probability > 0 generates 1)
        conv_count = max(0, int(round(clicks * rate)))
        
        if conv_count > 0:
            conversions[str(goal_id)] = {"AUTO": conv_count}
    
    return conversions


def update_conversions():
    """Update all records in direct_api_detail with mock conversions"""
    
    conn = psycopg2.connect(
        host=CONFIG["db_host"],
        port=CONFIG["db_port"],
        database=CONFIG["db_name"],
        user=CONFIG["db_user"],
        password=CONFIG["db_password"],
    )
    
    cur = conn.cursor()
    
    print("=" * 80)
    print("Adding Mock Conversions to direct_api_detail")
    print("=" * 80)
    
    # Get all rows that need conversions
    cur.execute("""
        SELECT id, clicks
        FROM direct_api_detail
        ORDER BY id
    """)
    
    rows = cur.fetchall()
    print(f"\n📊 Processing {len(rows)} records...")
    
    # Update each row with mock conversions
    updated = 0
    total_conversions = 0
    
    for row_id, clicks in rows:
        if clicks is None or clicks == 0:
            # No clicks = no conversions
            conversions = {}
        else:
            conversions = generate_mock_conversions(clicks, CONFIG["goal_ids"])
            if conversions:
                total_conversions += sum(
                    v.get("AUTO", 0) for v in conversions.values()
                )
        
        # Update the record
        cur.execute("""
            UPDATE direct_api_detail
            SET conversions = %s
            WHERE id = %s
        """, (json.dumps(conversions), row_id))
        
        updated += 1
        if updated % 10000 == 0:
            print(f"  ✓ Updated {updated}/{len(rows)} records...")
    
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"\n✅ COMPLETED")
    print(f"  Updated {updated} records")
    print(f"  Total conversions added: {total_conversions:,}")
    
    # Verify
    conn = psycopg2.connect(
        host=CONFIG["db_host"],
        port=CONFIG["db_port"],
        database=CONFIG["db_name"],
        user=CONFIG["db_user"],
        password=CONFIG["db_password"],
    )
    
    cur = conn.cursor()
    cur.execute("""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(CASE WHEN conversions IS NOT NULL AND conversions::text != '{}' THEN 1 END) as with_conversions,
            SUM((conversions->>key)::text::int) as total_conv
        FROM direct_api_detail,
        LATERAL jsonb_object_keys(conversions) as key
        WHERE conversions IS NOT NULL AND conversions::text != '{}'
    """)
    
    total_rows, with_conv, total_conv = cur.fetchone()
    print(f"\n📈 Verification:")
    print(f"  Rows with conversions: {with_conv if with_conv else 0:,}")
    print(f"  Total conversions: {total_conv if total_conv else 0:,}")
    
    cur.close()
    conn.close()


if __name__ == "__main__":
    print("\n⚠️  This will add MOCK/SYNTHETIC conversion data for testing purposes!")
    print("When real conversion data arrives from API, this will need to be replaced.\n")
    
    confirm = input("Continue? (yes/no): ").lower()
    if confirm == "yes":
        update_conversions()
    else:
        print("Cancelled.")
