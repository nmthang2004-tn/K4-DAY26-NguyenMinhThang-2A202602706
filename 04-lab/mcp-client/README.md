# Weather Agent - Google ADK with MCP Server

AI agent built with **Google Agent Development Kit (ADK)** that uses tools from a local **MCP server** via Streamable HTTP transport.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│   User Browser  │ ───> │  ADK Web UI      │ ───> │  Weather Agent      │
│   localhost:8000│      │  (Google ADK)    │      │  (Agent with MCP)   │
└─────────────────┘      └──────────────────┘      └─────────────────────┘
                                                             │
                                                             │ Streamable HTTP
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  MCP Server         │
                                                   │  localhost:8085/mcp │
                                                   │  FastMCP + Tools    │
                                                   └─────────────────────┘
                                                             │
                                                             ▼
                                                   ┌─────────────────────┐
                                                   │  WeatherAPI.com     │
                                                   └─────────────────────┘
```

## Features

- **Remote MCP Tools**: Connects to MCP server via Streamable HTTP
- **3 Weather Tools**:
  - `get_current_weather(city)` - Real-time weather conditions
  - `get_forecast(city, days)` - Weather forecast up to 3 days
  - `health_check()` - Server health verification
- **Web Interface**: UI via ADK web
- **Streaming Responses**: Real-time AI responses

## Quick Start

### 1. Start the MCP Server

```bash
cd ../mcp-server
# Set WEATHERAPI_KEY in the repository root .env
uv run python weather.py
```

### 2. Setup Environment

```bash
cd ../mcp-client

# Use .env.example as a template for the repository root .env.
# Set GEMINI_API_KEY and WEATHERAPI_KEY there.
# Gemini key: https://aistudio.google.com/apikey
```

### 3. Install Dependencies

```bash
uv sync
```

### 4. Run the Agent

```bash
uv run adk web
```

### 5. Use the Agent

1. Open browser: http://localhost:8000
2. Select `weather_agent` from dropdown
3. Ask questions like:
   - "What's the weather in Brisbane?"
   - "Give me a 3-day forecast for Tokyo"
   - "How's the weather in New York?"

## Project Structure

```
mcp-client/
├── weather_agent/
│   ├── agent.py           # Main agent with MCP connection
│   └── __init__.py
├── pyproject.toml
└── README.md
```

## Configuration

### Agent Configuration

In `weather_agent/agent.py`:

```python
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

connection_params = StreamableHTTPConnectionParams(
    url=MCP_SERVER_URL,
    timeout=30.0,
)

root_agent = Agent(
    name="weather_agent",
    model=FallbackGemini(model=MODEL),
    tools=[weather_tools],
)
```

## Troubleshooting

### Agent won't connect to MCP server

1. **404 errors**: MCP server is not running or wrong port
   - Ensure the MCP server is running on port 8085
   - Check `MCP_SERVER_URL` (env var / `.env`, default `http://localhost:8085/mcp`)

2. **405 errors**: Port conflict with another application
   - Check what's running on the port: `lsof -i :8085`
   - Change port in both server and client if needed

3. **Timeout errors**: Server not started
   - Start the MCP server first, then the ADK client

### Fallback Mode

If MCP connection fails, the agent runs in fallback mode without tools.
Fix the connection and restart ADK web.

## Environment Variables

Create `.env` at the repository root (next to `requirements.txt`):
```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
WEATHERAPI_KEY=your_weatherapi_key_here
MCP_SERVER_URL=http://localhost:8085/mcp
```

The agent maps `GEMINI_API_KEY` to `GOOGLE_API_KEY` for ADK. Both the server
and client load the root `.env` regardless of the current working directory.
Existing environment variables take precedence. Restart both processes after
changing the keys. Verify setup with `uv run python verify_setup.py`.

Set `GEMINI_MODEL` optionally; the agent defaults to `gemini-3.5-flash-lite`.
The `SystemTrustedGemini` class uses OS certificates for HTTPS to Gemini.
`FallbackGemini` tries the primary model first, then `gemini-3.1-flash-lite`,
`gemini-3.6-flash-lite`, `gemini-3.6-flash`, `gemini-3.7-flash`,
`gemini-3.8-flash` on model-request errors. Failed streamed output is discarded
before retrying; tool execution is not repeated by the fallback mechanism.
If every model fails, the error is reported. Unavailable models are skipped
when the API rejects them. The next request starts with the primary model again.
Verification opens a real MCP session, discovers the three expected tools
and calls `health_check`. An agent without tools fails verification.

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [MCP Specification](https://modelcontextprotocol.io/)
- [FastMCP GitHub](https://github.com/jlowin/fastmcp)
- [WeatherAPI](https://www.weatherapi.com/)
