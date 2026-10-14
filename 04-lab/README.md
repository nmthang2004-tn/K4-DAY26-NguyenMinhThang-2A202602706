# Lab 04 — Weather Agent with Remote MCP Server

A weather agent built with Google ADK that connects to an MCP server via Streamable HTTP transport.

## Architecture

```
┌─────────────────┐   Streamable HTTP    ┌─────────────────┐      REST       ┌─────────────────┐
│   ADK Agent     │ ──────────────────── │   MCP Server    │ ─────────────── │  WeatherAPI.com │
│  (mcp-client)   │   localhost:8085/mcp │  (mcp-server)   │                 │                 │
└─────────────────┘                      └─────────────────┘                 └─────────────────┘
```

## Tools

| Tool | Description |
|------|-------------|
| `get_current_weather(city)` | Get current weather conditions for a city |
| `get_forecast(city, days)` | Get weather forecast (1–3 days) |
| `health_check()` | Verify server is running |

## ADK làm gì trong Lab này?

ADK (Agent Development Kit) đóng vai trò **MCP Client** 
```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  1. KẾT NỐI tới MCP Server qua Streamable HTTP                  │
│     StreamableHTTPConnectionParams(url="localhost:8085/mcp")    │
│                                                                 │
│  2. KHÁM PHÁ tools tự động (list_tools)                         │
│     McpToolset → tự hỏi server "anh có tool gì?"                │
│     → nhận về: get_current_weather, get_forecast, health_check  │
│                                                                 │
│  3. TRUYỀN tools cho LLM (Gemini)                               │
│     Agent(model=Gemini(...), tools=[weather_tools])            │
│     → Gemini biết nó có thể gọi 3 tools trên                    │
│                                                                 │
│  4. ĐIỀU PHỐI vòng lặp Function Calling                         │
│     User hỏi → Gemini chọn tool → ADK gọi MCP Server            │
│     → nhận kết quả → đưa lại cho Gemini tổng hợp                │
│                                                                 │
│  5. CUNG CẤP giao diện web (adk web)                            │
│     → http://localhost:8000 để chat với agent                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

So với bài 02 (viết client thủ công bằng `mcp.ClientSession`), ADK giúp bạn **không phải viết vòng lặp function calling thủ công** nữa. Toàn bộ luồng list_tools → model quyết định → call_tool → model tổng hợp được ADK xử lý tự động.

## Setup

Tạo một file `.env` ở thư mục gốc repo (cùng cấp `requirements.txt`), dùng
`.env.example` làm mẫu. Nếu đã có `.env`, chỉ cần điền hai key:

```dotenv
GEMINI_API_KEY=your_gemini_api_key_here
WEATHERAPI_KEY=your_weatherapi_key_here
MCP_SERVER_URL=http://localhost:8085/mcp
```

Server, agent và `verify_setup.py` đọc cùng file theo đường dẫn mã nguồn,
không phụ thuộc thư mục terminal. Biến môi trường đã được đặt sẵn có ưu tiên
cao hơn `.env`. Client ánh xạ `GEMINI_API_KEY` sang `GOOGLE_API_KEY` cho ADK;
không cần khai báo thêm `GOOGLE_API_KEY`. `.env` đã được bỏ qua bởi Git.
Sau khi sửa key, khởi động lại server và client.

### 1. MCP Server

```bash
cd mcp-server
uv sync

# WEATHERAPI_KEY được đọc từ .env ở thư mục gốc repo

# Start the server (runs on port 8085 by default)
uv run python weather.py
```

The server will be available at `http://localhost:8085/mcp`.

Windows PowerShell, từ thư mục gốc repo:

```powershell
cd 04-lab/mcp-server
uv --system-certs sync --locked
# Key tự đọc từ .env gốc, không cần export.
# PORT cũng buộc dùng Streamable HTTP khi chạy từ terminal không tương tác.
$env:PORT = "8085"
uv run python -X utf8 weather.py
```

Giữ server chạy cho bước agent tiếp theo. Nếu thấy thông báo stdio, đặt
`PORT` như trên rồi chạy lại. Nếu cổng đã bị chiếm, không khởi động server
thứ hai trên cùng cổng; đổi `PORT` và `MCP_SERVER_URL` cho khớp.
Server dùng kho chứng chỉ của hệ điều hành cho HTTPS tới WeatherAPI.
`health_check` chỉ xác nhận MCP server hoạt động; cần gọi weather tool để
xác nhận key và kết nối WeatherAPI thật.

### 2. ADK Agent (Client)

```bash
cd mcp-client
uv sync

# GEMINI_API_KEY được đọc từ .env ở thư mục gốc repo

# Start ADK web interface
uv run adk web
```

Open http://localhost:8000 in your browser, select `weather_agent`, and ask about the weather.

## Configuration

| Variable | Where | Description |
|----------|-------|-------------|
| `WEATHERAPI_KEY` | .env ở thư mục gốc repo | API key from weatherapi.com |
| `GEMINI_API_KEY` | .env ở thư mục gốc repo | Gemini API key |
| `GEMINI_MODEL` | .env ở thư mục gốc repo | Model của agent, mặc định `gemini-3.5-flash-lite` |
| `PORT` | mcp-server (env) | Override server port (default: 8085) |
| `MCP_SERVER_URL` | .env ở thư mục gốc repo | MCP endpoint the agent connects to (default: `http://localhost:8085/mcp`; set to your Cloud Run URL + `/mcp` when deployed) |

## Bước agent: kiểm tra và chat trên Windows

Server 8085 phải đang chạy. Từ thư mục gốc repo:

```powershell
cd 04-lab/mcp-client
uv --system-certs sync --locked
uv run python -X utf8 verify_setup.py
uv run adk web --host 127.0.0.1 --port 8000
```

Không tạo thêm `.env` trong client: dùng `GEMINI_API_KEY` và `WEATHERAPI_KEY`
trong `.env` gốc. `GEMINI_MODEL` là tùy chọn. Agent dùng kho chứng chỉ
hệ điều hành cho cả lời gọi Gemini đồng bộ và bất đồng bộ.

`verify_setup.py` kiểm tra phiên MCP thật, danh sách ba tool và
`health_check`; không còn chỉ dựa vào GET thuần. Import agent ở chế độ
fallback không có tool cũng bị đánh dấu lỗi. Việc tạo `McpToolset` chưa
chứng minh kết nối thành công, vì khám phá tool diễn ra khi được yêu cầu.

Mở http://localhost:8000, chọn `weather_agent`, hỏi thời tiết hiện tại và
dự báo 3 ngày. Kiểm tra cả FunctionCall, FunctionResponse và câu trả lời
cuối; chúng chứng minh dữ liệu đến từ MCP/WeatherAPI, không phải mock.

Bằng chứng trong thư mục `screenshots` gốc repo:

- `04-verify-setup.txt`: output chạy script kiểm tra.
- `04-verify-setup.png`: ảnh báo cáo hiển thị output đã lưu, không phải ảnh terminal.
- `04-adk-current.png`, `04-adk-forecast.png`: ảnh chụp giao diện ADK thật.
- `04-adk-current-events.json`, `04-adk-forecast-events.json`: sự kiện model
  gọi tool, tool trả dữ liệu và câu trả lời cuối từ ADK Web.

Giữ cả MCP server và ADK Web chạy khi test. Đừng khởi động tiến trình thứ
hai trên cổng đang sử dụng. Trên Windows ADK tự tắt reload; sau khi sửa
`agent.py` hoặc key/model, cần khởi động lại ADK Web.

## Tùy chọn: Cloud Run

Xem [mcp-server/CLOUD_RUN.md](mcp-server/CLOUD_RUN.md) để tự điền project,
cấu hình Secret Manager, quyền service account và deploy bằng PowerShell.
`deploy-cloud-run.ps1 -DryRun` chỉ hiển thị lệnh. Docker sử dụng dependency
export từ lockfile và không chứa `.env`; Cloud Run cấp `WEATHERAPI_KEY` qua
secret. Sửa `MCP_SERVER_URL` trong `.env` **gốc repo** sau khi deploy xong.
Ảnh `screenshots/05-cloud-run.png` chỉ tạo sau khi kiểm tra endpoint cloud thật.
