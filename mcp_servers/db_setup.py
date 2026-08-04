"""
Run this ONCE to create crm.db with fake data.
This is in-memory _FAKE_DB (fake data for testing), and now it's a real
file on disk that persists between runs and that the MCP server reads/writes
independently of any Python process.
"""
 
import sqlite3
from pathlib import Path
 
DB_PATH = Path(__file__).parent / "crm.db"
 
SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL
);
 
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES accounts(customer_id)
);
 
CREATE TABLE IF NOT EXISTS refunds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id TEXT NOT NULL,
    amount REAL NOT NULL,
    reason TEXT
);
"""
 
FAKE_CUSTOMERS = [
    ("cust_001", "Jane Doe",     "jane@example.com"),
    ("cust_002", "Sam Lee",      "sam@example.com"),
    ("cust_003", "Priya Patel",  "priya@example.com"),
    ("cust_004", "Miguel Ruiz",  "miguel@example.com"),
    ("cust_005", "Wei Zhang",    "wei@example.com"),
    ("cust_006", "Aisha Khan",   "aisha@example.com"),
    ("cust_007", "Tom Baker",    "tom@example.com"),
    ("cust_008", "Nora Silva",   "nora@example.com"),
    ("cust_009", "Leo Fischer",  "leo@example.com"),
    ("cust_010", "Grace Kim",    "grace@example.com"),
    ("cust_011", "Omar Haddad",  "omar@example.com"),
    ("cust_012", "Ana Costa",    "ana@example.com"),
    ("cust_013", "David Cohen",  "david@example.com"),
    ("cust_014", "Fatima Noor",  "fatima@example.com"),
    ("cust_015", "Ben Carter",   "ben@example.com"),
]
 
FAKE_INVOICES = [
    ("inv_1001", "cust_001", 29.99,  "paid"),
    ("inv_1002", "cust_002", 199.00, "failed"),
    ("inv_1003", "cust_003", 49.50,  "paid"),
    ("inv_1004", "cust_004", 15.00,  "paid"),
    ("inv_1005", "cust_005", 89.99,  "refunded"),
    ("inv_1006", "cust_006", 29.99,  "paid"),
    ("inv_1007", "cust_007", 300.00, "failed"),
    ("inv_1008", "cust_008", 12.99,  "paid"),
    ("inv_1009", "cust_009", 75.00,  "paid"),
    ("inv_1010", "cust_010", 29.99,  "paid"),
    ("inv_1011", "cust_011", 199.00, "paid"),
    ("inv_1012", "cust_012", 9.99,   "paid"),
    ("inv_1013", "cust_013", 49.50,  "failed"),
    ("inv_1014", "cust_014", 29.99,  "paid"),
    ("inv_1015", "cust_015", 120.00, "paid"),
]
 
 
def seed():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)
    conn.executemany(
        "INSERT OR REPLACE INTO accounts (customer_id, name, email) VALUES (?, ?, ?)",
        FAKE_CUSTOMERS,
    )
    conn.executemany(
        "INSERT OR REPLACE INTO invoices (invoice_id, customer_id, amount, status) VALUES (?, ?, ?, ?)",
        FAKE_INVOICES,
    )
    conn.commit()
    conn.close()
    print(f"Seeded {DB_PATH} with {len(FAKE_CUSTOMERS)} customers and {len(FAKE_INVOICES)} invoices.")
 
 
if __name__ == "__main__":
    seed()
 
