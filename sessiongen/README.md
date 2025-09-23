# sessiongen/ – Session Generator

Bot minimal untuk pengguna yang hanya butuh string session Telethon.

## Cara Jalan
```bash
python sessiongen/main.py
```

## Fitur
- Input nomor, API ID, API hash → kirim OTP → hasilkan session string.
- Opsional simpan terenkripsi jika `SECRET_KEY` terisi.
- `/delete` untuk hapus penyimpanan terenkripsi.

Log dicatat di `logs/sessiongen.log`, hasil session terenkripsi tersimpan di `data/sessions.json`.
