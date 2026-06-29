data là 10 năm 2014- 2024

## Kinh nghiệm rút ra từ scrape dữ liệu macro (2026-06-19) — áp dụng cho forex/equity

Bối cảnh: các bài học này rút ra trong lúc viết `fetch_cpi_uk_alt_wip.py`,
`fetch_current_account_uk_wip.py`, `fetch_composite_pmi_wip.py` (ONS v1 beta API +
scraper investing.com). Áp dụng trực tiếp cho `fetch_forex_wip.py` (Dukascopy) và
`fetch_equity_wip.py` (yfinance) viết cùng ngày, session sau.

1. **Raw-dump trước khi tin parser**: mọi fetch script cần một flag (`--verify-only`
   hoặc `--raw-dump`) in ra response thô (HTTP status, vài dòng đầu) trước khi parse.
   Tránh tình trạng parser "chạy được" nhưng đang parse nhầm cấu trúc trang.
2. **Response trống/lỗi không đồng nghĩa với lỗi mạng**: ONS v0 API trả về rỗng không
   phải vì firewall mà vì API đó đã bị retire vĩnh viễn (xác nhận qua
   developer.ons.gov.uk/retirement/v0api). Khi gặp response rỗng/bất thường từ một thư
   viện/API bên thứ ba (kể cả thư viện "chính thức" như `yfinance`), việc đầu tiên là
   kiểm tra xem nguồn có còn tồn tại/đổi schema không, không vội kết luận là vấn đề kết
   nối.
3. **Một nguồn có thể có nhiều page-template khác nhau cho cùng một site**: trang
   economic-calendar của investing.com (PMI) chỉ giữ ~3-4 release gần nhất, nhưng trang
   historical-data theo từng instrument (cổ phiếu/FX) của cùng site lại có bảng nhiều
   năm. Một phương pháp (scrape AJAX) bị từ chối cho loại trang này có thể lại đúng cho
   loại trang khác — không suy rộng kết luận "site X không scrape được" từ một
   page-template sang toàn site.
4. **Không giả định độ sâu lịch sử đồng nhất giữa các instrument trong cùng batch**: UK
   GDP bị discontinue từ 2020-07, UK central bank rate trên FRED chỉ có từ 2014-08 — mỗi
   indicator/instrument cần verify riêng coverage, không suy từ 1 series ra cả batch.
   Áp dụng trực tiếp cho 13 cặp forex (major vs cross như GBP/NZD nhiều khả năng có ngày
   bắt đầu khác nhau) và 9 equity index.
5. **Naming convention cho code chưa verify chạy thật**: hậu tố `_wip.py`, docstring có
   dòng STATUS phân biệt rõ "đã verify schema/response sống" với "đã thực sự chạy ra
   output". Không gộp 2 trạng thái này thành một chữ "done".
6. **Anti-bot/rate-limit là rủi ro có thật, không cố vượt qua**: nếu gặp HTTP 403,
   CAPTCHA, hoặc bảng trống bất thường — fallback sang quy trình thủ công đã ghi trong
   docstring, đây là scope boundary có chủ đích, không phải thiếu sót.
7. **Quyết định đã chốt — forex volume bị loại khỏi scope**: yfinance `=X` ticker cho FX
   trả về volume = 0 (spot FX không có consolidated tape). Dukascopy có tick volume thật
   nhưng rất nặng (~800k requests). Sau khi đánh giá, **volume không đưa vào model** —
   chỉ dùng OHLC cho 13 FX pairs. Script `fetch_forex_wip.py` vẫn giữ cột `volume` trong
   CSV (= 0) nhưng `process_forex.py` sẽ bỏ qua cột này khi build panel. Dukascopy path
   trong script giữ nguyên như tài liệu WIP, không cần chạy.

## Môi trường Cowork — lỗi đã gặp, cách workaround

`mcp__workspace__bash` có độ trễ đồng bộ với mount Windows: file vừa Write/Edit qua
Read/Write/Edit tool có thể đọc ra **cũ/thiếu** khi `bash` đọc lại ngay sau đó (đã gặp
với `fetch_composite_pmi_wip.py`, `requirements.txt`, `README.md` — sai lệch tới hơn
70% số dòng, không tự hết dù đã `sleep` tới 20s+). Cách workaround: copy nội dung đúng
(theo Read tool, không theo bash) vào một path thuần sandbox như `/tmp/...` bằng
heredoc, rồi verify (`python3 -c "import ast; ast.parse(...)"`) tại path đó — không tin
kết quả `py_compile`/`wc -l` của bash chạy trực tiếp trên path mount ngay sau khi vừa
ghi file.