#  Weekend Helper Agent
A cheerful AI assistant that uses real tools (weather, jokes, books, dog pics, trivia) to help you plan your weekend!

Built with:
- **Ollama** (local LLM: `mistral:7b`)
- **MCP (Model Context Protocol)** for tool integration
- Python asyncio for async tool calling

## 🛠️ Requirements
## Prerequisites
- Python 3.10+
 ## Installation
1. Clone the repository:
git clone https://github.com/PS-Venkataramana-Morapally/L2-Weekend-Helper-Agent.git
## Create and activate a virtual environment
1.python -m venv venv
## Activate the virtual environment
2.venv\Scripts\activate

# 2) Install libraries
pip install "mcp>=1.2" requests ollama

# 3) Install Ollama (from ollama.com), then pull a small model
ollama pull mistral:7b
# Executing the scripts Start the agent (it will spawn the server via stdio)
Execute the following command:
python agent_fun.py

# Chat with your agent
YOU: Plan a cozy Saturday in New York at (40.7128, -74.0060). Include the current weather, 2 book ideas about mystery, one joke, and a dog pic.

YOU: What’s the temperature now at (37.7749, -122.4194)? Keep it brief.

YOU: Give me one trivia question.
