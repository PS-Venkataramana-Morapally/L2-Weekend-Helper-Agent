from mcp.server.fastmcp import FastMCP
from typing import Dict, Any, List
import requests, html, anyio

mcp = FastMCP("FunTools")

# ---------- helper ----------
def _get(url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    return r.json()

# ---- Weather (Open-Meteo) ----
@mcp.tool()
async def get_weather(latitude: float, longitude: float) -> Dict[str, Any]:
    """Current weather at coordinates via Open-Meteo."""
    def call():
        return _get(
            "https://api.open-meteo.com/v1/forecast",
            {
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,weather_code,wind_speed_10m",
                "timezone": "auto",
            },
        )

    data = await anyio.to_thread.run_sync(call)
    return {"ok": True, "data": data.get("current", {})}

# ---- Book recs (Open Library) ----
@mcp.tool()
async def book_recs(topic: str, limit: int = 5) -> Dict[str, Any]:
    """Simple book suggestions for a topic via Open Library search."""
    def call():
        return _get(
            "https://openlibrary.org/search.json",
            {"q": topic, "limit": limit},
        )

    data = await anyio.to_thread.run_sync(call)

    picks: List[Dict[str, Any]] = []
    for d in data.get("docs", []):
        picks.append({
            "title": d.get("title"),
            "author": (d.get("author_name") or ["Unknown"])[0],
            "year": d.get("first_publish_year"),
            "work": d.get("key"),
        })

    return {"ok": True, "topic": topic, "results": picks}

# ---- Jokes (JokeAPI) ----
@mcp.tool()
async def random_joke() -> Dict[str, Any]:
    """Return a safe, single-line joke."""
    def call():
        return _get(
            "https://v2.jokeapi.dev/joke/Any",
            {"type": "single", "safe-mode": True},
        )

    data = await anyio.to_thread.run_sync(call)
    return {"ok": True, "joke": data.get("joke", "No joke found")}

# ---- Dog pic (Dog CEO) ----
@mcp.tool()
async def random_dog() -> Dict[str, Any]:
    """Return a random dog image URL."""
    def call():
        return _get("https://dog.ceo/api/breeds/image/random")

    data = await anyio.to_thread.run_sync(call)
    return {"ok": True, "image": data.get("message")}

# ---- Trivia (Open Trivia DB) ----
@mcp.tool()
async def trivia() -> Dict[str, Any]:
    """Return one multiple-choice trivia question."""
    def call():
        return _get(
            "https://opentdb.com/api.php",
            {"amount": 1, "type": "multiple"},
        )

    data = await anyio.to_thread.run_sync(call)
    results = data.get("results", [])
    if not results:
        return {"ok": False, "error": "no trivia"}

    q = results[0]
    return {
        "ok": True,
        "question": html.unescape(q["question"]),
        "choices": [
            html.unescape(x) for x in q["incorrect_answers"]
        ] + [html.unescape(q["correct_answer"])],
        "answer": html.unescape(q["correct_answer"]),
    }

if __name__ == "__main__":
    mcp.run()  # stdio MCP server
