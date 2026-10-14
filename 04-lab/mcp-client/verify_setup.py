#!/usr/bin/env python3
"""
Verification script for Weather Agent setup
Checks if all components are configured correctly
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

CLIENT_DIR = Path(__file__).resolve().parent
ENV_FILE = CLIENT_DIR.parents[1] / ".env"

def check_environment():
    """Check if .env file exists and is configured"""
    print("🔍 Checking environment configuration...")
    
    load_dotenv(ENV_FILE, encoding="utf-8-sig")
    if not ENV_FILE.exists():
        print(f"⚠️  {ENV_FILE} not found; checking environment variables instead")

    configured = True
    for name in ("GEMINI_API_KEY", "WEATHERAPI_KEY"):
        value = os.getenv(name, "").strip()
        if not value or value.startswith("your_"):
            print(f"❌ {name} not configured; set it in {ENV_FILE}")
            configured = False
        else:
            print(f"✅ {name} configured")
    return configured

def check_dependencies():
    """Check if required packages are installed"""
    print("\n🔍 Checking dependencies...")
    
    required_packages = [
        ("google.adk", "Google ADK"),
        ("google.genai", "Google GenAI"),
        ("mcp", "MCP"),
        ("fastmcp", "FastMCP"),
        ("dotenv", "python-dotenv"),
        ("httpx", "httpx"),
    ]
    
    all_installed = True
    for package, name in required_packages:
        try:
            __import__(package)
            print(f"✅ {name}")
        except ImportError:
            print(f"❌ {name} not installed")
            all_installed = False
    
    if not all_installed:
        print("\n   Install with: uv sync")
        print("   Or: pip install google-adk google-genai mcp fastmcp python-dotenv httpx")
    
    return all_installed

def check_agent_structure():
    """Check if agent directory structure is correct"""
    print("\n🔍 Checking agent structure...")
    
    required_files = [
        "weather_agent/agent.py",
        "weather_agent/__init__.py",
    ]
    
    all_exist = True
    for file_path in required_files:
        path = CLIENT_DIR / file_path
        if path.exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} not found")
            all_exist = False
    
    return all_exist

def check_mcp_server():
    """Check if MCP server is accessible"""
    print("\n🔍 Checking MCP server connectivity...")

    # Cùng URL mà weather_agent/agent.py dùng (biến môi trường MCP_SERVER_URL)
    load_dotenv(ENV_FILE, encoding="utf-8-sig")
    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:8085/mcp")

    try:
        import asyncio
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client

        async def verify_connection():
            async with streamablehttp_client(server_url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    names = {tool.name for tool in tools.tools}
                    expected = {"get_current_weather", "get_forecast", "health_check"}
                    if not expected.issubset(names):
                        raise RuntimeError(f"Missing MCP tools: {expected - names}")
                    result = await session.call_tool("health_check", {})
                    if result.isError:
                        raise RuntimeError("MCP health_check failed")
                    print(f"✅ MCP server connected at {server_url}")
                    print(f"   Tools: {', '.join(sorted(names))}")

        asyncio.run(asyncio.wait_for(verify_connection(), timeout=30.0))
        return True

    except Exception as e:
        print(f"❌ Cannot reach MCP server at {server_url}: {e}")
        print("   Start it: cd ../mcp-server && uv run python weather.py")
        return False

def check_agent_import():
    """Try to import the agent"""
    print("\n🔍 Checking agent import...")
    
    try:
        # Suppress warnings during import
        import warnings
        warnings.filterwarnings("ignore")
        
        from weather_agent import root_agent
        print(f"✅ Agent imported successfully: {root_agent.name}")
        print(f"   Model: {getattr(root_agent.model, 'model', root_agent.model)}")
        if not root_agent.tools:
            print("❌ Agent has no MCP tools (fallback mode)")
            return False
        return True
    except Exception as e:
        print(f"❌ Failed to import agent: {e}")
        return False

def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Weather Agent Setup Verification")
    print("=" * 60)
    print()
    
    checks = [
        check_environment(),
        check_dependencies(),
        check_agent_structure(),
        check_mcp_server(),
        check_agent_import(),
    ]
    
    print("\n" + "=" * 60)
    if all(checks):
        print("✅ All checks passed!")
        print("\n🚀 Ready to start!")
        print("   Run: uv run adk web")
        print("\n📍 Then open: http://localhost:8000")
        return 0
    else:
        print("❌ Some checks failed")
        print("\n⚠️  Fix the issues above and run this script again")
        return 1

if __name__ == "__main__":
    sys.exit(main())

