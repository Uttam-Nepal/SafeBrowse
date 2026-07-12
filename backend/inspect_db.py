"""
inspect_db.py — quick peek at what's actually stored in safebrowse.db.
Run from the backend folder, with (venv) active:
    python inspect_db.py
"""

import sqlite3

conn = sqlite3.connect("safebrowse.db")
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("=" * 60)
print("USERS")
print("=" * 60)
cur.execute("SELECT id, email, created_at, is_active FROM users")
users = cur.fetchall()
if not users:
    print("(no users yet)")
for u in users:
    print(f"  #{u['id']}  {u['email']}  created={u['created_at']}  active={u['is_active']}")

print()
print("=" * 60)
print("CHECK HISTORY")
print("=" * 60)
cur.execute("""
    SELECT check_history.id, url, model, verdict, confidence, created_at, user_id
    FROM check_history
    ORDER BY created_at DESC
    LIMIT 50
""")
rows = cur.fetchall()
if not rows:
    print("(no checks logged yet)")
for r in rows:
    who = f"user #{r['user_id']}" if r['user_id'] else "guest"
    print(f"  #{r['id']}  [{who}]  {r['verdict']:7s} {r['confidence']:.2f}  {r['model']:10s}  {r['url'][:50]}")

conn.close()