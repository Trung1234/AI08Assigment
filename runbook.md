# Runbook — Screen Watcher

Hướng dẫn từng bước để cài đặt, cấu hình, chạy và xử lý sự cố Screen Watcher.

---

## Mục lục

1. [Yêu cầu hệ thống](#1-yêu-cầu-hệ-thống)
2. [Cài đặt](#2-cài-đặt)
3. [Cấu hình config.yaml](#3-cấu-hình-configyaml)
4. [Test từng bước trước khi chạy thật](#4-test-từng-bước-trước-khi-chạy-thật)
5. [Chạy workflow chính](#5-chạy-workflow-chính)
6. [Thiết lập lập lịch tự động](#6-thiết-lập-lập-lịch-tự-động)
7. [Kiểm tra kết quả & log](#7-kiểm-tra-kết-quả--log)
8. [Xử lý sự cố (Troubleshooting)](#8-xử-lý-sự-cố-troubleshooting)
9. [Chạy Unit Tests](#9-chạy-unit-tests)
10. [Cấu trúc thư mục](#10-cấu-trúc-thư-mục)

---

## 1. Yêu cầu hệ thống

| Thành phần | Yêu cầu |
|------------|---------|
| OS | Windows 10/11 hoặc Linux (Ubuntu 20.04+) |
| Python | 3.10 trở lên |
| Tesseract OCR | Đã cài và có trong PATH hoặc chỉ định đường dẫn trong config |
| Desktop session | Máy phải có màn hình hiển thị (không bị lock screen) |
| SMTP server | Có thông tin host, port, username, password |
| Quyền | Quyền đọc màn hình, quyền ghi vào thư mục data/ |

---

## 2. Cài đặt

### 2.1. Clone project

```bash
git clone <repo-url>
cd AI08Assigment
```

### 2.2. Tạo virtual environment

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2.3. Cài dependencies

```bash
pip install pyyaml pytesseract mss Pillow
```

> Nếu có file `requirements.txt`:
> ```bash
> pip install -r requirements.txt
> ```

### 2.4. Cài Tesseract OCR

**Windows:**
1. Tải installer tại: https://github.com/UB-Mannheim/tesseract/wiki
2. Cài đặt, mặc định vào `C:\Program Files\Tesseract-OCR\`
3. Ghi nhớ đường dẫn để điền vào `config.yaml`

**Linux:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
# Kiểm tra:
tesseract --version
```

### 2.5. Thiết lập biến môi trường cho SMTP password

**Không lưu password trong config file.** Dùng biến môi trường:

**Windows (CMD):**
```cmd
set SCREEN_WATCHER_SMTP_PASSWORD=your_smtp_password_here
```

**Windows (PowerShell):**
```powershell
$env:SCREEN_WATCHER_SMTP_PASSWORD = "your_smtp_password_here"
```

**Linux:**
```bash
export SCREEN_WATCHER_SMTP_PASSWORD="your_smtp_password_here"
```

> Để biến môi trường tồn tại sau reboot, thêm vào `~/.bashrc` (Linux) hoặc System Environment Variables (Windows).

---

## 3. Cấu hình config.yaml

Tạo file `config.yaml` tại thư mục gốc dự án. Dưới đây là template đầy đủ:

```yaml
# ─── Thông tin chung ───────────────────────────────────────
app:
  name: screen-watcher
  environment: production           # production / staging / dev
  timezone: Asia/Ho_Chi_Minh
  instance_id: ops-win-01-dashboard # dùng phân biệt khi nhiều máy chạy

# ─── Chụp màn hình ────────────────────────────────────────
capture:
  mode: full_screen                 # full_screen | region
  # Nếu mode: region, bật các dòng dưới:
  # monitor: 1
  # x: 100
  # y: 200
  # width: 1200
  # height: 600
  output_dir: ./data/screenshots
  image_format: png

# ─── OCR ───────────────────────────────────────────────────
ocr:
  engine: tesseract
  tesseract_cmd: C:\Program Files\Tesseract-OCR\tesseract.exe  # Windows
  # tesseract_cmd: /usr/bin/tesseract                           # Linux
  language: eng
  save_text: true
  output_dir: ./data/ocr

# ─── Rules ─────────────────────────────────────────────────
rules:
  - id: error_detected
    name: Error Detected
    type: regex
    pattern: "(ERROR|FAILED|TIMEOUT)"
    ignore_case: true
    severity: high
    owner_group: ops_team
    cooldown_minutes: 15

  - id: daily_sync_failed
    name: Daily Sync Failed
    type: all_keywords
    keywords:
      - "Failed"
      - "Daily Sync"
    severity: critical
    owner_group: zcoa_ops
    cooldown_minutes: 30

  - id: service_down
    name: Service Not Running
    type: not_contains
    keywords:
      - "Service Running"
    severity: high
    owner_group: ops_team
    cooldown_minutes: 30

# ─── Owner groups ──────────────────────────────────────────
owners:
  zcoa_ops:
    emails:
      - "owner1@company.com"
      - "owner2@company.com"
  ops_team:
    emails:
      - "ops-lead@company.com"
      - "oncall@company.com"

# ─── Email SMTP ────────────────────────────────────────────
email:
  smtp_host: smtp.company.com
  smtp_port: 587
  username: alert@company.com
  password_env: SCREEN_WATCHER_SMTP_PASSWORD   # tên biến môi trường
  from_address: alert@company.com
  use_tls: true

# ─── State (cooldown) ─────────────────────────────────────
state:
  path: ./data/state.json

# ─── Logging ───────────────────────────────────────────────
logging:
  level: INFO
  output_dir: ./data/logs
```

### Checklist trước khi chạy

- [ ] `tesseract_cmd` trỏ đúng đường dẫn Tesseract trên máy
- [ ] `capture.mode` và tọa độ region (nếu dùng) đã đúng
- [ ] `owners` có ít nhất 1 email hợp lệ
- [ ] `email.smtp_host`, `smtp_port`, `username` đúng SMTP server
- [ ] Biến môi trường `SCREEN_WATCHER_SMTP_PASSWORD` đã được set
- [ ] Thư mục `./data/` tồn tại hoặc tool có quyền tạo

---

## 4. Test từng bước trước khi chạy thật

Chạy theo thứ tự từ trên xuống. Mỗi bước xác nhận một thành phần hoạt động đúng.

### 4.1. Test chụp màn hình

```bash
python screen_watcher.py test-capture --config config.yaml
```

**Kết quả mong đợi:**
- File ảnh PNG xuất hiện trong `./data/screenshots/`
- Mở file ảnh kiểm tra: đúng vùng màn hình cần theo dõi
- Nếu chụp sai vùng → chỉnh `x`, `y`, `width`, `height` trong config

### 4.2. Test OCR

```bash
python screen_watcher.py test-ocr --config config.yaml
```

**Kết quả mong đợi:**
- File text xuất hiện trong `./data/ocr/`
- Mở file text: nội dung khớp với text trên màn hình
- Nếu OCR sai nhiều → chỉnh `capture.mode` sang `region` để thu hẹp vùng chụp

### 4.3. Test rule

```bash
python screen_watcher.py test-rule --config config.yaml
```

**Kết quả mong đợi:**
- Log hiển thị rule nào matched, rule nào không
- Kiểm tra rule matched có đúng với nội dung trên màn hình không

### 4.4. Test gửi email

```bash
python screen_watcher.py test-email --config config.yaml
```

**Kết quả mong đợi:**
- Email test gửi tới inbox của owner group
- Kiểm tra: subject, body, attachment (nếu có)
- Nếu lỗi → kiểm tra SMTP config và biến môi trường password

---

## 5. Chạy workflow chính

Khi tất cả test ở bước 4 đã pass:

```bash
python screen_watcher.py run --config config.yaml
```

### Workflow thực thi

```
Load config
    ↓
Capture screen → Save screenshot (audit)
    ↓
OCR → Save text (audit)
    ↓
Rule Engine: evaluate
    ↓
Rule matched? ──No──→ Log "no match" → End
    │Yes
    ↓
State Store: check cooldown ──In cooldown──→ Log "skipped" → End
    │OK
    ↓
Resolve owner emails ──No owner──→ Log "no owner" → End
    │OK
    ↓
Email Service: send (SMTP)
    ↓
Success? ──No──→ Log error (state KHÔNG update → retry lần sau) → End
    │Yes
    ↓
State Store: mark_sent (ghi timestamp cooldown)
    ↓
Log "email sent" → End
```

**Quan trọng:** State Store chỉ ghi `mark_sent` khi email gửi **thành công**. Nếu SMTP lỗi, state không cập nhật → lần chạy sau sẽ retry gửi email cho rule đó.

---

## 6. Thiết lập lập lịch tự động

### 6.1. Windows Task Scheduler

1. Mở **Task Scheduler** (tìm trong Start Menu)
2. Chọn **Create Basic Task**
3. Đặt tên: `Screen Watcher`
4. Trigger: **Daily** → Repeat every **5 minutes** (hoặc tần suất mong muốn)
5. Action: **Start a Program**
   - Program: `C:\path\to\python.exe` (hoặc `screen-watcher.exe` nếu đã đóng gói)
   - Arguments: `screen_watcher.py run --config config.yaml`
   - Start in: `C:\path\to\AI08Assigment`
6. Tick **"Run whether user is logged on or not"** (cần nhập password Windows)
7. Tick **"Run with highest privileges"**

**Ví dụ command đầy đủ:**
```cmd
C:\Users\admin\AppData\Local\Programs\Python\Python313\python.exe D:\AI08Assigment\screen_watcher.py run --config D:\AI08Assigment\config.yaml
```

> Lưu ý: nếu dùng biến môi trường cho SMTP password, đảm bảo biến đó có sẵn trong context của Task Scheduler (set ở System Environment Variables, không chỉ User Variables).

### 6.2. Linux Cron

```bash
# Mở crontab editor
crontab -e

# Thêm dòng — chạy mỗi 5 phút
*/5 * * * * SCREEN_WATCHER_SMTP_PASSWORD="your_password" /opt/screen-watcher/.venv/bin/python /opt/screen-watcher/screen_watcher.py run --config /opt/screen-watcher/config.yaml >> /opt/screen-watcher/data/logs/cron.log 2>&1
```

> Ghi cả stdout và stderr vào `cron.log` để dễ debug.

### 6.3. Kiểm tra scheduler đang hoạt động

**Windows:**
```cmd
schtasks /query /tn "Screen Watcher" /v
```

**Linux:**
```bash
crontab -l | grep screen-watcher
# Kiểm tra log mới nhất:
tail -20 /opt/screen-watcher/data/logs/cron.log
```

---

## 7. Kiểm tra kết quả & log

### 7.1. Thư mục output

```
data/
├── screenshots/         # Ảnh chụp màn hình mỗi lần chạy
│   ├── 20260627_100501.png
│   └── 20260627_101001.png
├── ocr/                 # Text OCR tương ứng
│   ├── 20260627_100501.txt
│   └── 20260627_101001.txt
├── logs/                # Log chi tiết
│   └── screen_watcher.log
└── state.json           # Cooldown state hiện tại
```

### 7.2. Đọc log

```bash
# Xem 30 dòng log cuối
tail -30 data/logs/screen_watcher.log
```

**Ví dụ log bình thường (rule matched, email sent):**
```
2026-06-27 10:05:00 INFO  Start Screen Watcher
2026-06-27 10:05:01 INFO  Screenshot saved: ./data/screenshots/20260627_100501.png
2026-06-27 10:05:02 INFO  OCR completed, text length=245
2026-06-27 10:05:02 INFO  Rule matched: daily_sync_failed (severity=CRITICAL)
2026-06-27 10:05:03 INFO  Email sent to owner group: zcoa_ops [owner1@company.com, owner2@company.com]
2026-06-27 10:05:03 INFO  State updated: daily_sync_failed → last_sent_at=2026-06-27T10:05:03
2026-06-27 10:05:03 INFO  Execution completed (duration=3.2s)
```

**Ví dụ log khi cooldown skip:**
```
2026-06-27 10:10:00 INFO  Start Screen Watcher
2026-06-27 10:10:01 INFO  Screenshot saved: ./data/screenshots/20260627_101001.png
2026-06-27 10:10:02 INFO  OCR completed, text length=243
2026-06-27 10:10:02 INFO  Rule matched: daily_sync_failed (severity=CRITICAL)
2026-06-27 10:10:02 INFO  Skip rule 'daily_sync_failed' — in cooldown (30 min, last sent 10:05:03)
2026-06-27 10:10:02 INFO  Execution completed (duration=2.1s)
```

**Ví dụ log khi không match:**
```
2026-06-27 10:15:00 INFO  Start Screen Watcher
2026-06-27 10:15:01 INFO  Screenshot saved: ./data/screenshots/20260627_101501.png
2026-06-27 10:15:02 INFO  OCR completed, text length=198
2026-06-27 10:15:02 INFO  No rules matched
2026-06-27 10:15:02 INFO  Execution completed (duration=2.0s)
```

### 7.3. Kiểm tra cooldown state

```bash
cat data/state.json
```

```json
{
  "daily_sync_failed": {
    "last_sent_at": "2026-06-27T10:05:03"
  },
  "error_detected": {
    "last_sent_at": "2026-06-27T09:45:12"
  }
}
```

### 7.4. Reset cooldown (khi cần gửi lại ngay)

Nếu muốn force gửi lại email cho một rule mà không đợi hết cooldown:

```bash
# Cách 1: Xóa entry của rule cụ thể — sửa file state.json, xóa dòng rule đó

# Cách 2: Xóa toàn bộ cooldown state
rm data/state.json
# Hoặc Windows:
del data\state.json
```

Lần chạy tiếp theo, rule sẽ gửi email bình thường vì không còn cooldown record.

---

## 8. Xử lý sự cố (Troubleshooting)

### 8.1. Screenshot đen / trống

| Nguyên nhân | Cách xử lý |
|-------------|-----------|
| Máy bị lock screen | Đăng nhập lại, đảm bảo desktop session đang active |
| Remote Desktop bị disconnect | Dùng `tscon` để giữ session hoặc chạy dưới console session |
| Sai monitor index | Đổi `capture.monitor` trong config (thử 0, 1, 2) |
| Sai tọa độ region | Chạy `test-capture` → mở ảnh kiểm tra → chỉnh tọa độ |

### 8.2. OCR cho kết quả sai / rác

| Nguyên nhân | Cách xử lý |
|-------------|-----------|
| Chụp toàn màn hình (quá nhiều noise) | Chuyển `capture.mode` sang `region`, chỉ chụp vùng cần thiết |
| Font nhỏ / mờ | Tăng kích thước region hoặc zoom UI trước khi chụp |
| Ngôn ngữ sai | Đổi `ocr.language` (ví dụ `vie` cho tiếng Việt) |
| Tesseract không tìm thấy | Kiểm tra `ocr.tesseract_cmd` trỏ đúng đường dẫn |

### 8.3. Rule không match dù text đúng

| Nguyên nhân | Cách xử lý |
|-------------|-----------|
| Case sensitive | Thêm `ignore_case: true` vào rule |
| OCR sai ký tự | Chạy `test-ocr` xem text thật sự là gì → chỉnh keyword cho khớp |
| Rule type sai | `contains` = bất kỳ keyword, `all_keywords` = phải có TẤT CẢ |
| Regex sai cú pháp | Chạy `test-rule` → log sẽ báo regex invalid |

### 8.4. Email không gửi được

| Nguyên nhân | Cách xử lý |
|-------------|-----------|
| SMTP authentication failed | Kiểm tra `email.username` và biến môi trường password |
| Connection refused | Kiểm tra `smtp_host`, `smtp_port`, firewall |
| TLS error | Thử `use_tls: false` nếu SMTP server không hỗ trợ STARTTLS |
| Timeout | Tăng `timeout_seconds` trong email config |
| Password env không set | Kiểm tra `echo %SCREEN_WATCHER_SMTP_PASSWORD%` (Windows) hoặc `echo $SCREEN_WATCHER_SMTP_PASSWORD` (Linux) |

**Lưu ý:** Khi email gửi fail, State Store **KHÔNG** cập nhật → lần chạy tiếp theo sẽ tự động retry.

### 8.5. Email bị spam liên tục

| Nguyên nhân | Cách xử lý |
|-------------|-----------|
| `cooldown_minutes` = 0 hoặc quá nhỏ | Tăng lên (khuyến nghị >= 15 phút) |
| State file bị xóa nhầm | Kiểm tra `data/state.json` có tồn tại |
| State file bị corrupt | Xóa `state.json` → tool sẽ tạo lại (nhưng sẽ gửi lại 1 lần) |

### 8.6. Tool crash / không chạy

```bash
# Kiểm tra Python
python --version

# Kiểm tra dependencies
pip list | grep -E "pytesseract|mss|Pillow|pyyaml"

# Chạy manual với verbose
python screen_watcher.py run --config config.yaml 2>&1

# Kiểm tra config YAML hợp lệ
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

---

## 9. Chạy Unit Tests

Các module Rule Engine, State Store, Email Service, Notification Service đều có unit test.

```bash
# Chạy tất cả tests
python -m unittest discover -v

# Chạy từng module
python -m unittest tests.test_rule_engine -v
python -m unittest tests.test_state_store -v
python -m unittest tests.test_email_service -v
python -m unittest tests.test_notification_service -v
```

**Kết quả mong đợi:**
```
Ran 50 tests in 0.5s

OK
```

> Tests không cần Tesseract OCR hay SMTP server thật — tất cả đều dùng mock.

---

## 10. Cấu trúc thư mục

```
AI08Assigment/
├── config.yaml                     # Config chính (tạo theo hướng dẫn mục 3)
├── README.md                       # Tổng quan sản phẩm
├── runbook.md                      # File này
├── pc.md                           # Product Concept gốc
│
├── screen_watcher/                 # Source code chính
│   ├── __init__.py
│   ├── models.py                   # Rule, OwnerGroup, MatchResult, EmailConfig
│   ├── rule_engine.py              # Evaluate OCR text theo rules
│   ├── state_store.py              # Cooldown state (JSON)
│   ├── email_service.py            # SMTP email sender
│   └── notification_service.py     # Orchestrator: cooldown → owner → email → state
│
├── tests/                          # Unit tests (50 tests)
│   ├── __init__.py
│   ├── test_rule_engine.py
│   ├── test_state_store.py
│   ├── test_email_service.py
│   └── test_notification_service.py
│
├── docs/
│   └── flow_rule_engine_email.md   # Flow diagram chi tiết
│
└── data/                           # Output (tự động tạo khi chạy)
    ├── screenshots/
    ├── ocr/
    ├── logs/
    └── state.json
```
