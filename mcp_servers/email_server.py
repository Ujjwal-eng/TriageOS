"""
MCP server exposing send_email(to, subject, body).
Logs to a file instead of actually sending — this is what the escalation
and resolution nodes will call to "notify" the customer.
"""
 
from datetime import datetime, timezone
from pathlib import Path
from mcp.server.fastmcp import FastMCP
 
LOG_PATH = Path(__file__).parent / "email_log.txt"
 
mcp = FastMCP("email")
 
 
@mcp.tool()
def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email notification to a customer. In this demo, it logs to
    a file instead of actually sending — swap this for a real email API
    (e.g. SendGrid, SES) for a live deployment."""
    timestamp = datetime.now(timezone.utc).isoformat()
    entry = (
        f"--- {timestamp} ---\n"
        f"To: {to}\n"
        f"Subject: {subject}\n"
        f"Body: {body}\n\n"
    )
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(entry)
    return {"status": "sent", "to": to, "logged_at": str(LOG_PATH)}
 
 
if __name__ == "__main__":
    mcp.run()
 
