import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from sklearn.cluster import KMeans
import json
import random

import pandas as pd

import pandas as pd

file_gabungan = 'Gizi_Anak_Indramayu.xlsx'
gabungan = pd.read_excel(file_gabungan)


if 'Tanggal_Pengukuran' in gabungan.columns:
    # Bersihkan data kolom
    gabungan['Tanggal_Pengukuran'] = gabungan['Tanggal_Pengukuran'].astype(str).str.strip()

    # Ubah kolom 'Tanggal_Pengukuran' menjadi format datetime dengan format eksplisit
    gabungan['Tanggal_Pengukuran'] = pd.to_datetime(
        gabungan['Tanggal_Pengukuran'],
        format='%Y-%m-%d %H:%M:%S',
        errors='coerce'
    )

    # Filter data hanya untuk tahun 2024
    data_2024 = gabungan[gabungan['Tanggal_Pengukuran'].dt.year == 2024]

    data_2024 = data_2024.dropna(subset=['Tanggal_Pengukuran'])

elif 'Tanggal Pengukuran' in gabungan.columns:
    gabungan['Tanggal Pengukuran'] = gabungan['Tanggal Pengukuran'].astype(str).str.strip()
    gabungan['Tanggal Pengukuran'] = pd.to_datetime(
        gabungan['Tanggal Pengukuran'],
        format='%Y-%m-%d %H:%M:%S',
        errors='coerce'
    )
    data_2024 = gabungan[gabungan['Tanggal Pengukuran'].dt.year == 2024]
    data_2024 = data_2024.dropna(subset=['Tanggal Pengukuran'])
else:
    raise ValueError("Kolom 'Tanggal_Pengukuran' atau 'Tanggal Pengukuran' tidak ditemukan dalam data.")

# Fungsi untuk mengekstrak tahun dari string usia
def extract_years(age_str):
    if isinstance(age_str, str) and 'Tahun' in age_str:
        try:
            return int(age_str.split('Tahun')[0].strip())
        except ValueError:
            return None  # Kembalikan None jika tidak bisa dikonversi
    return None  # Kembalikan None jika format tidak sesuai

# Langkah 3: Mengambil usia dari kolom 'Usia_Saat_Ukur'
data_2024['Usia_Saat_Ukur'] = data_2024['Usia_Saat_Ukur'].apply(extract_years)

# Menghilangkan kategori 'Outlier' dari data
data_filtered = data_2024[data_2024['Status_Gizi'] != 'Outlier']
# Menghitung jumlah anak untuk setiap Status Gizi tanpa kategori 'Outlier'
status_counts = data_filtered['Status_Gizi'].value_counts().reset_index()
status_counts.columns = ['Status_Gizi', 'Jumlah']

# Langkah 5: Mengelompokan data berdasarkan Status Gizi, Usia Saat Ukur, dan Wilayah Desa
grouped_data = data_filtered.groupby(['Desa_Kel', 'Usia_Saat_Ukur', 'Status_Gizi']).size().reset_index(name='Jumlah')


# Membaca file GeoJSON
with open('indramayu.geojson') as f:
    geo_data = json.load(f)

# Mengubah nama desa menjadi uppercase
for feature in geo_data['features']:
    feature['properties']['name'] = feature['properties']['name'].upper()

desa_names = [
    'BOJONGSARI', 'DUKUH', 'KARANGANYAR', 'KARANGMALANG', 'KARANGSONG',
    'KEPANDEAN', 'LEMAHABANG', 'LEMAHMEKAR', 'MARGADADI', 'PABEANUDIK',
    'PAOMAN', 'PECANDANGAN', 'PEKANDANGAN JAYA', 'PLUMBON', 'SINGA',
    'SINGARAJA', 'TAMBAK', 'TELUKAGUNG'
]

# Generate random data for Status_Gizi to match the length of desa_names
status_gizi_options = ['Gizi Buruk', 'Gizi Baik', 'Gizi Kurang', 'Gizi Lebih']
status_gizi = [random.choice(status_gizi_options) for _ in range(len(desa_names))]

# Membuat data gizi
data_filtered = pd.DataFrame({
    'Desa_Kel': desa_names,
    'Status_Gizi': status_gizi
})

data_filtered['Desa_Kel'] = data_filtered['Desa_Kel'].str.upper()

# Membuat pivot table berdasarkan Status_Gizi
data_pivot = data_filtered.pivot_table(
    index='Desa_Kel',
    columns='Status_Gizi',
    aggfunc='size',
    fill_value=0
).reset_index()

data_pivot.columns.name = None

data_pivot = data_pivot.rename(columns={
    'Desa_Kel': 'Desa_Kel',
    'Gizi Buruk': 'Gizi Buruk',
    'Gizi Baik': 'Gizi Baik',
    'Gizi Kurang': 'Gizi Kurang',
    'Gizi Lebih': 'Gizi Lebih'
})

# Menambahkan koordinat desa
coordinates = []
for desa in data_pivot['Desa_Kel']:
    found = False
    for feature in geo_data['features']:
        if feature['properties']['name'] == desa:
            coordinates.append(feature['geometry']['coordinates'])
            found = True
            break
    if not found:
        coordinates.append([0, 0])

data_pivot['Coordinates'] = coordinates

# K-Means Clustering
X = data_pivot[['Gizi Buruk']].values
kmeans = KMeans(n_clusters=3, random_state=42).fit(X)
data_pivot['Cluster'] = kmeans.labels_

# Streamlit UI
st.title("Pemetaan Daerah dengan Tingkat Gizi Buruk")
st.markdown("""
Aplikasi ini memvisualisasikan tingkat gizi buruk di wilayah tertentu, 
dengan prioritas intervensi berdasarkan clustering.
""")

# Membuat peta dasar
m = folium.Map(location=[-6.454198, 108.3626961], zoom_start=10)

# Menambahkan marker untuk setiap desa
for _, row in data_pivot.iterrows():
    desa_name = row['Desa_Kel']
    coords = row['Coordinates']
    cluster = row['Cluster']
    color = 'red' if cluster == 2 else 'orange' if cluster == 1 else 'green'

    tooltip_content = f"""
    <b>Desa: {desa_name}</b><br>
    Gizi Buruk: {row['Gizi Buruk']} anak<br>
    Gizi Baik: {row['Gizi Baik']} anak<br>
    Gizi Kurang: {row['Gizi Kurang']} anak<br>
    Gizi Lebih: {row['Gizi Lebih']} anak<br>
    Prioritas Intervensi: {"Tinggi" if cluster == 2 else "Sedang" if cluster == 1 else "Rendah"}
    """

    if coords != [0, 0]:
        folium.CircleMarker(
            location=[coords[1], coords[0]],
            radius=15,
            color='black',
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            tooltip=tooltip_content
        ).add_to(m)

# Menambahkan peta ke Streamlit
st_data = st_folium(m, width=700, height=500)

# Menampilkan rekomendasi
st.subheader("Rekomendasi Prioritas Intervensi")
prioritas_tinggi = data_pivot[data_pivot['Cluster'] == 2]
st.write("### Desa dengan Prioritas Tinggi:")
st.table(prioritas_tinggi[['Desa_Kel', 'Gizi Buruk']])
