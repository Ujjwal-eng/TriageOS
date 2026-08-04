"""
MCP server exposing search_kb(query) — retrieval over markdown help articles.
 
This uses simple keyword-overlap scoring, not real embeddings, so it runs
with zero extra downloads. It's a legitimate stand-in for a resume project,
but if we want to upgrade it later: swap `_score()` for cosine similarity
over embeddings from `sentence-transformers` (e.g. all-MiniLM-L6-v2) — the
rest of this file stays the same.
 
Add more articles by just dropping more .md files into kb_articles/ — no
code changes needed. Aim for 20-30 for the real project; 3 are here as a
starting demo.
"""
 
import re
from pathlib import Path
from mcp.server.fastmcp import FastMCP
 
ARTICLES_DIR = Path(__file__).parent / "kb_articles"
 
mcp = FastMCP("knowledge-base")
 
 
def _load_articles() -> list[dict]:
    articles = []
    for path in ARTICLES_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        # First line starting with "# " is treated as the title.
        title_match = re.search(r"^#\s+(.+)$", text, re.MULTILINE)
        title = title_match.group(1) if title_match else path.stem
        articles.append({"title": title, "body": text, "filename": path.name})
    return articles
 
 
_ARTICLES = _load_articles()
 
 
def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))
 
 
def _score(query: str, article: dict) -> int:
    """Simple word-overlap score: how many query words appear in the article."""
    query_words = _tokenize(query)
    article_words = _tokenize(article["title"] + " " + article["body"])
    return len(query_words & article_words)
 
 
@mcp.tool()
def search_kb(query: str, top_k: int = 2) -> list[dict]:
    """Search the knowledge base for help articles relevant to a query.
    Returns the top matching articles with title and a short snippet."""
    scored = [(_score(query, a), a) for a in _ARTICLES]
    scored = [(s, a) for s, a in scored if s > 0]
    scored.sort(key=lambda pair: pair[0], reverse=True)
 
    if not scored:
        return [{"result": "no matching articles found"}]
 
    results = []
    for score, article in scored[:top_k]:
        snippet = article["body"].strip().split("\n\n")[1][:200] \
            if "\n\n" in article["body"] else article["body"][:200]
        results.append({
            "title": article["title"],
            "snippet": snippet,
            "relevance_score": score,
        })
    return results
 
@mcp.tool()
def check_service_status() -> dict:
    """Check current status of the service (e.g. active outages).
    Simulated — always returns operational in this demo. A real version
    would call an internal status API or a page like status.company.com."""
    return {"status": "operational"}
 
 
_DEBUG_TICKETS_LOG = Path(__file__).parent / "debug_tickets.txt"
 
 
@mcp.tool()
def create_debug_ticket(description: str) -> dict:
    """File an internal engineering ticket for a bug that needs follow-up.
    Logs to a file in this demo instead of hitting a real issue tracker."""
    with open(_DEBUG_TICKETS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{description}\n")
    return {"ticket_id": f"dbg_{sum(1 for _ in open(_DEBUG_TICKETS_LOG))}",
             "description": description}
 
if __name__ == "__main__":
    # Quick manual sanity check before running as a real MCP server.
    print(f"Loaded {len(_ARTICLES)} articles from {ARTICLES_DIR}")
    print(search_kb("app crashes uploading photo"))
    mcp.run()
 
