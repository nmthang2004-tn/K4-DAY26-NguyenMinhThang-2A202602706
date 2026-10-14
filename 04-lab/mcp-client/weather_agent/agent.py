"""
Weather Agent - Connects to Remote MCP Server on Cloud Run
Successfully connects to custom MCP HTTP endpoints!
"""
from google.adk import Agent
from google.adk.models import Gemini
from google.genai import Client, types
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StreamableHTTPConnectionParams
import logging
import os
import ssl
from functools import cached_property
from pathlib import Path
from dotenv import load_dotenv
from pydantic import PrivateAttr

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(ENV_FILE, encoding="utf-8-sig")
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError(f"Set GEMINI_API_KEY in {ENV_FILE} or the environment.")
# ADK uses GOOGLE_API_KEY; users only configure GEMINI_API_KEY in .env.
os.environ["GOOGLE_API_KEY"] = gemini_api_key

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODELS = (
    "gemini-3.1-flash-lite", "gemini-3.6-flash-lite", "gemini-3.6-flash",
    "gemini-3.7-flash", "gemini-3.8-flash",
)


class SystemTrustedGemini(Gemini):
    """Use OS certificates for the Gemini HTTPS client, including async calls."""

    @cached_property
    def api_client(self) -> Client:
        ssl_context = ssl.create_default_context()
        return Client(
            api_key=gemini_api_key,
            vertexai=False,
            http_options=types.HttpOptions(
                client_args={"verify": ssl_context},
                async_client_args={"verify": ssl_context},
                timeout=60_000,
                retry_options=types.HttpRetryOptions(attempts=1),
            ),
        )


class FallbackGemini(SystemTrustedGemini):
    """Retry a model request without rerunning tools or publishing partial failures."""

    _workers: dict = PrivateAttr(default_factory=dict)

    async def generate_content_async(self, llm_request, stream=False):
        for model_name in dict.fromkeys((self.model, *FALLBACK_MODELS)):
            try:
                if model_name not in self._workers:
                    self._workers[model_name] = SystemTrustedGemini(model=model_name)
                request = llm_request.model_copy(deep=True)
                request.model = model_name
                responses = []
                async for response in self._workers[model_name].generate_content_async(
                    request, stream=stream
                ):
                    if response.error_code:
                        raise RuntimeError(f"Model response error: {response.error_code}")
                    responses.append(response)
                if not responses:
                    raise RuntimeError("Model returned no response")
            except Exception as error:
                logger.warning("Model %s failed (%s); trying next fallback",
                               model_name, type(error).__name__)
                continue
            logger.info("Model used: %s", model_name)
            for response in responses:
                yield response
            return
        raise RuntimeError("Tất cả model chính và fallback đều thất bại.")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mặc định: server chạy local. Deploy lên Cloud Run thì đặt MCP_SERVER_URL trong .env
# (ví dụ: https://<service>.run.app/mcp). verify_setup.py đọc cùng biến này.
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

logger.info(f"🌐 Initializing weather agent with remote MCP server")
logger.info(f"📡 MCP Server: {MCP_SERVER_URL}")

try:
    # Create connection parameters for the remote MCP server
    connection_params = StreamableHTTPConnectionParams(
        url=MCP_SERVER_URL,
        timeout=30.0,  # Increased timeout for Cloud Run cold starts
    )
    
    # Create the MCP toolset - this will connect to the remote server
    logger.info("🔌 Connecting to MCP server...")
    weather_tools = McpToolset(
        connection_params=connection_params,
    )
    logger.info("✅ MCP toolset created successfully")
    
    # Create the agent with remote MCP tools
    root_agent = Agent(
        name="weather_agent",
        model=FallbackGemini(model=MODEL),
        instruction=(
            "Trả lời hoàn toàn bằng tiếng Việt. Luôn dùng tool để lấy thời tiết thật; "
            "không tự bịa dữ liệu. Với thời tiết hiện tại, nêu nhiệt độ, cảm giác như, "
            "độ ẩm, UV và thời điểm cập nhật. Với dự báo, nêu ngày, nhiệt độ cao/thấp "
            "và khả năng mưa, tối đa 3 ngày. Nếu tool lỗi, nói rõ chưa lấy được dữ liệu."
        ),
        generate_content_config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
        tools=[weather_tools],
    )
    logger.info("✅ Weather agent initialized with remote MCP tools:")
    logger.info("   - get_current_weather(city)")
    logger.info("   - get_forecast(city, days)")
    logger.info("   - health_check()")
    logger.info("MCP toolset configured; discovery occurs when tools are requested.")
    
except Exception as e:
    logger.error(f"❌ Failed to connect to remote MCP server: {e}")
    logger.error(f"   Server URL: {MCP_SERVER_URL}")
    import traceback
    traceback.print_exc()
    
    # Create a fallback agent without tools
    logger.warning("⚠️  Creating fallback agent without MCP tools")
    root_agent = Agent(
        name="weather_agent",
        model=FallbackGemini(model=MODEL),
    )

