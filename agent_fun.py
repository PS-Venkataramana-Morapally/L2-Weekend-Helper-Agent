import asyncio
import json
import sys
from typing import Dict, Any, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from ollama import chat


# ---------------- CONFIG ----------------
MODEL = "mistral:7b"  # Make this configurable if needed


# ---------------- SYSTEM PROMPT ----------------
SYSTEM = """You are a cheerful weekend helper.

You have access to external tools.
You MUST use tools to get real data.
You are NOT allowed to invent tool results.

Rules:
1. If information is missing, call the correct tool.
2. Call ONLY ONE tool at a time.
3. After a tool call, wait for the tool result.
4. When all required data is collected, write a FRIENDLY, HUMAN, PLAIN-TEXT response.
5. DO NOT return JSON, lists, or action objects in the final answer.

Tool call format (ONLY this):
{"action":"tool_name","args":{...}}

Final answer format (ONLY this):
{"action":"final","answer":"<plain English text>"}"""


# ---------------- LLM (SAFE) ----------------
def llm_json(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Safe LLM call:
    - If model returns valid JSON → parse it
    - Otherwise → treat as final answer (fallback)
    """
    try:
        resp = chat(
            model=MODEL,
            messages=messages,
            options={"temperature": 0.2},
        )
        txt = resp["message"]["content"].strip()
    except Exception as e:
        return {
            "action": "final",
            "answer": f"Sorry, I had trouble reaching my brain: {e}"
        }

    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        # Not valid JSON → assume it's a final answer
        return {
            "action": "final",
            "answer": txt
        }


# ---------------- OUTPUT SANITIZER ----------------
def to_plain_text(answer: Any) -> str:
    """
    Convert final answer to clean plain text.
    Per system rules, only strings should arrive here.
    """
    if isinstance(answer, str):
        return answer.strip()
    return str(answer).strip()  # Fallback (should not happen in correct flow)


# ---------------- TOOL RESULT SUMMARIZER ----------------
def summarize_tool_result(tool_name: str, payload: str) -> str:
    """
    Convert raw tool output into a human-readable summary for chat history.
    Assumes tool returns a JSON string in .text.
    """
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        # If not JSON, treat as raw string
        return f"The '{tool_name}' tool returned: {payload}"

    if tool_name == "weather":
        desc = data.get("description", "unknown conditions")
        temp = data.get("temperature", "??")
        return f"The current weather is {desc} with a temperature of {temp}°C."
    
    elif tool_name == "book":
        title = data.get("title", "a great book")
        author = data.get("author", "an author")
        return f"I found a book: '{title}' by {author}."
    
    elif tool_name == "joke":
        joke_text = data.get("joke", "Why don't skeletons fight each other? They don't have the guts!")
        return f"Here's a joke: {joke_text}"
    
    elif tool_name == "dog":
        return "I fetched a cute dog picture for you! 🐶"
    
    elif tool_name == "trivia":
        question = data.get("question", "What is the meaning of life?")
        return f"Trivia question: {question}"
    
    else:
        # Generic fallback
        return f"Tool '{tool_name}' returned: {json.dumps(data)}"


# ---------------- MAIN ----------------
async def main():
    server_path = sys.argv[1] if len(sys.argv) > 1 else "server_fun.py"

    async with stdio_client(
        StdioServerParameters(command="python", args=[server_path])
    ) as (r_in, w_out):

        async with ClientSession(r_in, w_out) as session:
            await session.initialize()

            tools = (await session.list_tools()).tools
            tool_index = {t.name: t for t in tools}
            print("Connected tools:", list(tool_index.keys()))

            history: List[Dict[str, str]] = [
                {"role": "system", "content": SYSTEM}
            ]

            while True:
                user_input = input("You: ").strip()
                if not user_input or user_input.lower() in {"exit", "quit"}:
                    break

                history.append({"role": "user", "content": user_input})

                # -------- SPECIAL TRIVIA HANDLING (optional) --------
                if "trivia" in user_input.lower():
                    try:
                        result = await session.call_tool("trivia", {})
                        payload = (
                            result.content[0].text
                            if result.content and hasattr(result.content[0], "text")
                            else "{}"
                        )
                        data = json.loads(payload)
                        
                        print("\nAgent:")
                        print("🧠 Trivia Question:")
                        print(data.get("question", "No question received."))

                        choices = data.get("incorrect_answers", [])
                        if data.get("correct_answer"):
                            choices.append(data["correct_answer"])
                        choices = list(set(choices))  # dedupe just in case

                        for i, c in enumerate(choices, 1):
                            print(f"{i}. {c}")

                        # Add to history so conversation can continue
                        summary = summarize_tool_result("trivia", payload)
                        history.append({"role": "user", "content": f"[Tool Result] {summary}"})
                    except Exception as e:
                        error_msg = f"Oops! Trivia failed: {e}"
                        print(f"\nAgent: {error_msg}")
                        history.append({"role": "assistant", "content": error_msg})
                    continue
                # -------- END TRIVIA --------

                responded = False
                for step in range(8):  # Max 8 steps to avoid infinite loops
                    decision = llm_json(history)

                    # ---- FINAL ANSWER ----
                    if decision.get("action") == "final":
                        plain = to_plain_text(decision.get("answer", ""))
                        print("\nAgent:\n" + plain)
                        history.append({"role": "assistant", "content": plain})
                        responded = True
                        break

                    # ---- TOOL CALL ----
                    tname = str(decision.get("action", "")).strip()
                    args = decision.get("args", {})

                    if not tname or tname not in tool_index:
                        error_msg = f"Unknown tool: {tname}"
                        print(f"\nAgent: {error_msg}")
                        history.append({"role": "assistant", "content": error_msg})
                        responded = True
                        break

                    # Call tool with error handling
                    try:
                        result = await session.call_tool(tname, args)
                    except Exception as e:
                        error_msg = f"Tool '{tname}' failed: {e}"
                        print(f"\nAgent: {error_msg}")
                        history.append({"role": "user", "content": f"[Tool Error] {error_msg}"})
                        continue  # Let LLM react to error

                    # Extract payload safely
                    if result.content and hasattr(result.content[0], "text"):
                        payload = result.content[0].text
                    else:
                        payload = json.dumps(result.model_dump(), ensure_ascii=False)

                    # Summarize for history
                    summary = summarize_tool_result(tname, payload)
                    history.append({"role": "user", "content": f"[Tool Result] {summary}"})

                # If max steps reached without final answer
                if not responded:
                    msg = "I tried several steps but couldn't finish your request. Could you rephrase?"
                    print(f"\nAgent: {msg}")
                    history.append({"role": "assistant", "content": msg})


# ---------------- ENTRY ----------------
if __name__ == "__main__":
    asyncio.run(main())