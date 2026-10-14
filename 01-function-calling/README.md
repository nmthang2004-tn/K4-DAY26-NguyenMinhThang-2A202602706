# 01 — Function Calling thuần (Google Gemini SDK)

Tool `get_weather` được **định nghĩa schema thủ công** và **thực thi ngay trong app**.
Model chỉ quyết định gọi tool nào — app mới là nơi chạy.

```
User hỏi  →  Model quyết định gọi get_weather(city="Hà Nội")
                     │
                     ▼
              App TỰ THỰC THI hàm get_weather
                     │
                     ▼
              Model tổng hợp câu trả lời
```

## Cách chạy

```bash
pip install -r ../requirements.txt
# Set GEMINI_API_KEY in the repository root .env
python weather_function_calling.py
```

### Chạy trên Windows PowerShell và làm checkpoint

Từ thư mục gốc repo, không cần kích hoạt virtualenv hay export key:

```powershell
.\.venv\Scripts\python.exe -X utf8 .\01-function-calling\weather_function_calling.py
```

Script đọc `GEMINI_API_KEY` trong `.env` gốc. Bài này dùng dữ liệu mock,
không cần `WEATHERAPI_KEY` hay MCP server. Model mặc định là
`gemini-3.5-flash-lite`; có thể đổi bằng biến `GEMINI_MODEL` trong `.env`.
Khi lời gọi model lỗi, tự thử lần lượt `gemini-3.1-flash-lite`,
`gemini-3.6-flash-lite`, `gemini-3.6-flash`, `gemini-3.7-flash`,
`gemini-3.8-flash`. Model không có quyền truy cập hoặc không tồn tại sẽ
được bỏ qua khi API trả lỗi. Nếu tất cả lỗi, chương trình báo thất bại.
Fallback giữ nguyên lịch sử hội thoại và không chạy lại tool đã thực thi.
HTTPS dùng kho chứng chỉ của hệ điều hành và vẫn xác minh chứng chỉ.

Checkpoint đạt khi xuất hiện ít nhất một cặp `[model yêu cầu]` /
`[app thực thi]` và câu trả lời cuối dựa trên JSON mà app trả về.
Với câu hỏi mặc định, kiểm tra Hà Nội 29°C, mưa nhẹ và Đà Nẵng 30°C,
nhiều mây. Các số liệu này là mock, không phải thời tiết hôm nay.
Thứ tự gọi hai thành phố và cách diễn đạt câu trả lời có thể khác nhau.

Đã kiểm tra gọi Gemini thật thành công với model `gemini-3.6-flash`:
hai thành phố đều có cặp log yêu cầu/thực thi, rồi có `Trả lời:` dựa trên
đúng dữ liệu mock. Bằng chứng dạng text lưu tại
`screenshots/01-function-calling.txt` ở thư mục gốc repo.

### Test tay bằng câu hỏi khác

```powershell
# Một thành phố có trong mock: 33°C, mưa rào
.\.venv\Scripts\python.exe -X utf8 .\01-function-calling\weather_function_calling.py --prompt "Thời tiết Hồ Chí Minh thế nào?"

# Thành phố ngoài mock: 28°C, không có dữ liệu chi tiết
.\.venv\Scripts\python.exe -X utf8 .\01-function-calling\weather_function_calling.py --prompt "Lấy thời tiết Tokyo bằng get_weather, giữ nguyên tên city là Tokyo."

# Câu hỏi không cần thời tiết: có thể không xuất hiện dòng gọi tool
.\.venv\Scripts\python.exe -X utf8 .\01-function-calling\weather_function_calling.py --prompt "Chào bạn, hãy giới thiệu bản thân."
```

Muốn chứng minh app mới là nơi chạy hàm, đặt breakpoint tại
`result = get_weather(**fc.args)`. Khi dừng ở đây, model đã đưa ra yêu cầu,
nhưng hàm chưa chạy. Step Over sẽ chạy hàm và tạo `result`.

Sau khi chạy thành công, dùng Snipping Tool chụp terminal với đầy đủ
`[model yêu cầu]`, `[app thực thi]`, `Trả lời:` và lưu tại
`screenshots/01-function-calling.png` ở thư mục gốc repo.
Log dạng text, nếu có, không thay thế ảnh chụp màn hình yêu cầu nộp bài.

Nếu gặp 401/403, kiểm tra key trong `.env` và các biến môi trường đặt sẵn
(biến môi trường có ưu tiên cao hơn `.env`). Nếu gặp 404, kiểm tra model.
Nếu gặp 429 hoặc 503, đọc lỗi quota/quá tải rồi thử lại khi điều kiện cho phép.

## File

| File | Mô tả |
|---|---|
| `weather_function_calling.py` | Định nghĩa schema, thực thi tool, gọi model Gemini, xử lý vòng lặp function calling |

---

## Function Calling là gì? Giải thích đơn giản

Hình dung bạn có một **trợ lý ảo** rất giỏi ngôn ngữ, nhưng **không biết gì về thế giới thật** — không biết thời tiết, không truy cập được database, không gọi được API.

Function Calling là cách bạn **dạy trợ lý ảo sử dụng công cụ**:

```
Không có Function Calling:                 Có Function Calling:

User: "Thời tiết HN?"                     User: "Thời tiết HN?"
       │                                         │
       ▼                                         ▼
   ┌────────┐                                ┌────────┐
   │ Model  │                                │ Model  │
   │        │                                │        │ ← biết có tool get_weather
   │ "Tôi   │                                │ "Hãy   │
   │ không  │                                │  gọi   │
   │ biết"  │                                │ get_   │
   │        │                                │ weather│
   └────────┘                                │("HN")  │
                                             └───┬────┘
   Model bó tay vì                               │
   không có dữ liệu                              ▼
                                             App chạy hàm
                                                  │
                                                  ▼
                                             ┌────────┐
                                             │ Model  │
                                             │ "HN:   │
                                             │ 29°C,  │
                                             │ mưa"   │
                                             └────────┘
```

**Điểm mấu chốt:** Model **KHÔNG chạy** hàm. Nó chỉ nói *"hãy gọi hàm X với tham số Y"*.

---

## Minh hoạ từng bước chi tiết

User hỏi: **"Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?"**

```
Bước 1 — App chuẩn bị "hộp công cụ" cho model
═══════════════════════════════════════════════

    App định nghĩa schema THỦ CÔNG:
    ┌────────────────────────────────────────┐
    │  Tool: get_weather                     │
    │  Mô tả: "Lấy thời tiết thành phố"      │
    │  Tham số:                              │
    │    city: string (bắt buộc)             │
    │                                        │
    │   Schema viết TAY - 15 dòng code       │
    │     phải khớp với hàm thật             │
    └────────────────────────────────────────┘

Bước 2 — Gửi prompt + schema cho model
═══════════════════════════════════════

    App ──────────────────────────────────────────▶ Gemini
    │  "Thời tiết HN và ĐN?"                      │
    │  + schema get_weather                       │
    │                                             │
    │  Model hiểu: "À, có tool get_weather,       │
    │   tôi cần gọi nó 2 lần cho HN và ĐN"        │

Bước 3 — Model TRẢ VỀ yêu cầu gọi tool (không tự chạy!)
═════════════════════════════════════════════════════════

    Gemini ──────────────────────────────────────▶ App
    │  function_calls:                             │
    │    [                                         │
    │      get_weather(city="Hà Nội"),             │
    │      get_weather(city="Đà Nẵng")             │
    │    ]                                         │
    │                                              │
    │    Model CHỈ sinh JSON — không hề chạy       │

Bước 4 — App TỰ THI HÀNH hàm get_weather
═════════════════════════════════════════

    App nhận yêu cầu → CHẠY hàm Python:
    ┌──────────────────────────────────────────┐
    │  get_weather("Hà Nội")   → "29°C, mưa"   │ ← App chạy
    │  get_weather("Đà Nẵng")  → "30°C, mây"   │ ← App chạy
    └──────────────────────────────────────────┘

Bước 5 — Gửi kết quả lại cho model tổng hợp
════════════════════════════════════════════

    App ──────────────────────────────────────────▶ Gemini
    │  Kết quả: HN 29°C mưa, ĐN 30°C mây         │
    │                                            │
    │  Gemini: "Hà Nội 29°C, mưa nhẹ 🌧️          │
    │           nhớ mang ô nhé!                  │
    │           Đà Nẵng 30°C, nhiều mây 🌤️       │
    │           thời tiết dễ chịu!"              │
```

---

## Nhìn vào code thật

3 phần quan trọng trong `weather_function_calling.py`:

**Phần 1 — Schema viết tay** (model cần biết tool trông như thế nào):

```python
# App phải TỰ MÔ TẢ tool cho model — viết tay, dễ sai
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(type=types.Type.STRING, description="Tên thành phố")
        },
        required=["city"],
    ),
)
```

**Phần 2 — Hàm thực thi** (app tự chạy khi model yêu cầu):

```python
# App phải CÓ hàm thật để chạy — model không chạy hàm này
def get_weather(city: str) -> str:
    return json.dumps({"city": city, "nhiệt_độ": "29°C", ...})
```

**Phần 3 — Vòng lặp** (nhận yêu cầu → chạy → trả lại):

```python
while resp.function_calls:
    for fc in resp.function_calls:
        result = get_weather(**fc.args)   # ← APP chạy, không phải model
    # gửi result lại cho model để tổng hợp câu trả lời
```

---

## Luồng hoạt động

1. App định nghĩa `FunctionDeclaration` với schema viết tay (tên, tham số, kiểu)
2. App gửi prompt + danh sách tool tới Gemini
3. Model trả về `function_calls` — yêu cầu gọi `get_weather`
4. App **tự chạy** hàm `get_weather()` và đưa kết quả trả lại model
5. Model tổng hợp câu trả lời cuối cho user

## Nhược điểm

```
┌─────────────────────────────────────────────────────────────┐
│  ❌ Schema viết tay                                         │
│     FunctionDeclaration(name=..., parameters=...)           │
│     → 15+ dòng boilerplate, dễ lệch với hàm thật            │
│                                                             │
│  ❌ Tool gắn chặt trong app                                 │
│     App A có get_weather → App B muốn dùng?                 │
│     → Copy schema + hàm sang App B                          │
│     → Sửa hàm ở A? Phải nhớ sửa cả B                        │
│                                                             │
│  ❌ Mỗi provider 1 format                                   │
│     Google: FunctionDeclaration(...)                        │
│     OpenAI: {"type": "function", "function": {...}}         │
│     Anthropic: {"name": ..., "input_schema": {...}}         │
│     → Đổi model = viết lại schema                           │
└─────────────────────────────────────────────────────────────┘
```

**MCP giải quyết tất cả các vấn đề trên** → xem [02-mcp-basics/](../02-mcp-basics/)

Bước tiếp theo: [02-mcp-basics/](../02-mcp-basics/) — tách tool ra MCP server độc lập.
