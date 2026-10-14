# Deploy Weather MCP lên Cloud Run — Windows PowerShell

Bạn tự điền project ID. Các bước dưới đây tạo tài nguyên cloud trong project
có billing; chưa được chạy trên tài khoản Google Cloud của bạn.

## 1. Cài CLI và đăng nhập

Cài [Google Cloud CLI trên Windows](https://cloud.google.com/sdk/docs/install),
mở terminal mới rồi chạy:

```powershell
gcloud auth login
$cloudProjectId = "YOUR_PROJECT_ID"
$cloudRegion = "asia-southeast1"
$cloudService = "weather-mcp"
$cloudRuntimeSa = "$cloudService-runner@$cloudProjectId.iam.gserviceaccount.com"
```

Đăng nhập bằng tài khoản có quyền trên project đã bật billing. Không cần
`gcloud auth application-default login` để deploy bằng CLI.

## 2. Bật API và tạo service account

```powershell
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com secretmanager.googleapis.com --project=$cloudProjectId

gcloud iam service-accounts create "$cloudService-runner" --display-name="Weather MCP runtime" --project=$cloudProjectId

$cloudProjectNumber = gcloud projects describe $cloudProjectId --format="value(projectNumber)"
gcloud projects add-iam-policy-binding $cloudProjectId --member="serviceAccount:$cloudProjectNumber-compute@developer.gserviceaccount.com" --role="roles/run.builder"
```

Nếu service account đã có, bỏ qua lệnh tạo. Nếu project cấu hình build service
account riêng, cấp `roles/run.builder` cho đúng build account thay vì account
mặc định trên. Chờ vài phút để IAM cập nhật trước khi deploy.
Người deploy cần các quyền source deploy và dùng runtime service account;
nếu bị từ chối quyền, xem [các role cần thiết](https://docs.cloud.google.com/run/docs/deploying-source-code).
Không cần tải service-account key JSON về máy.

## 3. Tạo secret chứa WeatherAPI key

Trong Google Cloud Console, chọn đúng project → **Secret Manager** →
**Create secret**:

- Name: `weatherapi-key`.
- Secret value: chỉ giá trị `WEATHERAPI_KEY` hiện có trong `.env`, không có
  tiền tố `WEATHERAPI_KEY=`, không có dấu nháy hoặc dòng trống.
- Tạo version đầu tiên (`1`). Không chụp màn hình phần secret value.

Cho runtime account quyền đọc **riêng secret này**:

```powershell
gcloud secrets add-iam-policy-binding weatherapi-key --member="serviceAccount:$cloudRuntimeSa" --role="roles/secretmanager.secretAccessor" --project=$cloudProjectId
```

Cloud Run đưa secret vào biến môi trường `WEATHERAPI_KEY` khi container
khởi động. Không truyền Gemini key lên server, không chép `.env` vào image.
Tham khảo [cấu hình secrets chính thức](https://docs.cloud.google.com/run/docs/configuring/services/secrets).

## 4. Deploy

Từ thư mục gốc repo:

```powershell
cd 04-lab/mcp-server

# Xem lệnh, chưa deploy hay đổi IAM
.\deploy-cloud-run.ps1 -ProjectId $cloudProjectId -Region $cloudRegion -Service $cloudService -DryRun -AllowUnauthenticated

# Deploy lab endpoint cho client hiện tại
.\deploy-cloud-run.ps1 -ProjectId $cloudProjectId -Region $cloudRegion -Service $cloudService -AllowUnauthenticated
```

`-AllowUnauthenticated` làm endpoint công khai: người có URL có thể gọi tool
và sử dụng quota WeatherAPI của bạn. Client lab hiện chưa gửi Google Cloud
ID token. Bỏ switch này nếu muốn service private; khi đó cần bổ sung IAM
authentication phía client trước khi kiểm tra. Không tự nới quyền nếu tổ
chức chặn public access.

Script dùng `gcloud run deploy --source`, Cloud Build tự build Dockerfile;
không cần Docker trên máy deploy. Nó dùng runtime account riêng, secret
version `1`, port `8080`, RAM `512Mi`, min instances `0`, max instances `2`.
Max instances không phải giới hạn tổng chi phí. Script không bật API, tạo
secret hay tự cấp IAM; bạn làm các bước setup phía trên.

Kết thúc script sẽ in:

```dotenv
MCP_SERVER_URL=https://YOUR_SERVICE_URL.run.app/mcp
```

Không tự đặt `PORT` trong cấu hình cloud: Cloud Run cấp nó. Khi có `K_SERVICE`,
server dùng HTTP stateless + JSON response để không phụ thuộc phiên lưu
trong bộ nhớ một instance. Xem [container contract](https://docs.cloud.google.com/run/docs/container-contract).

## 5. Kết nối agent và lấy bằng chứng

Sửa **chỉ dòng `MCP_SERVER_URL` trong `.env` gốc repo**, giữ nguyên hai API key.
Không tạo `.env` mới trong `mcp-client`. Dừng ADK Web cũ rồi chạy lại để lấy URL mới.

```powershell
cd ../mcp-client
uv run python -X utf8 verify_setup.py
uv run adk web --host 127.0.0.1 --port 8000
```

Checkpoint:

- `verify_setup.py` có `MCP server connected at https://...run.app/mcp`,
  đủ ba tool và `All checks passed!`.
- Chat thời tiết hiện tại và dự báo, thấy `get_current_weather` /
  `get_forecast` và câu trả lời có dữ liệu thật.
- Chụp output verify có URL Cloud Run, lưu `screenshots/05-cloud-run.png`.
  Script không in giá trị key. Không chụp nội dung `.env` hoặc Secret Manager.

Lỗi 403: kiểm tra IAM/public invocation. Lỗi 503/startup: xem Cloud Run logs,
quyền secret và trạng thái version. Cảnh báo thiếu dữ liệu WeatherAPI:
kiểm tra secret value và WeatherAPI quota.

## Build/test image ở máy cá nhân (tùy chọn)

```powershell
docker build -t weather-mcp:lab-cloud-run .
docker run --rm -p 8086:8080 -e PORT=8080 -e K_SERVICE=weather-mcp weather-mcp:lab-cloud-run
```

Lệnh test này không đưa key vào container, chỉ test startup và health.
Không dùng `--env-file` trỏ vào `.env` gốc vì file đó còn chứa Gemini key.
Server hiện tại trên 8085 và ADK 8000 không bị ảnh hưởng bởi test 8086.

Dependencies Docker được xuất từ `pyproject.toml` + `uv.lock`. Khi thay
dependency, chạy lại:

```powershell
uv export --locked --no-dev --no-emit-project --format requirements-txt --output-file requirements-cloud-run.txt
```

`.dockerignore` và `.gcloudignore` chỉ cho phép các file build cần thiết;
không upload `.env`, `.venv`, screenshots hoặc log.

## Dọn tài nguyên khi không cần demo

```powershell
gcloud run services delete $cloudService --region=$cloudRegion --project=$cloudProjectId
```

Xóa service không xóa image trong Artifact Registry hoặc secret trong
Secret Manager. Chỉ xóa các tài nguyên đó nếu chúng dành riêng cho lab.

Tài liệu: [deploy từ source](https://docs.cloud.google.com/run/docs/deploying-source-code),
[secrets](https://docs.cloud.google.com/run/docs/configuring/services/secrets),
[container contract](https://docs.cloud.google.com/run/docs/container-contract).
