# Monitoring Drainase

Pemantauan dan pemeliharaan saluran drainase. Prototipe independen, bukan aplikasi resmi pemerintah.

## Fitur utama

- Inventaris saluran/wilayah, penanggung jawab, peta Leaflet/OpenStreetMap dan input koordinat melalui peta atau formulir.
- Admin mengelola Petugas, jadwal inspeksi/pemeliharaan dan laporan; Petugas hanya mengakses penugasan yang sesuai.
- Inspeksi kondisi/kerusakan/sumbatan, riwayat, foto JPEG/PNG/WebP maksimal 5 MB dengan metadata dihapus.
- Status/progres pekerjaan, dokumentasi sebelum/sesudah, dashboard/grafik dari database dan CSV periode/wilayah.

## Teknologi

Python 3.13, FastAPI, Jinja2, SQLAlchemy, SQLite, Pillow, Leaflet, HTML, CSS, JavaScript.

## Cara instalasi

~~~powershell
cd C:\laragon\www\monitoring-drainase
& 'C:\laragon\bin\python\python-3.13\python.exe' -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m core.migrate
.venv\Scripts\python -m core.users --role Admin
~~~

Sesuaikan lokasi Python jika berbeda. Tidak ada akun bawaan; buat Petugas melalui Admin atau CLI --role Petugas.

## Cara menjalankan

~~~powershell
.venv\Scripts\python run.py
~~~

Buka http://127.0.0.1:5511. Data privat berada di instance; APP_INSTANCE mengubah lokasi. Gunakan SECURE_COOKIE=1 saat HTTPS. Tes: .venv\Scripts\python -m pytest -q; lint: .venv\Scripts\python -m ruff check .; pemeriksaan sintaks: .venv\Scripts\python -m compileall -q app core. Migrasi awal aman diulang. Peta memerlukan internet untuk tile OpenStreetMap dan menampilkan atribusi; tabel/input manual tetap berfungsi tanpa tile. Gunakan lokasi/foto demonstrasi. Kondisi dihitung dari kerusakan dan persentase sumbatan; aturan ditampilkan di aplikasi.
