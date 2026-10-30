# Data Preparation & Pipeline Project — Automobile Dataset

Projek submission untuk Individual Assignment pada program AI Engineering Bootcamp (Topik: Data Engineering - Pipeline & Preparation).

Repo ini berisi pipeline ETL berbasis Python dan Pandas untuk membersihkan serta mentransformasi dataset otomotif mentah (`automobileEDA_dirty_training.csv`) sampai siap dipakai untuk analisis lanjutan atau pemodelan *machine learning*.

- **Nama Peserta:** Kanza Az Zahrawani
- **Email:** rexxar280903@gmail.com
- **Dataset:** Automobile Dataset (berdasarkan materi Sesi 3 Bootcamp)

---

## 1. Ringkasan Dataset

Dataset mentah yang digunakan adalah `automobileEDA_dirty_training.csv` yang disimpan di folder `data/raw/`. File ini berisi 205 baris dan 30 kolom spesifikasi mobil, termasuk dimensi bodi, performa mesin, efisiensi bahan bakar, harga, serta tanggal transaksi.

Catatan awal:
- Kolom `price` menjadi kandidat target utama untuk prediksi.
- Kolom dimensi `length` dan `width` pada data mentah sudah dalam skala ternormalisasi (rentang 0-1) dari tahap eksplorasi sebelumnya, sehingga tidak perlu di-scale ulang.

## 2. Struktur Direktori

Sesuai instruksi penyiapan project pada assignment:

```text
data-pipeline-assignment/
├── data/
│   ├── raw/
│   │   └── automobileEDA_dirty_training.csv   # dataset mentah (read-only)
│   └── processed/
│       └── automobileEDA_processed.csv        # output hasil pipeline
├── src/
│   └── pipeline.py                            # script utama ETL pipeline
├── documentation/
│   ├── data-flow-diagram.png                  # diagram alur data
│   └── make_diagram.py                        # script generator diagram
├── README.md                                  # dokumentasi lengkap project
└── requirements.txt                           # daftar dependensi python
```

## 3. Cara Menjalankan Pipeline

### Langkah 1: Persiapan Environment

```bash
# Clone repository
git clone https://github.com/rexxar280903/assignment-data-pipeline-kanza-az-zahrawani.git
cd assignment-data-pipeline-kanza-az-zahrawani

# Buat dan aktifkan virtual environment (opsional tetapi disarankan)
python -m venv .venv

# Di Windows:
.venv\Scripts\activate

# Di macOS / Linux:
source .venv/bin/activate
```

### Langkah 2: Install Dependensi

```bash
pip install -r requirements.txt
```

### Langkah 3: Eksekusi Script

```bash
python src/pipeline.py
```

Setelah script selesai:
1. Terminal akan menampilkan laporan lengkap per tahap (inspeksi awal, ringkasan cleaning, perbandingan transformasi, hingga summary akhir).
2. File hasil pemrosesan otomatis tersimpan di `data/processed/automobileEDA_processed.csv`.
3. Dataset mentah di `data/raw/` dijamin tidak berubah sedikit pun.

---

## 4. Alur ETL (Extract - Transform - Load)

Pipeline disusun dengan pendekatan modular menggunakan beberapa fungsi utama yang terangkai dalam fungsi `run_pipeline()`:

![Data Flow Diagram](documentation/data-flow-diagram.png)

1. **Extract (`load_data`)**:
   Membaca file CSV mentah dari `data/raw/` secara aman tanpa mengubah file sumber.
2. **Transform - Inspection (`inspect_data`)**:
   Memeriksa 5 baris pertama, dimensi, tipe data, missing values, duplikasi, keunikan nilai kategori, format tanggal, dan ringkasan statistik.
3. **Transform - Cleaning (`clean_data`)**:
   Menyeragamkan string kategori, membuang baris duplikat, merapikan format tanggal, menangani missing values, dan membetulkan tipe data kolom.
4. **Transform - Feature Transformation (`transform_data`)**:
   Melakukan Min-Max scaling pada kolom numerik, one-hot encoding pada variabel nominal, ordinal encoding pada data bertingkat, dan frequency encoding untuk merek mobil.
5. **Load (`save_data`)**:
   Menyimpan hasil akhir ke `data/processed/automobileEDA_processed.csv`.

---

## 5. Temuan Pemeriksaan Awal (Data Inspection)

Saat pertama kali dataset diperiksa lewat `inspect_data()`, ditemukan beberapa kendala kualitas data berikut:

1. **Ukuran Awal**: 205 baris dan 30 kolom.
2. **Missing Values**: Total ada 17 sel kosong yang tersebar di 7 kolom:
   - `stroke`: 4 baris kosong
   - `horsepower`: 3 baris kosong
   - `price`: 3 baris kosong
   - `transaction_date`: 2 baris kosong
   - `make`: 2 baris kosong
   - `num-of-doors`: 2 baris kosong
   - `horsepower-binned`: 1 baris kosong
3. **Baris Terduplikasi**: Ditemukan 4 baris data yang duplikat persis di baris indeks 201–204 (salinan dari data nomor 5, 25, 60, dan 100).
4. **Format Tanggal Tidak Seragam**:
   Kolom `transaction_date` masih berupa teks dengan 4 gaya penulisan berbeda: `YYYY-MM-DD`, `DD/MM/YYYY`, `MM-DD-YYYY`, dan `DD-Mon-YYYY`.
5. **Penulisan Kategori Tidak Konsisten**:
   - `make`: Terdapat perbedaan huruf besar-kecil seperti `ALFA-ROMERO`, `Audi`, `BMW`, serta spasi berlebih di belakang kata (`dodge  `, `mercury  `, `porsche  `). Hal ini membuat merek terhitung 27 kategori padahal aslinya hanya 22.
   - `body-style`: Terbaca `SEDAN`, `Sedan`, dan `sedan`.
   - `drive-wheels`: Terbaca `AWD`, `RWD`, dan varian huruf kecil.
   - `fuel-system`: Terbaca `MPFI`, `Mpfi`, dan `mpfi`.
6. **Karakteristik Khusus**:
   - Nilai `stroke` yang kosong seluruhnya terjadi pada mobil Mazda bermesin rotary (`engine-type = rotor`). Mesin rotary tidak memakai piston bolak-balik, sehingga secara teknis memang tidak memiliki langkah piston (stroke).
   - Nilai `price` kosong pada 3 baris. Karena `price` adalah variabel target analisis/prediksi, baris ini tidak boleh diisi sembarangan dengan nilai tebakan.

---

## 6. Proses Data Cleaning & Alasannya

Berikut strategi pembersihan yang saya terapkan di `clean_data()`:

| Permasalahan | Kolom Terdampak | Tindakan Pembersihan | Alasan Pemilihan Metode |
|---|---|---|---|
| Penulisan string tidak rapi | Kolom kategorikal (`make`, `body-style`, dll.) | Menghapus spasi (`strip()`) dan menyeragamkan ke huruf kecil (`lower()`). Khusus `horsepower-binned` tetap mempertahankan Title Case. | Agar kategori yang maknanya sama tidak terpecah menjadi grup yang berbeda. Dilakukan paling awal agar duplikasi terselubung bisa terdeteksi. |
| Baris duplikat | Semua kolom | Menghapus 4 baris duplikat (`drop_duplicates()`). | Data duplikat identik tidak memberikan variasi informasi baru dan bisa membuat evaluasi model menjadi bias. |
| Format tanggal beragam & 2 data tanggal kosong | `transaction_date` | Parsing tanggal dengan pola format eksplisit ke `datetime`, lalu mengisi 2 nilai kosong dengan interpolasi deret tanggal. | Menghindari tertukarnya hari dan bulan. Dataset tersusun harian secara urut dari awal tahun 2025, sehingga interpolasi memberikan tanggal yang tepat (terisi tanggal 2025-02-10 dan 2025-05-21). |
| Data target kosong | `price` | Menghapus baris yang memiliki missing value pada kolom `price` (3 baris dihapus). | Target prediksi tidak boleh diimputasi/ditebak agar tidak menciptakan label palsu (*ground truth leakage*). |
| Merek mobil kosong | `make` | Mengisi nilai kosong berdasarkan kecocokan spesifikasi teknis mobil yang identik dan baris sekitarnya. | Baris kosong yang tersisa setelah dedup berada di tengah kelompok mobil Nissan dengan dimensi dan mesin identik, sehingga diisi sebagai `nissan`. |
| Jumlah pintu kosong | `num-of-doors` | Mengisi nilai kosong menggunakan modus (nilai tersering) berdasarkan kombinasi `make` dan `body-style`. | Jumlah pintu mobil sedan dari brand sejenis (misal BMW sedan atau Mercedes sedan) secara dominan adalah empat pintu. |
| Nilai horsepower kosong | `horsepower` | Mengisi nilai kosong menggunakan median berdasarkan kelompok `engine-size` dan kategori `horsepower-binned`. | Ukuran kapasitas mesin berkorelasi sangat kuat dengan tenaga kuda, dan batas bin membantu membatasi rentang imputasi agar tetap masuk akal. |
| Nilai stroke kosong | `stroke` | Mengisi dengan median keseluruhan dan menambahkan kolom indikator `stroke_was_missing`. | Khusus mesin rotary tidak punya stroke fisik. Pengisian median menjaga kolom tetap numerik untuk algoritma, sementara indikator biner menandai bahwa nilai tersebut merupakan hasil imputasi. |
| Kategori horsepower kosong | `horsepower-binned` | Mengisi 1 nilai kosong Jaguar (262 hp) menggunakan batas rentang bin yang sudah ada pada data. | Jaguar 262 hp berada di atas batas nilai Medium (≤155), sehingga secara logis masuk kategori `High`. |
| Tipe data | `horsepower`, `peak-rpm`, tanggal | Mengubah kolom numerik bulat menjadi integer, serta kolom tanggal menjadi format standar `datetime`. | Memastikan tipe data efisien dan sesuai dengan sifat data aslinya setelah ketiadaan nilai NaN. |

### Perbandingan Data Sebelum & Sesudah Cleaning:
- **Jumlah Baris**: 205 baris → **198 baris** (berkurang 4 karena duplikat dan 3 karena harga kosong).
- **Missing Values**: 17 sel kosong → **0 (bersih seluruhnya)**.
- **Kategori Merek (`make`)**: 27 variasi teks → **22 merek valid**.

---

## 7. Proses Data Transformation

Setelah dataset bersih dari duplikat dan nilai kosong, tahap transformasi dilakukan pada `transform_data()`:

### 7.1 Normalisasi Fitur Numerik (Min-Max Scaling)

Saya memilih **Min-Max Scaling** untuk menyeragamkan rentang kolom-kolom numerik ke skala `0` sampai `1`.

- **Rumus**:
  $$\text{scaled} = \frac{x - x_{\min}}{x_{\max} - x_{\min}}$$
- **Kolom yang Ditransformasi**:
  `price`, `horsepower`, `engine-size`, `curb-weight`, `peak-rpm`, `city-mpg`, `highway-mpg`.
- **Alasan Pemilihan Kolom**:
  Kolom-kolom tersebut memiliki satuan dan rentang angka yang berbeda jauh (misal harga berkisar puluhan ribu, sedangkan mpg di angka puluhan). Normalisasi diperlukan agar fitur bernilai besar tidak mendominasi model berbasis jarak atau gradien.
- **Implementasi**:
  Nilai hasil skala disimpan ke dalam kolom baru berakhiran `_minmax`, sementara kolom aslinya tetap dipertahankan agar mudah dibandingkan.

**Contoh Nilai Sebelum vs Sesudah Min-Max Scaling:**

| make | price (asli) | price_minmax | horsepower (asli) | horsepower_minmax | curb-weight (asli) | curb-weight_minmax |
|---|---|---|---|---|---|---|
| alfa-romero | 13495.0 | 0.207959 | 111 | 0.294393 | 2548 | 0.411171 |
| alfa-romero | 16500.0 | 0.282558 | 111 | 0.294393 | 2548 | 0.411171 |
| alfa-romero | 16500.0 | 0.282558 | 154 | 0.495327 | 2823 | 0.517843 |
| audi | 13950.0 | 0.219254 | 102 | 0.252336 | 2337 | 0.329325 |
| audi | 17450.0 | 0.306142 | 115 | 0.313084 | 2824 | 0.518231 |

### 7.2 Encoding Variabel Kategorikal

Transformasi variabel kategori dibagi menjadi beberapa metode sesuai sifat datanya:

1. **One-Hot Encoding**:
   - Diterapkan pada kolom kategori nominal (tanpa tingkatan urutan): `aspiration`, `body-style`, `drive-wheels`, `engine-location`, `engine-type`, dan `fuel-system`.
   - Menggunakan `pd.get_dummies()` sehingga menghasilkan kolom biner (0/1) untuk tiap nilai unik tanpa mengasumsikan urutan nilai.
2. **Ordinal Encoding (Kata ke Angka)**:
   - Diterapkan pada `num-of-doors` (`two` → 2, `four` → 4) dan `num-of-cylinders` (`two` → 2, `four` → 4, `six` → 6, dst.).
   - Kolom `horsepower-binned` diubah ke urutan tingkat performa: `Low` = 0, `Medium` = 1, `High` = 2.
3. **Frequency Encoding**:
   - Diterapkan pada kolom `make`. Karena merek mobil memiliki 22 variasi unik, penggunaan One-Hot Encoding akan menghasilkan terlalu banyak kolom baru (*curse of dimensionality*). Merek dikonversi ke frekuensi kemunculannya pada dataset (kolom `make_freq`).

**Contoh Nilai Sebelum vs Sesudah Encoding:**

| make | num-of-doors | num-of-cylinders | drive-wheels | make_freq | num-of-doors_num | num-of-cylinders_num | drive-wheels_fwd | drive-wheels_rwd |
|---|---|---|---|---|---|---|---|---|
| alfa-romero | two | four | rwd | 0.015152 | 2 | 4 | 0 | 1 |
| alfa-romero | two | six | rwd | 0.015152 | 2 | 6 | 0 | 1 |
| audi | four | four | fwd | 0.035354 | 4 | 4 | 1 | 0 |
| audi | four | five | 4wd | 0.035354 | 4 | 5 | 0 | 0 |

---

## 8. Ringkasan Hasil Akhir Dataset

Perbandingan kondisi dataset dari awal hingga siap digunakan:

| Metrik Evaluasi | Kondisi Awal (Raw) | Kondisi Akhir (Processed) |
|---|---|---|
| **Jumlah Baris** | 205 baris | **198 baris** |
| **Jumlah Kolom** | 30 kolom | **61 kolom** |
| **Total Missing Value** | 17 sel | **0 sel (bersih)** |
| **Baris Terduplikasi** | 4 baris | **0 baris** |
| **Format File Output** | CSV mentah | CSV siap model (`data/processed/automobileEDA_processed.csv`) |

File output berhasil digenerate langsung melalui eksekusi `python src/pipeline.py` dan siap digunakan pada tahapan pemodelan AI berikutnya.
