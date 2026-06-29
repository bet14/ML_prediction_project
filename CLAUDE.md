# CLAUDE.md — GBP/USD ML Prediction Project

**Dự án:** Dự đoán chiều hướng GBP/USD ngày tiếp theo (binary: tăng/không tăng), ML, dữ liệu 2014–2024. Adapted từ paper Guyard & Deriaz (2024) về EUR/USD.
**Khóa học — 4 goals:** (1) Thu thập data nhiều nguồn (FRED/ONS/yfinance) ✅ ~80% · (2) EDA + define target ⚠️ ~15% · (3) Model pipeline + metrics ⚠️ ~5% · (4) Streamlit UI ❌ 0%
**Branch:** `branch_lee` · Spec đầy đủ: `References/GBPUSD_ML_data_requirements_spec.md`

---

## Khi bắt đầu session mới

1. `python project_status.py` → in ra trạng thái từng file data (luôn đọc file thật, không bao giờ lỗi thời)
2. Đọc **entry đầu tiên** `SESSION_LOG.md` → biết đang dừng ở đâu + bước tiếp theo
3. Tra `map.md` → "muốn làm X → dùng file nào" (lookup nhanh)
4. Đọc `PROJECT_GUIDE.md` nếu cần hiểu sâu: conventions đặt tên, flags pipeline, logic xử lý data

## Khi sửa code (bắt buộc)

Trước khi thay đổi bất kỳ file `.py` nào: copy file gốc sang `file_name.py.bak` cùng thư mục, rồi mới edit.
Ví dụ: sửa `src/features/process_gdp.py` → tạo `src/features/process_gdp.py.bak` trước.

## Khi tạo file mới

Cập nhật `map.md` ngay lập tức — thêm dòng vào đúng section task tương ứng.
Kiểm tra: file đó có trong `project_status.py` CHECKLIST chưa? Nếu chưa → thêm luôn.

## Khi kết thúc session (làm thủ công trước khi đóng)

Thêm entry mới vào **đầu** `SESSION_LOG.md` theo template cuối file. Giữ tối đa **2 entry** — entry thứ 3 trở đi chuyển sang `SESSION_LOG_archive.md`.

## Cảnh báo môi trường

- **Cowork (không mạng):** không chạy `fetch_*.py` — chỉ xử lý data đã có, train model, chỉnh script
- **Máy cá nhân (có mạng):** fetch data → copy CSV vào repo → `push.bat`
