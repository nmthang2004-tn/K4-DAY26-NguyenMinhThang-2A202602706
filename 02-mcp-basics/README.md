# 02 — MCP Basics (Server + Client)

Cùng tool `get_weather`, nhưng giờ tách ra **MCP server độc lập**. Server tự công bố
tool qua giao thức MCP; bất kỳ client nào (Claude Code, Cursor, hoặc `weather_client.py`)
cũng cắm vào dùng được — không cần biết code bên trong.

```
weather_client.py                       weather_server.py
┌─────────────┐    giao thức MCP    ┌─────────────────┐
│  list_tools │ ──────────────────▶ │ @mcp.tool()     │
│  call_tool  │ ◀────────────────── │ get_weather()   │
└─────────────┘     stdio           └─────────────────┘
```

## Cách chạy (không cần API key)

```bash
pip install -r ../requirements.txt
python weather_client.py     # client tự khởi động weather_server.py
```

Trên Windows PowerShell, từ thư mục gốc repo:

```powershell
cd 02-mcp-basics
..\.venv\Scripts\python.exe -X utf8 weather_client.py
```

Client tự khởi động server bằng cùng Python interpreter. Không cần terminal
server riêng, `.env`, Gemini hay WeatherAPI. Chạy từ `02-mcp-basics` vì
đường dẫn `weather_server.py` trong client hiện là đường dẫn tương đối.

### Checkpoint đã kiểm tra

- Chạy thành công khi loại bỏ các biến môi trường API key khỏi tiến trình test.
- `list_tools()` công bố `get_weather` với mô tả khớp docstring server.
- Schema nhận `city` kiểu string, bắt buộc.
- Ba lần gọi Hanoi, Danang, Haiphong trả đúng dữ liệu mock bên dưới.
- Gọi Tokyo trả dữ liệu mặc định 28°C; thiếu `city` trả lỗi tool.

Log thực tế: `screenshots/02-mcp-client.txt` ở thư mục gốc repo.
Schema và hai trường hợp bổ sung: `screenshots/02-mcp-schema-check.json`.
Ảnh terminal vẫn cần chụp thủ công bằng Snipping Tool, có đủ danh sách
tools và ba lần `call_tool`, lưu thành `screenshots/02-mcp-client.png`.

### Test tay

1. Chạy client, đối chiếu ba kết quả với output mong đợi bên dưới.
2. Đổi **chỉ docstring** của `get_weather` trong server, chạy lại client:
   mô tả được liệt kê phải đổi theo. Sau đó khôi phục docstring.
3. Đổi giá trị mock của Hanoi trong server, chạy lại client:
   kết quả Hanoi phải đổi mà không sửa logic client. Sau đó khôi phục dữ liệu.
4. Thêm `"Tokyo"` vào danh sách thành phố trong client, chạy lại:
   nhận `Tokyo: 28°C, không có dữ liệu chi tiết`. Sau đó khôi phục danh sách.

Lưu ý: client khám phá **schema** lúc chạy, nhưng demo vẫn ghi cố định
tên `"get_weather"`, tham số `"city"` và danh sách thành phố khi gọi.
Chưa có model chọn tool tự động. Việc tự sinh schema ở đây do decorator
của MCP SDK thực hiện; giao thức MCP chuẩn hóa cách công bố và gọi tool.

Kết quả mong đợi:

```
Tools server cung cấp:
  - get_weather: Lấy thời tiết hiện tại của một thành phố.

call_tool get_weather(city='Hanoi'):
  -> Hanoi: 29°C, trời mưa

call_tool get_weather(city='Danang'):
  -> Danang: 30°C, nhiều mây

call_tool get_weather(city='Haiphong'):
  -> Haiphong: 33°C, mưa rào
```

## Files

| File | Mô tả |
|---|---|
| `weather_server.py` | MCP server — `@mcp.tool()` tự sinh schema từ type hints + docstring |
| `weather_client.py` | MCP client — `list_tools` + `call_tool` qua stdio transport |

---

## MCP là gì? Giải thích đơn giản

### Phép so sánh: ổ cắm điện chuẩn

```
KHÔNG CÓ MCP (mỗi nhà 1 kiểu ổ cắm)
══════════════════════════════════════

  Quạt ──[phích A]──▶ Ổ cắm nhà 1       ← Quạt chỉ dùng được ở nhà 1
  Quạt ──[phích B]──▶ Ổ cắm nhà 2       ← Phải đổi phích cho nhà 2
  Quạt ──[phích C]──▶ Ổ cắm nhà 3       ← Lại đổi phích cho nhà 3

  Mỗi nhà 1 kiểu ổ → mua thiết bị phải xem nhà dùng ổ gì


CÓ MCP (chuẩn hoá ổ cắm)
══════════════════════════

  Quạt  ──┐                    ┌── Nhà 1
  Tivi  ──┼── ổ cắm chuẩn ──   ├── Nhà 2
  Máy lạnh┘                    └── Nhà 3

  Viết tool 1 lần → mọi AI app dùng được
  Viết client 1 lần → mọi tool server cắm vào được
```

### 3 bước MCP hoạt động

```
Bước 1 — KHÁM PHÁ: "Anh có tool gì?"
══════════════════════════════════════

  Client                          Server
    │                               │
    │── "list_tools()" ───────────▶ │
    │                               │  Server tự trả lời:
    │                               │  "Tôi có get_weather(city: str)"
    │◀── [{name, description,  ──── │  Schema SINH TỰ ĐỘNG
    │      parameters}]             │  từ type hints + docstring
    │                               │

  So sánh Function Calling:
    FC:  Developer viết schema THỦ CÔNG 15+ dòng
    MCP: @mcp.tool() → schema TỰ SINH từ type hints


Bước 2 — GỌI TOOL: "Cho tôi thời tiết HN"
═══════════════════════════════════════════

  Client                          Server
    │                               │
    │── call_tool("get_weather", ─▶ │
    │    {"city": "Hanoi"})         │
    │                               │  SERVER thực thi hàm
    │                               │  get_weather("Hanoi")
    │◀── "Hanoi: 29°C, mưa" ──────  │
    │                               │

  So sánh Function Calling:
    FC:  APP phải tự chạy hàm
    MCP: SERVER chạy — client không cần biết code bên trong


Bước 3 — TÁI SỬ DỤNG: viết 1 lần, dùng mọi nơi
═════════════════════════════════════════════════

                     ┌── Claude Code
                     │      "list_tools → get_weather"
  weather_server.py ─┼── Cursor
                     │      "list_tools → get_weather"
                     ├── Gemini CLI
                     │      "list_tools → get_weather"
                     └── App tự viết
                            "list_tools → get_weather"

  1 server phục vụ N client — không sửa dòng code nào
```

---

## So sánh code: Function Calling vs MCP

### Khai báo tool

```
Function Calling (01):                    MCP (02):
30 dòng schema viết tay                   4 dòng, tự sinh schema

types.FunctionDeclaration(                @mcp.tool()
  name="get_weather",                     def get_weather(city: str) -> str:
  description="Lấy thời tiết...",             """Lấy thời tiết..."""
  parameters=types.Schema(                    return f"{city}: 29°C"
    type=types.Type.OBJECT,
    properties={                           ✅ Schema tự sinh từ:
      "city": types.Schema(                   city: str    → type: string
        type=types.Type.STRING,               -> str       → return type
        description="Tên thành phố"           docstring    → description
      )
    },
    required=["city"],
  ),
)
```

### Nơi thực thi

```
Function Calling:                          MCP:
Mọi thứ trong 1 file                      Tách server / client

┌── weather_app.py ──────────┐             ┌── server.py ─────────┐
│                            │             │  @mcp.tool()         │
│  schema = {...}            │             │  def get_weather():  │
│  def get_weather(): ...    │             │      ...             │
│  model.generate(...)       │             └──────────────────────┘
│  result = get_weather()    │                       ▲
│                            │                       │ MCP
└────────────────────────────┘                       │
                                           ┌── client.py ─────────┐
App = schema + hàm + model                 │  list_tools()        │
    = làm hết mọi thứ                      │  call_tool()         │
                                           └──────────────────────┘

                                           Client chỉ biết giao thức
                                           Server chỉ biết logic tool
```

### Thêm tool mới

```
Function Calling:                          MCP:

  App A: thêm schema + hàm                  Server: thêm 1 hàm @mcp.tool()
  App B: copy schema + hàm                  Client A: không đổi (tự khám phá)
  App C: copy schema + hàm                  Client B: không đổi
                                            Client C: không đổi
  3 chỗ phải sửa                             1 chỗ phải sửa
```

---

## Khác biệt so với Function Calling thuần

| | 01-function-calling | 02-mcp-basics |
|---|---|---|
| Khai báo schema | Viết tay `FunctionDeclaration` | `@mcp.tool()` tự sinh |
| Nơi thực thi tool | Trong app gọi model | Trong MCP server riêng |
| Khám phá tool | Hard-code danh sách | `list_tools()` tại runtime |
| Dùng lại ở app khác | Copy code | Cắm thêm client |

---

## MCP trong thực tế: kết hợp với LLM

Ví dụ trên chỉ demo **lớp giao thức** (không cần API key). Trong production, MCP kết hợp với Function Calling:

```
┌──────────────────────────────────────────────────────────┐
│                    Luồng đầy đủ                          │
│                                                          │
│  User: "Thời tiết HN?"                                   │
│    │                                                     │
│    ▼                                                     │
│  AI Client (Claude, Cursor...)                           │
│    │                                                     │
│    ├─ 1. list_tools() ──▶ MCP Server                     │
│    │◀── "có get_weather"                                 │
│    │                                                     │
│    ├─ 2. Gửi prompt + tool list cho LLM                  │
│    │◀── LLM dùng FUNCTION CALLING:                       │
│    │    "gọi get_weather(city='HN')"                     │
│    │                                                     │
│    ├─ 3. call_tool("get_weather") ──▶ MCP Server         │
│    │◀── "HN: 29°C, mưa"                                  │
│    │                                                     │
│    ├─ 4. Gửi kết quả cho LLM tổng hợp                    │
│    │◀── "HN 29°C, mưa, nhớ mang ô!"                      │
│    │                                                     │
│    ▼                                                     │
│  User nhận câu trả lời                                   │
│                                                          │
│  Function Calling = LLM quyết định gọi tool nào (bước 2) │
│  MCP = giao thức kết nối client ↔ server (bước 1, 3)     │
│  → Chúng BỔ SUNG cho nhau, không thay thế                │
└──────────────────────────────────────────────────────────┘
```

---

## Đăng ký server với AI client

**Claude Code** (làm 1 lần, dùng mãi):

```bash
claude mcp add weather -- python /đường/dẫn/tới/weather_server.py
```

**Gemini CLI**:

```bash
# Thêm vào ~/.gemini/settings.json
"mcpServers": {
  "weather": {
    "command": "python",
    "args": ["/đường/dẫn/tới/weather_server.py"]
  }
}
```

Bước tiếp theo: [03-production/](../03-production/) — Auth, Tool Registry, Versioning.
