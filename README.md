# UROSON Patient API

Backend + form website untuk menjembatani data pasien antara **website input** dan **aplikasi UROSON**.

```
Website (form pasien)  --POST /api/patients-->  MongoDB (Railway)
UROSON (desktop app)   --GET  /api/patients/{id}-->  MongoDB (Railway)
```

## Isi folder

- `main.py` — server FastAPI (endpoint API + menyajikan form website)
- `static/index.html` — halaman form input data pasien
- `requirements.txt` — dependency Python
- `Procfile` — perintah start untuk Railway

## Cara deploy ke Railway

1. **Buat project baru** di [railway.com](https://railway.com) → "New Project".
2. **Tambahkan MongoDB**: klik "+ New" → "Database" → "Add MongoDB". Railway akan
   membuat service MongoDB dan menyediakan environment variable koneksi
   (biasanya `MONGO_URL` atau `MONGO_PUBLIC_URL`) secara otomatis.
3. **Deploy folder ini** sebagai service terpisah:
   - Opsi A: push folder ini ke repo GitHub, lalu di Railway pilih "Deploy from GitHub repo".
   - Opsi B: install Railway CLI, lalu jalankan `railway up` dari dalam folder ini.
4. **Hubungkan variabel MongoDB ke service API**: di tab Variables service API,
   tambahkan reference ke variabel Mongo, misalnya:
   ```
   MONGO_URL=${{Mongo.MONGO_URL}}
   ```
   (nama service Mongo bisa berbeda, sesuaikan dengan nama service Mongo Anda di Railway.)
5. **(Opsional) Amankan endpoint tulis** dengan menambahkan variabel:
   ```
   API_KEY=isi-bebas-yang-rahasia
   ```
   Jika diisi, `POST /api/patients` akan menolak request tanpa header `x-api-key` yang cocok.
   Kalau Anda mengaktifkan ini, isi juga nilai yang sama di `const API_KEY = "..."`
   pada `static/index.html`.
6. Railway akan memberi Anda domain publik, misalnya:
   `https://uroson-api-production.up.railway.app`
   - Buka domain itu di browser → tampil form input pasien.
   - Endpoint API ada di `https://.../api/patients/...`

## Kontrak API (dipakai UROSON)

Semua respons dibungkus format `{"status": true/false, ...}` supaya gampang
dicek dari kode UROSON (`if data["status"]: ...`).

**GET `/api/patients/{patientid}`**

Header wajib (jika `API_KEY` di-set): `x-api-key: <API_KEY>`

Respons 200 (ditemukan):
```json
{
  "status": true,
  "data": {
    "patientid": 1235,
    "name": "Budi Santoso",
    "dob": "1980-05-15",
    "gender": "F"
  }
}
```
Respons 404 (tidak ditemukan) atau 401 (API key salah):
```json
{ "status": false }
```

**POST `/api/patients`** (dipanggil form website)

Header wajib (jika `API_KEY` di-set): `x-api-key: <API_KEY>`

Body:
```json
{
  "patientid": 1235,
  "name": "Budi Santoso",
  "dob": "1980-05-15",
  "gender": "F",
  "hospital_name": "RS Contoh",
  "doctor_name": "dr. Andi"
}
```
- `gender` hanya menerima `"M"` atau `"F"`.
- `dob` format `YYYY-MM-DD`.
- `hospital_name` dan `doctor_name` opsional.

Respons 200 (berhasil):
```json
{
  "status": true,
  "data": {
    "patientid": 1235,
    "name": "Budi Santoso",
    "dob": "1980-05-15",
    "gender": "F"
  }
}
```
- 409: `patientid` sudah pernah dipakai → `{"status": false, "message": "..."}`.
- 401: `API_KEY` aktif tapi header `x-api-key` tidak cocok/tidak ada → `{"status": false}`.

> Catatan: dibanding versi sebelumnya, endpoint GET sekarang juga dilindungi
> `API_KEY` (kalau di-set), karena data pasien sebaiknya tidak bisa dibaca
> siapa saja yang tahu URL Railway-nya.

## Menghubungkan UROSON

Di kode UROSON, ganti `API_BASE_URL` (dekat bagian atas file) dengan domain Railway
Anda, misalnya:
```python
API_BASE_URL = "https://uroson-api-production.up.railway.app"
```
Setelah itu, saat staf mengetik ID Pasien dan klik tombol **"🔍 Cari"** di form
"Patient Information", UROSON akan memanggil `GET /api/patients/{id}` dan mengisi
otomatis Nama, Jenis Kelamin, Usia, Rumah Sakit, dan Dokter — field-field ini
dikunci (read-only) di UROSON karena sumber datanya adalah website, bukan
diketik ulang di alat.

## Menjalankan secara lokal (opsional, untuk uji coba sebelum deploy)

```bash
pip install -r requirements.txt
export MONGO_URL="mongodb://localhost:27017"   # atau connection string Atlas/Railway
uvicorn main:app --reload
```
Buka `http://127.0.0.1:8000` untuk form, dan `http://127.0.0.1:8000/docs` untuk
dokumentasi API interaktif (Swagger UI) bawaan FastAPI.
