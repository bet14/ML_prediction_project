# CLAUDE.md — GBP/USD ML Prediction Project

## Khi bắt đầu session mới

1. Chạy `python project_status.py` → xem snapshot data hiện tại (74% tính đến 2026-06-29)
2. Đọc **entry đầu tiên** của `SESSION_LOG.md` → biết đang dừng ở đâu, bước tiếp theo là gì
3. Tra `map.md` khi cần tìm file cho một task cụ thể

## Khi kết thúc session

Prepend entry mới vào `SESSION_LOG.md` theo template cuối file. Giữ tối đa **2 entry** — entry thứ 3 trở đi chuyển sang `SESSION_LOG_archive.md`.

## Cảnh báo môi trường

- **Cowork (không mạng):** không chạy `fetch_*.py` — chỉ xử lý data đã có, train model, chỉnh script
- **Máy cá nhân (có mạng):** fetch data → copy CSV vào repo → `push.bat`

## Trạng thái nhanh (2026-06-29)

- Phase 1B Forex: **OK** — 13 cặp, ~2867 rows, 2014–2024
- Phase 1C Equity: **OK** — 9 index, ~2778 rows, 2014–2024
- Phase 1A Macro: phần lớn OK — UK GDP WARN, UK CPI WARN, PMI BLOCKED
- Phase 2 Interim: 4 macro panels OK — **forex/equity panel chưa có** ← ưu tiên tiếp theo
- Phase 3–5: chưa có
