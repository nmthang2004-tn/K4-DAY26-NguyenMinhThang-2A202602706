"""Minh hoạ FUNCTION CALLING thuần với Google Gemini SDK.

Tool `get_weather` được định nghĩa schema thủ công VÀ thực thi ngay trong
chính file app này. Model chỉ QUYẾT ĐỊNH gọi tool nào; app mới là nơi chạy.

Cách chạy:
    pip install -r ../requirements.txt
    Điền GEMINI_API_KEY trong .env ở thư mục gốc repo.
    python weather_function_calling.py
"""

from google import genai
from google.genai import types
import os
import ssl
from pathlib import Path
from dotenv import load_dotenv

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(ENV_FILE, encoding="utf-8-sig")
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(f"Set GEMINI_API_KEY in {ENV_FILE} or the environment.")
# Use the OS trust store, including Windows certificates, for HTTPS.
client = genai.Client(
    api_key=api_key,
    http_options=types.HttpOptions(
        client_args={"verify": ssl.create_default_context()},
        timeout=60_000,
        retry_options=types.HttpRetryOptions(attempts=1),
    ),
)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODELS = (
    "gemini-3.1-flash-lite", "gemini-3.6-flash-lite", "gemini-3.6-flash",
    "gemini-3.7-flash", "gemini-3.8-flash",
)


def generate_with_fallback(**kwargs):
    """Retry only model generation, preserving the current conversation/tools."""
    for model in dict.fromkeys((MODEL, *FALLBACK_MODELS)):
        try:
            response = client.models.generate_content(model=model, **kwargs)
            print(f"  [model sử dụng] {model}")
            return response
        except Exception as error:
            print(f"  [model lỗi] {model}: {type(error).__name__}; thử model tiếp theo")
    raise RuntimeError("Tất cả model chính và fallback đều thất bại.")

SYSTEM_INSTRUCTION = (
    "Bạn là trợ lý thời tiết thân thiện, trả lời bằng tiếng Việt tự nhiên. "
    "Dùng emoji phù hợp (🌧️ 🌤️ 💨 💧). "
    "Tóm tắt ngắn gọn, dễ hiểu, và đưa ra lời khuyên thực tế "
    "(ví dụ: mang ô, mặc áo mỏng, ...)."
)

# 1. App tự định nghĩa schema của tool
get_weather_declaration = types.FunctionDeclaration(
    name="get_weather",
    description="Lấy thời tiết hiện tại của một thành phố",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "city": types.Schema(
                type=types.Type.STRING, description="Tên thành phố"
            )
        },
        required=["city"],
    ),
)

TOOLS = [types.Tool(function_declarations=[get_weather_declaration])]


# 2. App tự thực thi tool (trong thực tế sẽ gọi API thời tiết thật)
def get_weather(city: str) -> str:
    """Trả về thời tiết (mock) của *city*. Dùng làm tool cho model."""
    mock_data = {
        "Hà Nội": {
            "nhiệt_độ": "29°C",
            "thời_tiết": "trời mưa nhẹ",
            "độ_ẩm": "82%",
            "gió": {"hướng": "Đông Nam", "tốc_độ": "12 km/h"},
        },
        "Hồ Chí Minh": {
            "nhiệt_độ": "33°C",
            "thời_tiết": "mưa rào",
            "độ_ẩm": "75%",
            "gió": {"hướng": "Tây Nam", "tốc_độ": "15 km/h"},
        },
        "Đà Nẵng": {
            "nhiệt_độ": "30°C",
            "thời_tiết": "nhiều mây",
            "độ_ẩm": "78%",
            "gió": {"hướng": "Đông", "tốc_độ": "10 km/h"},
        },
    }
    import json

    # Gemini may return English names even when the question is Vietnamese.
    city_aliases = {
        "hanoi": "Hà Nội",
        "ha noi": "Hà Nội",
        "da nang": "Đà Nẵng",
        "danang": "Đà Nẵng",
        "ho chi minh": "Hồ Chí Minh",
        "ho chi minh city": "Hồ Chí Minh",
    }
    city = city_aliases.get(city.strip().lower(), city.strip())
    default = {"nhiệt_độ": "28°C", "thời_tiết": "không có dữ liệu chi tiết"}
    return json.dumps({"city": city, **mock_data.get(city, default)}, ensure_ascii=False)


def run(prompt: str) -> str:
    """Gửi *prompt* tới Gemini, tự động xử lý function calling và trả về câu trả lời cuối."""
    contents: list[types.Content] = [
        types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
    ]

    # 3. Gọi model — model quyết định có gọi tool hay không
    resp = generate_with_fallback(
        contents=contents,
        config=types.GenerateContentConfig(
            tools=TOOLS,
            system_instruction=SYSTEM_INSTRUCTION,
            thinking_config=types.ThinkingConfig(thinking_level="low"),
        ),
    )

    # 4. Vòng lặp: nếu model yêu cầu tool, app TỰ THỰC THI rồi đưa kết quả trả lại
    while resp.function_calls:
        # Thêm phản hồi của model vào lịch sử hội thoại
        contents.append(resp.candidates[0].content)

        function_responses = []
        for fc in resp.function_calls:
            print(f"  [model yêu cầu] {fc.name}({fc.args})")
            result = get_weather(**fc.args)  # <-- app chạy, không phải model
            print(f"  [app thực thi]  -> {result}")
            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name, response={"result": result}
                )
            )

        # Gửi kết quả tool trả về cho model
        contents.append(types.Content(role="user", parts=function_responses))
        resp = generate_with_fallback(
            contents=contents,
            config=types.GenerateContentConfig(
                tools=TOOLS,
                system_instruction=SYSTEM_INSTRUCTION,
                thinking_config=types.ThinkingConfig(thinking_level="low"),
            ),
        )

    # 5. Model tổng hợp câu trả lời cuối
    return resp.text


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gemini Function Calling demo")
    parser.add_argument(
        "--prompt",
        default="Thời tiết Hà Nội và Đà Nẵng hôm nay thế nào?",
        help="Câu hỏi để kiểm tra function calling",
    )
    question = parser.parse_args().prompt
    print(f"Model: {MODEL}")
    print(f"User: {question}\n")
    print("Trả lời:", run(question))
