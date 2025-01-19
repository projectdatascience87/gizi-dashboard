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
data_file = 'Gizi_Anak_Indramayu.xlsx'  # Ganti dengan nama file data Anda
data = pd.read_csv(data_file)

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

# Judul aplikasi
st.title("Pemetaan dan Analisis Gizi di Indramayu")

# Filter data berdasarkan status gizi jika diinginkan
status_filter = st.multiselect(
    "Pilih Status Gizi untuk Ditampilkan:",
    options=data['Status_Gizi'].unique(),
    default=data['Status_Gizi'].unique()
)

data_filtered = data[data['Status_Gizi'].isin(status_filter)]

# Analisis tingkat gizi terburuk
st.header("Analisis Daerah dengan Tingkat Gizi Terburuk")
worst_gizi = data[data['Status_Gizi'] == 'Gizi Buruk']
worst_summary = worst_gizi.groupby('Desa_Kel').size().reset_index(name='Jumlah Anak Gizi Buruk')
worst_summary = worst_summary.sort_values(by='Jumlah Anak Gizi Buruk', ascending=False)

st.subheader("Daftar Desa dengan Jumlah Anak Gizi Buruk Tertinggi")
st.dataframe(worst_summary)

# Menambahkan rekomendasi
st.subheader("Rekomendasi Intervensi Pemerintah")
if not worst_summary.empty:
    top_desa = worst_summary.iloc[0]
    st.write(f"Desa dengan prioritas tertinggi untuk intervensi adalah **{top_desa['Desa_Kel']}**, "
             f"dengan jumlah **{top_desa['Jumlah Anak Gizi Buruk']} anak** yang mengalami gizi buruk. "
             "Pemerintah dapat memprioritaskan pengiriman makanan bergizi ke desa ini.")
else:
    st.write("Tidak ada data gizi buruk untuk dianalisis.")

# Clustering menggunakan K-Means
st.header("Clustering Daerah Berdasarkan Status Gizi")
cluster_features = data.groupby('Desa_Kel').size().reset_index(name='Total Anak')
kmeans = KMeans(n_clusters=3, random_state=42)
cluster_features['Cluster'] = kmeans.fit_predict(cluster_features[['Total Anak']])

st.subheader("Hasil Clustering")
st.dataframe(cluster_features)

# Membuat peta dasar
m = folium.Map(location=[-6.454198, 108.3626961], zoom_start=10)

# Menambahkan marker berdasarkan data
for feature in geo_data['features']:
    desa_name = feature['properties']['name']

    # Filter data untuk desa tertentu tanpa 'Outlier'
    subset = data_filtered[(data_filtered['Desa_Kel'].str.upper() == desa_name) & (data_filtered['Status_Gizi'] != 'Outlier')]

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

        # Menambahkan marker untuk desa tersebut dengan Tooltip
        folium.CircleMarker(
            location=[feature['geometry']['coordinates'][1], feature['geometry']['coordinates'][0]],
            radius=15,
            color='black',
            fill=True,
            fill_color=dominant_color,
            fill_opacity=0.8,
            tooltip=folium.Tooltip(tooltip_content, sticky=True)
        ).add_to(m)

# Menambahkan legenda
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

# Menampilkan peta di Streamlit
st.subheader("Peta Persebaran Status Gizi")
st_folium(m, width=700, height=500)
