import streamlit as st
import pandas as pd
import folium
import json
from streamlit_folium import st_folium
from sklearn.cluster import KMeans
from branca.element import Template, MacroElement

# Membaca file GeoJSON
with open('indramayu.geojson') as f:
    geo_data = json.load(f)

# Membaca data status gizi
data_file = 'Gizi_Anak_Indramayu.xlsx'
data = pd.read_excel(data_file)

# Bersihkan kolom Tanggal_Pengukuran
if 'Tanggal_Pengukuran' in data.columns:
    data['Tanggal_Pengukuran'] = pd.to_datetime(data['Tanggal_Pengukuran'], errors='coerce')
else:
    st.error("Kolom 'Tanggal_Pengukuran' tidak ditemukan dalam data.")
    st.stop()

# Filter data untuk tahun 2024 dan tanpa 'Outlier'
data = data[data['Tanggal_Pengukuran'].dt.year == 2024]
data = data[data['Status_Gizi'] != 'Outlier']

# Ekstrak usia dari kolom Usia_Saat_Ukur
def extract_years(age_str):
    if isinstance(age_str, str) and 'Tahun' in age_str:
        try:
            return int(age_str.split('Tahun')[0].strip())
        except ValueError:
            return None
    return None

data['Usia_Saat_Ukur'] = data['Usia_Saat_Ukur'].apply(extract_years)

# Warna untuk status gizi
status_colors = {
    'Gizi Baik': 'green',
    'Gizi Buruk': 'red',
    'Gizi Kurang': 'orange',
    'Gizi Lebih': 'blue'
}

# Sidebar Navigation
st.sidebar.title("Dashboard Gizi Anak")
menu = st.sidebar.radio("Navigasi", ["Beranda", "Analisis Gizi", "Clustering", "Peta"])

# Judul Dashboard
st.markdown(
    """
    <style>
        .main-title {
            font-size: 2.5em;
            color: #4CAF50;
            text-align: center;
            font-weight: bold;
        }
    </style>
    <div class="main-title">Dashboard Gizi Anak di Indramayu</div>
    """,
    unsafe_allow_html=True
)

# Beranda
if menu == "Beranda":
    st.markdown("### Selamat Datang di Dashboard Gizi Anak Update 2024 di Indramayu!")
    st.write("Gunakan navigasi di sebelah kiri untuk melihat analisis data, clustering, dan peta.")

# Analisis Gizi
elif menu == "Analisis Gizi":
    st.header("Analisis Daerah dengan Tingkat Gizi Terburuk")
    worst_gizi = data[data['Status_Gizi'] == 'Gizi Buruk']
    worst_summary = worst_gizi.groupby('Desa_Kel').size().reset_index(name='Jumlah Anak Gizi Buruk')
    worst_summary = worst_summary.sort_values(by='Jumlah Anak Gizi Buruk', ascending=False)

    st.subheader("Daftar Desa dengan Jumlah Anak Gizi Buruk Tertinggi")
    st.dataframe(worst_summary)

# Clustering
elif menu == "Clustering":
    st.header("Clustering Daerah Berdasarkan Status Gizi")
    cluster_features = data.groupby('Desa_Kel').size().reset_index(name='Total Anak')
    kmeans = KMeans(n_clusters=3, random_state=42)
    cluster_features['Cluster'] = kmeans.fit_predict(cluster_features[['Total Anak']])

    st.subheader("Hasil Clustering")
    st.dataframe(cluster_features)

# Peta
elif menu == "Peta":
    st.header("Peta Persebaran Status Gizi")
    m = folium.Map(location=[-6.454198, 108.3626961], zoom_start=10)

    for feature in geo_data['features']:
        desa_name = feature['properties']['name']
        subset = data[data['Desa_Kel'].str.upper() == desa_name]
        if not subset.empty:
            status_counts = subset['Status_Gizi'].value_counts()
            total_anak = status_counts.sum()
            dominant_status = status_counts.idxmax()
            dominant_color = status_colors.get(dominant_status, 'purple')

            tooltip_content = f"<b>Desa: {desa_name}</b><br>Total Anak: {total_anak}<br>"
            for status_gizi, jumlah in status_counts.items():
                presentase = (jumlah / total_anak) * 100
                tooltip_content += f"<i style='color:{status_colors[status_gizi]};'>{status_gizi}: {jumlah} ({presentase:.2f}%)</i><br>"

            folium.CircleMarker(
                location=[feature['geometry']['coordinates'][1], feature['geometry']['coordinates'][0]],
                radius=15,
                color='black',
                fill=True,
                fill_color=dominant_color,
                fill_opacity=0.8,
                tooltip=tooltip_content
            ).add_to(m)

    st_folium(m, width=700, height=500)
