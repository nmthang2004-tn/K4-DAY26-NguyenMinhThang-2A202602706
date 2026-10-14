# 03 — Production (Auth, Tool Registry, Versioning)

`02-mcp-basics` chạy tốt trên máy cá nhân. Đưa vào production cần giải quyết thêm 3 vấn đề:

| Vấn đề | Demo | Production |
|---|---|---|
| **Auth** | stdio, cùng máy, ai cũng gọi | HTTP + Bearer token / OAuth |
| **Discovery** | Hard-code tool/server | Tool Registry — agent tìm tool theo task |
| **Versioning** | 1 tool duy nhất | v1 + v2 song song, deprecation notice |

## Files

| File | Vấn đề | Mô tả |
|---|---|---|
| `auth_server.py` | Auth | MCP server qua HTTP + `TokenVerifier` kiểm tra bearer token |
| `auth_client.py` | Auth | Client gửi token qua `create_mcp_http_client(headers=...)` |
| `registry.json` | Discovery | Tool Registry — danh mục tool-centric, agent tìm theo tag/keyword |
| `registry_client.py` | Discovery | Agent tra cứu registry, chọn best match, tự kết nối |
| `versioned_server.py` | Versioning | Server v2: giữ tool v1 (deprecated) + thêm v2 + resource metadata |
| `versioned_client.py` | Versioning | Client test gọi tool v1, v2 và đọc `server://info` metadata |

---

## 3a. Authentication

Server chạy qua **Streamable HTTP** thay vì stdio, kèm bearer token verification.

```bash
# Terminal 1 — khởi động server
python auth_server.py
# Server lắng nghe tại http://127.0.0.1:8002/mcp

# Terminal 2 — client kết nối kèm token
python auth_client.py
```

Luồng:

```
Client                                Server
  │                                      │
  │── POST /mcp ──────────────────────▶  │
  │   Authorization: Bearer <token>      │
  │                                      │── TokenVerifier.verify_token()
  │                                      │   token hợp lệ → AccessToken
  │◀── 200 OK (tools, results) ────────  │
  │                                      │
  │── POST /mcp (token sai) ──────────▶  │
  │◀── 401 Unauthorized ───────────────  │
```

- Token hợp lệ → truy cập tool bình thường
- Thiếu token → `401`
- Token sai → `401` (đã kiểm tra với MCP SDK 2.3.0)
- Token hợp lệ nhưng thiếu scope bắt buộc → `403` nếu server cấu hình required scopes
- Logic tool không biết gì về auth — SDK xử lý ở tầng transport

---

## 3b. Tool Registry & Discovery

Agent **không hard-code** tool nào. Nó hỏi Tool Registry theo yêu cầu task:

```bash
python registry_client.py
```

Kết quả mong đợi:

```
=== Tool Registry ===

  get_weather v1.0.0
    Lấy thời tiết hiện tại của một thành phố
    tags: ['weather', 'current', 'vietnam']  →  server: weather
  get_weather_v2 v2.0.0
    Lấy thời tiết chi tiết — JSON, hỗ trợ forecast và đơn vị đo
    tags: ['weather', 'forecast', 'detailed', 'vietnam']  →  server: weather-v2
  ...

--- Agent cần tool có tag "weather" ---
Tìm thấy 2 tool(s):
  • get_weather v1.0.0 (server: weather)
  • get_weather_v2 v2.0.0 (server: weather-v2)

Best match: get_weather_v2 v2.0.0
Kết nối tới server [weather-v2]...
Kết quả: ...
```

Luồng:

```
Agent nhận task
   │
   ▼
ToolRegistry.search(tag="weather")  ← tìm tool theo capability
   │
   ├── get_weather v1.0 → server: weather
   └── get_weather_v2 v2.0 → server: weather-v2
   │
   ▼
ToolRegistry.best_match()  ← chọn version cao nhất, không deprecated
   │
   ▼
connect_and_call()  ← tự kết nối đúng transport (stdio/HTTP) + auth
```

`registry.json` là **tool-centric** — đơn vị khám phá là tool (tag, description, parameters), không phải server. Production thay JSON bằng DB/API với semantic search.

---

## 3c. Versioning & Backward Compatibility

Server v2 dùng 3 kỹ thuật để thêm tính năng mà không break client cũ:

```bash
# Server chạy qua stdio — client tự spawn
python versioned_client.py
```

| Kỹ thuật | Mô tả |
|---|---|
| **Tool mới song song** | `get_weather_v2` tồn tại bên cạnh `get_weather` — không xoá tool cũ |
| **Tham số optional** | `include_forecast`, `units` có default → client cũ gọi `get_weather_v2(city="Hanoi")` vẫn đúng |
| **Server metadata** | Resource `server://info` công bố version, deprecated tools, migration guide |

```
Server v2
├── get_weather(city)              ← v1, deprecated nhưng vẫn hoạt động
├── get_weather_v2(city, ...)      ← v2, thêm forecast + units
└── resource server://info         ← version + migration guide cho client
```

Kết quả mong đợi:

```
Server: weather-v2 v2.0.0
Deprecated tools: ['get_weather']
Migration: Chuyển từ get_weather sang get_weather_v2. Tham số 'city' giữ nguyên, thêm include_forecast và units.

Tools:
  - get_weather: [v1] Lấy thời tiết hiện tại — trả chuỗi đơn giản. Deprecated, dùng get_weather_v2.
  - get_weather_v2: [v2] Lấy thời tiết chi tiết — JSON, hỗ trợ forecast và đơn vị đo.

[v1] get_weather('Hanoi'):
  Hanoi: 29°C, trời mưa

[v2] get_weather_v2('Hanoi', forecast=True):
  { "api_version": "2.0", "city": "Hanoi", "temp": 29, ... }
```

Luồng:

```
versioned_client.py                     versioned_server.py
       │                                        │
       │── read_resource("server://info") ────▶ │  ← đọc metadata trước
       │◀── version, deprecated_tools ────────  │
       │                                        │
       │── list_tools() ─────────────────────▶  │  ← khám phá tool
       │◀── [get_weather, get_weather_v2] ────  │
       │                                        │
       │── call_tool("get_weather") ──────────▶ │  ← v1 deprecated, vẫn chạy
       │── call_tool("get_weather_v2") ───────▶ │  ← v2 đầy đủ tính năng
```

Client thông minh đọc `server://info` để biết tool nào deprecated, tự chọn dùng v2 nếu có, fallback v1 nếu không.

## Chạy checkpoint trên Windows PowerShell

Mở hai terminal tại thư mục gốc repo. Terminal 1:

```powershell
cd 03-production
# Dùng token demo mặc định cho server
Remove-Item Env:MCP_AUTH_TOKEN -ErrorAction SilentlyContinue
..\.venv\Scripts\python.exe -X utf8 auth_server.py
```

Terminal 2:

```powershell
cd 03-production
# Token đúng, mặc định
Remove-Item Env:MCP_AUTH_TOKEN -ErrorAction SilentlyContinue
..\.venv\Scripts\python.exe -X utf8 auth_client.py

# Token sai: server từ chối, không có danh sách tool
$env:MCP_AUTH_TOKEN = "wrong-token"
..\.venv\Scripts\python.exe -X utf8 auth_client.py

# Khôi phục biến môi trường trước khi chạy các demo tiếp theo
Remove-Item Env:MCP_AUTH_TOKEN -ErrorAction SilentlyContinue
..\.venv\Scripts\python.exe -X utf8 registry_client.py
..\.venv\Scripts\python.exe -X utf8 versioned_client.py
```

Auth server dùng cổng 8002, ADK Web dùng 8000; có thể chạy song song.
Dừng auth server bằng Ctrl+C khi test xong. Có thể đặt `MCP_AUTH_PORT`
giống nhau ở cả hai terminal để đổi cổng. Dùng endpoint `/mcp`; auth server
không có trang chủ `/`. `0.0.0.0` là địa chỉ bind, không phải URL trang web.
Token demo là dữ liệu minh họa; việc xác thực do middleware xử lý,
không được đặt trong hàm `get_weather`.

Registry demo chưa dùng LLM: code chọn tool theo tag và semantic version.
Nếu tất cả kết quả đều deprecated, `best_match()` vẫn chọn một kết quả
deprecated làm fallback. Chỉ hai server weather có mã triển khai trong repo;
email và database là mục registry minh họa, không cần kết nối để làm checkpoint.

### Bằng chứng và test tay

Log nằm trong thư mục `screenshots` ở gốc repo:

| Demo | Log | Ảnh cần chụp thủ công |
|---|---|---|
| Auth, token đúng | `03a-auth-ok.txt` | `03a-auth-ok.png` |
| Auth, token sai | `03a-auth-fail.txt` | `03a-auth-fail.png` |
| Tool Registry | `03b-registry.txt` | `03b-registry.png` |
| Versioning | `03c-versioning.txt` | `03c-versioning.png` |

Log server: `03a-auth-server.txt`; mã HTTP kiểm tra trực tiếp:
`03a-auth-status.json`. Trên môi trường test, HTTP client có thể báo
`peer unexpectedly closed connection` khi server trả lỗi auth, hoặc cảnh báo
khi kết thúc session. Đối chiếu access log của server để thấy HTTP 401;
không coi lỗi kết nối đơn thuần là bằng chứng xác thực bị từ chối.

Test tay thêm:

- Auth: token đúng nhận tool và dữ liệu; token sai không được khám phá tool.
  Đổi token ở **client**, giữ nguyên token cấu hình lúc server khởi động.
- Registry: đặt `deprecated: true` cho `get_weather_v2` trong `registry.json`,
  chạy lại: best match phải chuyển về v1. Sau đó khôi phục JSON.
- Versioning: bỏ `include_forecast` và `units` khỏi lời gọi v2 trong client,
  chạy lại: vẫn nhận JSON, `units` là `celsius` và không có `forecast`.
  Sau đó khôi phục lời gọi.
