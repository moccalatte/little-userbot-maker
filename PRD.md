# Little Userbot Maker – PRD

## Purpose & Users
- Goal: help non-technical Telegram users safely membuat string session Telethon (via OTP maupun QR) dan menjalankan userbot ringan tanpa setup server.
- Primary users: power users who need automation without server setup; makers helping friends bootstrap bots.
- Success: users finish the wizard in one attempt, receive a working session, and can run commands without hidden steps.

## Components & Core Features
### bot/ (Wizard Bot API)
- Dua mode login: OTP (kode Telegram dengan retry + backoff) dan QR login (scan `tg://login`, dukung `retry`, dan timeout yang dapat dikonfigurasi).
- Validasi nomor E.164, `api_id`, `api_hash`; dukungan 2FA password tanpa menyimpan OTP atau password.
- Setelah login sukses, wizard langsung menyalin string session ke file `SESSION_OUTPUT_FILE`, menampilkannya di chat, dan menawarkan penyimpanan terenkripsi (opsional).
- Perintah `/delete` menghapus data terenkripsi milik user; log aktivitas mem-mask data sensitif dan mencatat event penting (OTP invalid, QR timeout, retry).
- Konsumsi `QR_TIMEOUT` untuk mengatur batas menunggu QR; log dapat diteruskan ke Telegram jika `TELEGRAM_LOG_CHAT_ID` diisi.

### userbot/ (Telethon Userbot)
- Single event parser with centralized command map → auto-generates `!help` contents.
- `!help`: lists commands, shows usage from command metadata, redacts sensitive values.
- `!sg <message> <interval_minute> <target>`: schedules broadcasts; supports `allgroup` or explicit group IDs, start/stop control, rate-limit and status feedback.
- `!gg`: gathers joined group IDs with pagination (50 per page) and optional CSV export reminder.
- `!scr <rules>`: configurable listener storing matches to JSON/CSV; supports keywords, regex allow/deny lists, and `!scr stop` reset.
- Extensibility: adding a command requires only a new handler module/function plus a map entry.

### sessiongen/ (Session Generator Bot API)
- Bot minimal OTP-only untuk operator yang ingin flow tercepat tanpa wizard penuh.
- Kebijakan keamanan sama: tidak menyimpan OTP, penyimpanan terenkripsi hanya jika diminta, tersedia perintah `/delete`.
- Menyediakan pengingat cara menyalin dan memakai string session pada proyek lain.

## Architecture & Data Flow
```
[User]
   |
   v
[Telegram Bot API]
   | (bot/, sessiongen/ use HTTPS polling/webhook)
   v
[Wizard Controller] --creates--> [Telethon Client Session]
                                   |
                                   v
                              [Encrypted Vault]
                                   |
                                   v
                             [Return Session]

[userbot/]
[Telethon Event Loop] -> [Command Router] -> [Handlers]
                                     |            |
                                     |            v
                                     |       [Storage Layer]
                                     v
                               [Logger + Alerts]
```
- Shared utilities: validation helpers, encryption service, logging setup.
- Separation keeps bot/ and sessiongen/ lightweight while userbot/ focuses on command execution.

## Data Contracts
- E.164 phone validation regex `^\+[1-9]\d{7,14}$`.
- API credentials kept in memory until encrypted (libsodium/Fernet) if user opts in.
- Sessions stored as base64 strings; tagged with timestamp and phone hash (SHA-256 with salt).

## Command Reference (userbot/)
- `!help`
  - Output: command list with usage and short notes.
  - Errors: none; when map empty, show "No commands enabled".
- `!sg <message> <interval_minute> <target>`
  - Args: `message` (quoted for spaces), `interval_minute` (int ≥5), `target` (`allgroup` or comma IDs).
  - Behavior: starts scheduler if not running; `!sg stop` cancels all jobs.
  - Errors: invalid number → explain; unknown target → suggest `!gg`; flood wait → log and pause.
  - Example: `!sg "Daily update" 30 allgroup`.
- `!gg`
  - Output: page of group ID, title; `!gg next`/`!gg prev` to paginate.
  - Errors: if no groups, respond with guidance; on Telethon errors, prompt to re-auth.
- `!scr <rules>`
  - Rules format JSON string `{"include":["sale"],"exclude":["test"],"regex":["buy.*now"]}`.
  - Start: validates JSON & regex; begins listener with backoff if rate-limited.
  - Stop: `!scr stop` clears listeners and flushes buffers.
  - Errors: malformed JSON, invalid regex (report pattern), storage write failures (suggest disk check).

## Conversation Flows
### bot/
1. Salam pembuka → jelaskan opsi login, minta user ketik `otp` atau `qr` serta beri peringatan keamanan.
2. Mode OTP:
   - Validasi nomor E.164, `api_id`, `api_hash`.
   - Kirim OTP; terima input user (dibersihkan dari karakter asing); retry maksimal 3 kali dengan jeda `RATE_LIMIT_INTERVAL` saat gagal/expired.
   - Jika 2FA aktif, minta password dan tekankan tidak disimpan.
3. Mode QR:
   - Minta `api_id` & `api_hash`, generate token `tg://login`.
   - Kirim QR + instruksi scan via Telegram dan tekan tombol *Masuk*; balasan `retry` memicu QR baru melalui `recreate()`.
   - Task async menunggu otorisasi hingga `QR_TIMEOUT`; saat sukses lanjut ke langkah berikut, jika timeout informasikan user.
4. Setelah login sukses (OTP/QR): tampilkan string session, otomatis tulis ke `SESSION_OUTPUT_FILE`, tawarkan penyimpanan terenkripsi.
5. `/delete` dapat dipanggil kapan saja untuk menghapus data terenkripsi; wizard akhiri percakapan dengan pesan ringkas.

### sessiongen/
1. Sapaan singkat → jelaskan fokus OTP-only.
2. Validasi nomor / `api_id` / `api_hash` seperti wizard.
3. Kirim OTP dengan retry terbatas; dukung password 2FA.
4. Setelah sukses, kirim string session dan tawarkan simpan terenkripsi (opsional, default skip).
5. `/delete` menghapus data terenkripsi dan bot menutup percakapan.

## Logging & Monitoring Plan
- Python logging configured per module; default level INFO, `LOG_LEVEL` override.
- Log file per component (e.g., `logs/bot.log`); rotation via size (10 MB) to keep debugging easy.
- Sensitive fields masked (phone hashed, session truncated, QR URL tidak ditulis penuh).
- Wizard mencatat event login (pilihan metode, hash OTP, hasil retry/timeout QR, input `done`/`retry`), memudahkan audit.
- Optional forwarding: if `TELEGRAM_LOG_CHAT_ID` set, send WARN/ERROR batches dengan exponential backoff (1m, 5m, 15m).
- Fatal errors log reason then exit(1), matching project rules.

## Storage Plan
- Initial storage: JSON files (`data/sessions.json`, `data/rules.json`) and CSV for scraped messages (`scrape_output/*.csv`).
- JSON schema example: `{ "phone_hash": "...", "session": "...", "created_at": "ISO8601", "encrypted": true }`.
- CSV columns: `timestamp,chat_id,chat_title,message_text,rule_tag`.
- Rotation policy: keep max 100 sessions; oldest removed unless pinned.
- Upgrade path to SQLite when scraped messages exceed 50k rows or JSON size >5 MB.
  - Suggested schema: `sessions(phone_hash TEXT PRIMARY KEY, session TEXT, created_at TEXT, encrypted BOOLEAN)` and `scraped_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, chat_id TEXT, chat_title TEXT, message_text TEXT, rule_tag TEXT, captured_at TEXT)`.
  - Indices: `CREATE INDEX idx_scraped_chat_time ON scraped_messages(chat_id, captured_at);`
  - Use parameterized queries and WAL mode for concurrency.

## Config & Environment Variables
| Name | Component | Required | Default | Purpose |
| --- | --- | --- | --- | --- |
| `PYTHON_VERSION` | all | yes | `3.11` | Dokumentasi versi Python yang dipakai proyek. |
| `TELEGRAM_BOT_TOKEN` | bot/, sessiongen/ | yes | – | Bot token utama wizard (boleh reuse untuk sessiongen). |
| `SESSIONGEN_BOT_TOKEN` | sessiongen/ | no | – | Bot token jika sessiongen dijalankan sebagai bot terpisah. |
| `API_ID` | bot/, sessiongen/, userbot/ | yes | – | App ID Telegram yang sama untuk semua komponen. |
| `API_HASH` | bot/, sessiongen/, userbot/ | yes | – | App hash Telegram yang sama untuk semua komponen. |
| `SESSION_FILE` | userbot/ | yes | `session.session` | File berisi string session yang dibaca userbot. |
| `SESSION_OUTPUT_FILE` | bot/ | no | `session.session` | Lokasi file auto-save session dari wizard. |
| `SECRET_KEY` | bot/, sessiongen/ | yes if storing | – | Kunci enkripsi (Fernet) saat user memilih simpan terenkripsi. |
| `QR_TIMEOUT` | bot/ | no | `180` | Batas menunggu otorisasi QR sebelum dianggap kedaluwarsa (detik). |
| `RATE_LIMIT_INTERVAL` | userbot/, bot/ | no | `30` | Jeda retry untuk OTP & broadcast. |
| `LOG_LEVEL` | all | no | `INFO` | Level logging default. |
| `LOG_DIR` | all | no | `./logs` | Direktori untuk file log ber-rotasi. |
| `TELEGRAM_LOG_CHAT_ID` | all | no | – | Chat ID untuk meneruskan log WARN/ERROR penting. |
| `DATA_DIR` | bot/, sessiongen/, userbot/ | no | `./data` | Root penyimpanan JSON/CSV lokal. |
| `.env` placement | root | yes | Berkas konfigurasi utama yang dibaca semua komponen. |

## Performance, Rate Limits & Retries
- Respect Telegram flood wait by catching exceptions; apply incremental backoff (5s, 15s, 60s) before retry.
- Scheduler checks queue every minute; sleeps when idle to avoid tight loops.
- Listener batches writes (max 50 messages) with short delay (1s) to reduce disk churn.
- Commands short-circuit if Telethon client disconnected; prompt user to re-login.
- QR login menjalankan task async tunggal per user; timeout dikontrol `QR_TIMEOUT` dan dibatalkan saat user meminta `retry`.

## Acceptance Criteria
- Wizard menyelesaikan login OTP dan QR (termasuk opsi retry, timeout, serta 2FA) dan mengembalikan string session valid di file & chat.
- Userbot responds to all four commands with expected behaviour under happy path and error cases.
- Logs show masked sensitive data and include timestamps, levels, context IDs.
- Deletion command removes stored sessions and confirms to user.
- `.env` template provided with all documented variables.

## Test Plan
- Unit tests untuk command parser → handler, scheduler start/stop, dan validator rules.
- Integration/manual: jalankan wizard dengan akun uji, validasi login OTP (termasuk retry), QR (scan, tekan *Masuk*, test `retry` dan timeout), dan flow 2FA; cek penulisan `SESSION_OUTPUT_FILE`.
- Manual: jalankan userbot, uji `!help`, `!sg`, `!gg`, `!scr`, pastikan penyimpanan JSON/CSV bekerja dan rate limit dihormati.
- Security manual checks: pastikan data terenkripsi tak terbaca tanpa `SECRET_KEY`, log tidak menulis OTP/QR token.

## Rollout & Rollback
- Rollout: deploy components one at a time, verify `python3.11 main.py` (or component-specific runner) starts cleanly, review logs after first session creation.
- Post-rollout checklist: confirm `.env` loaded, commands functional, log forwarding working if enabled.
- Rollback: stop service, restore previous session and data files from backup, redeploy prior git commit per project rules (small patch reversion), verify startup logs again.

## Run Instructions (summary for reference)
- Runtime: Python 3.11 (gunakan virtualenv `.venv`).
- Install dependencies: `pip install -r requirements.txt` setelah aktivasi venv.
- Jalankan wizard: `python -m bot.main`; session generator: `python -m sessiongen.main`; userbot: `python -m userbot.main`.
- Pastikan `.env` terisi lengkap (`TELEGRAM_BOT_TOKEN`, `API_ID`, `API_HASH`, dll.) sebelum menjalankan komponen.

## Out of Scope
- No web dashboard or admin UI.
- No cloud storage or queue services; local-first only.
- No command set beyond `!help`, `!sg`, `!gg`, `!scr`.
- No auto-updates or advanced analytics.
