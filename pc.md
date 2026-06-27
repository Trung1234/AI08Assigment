# Product Concept: Screen Watcher Automation Tool

## 1. Tên sản phẩm đề xuất

**Screen Watcher**

Screen Watcher là một tool Python chạy dạng CLI, được kích hoạt định kỳ bằng Windows Task Scheduler hoặc Linux cron job. Tool có nhiệm vụ chụp màn hình, bóc tách text từ ảnh bằng OCR, kiểm tra nội dung text theo các rule đã cấu hình trước và gửi email cảnh báo cho owner nếu nội dung phù hợp với mục tiêu theo dõi.

---

## 2. Bối cảnh và vấn đề cần giải quyết

Trong nhiều hệ thống vận hành thực tế, không phải lúc nào cũng có API, webhook, log tập trung hoặc khả năng tích hợp trực tiếp với hệ thống monitoring.

Một số thông tin quan trọng chỉ xuất hiện trên:

- Dashboard web nội bộ
- Ứng dụng desktop
- Terminal session
- Màn hình batch job
- Monitoring UI cũ
- Hệ thống legacy không có API
- Màn hình nghiệp vụ chỉ cho phép quan sát thủ công

Điều này khiến đội vận hành phải kiểm tra bằng mắt, dễ bỏ sót cảnh báo, tốn nhân lực và không có cơ chế cảnh báo tự động.

Screen Watcher giải quyết vấn đề này bằng cách mô phỏng thao tác quan sát màn hình của con người:

1. Chụp màn hình theo lịch.
2. Đọc text từ ảnh.
3. Kiểm tra text theo rule nghiệp vụ.
4. Gửi email nếu phát hiện nội dung cần theo dõi.

---

## 3. Product Vision

**Biến màn hình thành một nguồn dữ liệu giám sát tự động.**

Screen Watcher không thay thế monitoring chuẩn như Prometheus, Grafana, Datadog, Zabbix hoặc ELK. Sản phẩm này phù hợp với các tình huống chưa thể tích hợp monitoring chuẩn, không có API hoặc hệ thống nguồn là legacy UI.

---

## 4. Người dùng mục tiêu

### 4.1. Operation Team

Theo dõi trạng thái màn hình vận hành, dashboard hệ thống, batch job hoặc các màn hình cảnh báo.

### 4.2. DevOps Team

Giám sát tạm thời các hệ thống chưa tích hợp được Prometheus, Grafana, Datadog hoặc log collector.

### 4.3. DBA Team

Theo dõi dashboard database, màn hình job backup, replication, sync, batch hoặc cảnh báo lỗi.

### 4.4. Support Team

Theo dõi màn hình của ứng dụng nghiệp vụ để phát hiện lỗi, trạng thái pending, failed hoặc timeout.

### 4.5. Business Owner

Nhận email khi màn hình nghiệp vụ xuất hiện trạng thái cần quan tâm, ví dụ giao dịch lỗi, đơn hàng treo, đồng bộ thất bại.

---

## 5. Mục tiêu sản phẩm

Screen Watcher cần đạt các mục tiêu chính:

1. Chạy được bằng Python CLI.
2. Có thể được gọi bởi Windows Task Scheduler hoặc Linux cron job.
3. Chụp màn hình hoặc vùng màn hình được cấu hình.
4. Trích xuất text từ ảnh bằng OCR.
5. Đánh giá nội dung text theo rule cấu hình trước.
6. Gửi email cho owner nếu rule được kích hoạt.
7. Cho phép cấu hình owner, rule, email, capture region và runtime behavior từ file config.
8. Lưu log, ảnh chụp và OCR result để phục vụ audit.

---

## 6. Luồng hoạt động tổng thể

```text
Windows Task Scheduler / Linux Cron
        ↓
Run Python CLI
        ↓
Load config
        ↓
Capture screen / region
        ↓
Save screenshot
        ↓
OCR image to text
        ↓
Evaluate rules
        ↓
Rule matched?
        ↓
Yes → Send email to owner
No  → Write log only
        ↓
Save execution result
```

---

## 7. Phạm vi MVP

Phiên bản MVP nên tập trung vào tính ổn định, đơn giản và dễ triển khai nội bộ.

### 7.1. MVP Features

1. Python CLI runner.
2. Config bằng YAML.
3. Chụp toàn màn hình hoặc chụp theo region.
4. OCR bằng Tesseract.
5. Rule type: contains, regex, not_contains.
6. Rule có severity.
7. Owner được cấu hình theo group.
8. Gửi email qua SMTP.
9. Cooldown chống spam email.
10. Lưu screenshot, OCR text và execution log.
11. Hỗ trợ chạy manual để test config.

### 7.2. Ngoài phạm vi MVP

Các tính năng sau chưa cần đưa vào MVP:

1. Web UI quản lý rule.
2. Dashboard history.
3. Tích hợp Slack, Teams, Telegram.
4. AI classification.
5. Multi tenant.
6. Database server tập trung.
7. Agent cài trên nhiều máy và quản lý tập trung.

---

## 8. Chức năng chi tiết

## 8.1. Python CLI Runner

Tool chạy dạng command line.

Ví dụ:

```bash
python screen_watcher.py run --config config.yaml
```

Hoặc khi đóng gói thành executable:

```bash
screen-watcher.exe run --config config.yaml
```

Các command nên hỗ trợ:

```bash
screen-watcher run --config config.yaml
screen-watcher test-capture --config config.yaml
screen-watcher test-ocr --config config.yaml
screen-watcher test-rule --config config.yaml
screen-watcher test-email --config config.yaml
```

Ý nghĩa:

- `run`: chạy toàn bộ workflow.
- `test-capture`: chụp thử màn hình.
- `test-ocr`: kiểm tra OCR.
- `test-rule`: kiểm tra rule với OCR text.
- `test-email`: gửi email test cho owner.

---

## 8.2. Scheduler Integration

Screen Watcher không cần tự xây scheduler trong MVP. Tool chỉ cần chạy tốt ở dạng CLI để scheduler bên ngoài gọi.

### Windows Task Scheduler

Ví dụ command:

```powershell
python C:\tools\screen-watcher\screen_watcher.py run --config C:\tools\screen-watcher\config.yaml
```

### Linux Cron

Ví dụ cron chạy mỗi 5 phút:

```bash
*/5 * * * * /usr/bin/python3 /opt/screen-watcher/screen_watcher.py run --config /opt/screen-watcher/config.yaml
```

Ưu điểm của cách này:

1. Không cần service chạy nền.
2. Dễ kiểm soát lịch chạy.
3. Dễ triển khai trên Windows và Linux.
4. Dễ debug vì mỗi lần chạy là một execution độc lập.

---

## 8.3. Screen Capture

Tool cần hỗ trợ hai chế độ chụp chính.

### Chụp toàn màn hình

```yaml
capture:
  mode: full_screen
```

### Chụp theo vùng màn hình

```yaml
capture:
  mode: region
  x: 100
  y: 200
  width: 1200
  height: 600
```

### Cấu hình nâng cao đề xuất

```yaml
capture:
  mode: region
  monitor: 1
  x: 100
  y: 200
  width: 1200
  height: 600
  output_dir: ./data/screenshots
  image_format: png
```

Lý do cần chụp theo region:

1. Giảm nhiễu OCR.
2. Tăng tốc xử lý.
3. Tránh đọc nhầm text từ vùng không liên quan.
4. Rule chính xác hơn.

---

## 8.4. OCR Text Extraction

OCR là thành phần bóc tách text từ ảnh.

### Engine đề xuất cho MVP

**Tesseract OCR**

Lý do:

1. Dễ dùng.
2. Chạy offline.
3. Không phụ thuộc cloud.
4. Phù hợp với text dashboard, terminal, UI đơn giản.

### Engine có thể cân nhắc sau MVP

1. PaddleOCR nếu cần độ chính xác cao hơn.
2. EasyOCR nếu muốn triển khai nhanh cho nhiều ngôn ngữ.
3. Cloud OCR nếu doanh nghiệp cho phép dùng dịch vụ ngoài.

### Output OCR

Tool cần lưu OCR text để audit.

Ví dụ:

```text
Status: Failed
Job Name: Daily Sync
Last Run: 2026-06-27 10:00:00
Error: Connection timeout
```

---

## 8.5. Rule Engine

Rule Engine là phần quyết định text OCR có đáp ứng mục tiêu theo dõi hay không.

### Rule type cần hỗ trợ trong MVP

| Rule type | Ý nghĩa |
|---|---|
| contains | Text chứa một hoặc nhiều keyword |
| not_contains | Text không chứa keyword bắt buộc |
| regex | Text match regular expression |
| all_keywords | Phải chứa tất cả keyword |
| any_keywords | Chỉ cần chứa một trong các keyword |

### Ví dụ rule contains

```yaml
rules:
  - id: daily_sync_failed
    name: Daily Sync Failed
    type: contains
    keywords:
      - "Failed"
      - "Daily Sync"
    severity: critical
    owner_group: zcoa_ops
    cooldown_minutes: 30
```

### Ví dụ rule regex

```yaml
rules:
  - id: timeout_error
    name: Timeout Error Detected
    type: regex
    pattern: "(ERROR|FAILED|TIMEOUT)"
    ignore_case: true
    severity: high
    owner_group: ops_team
    cooldown_minutes: 15
```

### Ví dụ rule not_contains

```yaml
rules:
  - id: service_not_running
    name: Service Running Text Missing
    type: not_contains
    keywords:
      - "Service Running"
    severity: high
    owner_group: ops_team
    cooldown_minutes: 30
```

---

## 8.6. Owner Configuration

Owner được cấu hình từ config.

Ví dụ:

```yaml
owners:
  zcoa_ops:
    emails:
      - "owner1@company.com"
      - "owner2@company.com"

  dba_team:
    emails:
      - "dba-owner@company.com"
```

Mỗi rule sẽ tham chiếu tới `owner_group`.

```yaml
owner_group: zcoa_ops
```

Cách này giúp:

1. Không hard-code email trong source code.
2. Nhiều rule có thể dùng chung một owner group.
3. Dễ thay đổi người nhận khi tổ chức thay đổi.
4. Có thể mở rộng thêm Slack, Teams sau này.

---

## 8.7. Email Notification

Email cần rõ ràng, đủ dữ liệu để owner đánh giá nhanh.

### Nội dung email đề xuất

Subject:

```text
[Screen Watcher][CRITICAL] Daily Sync Failed
```

Body:

```text
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

Action:
Please check the dashboard or related batch job.
```

Attachment:

1. Screenshot image.
2. OCR text file nếu cần.

---

## 8.8. Cooldown và chống spam

Nếu scheduler chạy mỗi 5 phút và màn hình vẫn đang hiển thị lỗi, tool có thể gửi email liên tục.

Vì vậy cần có cooldown.

Ví dụ:

```yaml
cooldown_minutes: 30
```

Ý nghĩa:

Nếu rule `daily_sync_failed` đã gửi email lúc 10:00, thì trong 30 phút tiếp theo không gửi lại email cho cùng rule đó, trừ khi cấu hình cho phép gửi repeat.

State có thể lưu bằng file JSON hoặc SQLite.

Ví dụ file state:

```json
{
  "daily_sync_failed": {
    "last_sent_at": "2026-06-27T10:00:00"
  }
}
```

---

## 8.9. Logging và Audit

Mỗi lần chạy tool cần ghi log.

Thông tin nên ghi:

1. Start time.
2. Config path.
3. Capture result.
4. Screenshot path.
5. OCR text path.
6. Rule evaluation result.
7. Email sent or skipped.
8. Error nếu có.
9. End time.
10. Duration.

Ví dụ log:

```text
2026-06-27 10:05:00 INFO Start Screen Watcher
2026-06-27 10:05:01 INFO Screenshot saved: ./data/screenshots/20260627_100501.png
2026-06-27 10:05:02 INFO OCR completed, text length=245
2026-06-27 10:05:02 INFO Rule matched: daily_sync_failed
2026-06-27 10:05:03 INFO Email sent to owner group: zcoa_ops
2026-06-27 10:05:03 INFO Execution completed
```

---

## 9. Cấu trúc config đề xuất

```yaml
app:
  name: screen-watcher
  environment: production
  timezone: Asia/Ho_Chi_Minh
  instance_id: ops-win-01-dashboard

capture:
  mode: region
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
      - "Daily Sync"
      - "Failed"
    ignore_case: true
    severity: critical
    owner_group: zcoa_ops
    cooldown_minutes: 30

owners:
  ops_team:
    emails:
      - "ops-owner@company.com"

  zcoa_ops:
    emails:
      - "zcoa-owner@company.com"

email:
  smtp_host: smtp.company.com
  smtp_port: 587
  use_tls: true
  username: watcher@company.com
  password_env: WATCHER_SMTP_PASSWORD
  from: watcher@company.com

state:
  type: json
  path: ./data/state/state.json

logging:
  level: INFO
  log_dir: ./logs
  retention_days: 30
```

---

## 10. Kiến trúc module đề xuất

```text
screen_watcher/
  __init__.py
  main.py
  cli.py
  config_loader.py
  screen_capture.py
  ocr_service.py
  rule_engine.py
  notification_service.py
  email_service.py
  state_store.py
  audit_store.py
  logger.py
  models.py
```

### Mô tả module

| Module | Vai trò |
|---|---|
| main.py | Entry point |
| cli.py | Xử lý command line argument |
| config_loader.py | Đọc và validate config |
| screen_capture.py | Chụp màn hình |
| ocr_service.py | OCR ảnh thành text |
| rule_engine.py | Đánh giá text theo rule |
| notification_service.py | Điều phối gửi cảnh báo |
| email_service.py | Gửi email SMTP |
| state_store.py | Lưu cooldown state |
| audit_store.py | Lưu screenshot, OCR text, result |
| logger.py | Cấu hình logging |
| models.py | Định nghĩa schema bằng Pydantic |

---

## 11. Công nghệ đề xuất

| Thành phần | Công nghệ đề xuất |
|---|---|
| CLI | Typer hoặc argparse |
| Config | YAML |
| Config validation | Pydantic |
| Screen capture | mss hoặc pyautogui |
| OCR | pytesseract + Tesseract OCR |
| Image preprocessing | Pillow, OpenCV tùy nhu cầu |
| Email | smtplib hoặc aiosmtplib |
| State | JSON file cho MVP, SQLite cho bản mở rộng |
| Logging | Python logging |
| Packaging | PyInstaller |
| Windows schedule | Windows Task Scheduler |
| Linux schedule | cron |

---

## 12. User Story

### US01: Cấu hình rule theo keyword

Là operation owner, tôi muốn cấu hình danh sách keyword cần theo dõi để tool gửi email khi màn hình xuất hiện nội dung lỗi.

### US02: Cấu hình owner nhận email

Là admin, tôi muốn cấu hình owner group trong file config để mỗi rule có thể gửi email cho đúng nhóm phụ trách.

### US03: Chụp màn hình theo vùng

Là người vận hành, tôi muốn cấu hình tọa độ vùng màn hình để OCR chỉ đọc phần dashboard quan trọng.

### US04: Gửi email khi rule match

Là owner, tôi muốn nhận email khi nội dung màn hình match rule để có thể phản ứng kịp thời.

### US05: Lưu bằng chứng kiểm tra

Là auditor, tôi muốn tool lưu screenshot và OCR text để kiểm tra lại vì sao email đã được gửi.

### US06: Tránh gửi email liên tục

Là owner, tôi muốn tool có cooldown để không bị spam email khi lỗi vẫn đang tồn tại.

---

## 13. Acceptance Criteria cho MVP

### AC01: Run CLI thành công

Given config hợp lệ  
When chạy command:

```bash
screen-watcher run --config config.yaml
```

Then tool phải chạy đủ workflow capture, OCR, rule evaluation và logging.

### AC02: Capture screenshot

Given capture mode là region  
When tool chạy  
Then screenshot phải được lưu vào output directory.

### AC03: OCR text

Given screenshot có text rõ ràng  
When OCR chạy  
Then OCR text phải được lưu thành file text.

### AC04: Rule matched

Given OCR text chứa keyword hoặc regex theo rule  
When rule engine đánh giá  
Then rule phải được đánh dấu là matched.

### AC05: Email sent

Given rule matched và chưa trong cooldown  
When notification service chạy  
Then email phải được gửi tới owner group.

### AC06: Cooldown working

Given rule đã gửi email trong cooldown window  
When rule tiếp tục matched  
Then tool không gửi lại email và ghi log skipped by cooldown.

### AC07: Config owner

Given owner group được cấu hình trong config  
When rule matched  
Then email phải gửi tới đúng danh sách email của owner group.

---

## 14. Rủi ro và giới hạn

| Rủi ro | Mô tả | Hướng xử lý |
|---|---|---|
| OCR sai | Font nhỏ, ảnh mờ, màu nền khó đọc | Cho phép cấu hình region, tăng độ phân giải, tiền xử lý ảnh |
| UI thay đổi | Vùng chụp bị lệch | Cho phép test-capture và cập nhật tọa độ nhanh |
| Spam email | Rule match liên tục | Bắt buộc cooldown |
| Máy bị lock screen | Không chụp được màn hình đúng | Cần session GUI hợp lệ hoặc chạy trên môi trường có desktop session |
| False positive | Text match nhưng không thật sự là lỗi | Rule cần hỗ trợ all_keywords, regex, ignore pattern |
| SMTP lỗi | Không gửi được email | Log lỗi, retry giới hạn |
| Bảo mật password | Password SMTP nằm trong config | Dùng biến môi trường password_env |

---

## 15. Non-functional Requirements

### 15.1. Reliability

Tool phải không crash toàn bộ nếu một bước lỗi. Mỗi lỗi cần được log rõ ràng.

### 15.2. Observability

Mỗi lần chạy phải có log đầy đủ để biết tool đã làm gì.

### 15.3. Security

Không lưu password trực tiếp trong config. Nên dùng biến môi trường.

### 15.4. Portability

Tool phải chạy được trên Windows và Linux.

### 15.5. Maintainability

Rule, owner, email, capture region phải thay đổi được qua config, không sửa source code.

### 15.6. Auditability

Lưu lại ảnh, OCR text và rule result để kiểm chứng.

---

## 16. Roadmap đề xuất

### Phase 1: MVP CLI

1. Python CLI.
2. YAML config.
3. Screen capture.
4. OCR.
5. Rule engine.
6. Email.
7. Cooldown.
8. Logging.

### Phase 2: Stability Enhancement

1. SQLite state store.
2. Retry email.
3. Image preprocessing.
4. Multiple capture regions.
5. Rule ignore pattern.
6. Daily report.

### Phase 3: Integration

1. Slack notification.
2. Microsoft Teams notification.
3. Webhook notification.
4. Export result JSON.
5. REST API optional.

### Phase 4: Management UI

1. Web UI quản lý config.
2. Rule editor.
3. Execution history.
4. Screenshot viewer.
5. Owner management.
6. Role based access control.

---

## 17. Định vị sản phẩm

Screen Watcher là một **automation observer tool** dành cho các hệ thống khó tích hợp trực tiếp.

Nó phù hợp khi:

1. Hệ thống không có API.
2. Không thể sửa source code.
3. Không có webhook.
4. Không có log collector.
5. Dashboard chỉ hiển thị trên UI.
6. Cần giải pháp giám sát tạm thời hoặc bán tự động.

Nó không phù hợp khi:

1. Cần realtime monitoring nghiêm ngặt.
2. Hệ thống đã có API monitoring đầy đủ.
3. Cần độ chính xác tuyệt đối như giao dịch tài chính core.
4. Không thể duy trì desktop session để chụp màn hình.

---

## 18. Kết luận

Screen Watcher là một sản phẩm nhỏ nhưng có giá trị thực tế cao trong môi trường vận hành doanh nghiệp, đặc biệt với hệ thống legacy hoặc dashboard không có khả năng tích hợp.

MVP nên được thiết kế theo hướng:

1. Cấu hình đơn giản.
2. Chạy ổn định bằng CLI.
3. Không phụ thuộc service nền.
4. Dễ audit.
5. Dễ mở rộng rule.
6. Gửi cảnh báo đúng người.

Tuyên bố sản phẩm ngắn gọn:

**Screen Watcher giúp tự động quan sát màn hình, đọc nội dung, kiểm tra theo rule và cảnh báo cho owner khi phát hiện trạng thái cần theo dõi.**
