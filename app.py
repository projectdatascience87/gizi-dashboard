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
    data['Tanggal_Pengukuran'] = data['Tanggal_Pengukuran'].astype(str).str.strip()
    data['Tanggal_Pengukuran'] = pd.to_datetime(data['Tanggal_Pengukuran'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
elif 'Tanggal Pengukuran' in data.columns:
    data['Tanggal Pengukuran'] = data['Tanggal Pengukuran'].astype(str).str.strip()
    data['Tanggal Pengukuran'] = pd.to_datetime(data['Tanggal Pengukuran'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    data.rename(columns={'Tanggal Pengukuran': 'Tanggal_Pengukuran'}, inplace=True)
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

# Mengubah nama desa menjadi uppercase di GeoJSON
for feature in geo_data['features']:
    feature['properties']['name'] = feature['properties']['name'].upper()

# Warna untuk status gizi
status_colors = {
    'Gizi Baik': 'green',
    'Gizi Buruk': 'red',
    'Gizi Kurang': 'orange',
    'Gizi Lebih': 'blue'
}

# Sidebar navigasi
st.sidebar.title("Dashboard Navigasi")
menu = st.sidebar.radio(
    "Pilih Halaman",
    ["Beranda", "Analisis Gizi Buruk", "Clustering", "Peta Persebaran"]
)

# Halaman Beranda
if menu == "Beranda":
    st.title("Dashboard Gizi Anak di Indramayu Data Update 2024")
    st.markdown(
        """
        Selamat datang di dashboard pemetaan dan menganalisis status gizi anak-anak di Kabupaten Indramayu Data Update 2024. 
        Gunakan navigasi di sebelah kiri untuk menjelajahi data.
        """
    )

# Halaman Analisis Gizi Buruk
elif menu == "Analisis Gizi Buruk":
    st.title("Analisis Daerah dengan Tingkat Gizi Terburuk")
    worst_gizi = data[data['Status_Gizi'] == 'Gizi Buruk']
    worst_summary = worst_gizi.groupby('Desa_Kel').size().reset_index(name='Jumlah Anak Gizi Buruk')
    worst_summary = worst_summary.sort_values(by='Jumlah Anak Gizi Buruk', ascending=False)

    st.subheader("Daftar Desa dengan Jumlah Anak Gizi Buruk Tertinggi")
    st.dataframe(worst_summary)

    st.subheader("Rekomendasi Intervensi Pemerintah")
    if not worst_summary.empty:
        top_desa = worst_summary.iloc[0]
        st.write(f"Desa dengan prioritas tertinggi untuk intervensi adalah **{top_desa['Desa_Kel']}**, "
                 f"dengan jumlah **{top_desa['Jumlah Anak Gizi Buruk']} anak** yang mengalami gizi buruk. "
                 "Pemerintah dapat memprioritaskan pengiriman makanan bergizi ke desa ini.")
    else:
        st.write("Tidak ada data gizi buruk untuk dianalisis.")

# Halaman Clustering
elif menu == "Clustering":
    st.title("Clustering Daerah Berdasarkan Status Gizi")
    cluster_features = data.groupby('Desa_Kel').size().reset_index(name='Total Anak')
    kmeans = KMeans(n_clusters=3, random_state=42)
    cluster_features['Cluster'] = kmeans.fit_predict(cluster_features[['Total Anak']])

    st.subheader("Hasil Clustering")
    st.dataframe(cluster_features)

# Halaman Peta Persebaran
elif menu == "Peta Persebaran":
    st.title("Peta Persebaran Status Gizi Data Update 2024")
    m = folium.Map(location=[-6.454198, 108.3626961], zoom_start=10)

    for feature in geo_data['features']:
        desa_name = feature['properties']['name']
        subset = data[data['Desa_Kel'].str.upper() == desa_name]
        if not subset.empty:
            status_counts = subset['Status_Gizi'].value_counts()
            total_anak = status_counts.sum()
            dominant_status = status_counts.idxmax()
            dominant_color = status_colors.get(dominant_status, 'purple')

            tooltip_content = f"<b>Desa: {desa_name}</b><br>Total Anak: {total_anak}<br><br>"
            for status_gizi, jumlah in status_counts.items():
                presentase = (jumlah / total_anak) * 100
                color = status_colors.get(status_gizi, 'purple')
                tooltip_content += f"""
                <span style="color:{color};">
                    • {status_gizi}: {jumlah} anak ({presentase:.2f}%)
                </span><br>
                """

            folium.CircleMarker(
                location=[feature['geometry']['coordinates'][1], feature['geometry']['coordinates'][0]],
                radius=15,
                color='black',
                fill=True,
                fill_color=dominant_color,
                fill_opacity=0.8,
                tooltip=folium.Tooltip(tooltip_content, sticky=True)
            ).add_to(m)

    legend_html = """
    {% macro html(this, kwargs) %}
    <div style="
        position: fixed;
        bottom: 50px; left: 50px; width: 150px; height: 120px;
        background-color: white; z-index:9999; font-size:14px;
        border:2px solid grey; padding: 10px;">
        <b>Status Gizi:</b><br>
        <i style="background:green; width:10px; height:10px; display:inline-block;"></i> Gizi Baik<br>
        <i style="background:red; width:10px; height:10px; display:inline-block;"></i> Gizi Buruk<br>
        <i style="background:orange; width:10px; height:10px; display:inline-block;"></i> Gizi Kurang<br>
        <i style="background:blue; width:10px; height:10px; display:inline-block;"></i> Gizi Lebih<br>
    </div>
    {% endmacro %}
    """
    legend = MacroElement()
    legend._template = Template(legend_html)
    m.get_root().add_child(legend)

    st_folium(m, width=700, height=500)
