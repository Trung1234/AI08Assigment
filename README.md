# Screen Watcher

> Biến màn hình thành một nguồn dữ liệu giám sát tự động.

**Screen Watcher** là một tool Python dạng CLI, được kích hoạt định kỳ bằng **Windows Task Scheduler** hoặc **Linux cron**. Tool chụp màn hình, bóc tách text bằng **OCR**, kiểm tra nội dung theo **rule** đã cấu hình và **gửi email cảnh báo** cho owner khi phát hiện trạng thái cần theo dõi.

Sản phẩm phù hợp với các hệ thống **legacy / không có API / không có webhook / không có log collector**, nơi thông tin quan trọng chỉ hiển thị trên UI và phải quan sát thủ công.

> ⚠️ Screen Watcher **không thay thế** monitoring chuẩn (Prometheus, Grafana, Datadog, Zabbix, ELK). Nó là giải pháp giám sát **tạm thời / bán tự động** cho các trường hợp chưa thể tích hợp monitoring chuẩn.

---

## Mục lục

- [Bối cảnh & vấn đề](#bối-cảnh--vấn-đề)
- [Người dùng mục tiêu](#người-dùng-mục-tiêu)
- [Luồng hoạt động](#luồng-hoạt-động)
- [Tính năng MVP](#tính-năng-mvp)
- [Cài đặt](#cài-đặt)
- [Sử dụng (CLI)](#sử-dụng-cli)
- [Cấu hình](#cấu-hình)
- [Lập lịch (Scheduler)](#lập-lịch-scheduler)
- [Kiến trúc module](#kiến-trúc-module)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Logging & Audit](#logging--audit)
- [Rủi ro & giới hạn](#rủi-ro--giới-hạn)
- [Roadmap](#roadmap)

---

## Bối cảnh & vấn đề

Trong nhiều hệ thống vận hành thực tế, không phải lúc nào cũng có API, webhook, log tập trung hoặc khả năng tích hợp monitoring. Một số thông tin quan trọng chỉ xuất hiện trên dashboard web nội bộ, ứng dụng desktop, terminal session, màn hình batch job, monitoring UI cũ hoặc hệ thống legacy.

Điều này khiến đội vận hành phải **kiểm tra bằng mắt**, dễ bỏ sót cảnh báo, tốn nhân lực. Screen Watcher mô phỏng thao tác quan sát của con người:

1. Chụp màn hình theo lịch
2. Đọc text từ ảnh
3. Kiểm tra text theo rule nghiệp vụ
4. Gửi email nếu phát hiện nội dung cần theo dõi

---

## Người dùng mục tiêu

| Nhóm | Mục đích sử dụng |
|------|------------------|
| **Operation Team** | Theo dõi trạng thái màn hình vận hành, dashboard, batch job, màn hình cảnh báo |
| **DevOps Team** | Giám sát tạm thời các hệ thống chưa tích hợp được Prometheus / Grafana / log collector |
| **DBA Team** | Theo dõi dashboard database, job backup, replication, sync, cảnh báo lỗi |
| **Support Team** | Theo dõi ứng dụng nghiệp vụ để phát hiện lỗi, pending, failed, timeout |
| **Business Owner** | Nhận email khi màn hình xuất hiện trạng thái cần quan tâm (giao dịch lỗi, đơn hàng treo, đồng bộ thất bại) |

---

## Luồng hoạt động

```
Windows Task Scheduler / Linux Cron
        ↓
Run Python CLI
        ↓
Load config (YAML + validate)
        ↓
Capture screen / region
        ↓
Save screenshot (Audit)
        ↓
OCR image → text
        ↓
Save OCR text (Audit)
        ↓
Rule Engine: evaluate rules
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
Email Service: send email (SMTP)
        ↓
Send success? ──No──→ Log error (state KHÔNG update, lần sau retry) → End
        │Yes
        ↓
State Store: mark_sent (ghi cooldown timestamp)
        ↓
Log "email sent" → End
```

**Lưu ý quan trọng:** State Store được **đọc trước** (check cooldown) và chỉ **ghi sau** khi email gửi thành công. Nếu SMTP lỗi, state không cập nhật → lần chạy tiếp theo sẽ tự động retry gửi email cho rule đó.

---

## Tính năng MVP

- ✅ Python CLI runner
- ✅ Config bằng **YAML** (validate bằng Pydantic)
- ✅ Chụp **toàn màn hình** hoặc **theo vùng (region)**
- ✅ OCR bằng **Tesseract**
- ✅ Rule type: `contains`, `not_contains`, `regex`, `all_keywords`, `any_keywords`
- ✅ Rule có **severity**
- ✅ Owner cấu hình theo **group**
- ✅ Gửi email qua **SMTP**
- ✅ **Cooldown** chống spam email
- ✅ Lưu screenshot, OCR text và execution log (audit)
- ✅ Chạy manual để test từng bước cấu hình

**Ngoài phạm vi MVP:** Web UI quản lý rule, dashboard history, tích hợp Slack/Teams/Telegram, AI classification, multi-tenant, database server tập trung, agent quản lý tập trung.

---

## Cài đặt

### Yêu cầu

- Python 3.10+
- **Tesseract OCR** đã được cài đặt
  - Windows: tải tại [UB Mannheim Tesseract build](https://github.com/UB-Mannheim/tesseract/wiki)
  - Linux: `sudo apt-get install tesseract-ocr`
- Môi trường có **desktop session** hợp lệ (cần để chụp màn hình)

### Cài đặt dependencies

```bash
git clone <repo-url>
cd screen-watcher
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux
source .venv/bin/activate

pip install -r requirements.txt
```

---

## Sử dụng (CLI)

```bash
# Chạy toàn bộ workflow
python screen_watcher.py run --config config.yaml

# Các lệnh test cấu hình từng bước
python screen_watcher.py test-capture --config config.yaml   # Chụp thử màn hình
python screen_watcher.py test-ocr     --config config.yaml   # Kiểm tra OCR
python screen_watcher.py test-rule    --config config.yaml   # Kiểm tra rule với OCR text
python screen_watcher.py test-email   --config config.yaml   # Gửi email test cho owner
```

Khi đóng gói thành executable (PyInstaller):

```bash
screen-watcher.exe run --config config.yaml
```

---

## Cấu hình

Toàn bộ hành vi (owner, rule, email, capture region, runtime) được điều khiển qua file `config.yaml` — **không hard-code trong source**.

```yaml
app:
  name: screen-watcher
  environment: production
  timezone: Asia/Ho_Chi_Minh
  instance_id: ops-win-01-dashboard

capture:
  mode: region            # full_screen | region
  monitor: 1
  x: 100
  y: 200
  width: 1200
  height: 600
  output_dir: ./data/screenshots
  image_format: png

ocr:
  engine: tesseract
  tesseract_cmd: C:\Program Files\Tesseract-OCR\tesseract.exe
  language: eng
  save_text: true
  output_dir: ./data/ocr

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

owners:
  zcoa_ops:
    emails:
      - "owner1@company.com"
      - "owner2@company.com"
  ops_team:
    emails:
      - "dba-owner@company.com"

email:
  smtp_host: smtp.company.com
  smtp_port: 587
  username: alert@company.com
  password_env: SCREEN_WATCHER_SMTP_PASSWORD   # đọc từ biến môi trường
  from_address: alert@company.com
```

### Rule types

| Rule type | Ý nghĩa |
|-----------|---------|
| `contains` | Text chứa một hoặc nhiều keyword |
| `not_contains` | Text **không** chứa keyword bắt buộc |
| `regex` | Text match regular expression |
| `all_keywords` | Phải chứa **tất cả** keyword |
| `any_keywords` | Chỉ cần chứa **một trong** các keyword |

### Cooldown (chống spam)

Nếu scheduler chạy mỗi 5 phút và màn hình vẫn hiển thị lỗi, tool có thể gửi email liên tục. `cooldown_minutes` đảm bảo một rule chỉ gửi lại email sau khoảng thời gian quy định. State được lưu trong file JSON (MVP) hoặc SQLite (bản mở rộng):

```json
{
  "daily_sync_failed": {
    "last_sent_at": "2026-06-27T10:00:00"
  }
}
```

### Bảo mật

- **Không** lưu password SMTP trực tiếp trong config — dùng `password_env` trỏ tới biến môi trường.

---

## Lập lịch (Scheduler)

Screen Watcher **không tự xây scheduler**. Tool chạy tốt ở dạng CLI để scheduler bên ngoài gọi — không cần service chạy nền, mỗi lần chạy là một execution độc lập, dễ debug.

### Windows Task Scheduler

```bat
python C:\tools\screen-watcher\screen_watcher.py run --config C:\tools\screen-watcher\config.yaml
```

### Linux Cron (mỗi 5 phút)

```cron
*/5 * * * * /usr/bin/python3 /opt/screen-watcher/screen_watcher.py run --config /opt/screen-watcher/config.yaml
```

---

## Kiến trúc module

```
screen_watcher/
  __init__.py
  main.py                  # Entry point
  cli.py                   # Xử lý command line argument
  config_loader.py         # Đọc và validate config
  screen_capture.py        # Chụp màn hình
  ocr_service.py           # OCR ảnh thành text
  rule_engine.py           # Đánh giá text theo rule
  notification_service.py  # Điều phối gửi cảnh báo
  email_service.py         # Gửi email SMTP
  state_store.py           # Lưu cooldown state
  audit_store.py           # Lưu screenshot, OCR text, result
  logger.py                # Cấu hình logging
  models.py                # Định nghĩa schema bằng Pydantic
```

---

## Công nghệ sử dụng

| Thành phần | Công nghệ |
|------------|-----------|
| CLI | Typer hoặc argparse |
| Config | YAML |
| Config validation | Pydantic |
| Screen capture | mss hoặc pyautogui |
| OCR | pytesseract + Tesseract OCR |
| Image preprocessing | Pillow, OpenCV (tùy nhu cầu) |
| Email | smtplib hoặc aiosmtplib |
| State | JSON file (MVP), SQLite (mở rộng) |
| Logging | Python logging |
| Packaging | PyInstaller |
| Scheduler | Windows Task Scheduler / cron |

---

## Logging & Audit

Mỗi lần chạy ghi log đầy đủ: start time, config path, capture result, screenshot path, OCR text path, rule evaluation result, email sent/skipped, error (nếu có), end time, duration.

```
2026-06-27 10:05:00 INFO Start Screen Watcher
2026-06-27 10:05:01 INFO Screenshot saved: ./data/screenshots/20260627_100501.png
2026-06-27 10:05:02 INFO OCR completed, text length=245
2026-06-27 10:05:02 INFO Rule matched: daily_sync_failed
2026-06-27 10:05:03 INFO Email sent to owner group: zcoa_ops
2026-06-27 10:05:03 INFO Execution completed
```

### Ví dụ email cảnh báo

```
Subject: [Screen Watcher][CRITICAL] Daily Sync Failed

Rule matched: Daily Sync Failed
Severity: CRITICAL
Detected at: 2026-06-27 10:05:00
Host: OPS-WIN-01
Config: production-dashboard
Capture mode: region

Matched text:
Status: Failed
Job Name: Daily Sync
Error: Connection timeout

Action: Please check the dashboard or related batch job.
Attachment: screenshot image, OCR text file (nếu cần)
```

---

## Rủi ro & giới hạn

| Rủi ro | Hướng xử lý |
|--------|-------------|
| OCR sai (font nhỏ, ảnh mờ) | Cấu hình region, tăng độ phân giải, tiền xử lý ảnh |
| UI thay đổi (vùng chụp lệch) | Dùng `test-capture` để cập nhật tọa độ nhanh |
| Spam email | Bắt buộc `cooldown` |
| Máy bị lock screen | Cần session GUI hợp lệ / môi trường có desktop |
| False positive | Dùng `all_keywords`, `regex`, ignore pattern |
| SMTP lỗi | Log lỗi, retry giới hạn |
| Bảo mật password | Dùng `password_env` |

**Không phù hợp khi:** cần realtime monitoring nghiêm ngặt; hệ thống đã có API monitoring đầy đủ; cần độ chính xác tuyệt đối (giao dịch tài chính core); không thể duy trì desktop session.

---

## Roadmap

- **Phase 1 — MVP CLI:** Python CLI, YAML config, screen capture, OCR, rule engine, email, cooldown, logging.
- **Phase 2 — Stability:** SQLite state store, retry email, image preprocessing, multiple capture regions, rule ignore pattern, daily report.
- **Phase 3 — Integration:** Slack / Teams / webhook notification, export JSON, REST API (optional).
- **Phase 4 — Management UI:** Web UI quản lý config, rule editor, execution history, screenshot viewer, owner management, RBAC.

---

## Kết luận

Screen Watcher là sản phẩm nhỏ nhưng giá trị thực tế cao trong môi trường vận hành doanh nghiệp, đặc biệt với hệ thống legacy hoặc dashboard không có khả năng tích hợp. Thiết kế hướng tới: cấu hình đơn giản, chạy ổn định bằng CLI, không phụ thuộc service nền, dễ audit, dễ mở rộng rule, gửi cảnh báo đúng người.

> **Screen Watcher giúp tự động quan sát màn hình, đọc nội dung, kiểm tra theo rule và cảnh báo cho owner khi phát hiện trạng thái cần theo dõi.**
