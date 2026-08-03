"""
A real MCP server exposing the CRM tools billing and account agents
use. 
 
Notice this file has NO knowledge of LangGraph, agents, prompts, or risk
rules. It only knows about the CRM. That separation is the whole point of
MCP: this server could be reused by a completely different AI app later.
"""
 
import sqlite3
from pathlib import Path
from mcp.server.fastmcp import FastMCP
 
DB_PATH = Path(__file__).parent / "crm.db"
 
mcp = FastMCP("crm")
 
 
def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
 
 
@mcp.tool()
def get_invoice(customer_id: str) -> dict:
    """Look up the most recent invoice for a customer."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT invoice_id, amount, status FROM invoices "
        "WHERE customer_id = ? ORDER BY invoice_id DESC LIMIT 1",
        (customer_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {"error": "not found"}
 
 
@mcp.tool()
def check_payment_status(customer_id: str) -> dict:
    """Check whether a customer's last payment succeeded, failed, or was refunded."""
    inv = get_invoice(customer_id)
    if "error" in inv:
        return inv
    return {"status": inv["status"]}
 
 
@mcp.tool()
def issue_refund(customer_id: str, amount: float, reason: str) -> dict:
    """Issue a refund to a customer. Amount is in INR. Records it permanently."""
    conn = _get_conn()
    conn.execute(
        "INSERT INTO refunds (customer_id, amount, reason) VALUES (?, ?, ?)",
        (customer_id, amount, reason),
    )
    conn.commit()
    conn.close()
    return {"refunded": amount, "customer_id": customer_id, "reason": reason}
 
 
@mcp.tool()
def get_account_info(customer_id: str) -> dict:
    """Look up basic account info (name, email) for a customer."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT customer_id, name, email FROM accounts WHERE customer_id = ?",
        (customer_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {"error": "not found"}
 
 
@mcp.tool()
def update_email(customer_id: str, new_email: str) -> dict:
    """Update the email address on file for a customer."""
    conn = _get_conn()
    conn.execute(
        "UPDATE accounts SET email = ? WHERE customer_id = ?",
        (new_email, customer_id),
    )
    conn.commit()
    conn.close()
    return {"customer_id": customer_id, "new_email": new_email}
 
 
@mcp.tool()
def reset_password(customer_id: str) -> dict:
    """Trigger a password reset for a customer. (Simulated — no real email sent here;
    that's the email server's job, called separately.)"""
    return {"customer_id": customer_id, "reset_sent": True}
 
 
@mcp.tool()
def delete_account(customer_id: str) -> dict:
    """Permanently delete a customer account. Irreversible."""
    conn = _get_conn()
    conn.execute("DELETE FROM accounts WHERE customer_id = ?", (customer_id,))
    conn.commit()
    conn.close()
    return {"customer_id": customer_id, "deleted": True}
 
 
if __name__ == "__main__":
    mcp.run()
 
