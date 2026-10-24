# Báo cáo thực hành IoT - Buổi 3

## Lập trình Python với giao thức CoAP

Bài thực hành gồm 3 chương trình CoAP Server/Client, sử dụng thư viện `aiocoap`:

- **Bài 1**: Gửi/nhận thông điệp CoAP cơ bản bằng GET và POST.
- **Bài 2**: Mô phỏng cảm biến nhiệt độ - độ ẩm, giám sát định kỳ và cảnh báo.
- **Bài 3**: Giám sát và điều khiển đèn thông minh bằng GET/PUT và cơ chế **CoAP Observe**.

---

## 1. Thông tin sinh viên

| Nội dung | Thông tin |
|---|---|
| Họ và tên | .................................................. |
| Mã sinh viên | .................... |
| Lớp | .................... |
| Môn học | Internet of Things (IoT) |
| Buổi thực hành | Buổi 3 - Lập trình Python với giao thức CoAP |

> Sinh viên điền thông tin cá nhân/nhóm trước khi nộp bài.

---

## 2. Môi trường thực hiện

| Thành phần | Phiên bản / Ghi chú |
|---|---|
| Hệ điều hành | Windows 11 (chương trình cũng chạy trên Linux/macOS) |
| Python | 3.13.9 |
| Thư viện | `aiocoap` 0.4.17 |
| Giao thức | CoAP over UDP |
| Cổng mặc định | `5683` |

Cài đặt thư viện:

```powershell
cd CoAP_Lab
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell chặn kích hoạt môi trường ảo:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Có thể cài trực tiếp không cần môi trường ảo:

```powershell
python -m pip install aiocoap==0.4.17
```

Kiểm tra:

```powershell
python -c "import aiocoap; print(aiocoap.__version__)"
```

---

## 3. Cấu trúc thư mục

```text
CoAP_Lab/
|
|-- bai1/
|   |-- coap_server_bai1.py
|   |-- coap_client_bai1.py
|
|-- bai2/
|   |-- sensor_server_bai2.py
|   |-- monitor_client_bai2.py
|
|-- bai3/
|   |-- light_server_bai3.py
|   |-- light_controller_bai3.py
|   |-- light_monitor_bai3.py
|
|-- docs/
|   |-- logs/                 # Log minh chứng chương trình đã chạy
|   |-- screenshots/          # Có thể bổ sung ảnh chụp màn hình
|
|-- requirements.txt
|-- .gitignore
|-- README.md
```

---

## 4. Bài 1 - Gửi và nhận thông điệp CoAP cơ bản

### 4.1. Tài nguyên

```text
coap://localhost:5683/iot/lab/message
```

### 4.2. Cách chạy

Mở **Terminal 1** - chạy Server:

```powershell
python bai1/coap_server_bai1.py
```

Mở **Terminal 2** - chạy Client:

```powershell
python bai1/coap_client_bai1.py
```

Có thể truyền thông tin sinh viên:

```powershell
python bai1/coap_client_bai1.py --name "Nguyen Van A" --mssv B23DCCN001
```

Gửi nhiều thông điệp POST liên tiếp:

```powershell
python bai1/coap_client_bai1.py --repeat 5
```

Kiểm tra lỗi timeout khi Server không chạy:

```powershell
python bai1/coap_client_bai1.py --timeout 2
```

### 4.3. Chức năng đã thực hiện

- GET trả về lời chào mặc định `Xin chao tu CoAP Server`.
- POST nhận thông điệp, hiển thị nội dung và thời điểm nhận.
- Server trả về `2.04 Changed` kèm xác nhận `Server da nhan thong diep`.
- Server lưu thông điệp POST gần nhất; GET tiếp theo trả lại thông điệp đó.
- Tự động trả `4.04 Not Found` khi truy cập tài nguyên không tồn tại.
- Client xử lý timeout, lỗi mạng và hiển thị mã phản hồi CoAP.

### 4.4. Kết quả mẫu

Client (`docs/logs/bai1_client.log`):

```text
Sending GET request...
URI: coap://127.0.0.1:5683/iot/lab/message

Response:
Code: 2.05 Content
Payload: Xin chao tu CoAP Server

Sending POST request...
Payload: Xin chao tu CoAP Client - B23DCCN001 - Nguyen Van A

Response:
Code: 2.04 Changed
Payload: Server da nhan thong diep
```

Server (`docs/logs/bai1_server.log`):

```text
GET request received: /iot/lab/message
Time: 17:06:34
Tra ve thong diep: Xin chao tu CoAP Server

POST request received:
Payload: Xin chao tu CoAP Client - B23DCCN001 - Nguyen Van A
Time: 17:06:34
Da luu thong diep thu 1.
```

Log kiểm tra tài nguyên không tồn tại: `docs/logs/bai1_404.log`

```text
GET /iot/lab/khong_ton_tai
Code: 4.04 Not Found
```

Log kiểm tra timeout: `docs/logs/bai1_timeout.log`

```text
ERROR: Het thoi gian cho phan hoi sau 2 giay.
Kiem tra Server da chay chua va dia chi IP/cong co dung khong.
```

---

## 5. Bài 2 - Mô phỏng cảm biến nhiệt độ và độ ẩm

### 5.1. Tài nguyên

```text
coap://localhost:5683/iot/lab/sensor01/data
coap://localhost:5683/iot/lab/sensor02/data
coap://localhost:5683/iot/lab/sensor03/data
coap://localhost:5683/iot/lab/sensors       (tổng hợp - phần mở rộng)
```

### 5.2. Cách chạy

**Terminal 1** - chạy Sensor Server:

```powershell
python bai2/sensor_server_bai2.py
```

**Terminal 2** - chạy Monitoring Client:

```powershell
python bai2/monitor_client_bai2.py --device sensor01
```

Giám sát cảm biến đang có cảnh báo (sensor03 được khởi tạo với nhiệt độ cao, độ ẩm thấp):

```powershell
python bai2/monitor_client_bai2.py --device sensor03
```

Chạy một số lần rồi dừng (phục vụ kiểm thử):

```powershell
python bai2/monitor_client_bai2.py --device sensor03 --count 5
```

### 5.3. Dữ liệu JSON

```json
{
  "device_id": "sensor01",
  "temperature": 28.5,
  "humidity": 65.2,
  "timestamp": "2026-10-24T17:06:49"
}
```

Server trả về `Content-Format: application/json` (giá trị 50).

### 5.4. Chức năng đã thực hiện

- Mô phỏng 3 cảm biến `sensor01`, `sensor02`, `sensor03`.
- Tự động cập nhật dữ liệu mỗi 3 giây bằng random walk trong khoảng hợp lý.
- Client GET định kỳ mỗi 3 giây, phân tích JSON và hiển thị:
  - Mã thiết bị.
  - Nhiệt độ.
  - Độ ẩm.
  - Thời điểm nhận.
- Cảnh báo khi nhiệt độ > 35°C hoặc độ ẩm < 40%.
- Ghi dữ liệu ra CSV: `bai2/logs/sensor_data.csv`.
- Đếm số lần GET, số lỗi và tính thời gian phản hồi trung bình.
- Xử lý timeout/lỗi mạng, tiếp tục giám sát thay vì dừng chương trình.

### 5.5. Kết quả mẫu

Cảnh báo (`docs/logs/bai2_client.log`):

```text
[17:06:49] Received sensor data

Device: sensor03
Temperature: 36.1 C
Humidity: 38.7 %

CANH BAO: Nhiet do cao
CANH BAO: Do am thap

------------------------------
```

Trạng thái bình thường (`docs/logs/bai2_client_normal.log`):

```text
Device: sensor01
Temperature: 27.7 C
Humidity: 63.6 %

Trang thai: Binh thuong
```

Tổng kết:

```text
So lan GET: 2
Thanh cong: 2 | Loi: 0
Thoi gian phan hoi trung binh: 2.94 ms
```

Dữ liệu CSV: `docs/logs/bai2_sensor_data.csv`

```csv
received_at,device_id,temperature_c,humidity_percent,response_time_ms,status,alert
2026-10-24T17:06:49,sensor03,36.1,38.7,3.8,ALERT,CANH BAO: Nhiet do cao | CANH BAO: Do am thap
```

Log Server cập nhật định kỳ: `docs/logs/bai2_server.log`.

Log mất kết nối: `docs/logs/bai2_timeout.log`.

---

## 6. Bài 3 - Giám sát và điều khiển đèn thông minh bằng CoAP Observe

### 6.1. Tài nguyên

```text
coap://localhost:5683/iot/lab/light01/status
coap://localhost:5683/iot/lab/fan01/status     (phần mở rộng)
coap://localhost:5683/iot/lab/pump01/status    (phần mở rộng)
```

### 6.2. Cách chạy

Mở **3 terminal**.

**Terminal 1** - Smart Light Server:

```powershell
python bai3/light_server_bai3.py
```

**Terminal 2** - Monitoring Client (đăng ký Observe):

```powershell
python bai3/light_monitor_bai3.py
```

**Terminal 3** - Controller Client (nhập lệnh ON/OFF/STATUS/EXIT):

```powershell
python bai3/light_controller_bai3.py
```

Có thể chạy Controller không tương tác để kiểm thử nhanh:

```powershell
python bai3/light_controller_bai3.py --commands ON,STATUS,OFF,STATUS,EXIT
```

Điều khiển thiết bị khác:

```powershell
python bai3/light_controller_bai3.py --device fan01
```

### 6.3. Giao thức trao đổi

PUT điều khiển:

```json
{
  "device_id": "light01",
  "command": "ON"
}
```

GET / Observe trả về:

```json
{
  "device_id": "light01",
  "status": "ON",
  "timestamp": "2026-10-24T17:08:00"
}
```

### 6.4. Chức năng đã thực hiện

- Server quản lý trạng thái đèn, mặc định là `OFF`.
- GET trả trạng thái hiện tại dưới dạng JSON.
- PUT nhận lệnh `ON`/`OFF`, kiểm tra `device_id` và lệnh hợp lệ.
- Trả `2.04 Changed` khi điều khiển thành công.
- Trả `4.00 Bad Request` khi JSON sai, sai `device_id` hoặc lệnh không hợp lệ.
- **CoAP Observe**:
  - Client đăng ký bằng `Observe: 0`.
  - Server dùng `ObservableResource` và `updated_state()` để thông báo.
  - Monitoring Client **không dùng vòng lặp GET định kỳ**.
  - Hỗ trợ nhiều observer cùng lúc.
- Ghi nhật ký thay đổi trạng thái: `bai3/logs/light_state.log`.
- Hỗ trợ nhiều thiết bị: `light01`, `fan01`, `pump01`.

### 6.5. Kết quả mẫu

Server (`docs/logs/bai3_server.log`):

```text
CoAP Smart Light Server started...
Resource: coap://127.0.0.1:5683/iot/lab/light01/status

New Observe registration received (light01)
Observers hien tai cua light01: 1

PUT request received:
Device: light01
Command: ON
Light state changed: OFF -> ON
Notify observers: ON
```

Controller (`docs/logs/bai3_controller.log`):

```text
Sending PUT request...
Response Code: 2.04 Changed
Da bat den light01

Sending GET request...
Response:
{"device_id":"light01","status":"ON","timestamp":"2026-10-24T17:08:00"}
```

Monitoring Client (`docs/logs/bai3_monitor.log`):

```text
Registering CoAP Observe...
Observe registration successful

[17:07:47] Initial State
Device: light01
Status: OFF

[17:08:00] State Updated
Device: light01
Status: ON

[17:08:00] State Updated
Device: light01
Status: OFF
```

Kiểm tra lệnh không hợp lệ (`docs/logs/bai3_invalid_command.log`):

```text
Code: 4.00 Bad Request
Payload: Lenh khong hop le, chi chap nhan ON hoac OFF
```

Nhật ký trạng thái (`docs/logs/bai3_state_changes.log`):

```csv
2026-10-24T17:08:00,light01,OFF,ON
2026-10-24T17:08:00,light01,ON,OFF
```

---

## 7. Bảng tổng hợp URI và phương thức

| Bài | URI | Phương thức | Mô tả |
|---|---|---|---|
| 1 | `/iot/lab/message` | GET | Lấy lời chào / thông điệp POST gần nhất |
| 1 | `/iot/lab/message` | POST | Gửi thông điệp từ Client |
| 2 | `/iot/lab/sensor01/data` | GET | Dữ liệu cảm biến 01 |
| 2 | `/iot/lab/sensor02/data` | GET | Dữ liệu cảm biến 02 |
| 2 | `/iot/lab/sensor03/data` | GET | Dữ liệu cảm biến 03 |
| 2 | `/iot/lab/sensors` | GET | Dữ liệu tổng hợp các cảm biến |
| 3 | `/iot/lab/light01/status` | GET, PUT, Observe | Trạng thái đèn 01 |
| 3 | `/iot/lab/fan01/status` | GET, PUT, Observe | Trạng thái quạt 01 |
| 3 | `/iot/lab/pump01/status` | GET, PUT, Observe | Trạng thái bơm 01 |

---

## 8. Kết quả kiểm thử

| STT | Nội dung kiểm thử | Kết quả | Minh chứng |
|---|---|---|---|
| 1 | Server Bài 1 khởi động cổng 5683 | Thành công | `bai1_server.log` |
| 2 | Client GET nhận `2.05 Content` | Thành công | `bai1_client.log` |
| 3 | Client POST nhận `2.04 Changed` | Thành công | `bai1_client.log` |
| 4 | Server lưu thông điệp POST gần nhất | Thành công | `bai1_server.log` |
| 5 | Truy cập tài nguyên không tồn tại | `4.04 Not Found` | `bai1_404.log` |
| 6 | Client xử lý timeout khi Server tắt | Thành công | `bai1_timeout.log` |
| 7 | Server Bài 2 cập nhật mỗi 3 giây | Thành công | `bai2_server.log` |
| 8 | Client nhận và phân tích JSON | Thành công | `bai2_client.log` |
| 9 | Cảnh báo nhiệt độ cao, độ ẩm thấp | Thành công | `bai2_client.log` |
| 10 | Trạng thái bình thường | Thành công | `bai2_client_normal.log` |
| 11 | Ghi dữ liệu CSV | Thành công | `bai2_sensor_data.csv` |
| 12 | Client Bài 2 xử lý mất kết nối | Thành công | `bai2_timeout.log` |
| 13 | Server Bài 3 khởi động, trạng thái OFF | Thành công | `bai3_server.log` |
| 14 | Client Observe đăng ký thành công | Thành công | `bai3_monitor.log` |
| 15 | PUT ON đổi trạng thái và thông báo | Thành công | `bai3_server.log`, `bai3_monitor.log` |
| 16 | PUT OFF đổi trạng thái và thông báo | Thành công | `bai3_server.log`, `bai3_monitor.log` |
| 17 | GET STATUS trả JSON hiện tại | Thành công | `bai3_controller.log` |
| 18 | Lệnh không hợp lệ trả `4.00` | Thành công | `bai3_invalid_command.log` |
| 19 | Ghi nhật ký thay đổi trạng thái | Thành công | `bai3_state_changes.log` |

---

## 9. Lưu ý khi chạy trên Windows và trong LAN

### 9.1. Địa chỉ `localhost`

Trên một số máy Windows, `localhost` được phân giải thành `::1` (IPv6), trong khi Server CoAP trong bài chạy trên IPv4. Vì vậy các Client có hàm `resolve_host()` tự đổi `localhost` thành `127.0.0.1` khi tạo URI thực tế. URI hiển thị cho người dùng vẫn giữ `localhost` đúng theo yêu cầu.

### 9.2. Chạy trên hai máy trong cùng LAN

Máy chạy Server lấy IP LAN, ví dụ `192.168.1.10`:

```powershell
python bai3/light_server_bai3.py --host 192.168.1.10
```

Máy Client trỏ tới IP đó:

```powershell
python bai3/light_controller_bai3.py --host 192.168.1.10
python bai3/light_monitor_bai3.py --host 192.168.1.10
```

Mở tường lửa UDP cổng 5683 trên máy Server (PowerShell quyền Administrator):

```powershell
New-NetFirewallRule -DisplayName "CoAP Lab UDP 5683" -Direction Inbound -Protocol UDP -LocalPort 5683 -Action Allow
```

> **Không dùng `--host 0.0.0.0`** với cấu hình `aiocoap` hiện tại trên Windows: transport `simplesocketserver` không cho phép bind địa chỉ any-address, còn transport `udp6` gặp lỗi `IPV6_RECVPKTINFO` trên Windows. Hãy truyền địa chỉ IPv4 cụ thể của máy Server.

---

## 10. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân / Cách xử lý |
|---|---|
| `ERROR: Loi mang: Network error` | Server chưa chạy hoặc sai IP/cổng. Khởi động Server trước. |
| `ERROR: Het thoi gian cho phan hoi` | Sai địa chỉ, firewall chặn UDP 5683, hoặc Server không phản hồi. |
| `Address already in use` | Cổng 5683 đang bị chương trình khác chiếm. Dùng `--port 5684` cho cả Server và Client. |
| Client Observe báo không hỗ trợ | Đang chạy sai Server (phải là `light_server_bai3.py`) hoặc tài nguyên không tồn tại. |
| Không cài được `aiocoap` | Kiểm tra Python >= 3.9 và chạy `python -m pip install --upgrade pip` trước. |
| Tiếng Việt bị lỗi font | Các thông báo runtime dùng ASCII; README dùng UTF-8. Có thể đổi terminal sang UTF-8. |

---

## 11. Các phần mở rộng đã triển khai

### Bài 1

- Gửi nhiều POST liên tiếp bằng `--repeat`.
- Lưu thông điệp POST gần nhất và trả lại khi GET.
- Tự động trả `4.04` cho tài nguyên không tồn tại.
- Xử lý timeout và lỗi mạng ở Client.

### Bài 2

- Thêm trường `timestamp` trong JSON.
- Mô phỏng 3 cảm biến và cho phép chọn bằng `--device`.
- Ghi dữ liệu ra CSV.
- Đếm số lần GET, số lỗi và tính thời gian phản hồi trung bình.
- Tài nguyên tổng hợp `/iot/lab/sensors`.

### Bài 3

- Kiểm tra lệnh không hợp lệ, trả `4.00 Bad Request`.
- Hỗ trợ nhiều observer cùng lúc.
- Mô phỏng nhiều thiết bị `light01`, `fan01`, `pump01`.
- Thêm `timestamp` vào payload.
- Ghi nhật ký thay đổi trạng thái ra file.

---

## 12. Nộp bài qua GitHub

```powershell
cd CoAP_Lab
git init
git add .
git commit -m "CoAP Lab - Bai 1, 2, 3"
git branch -M main
git remote add origin https://github.com/<username>/<repo-name>.git
git push -u origin main
```

Trước khi nộp:

- Điền thông tin sinh viên ở Mục 1.
- Kiểm tra lại toàn bộ log trong `docs/logs/`.
- Có thể bổ sung ảnh chụp màn hình vào `docs/screenshots/`.
- Không commit thư mục `.venv/` và `__pycache__/` (đã có `.gitignore`).

---

## 13. Tài liệu tham khảo

- RFC 7252 - Constrained Application Protocol (CoAP).
- RFC 7641 - Observing Resources in CoAP.
- aiocoap Documentation: <https://aiocoap.readthedocs.io/>
