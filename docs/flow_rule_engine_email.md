# Flow — Rule Engine & Email Notification

Mục 5 của assignment: phần "trí thông minh" của Screen Watcher — chấm điểm OCR text theo rule,
quyết định có gửi email không, và đảm bảo không spam owner.

---

## 1. Sơ đồ tổng quan (high-level)

```
                ┌────────────────────────┐
                │   OCR text (string)    │
                └───────────┬────────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │      Rule Engine       │
                │ ───────────────────── │
                │ evaluate(text, rules)  │
                │ trả về danh sách       │
                │ MatchResult            │
                └───────────┬────────────┘
                            │ matched rules
                            ▼
                ┌────────────────────────┐
                │  Notification Service  │
                │ ───────────────────── │
                │ với mỗi matched rule:  │
                │  1. check cooldown     │
                │  2. resolve owner emails│
                │  3. gọi email service  │
                │  4. cập nhật state     │
                └─────┬────────────┬─────┘
                      │            │
            in cooldown            không cooldown
                      │            │
                      ▼            ▼
              ┌──────────────┐  ┌──────────────────┐
              │ Skip + log   │  │  Email Service   │
              │ "cooldown"   │  │  smtplib.SMTP    │
              └──────────────┘  │  send_message()  │
                                └────────┬─────────┘
                                         │ success
                                         ▼
                                ┌──────────────────┐
                                │  State Store     │
                                │ mark_sent(rule)  │
                                │ persist JSON     │
                                └──────────────────┘
```

---

## 2. Flow rule evaluation (chi tiết)

```
        Rule Engine.evaluate(text, rules)
                    │
                    ▼
        ┌───────────────────────────┐
        │ for each rule in rules:   │
        └─────────────┬─────────────┘
                      │
                      ▼
        ┌──────────────────────────────────────┐
        │  switch rule.type                    │
        ├──────────────────────────────────────┤
        │  contains      → text contains       │
        │                  ANY keyword         │
        │  any_keywords  → text contains       │
        │                  ANY keyword         │
        │  all_keywords  → text contains       │
        │                  ALL keyword         │
        │  not_contains  → text does NOT       │
        │                  contain any keyword │
        │  regex         → re.search(pattern)  │
        └──────────────────┬───────────────────┘
                           │
                           ▼
                   matched? yes/no
                           │
                           ▼
                  collect MatchResult(
                      rule_id, name, severity,
                      owner_group, matched_text,
                      cooldown_minutes
                  )
```

---

## 3. Flow notification + cooldown

```
NotificationService.dispatch(matched_results)
            │
            ▼
  for each match in matched_results:
            │
            ▼
  ┌─────────────────────────────┐
  │ state = state_store.get(    │
  │            match.rule_id)   │
  └────────────┬────────────────┘
               │
               ▼
  ┌─────────────────────────────────┐
  │ now - state.last_sent_at        │
  │   < cooldown_minutes ?          │
  └───┬─────────────────────────┬───┘
      │ yes                     │ no
      ▼                         ▼
  log skipped       resolve owner emails
                              │
                              ▼
                    email_service.send(
                        subject, body,
                        to=owner emails,
                        attachments=[
                          screenshot,
                          ocr_text_file
                        ])
                              │
                  ┌───────────┴──────────┐
                  │ success              │ failure
                  ▼                      ▼
        state_store.mark_sent     log error
        (rule_id, now)            (no state update,
                                   sẽ retry lần sau)
```

---

## 4. Cooldown state (file JSON)

```json
{
  "daily_sync_failed": {
    "last_sent_at": "2026-06-27T10:00:00"
  },
  "error_detected": {
    "last_sent_at": "2026-06-27T10:03:12"
  }
}
```

Mỗi lần email gửi thành công → ghi `last_sent_at = now()`. Lần chạy tiếp theo, nếu
`(now - last_sent_at) < cooldown_minutes` → skip.

---

## 5. Tách nhiệm vụ (separation of concerns)

| Module | Trách nhiệm | KHÔNG làm |
|--------|-------------|-----------|
| `rule_engine.py` | Match text theo rule, trả về kết quả thuần | Không biết về email, cooldown, state |
| `state_store.py` | Đọc/ghi cooldown state (JSON) | Không biết về rule logic hay SMTP |
| `email_service.py` | Build MIME message + gọi SMTP | Không biết về rule hay cooldown |
| `notification_service.py` | Orchestrator: cooldown → owner → email → state | Không tự match rule, không tự gửi SMTP |

Lợi ích: mỗi module test độc lập, mock dễ, đổi email backend (SMTP → Slack) chỉ cần
sửa `email_service.py`, không ảnh hưởng rule engine.
