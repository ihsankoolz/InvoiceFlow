"""
Seed script for InvoiceFlow development/testing.
Run once after `docker-compose up` to populate test accounts.

Usage:
    python scripts/seed.py
"""

import pymysql

# Pre-hashed bcrypt hash for "testing1"
PASSWORD_HASH = "$2b$12$rYy4u91O8cfmGv3EbZwH0eKvEO8dhfgbHvUI7pU/OHyqE2JqxuNEO"

USERS = [
    # Sellers
    {
        "email": "tan.michelletingyee@gmail.com",
        "full_name": "Michelle Tan",
        "role": "SELLER",
        "uen": "202056789A",
    },
    {
        "email": "seller2@test.com",
        "full_name": "Seller Two",
        "role": "SELLER",
        "uen": "202056790B",
    },
    {
        "email": "seller3@test.com",
        "full_name": "Seller Three",
        "role": "SELLER",
        "uen": "202056791C",
    },
    # Investors
    {
        "email": "michelletan.2024@smu.edu.sg",
        "full_name": "Michelle Tan (Investor)",
        "role": "INVESTOR",
        "uen": None,
    },
    {
        "email": "investor2@test.com",
        "full_name": "Investor Two",
        "role": "INVESTOR",
        "uen": None,
    },
    {
        "email": "investor3@test.com",
        "full_name": "Investor Three",
        "role": "INVESTOR",
        "uen": None,
    },
]


def seed():
    conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="password",
        database="user_db",
    )
    try:
        with conn.cursor() as cur:
            inserted = 0
            skipped = 0
            for u in USERS:
                cur.execute("SELECT id FROM users WHERE email = %s", (u["email"],))
                if cur.fetchone():
                    print(f"  SKIP  {u['email']} (already exists)")
                    skipped += 1
                    continue
                cur.execute(
                    """
                    INSERT INTO users (email, password_hash, full_name, role, uen)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (u["email"], PASSWORD_HASH, u["full_name"], u["role"], u["uen"]),
                )
                print(f"  OK    {u['email']} ({u['role']})")
                inserted += 1
        conn.commit()
        print(f"\nDone — {inserted} inserted, {skipped} skipped.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
