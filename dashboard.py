from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Dashboard Bike Sharing", page_icon="🚲", layout="wide")

DATA_DIR = Path(__file__).parent

COLOR_MAIN = "#2a78d6"
COLOR_SECOND = "#eb6834"
COLOR_MUTED = "#c9c8c2"
DAY_TYPE_COLORS = {"Workday": COLOR_MAIN, "Weekend/Holiday": COLOR_SECOND}

SEASON_ORDER = ["Spring", "Summer", "Fall", "Winter"]
WEATHER_ORDER = ["Clear", "Misty", "Light Rain/Snow"]
MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 3rem;}
    div[data-testid="stMetric"] {
        background-color: rgba(128, 128, 128, 0.08);
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 12px;
        padding: 14px 18px;
    }
    div[data-testid="stMetricValue"] {font-size: 1.9rem;}
    button[data-baseweb="tab"] {font-size: 1rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt_int(value):
    return f"{value:,.0f}".replace(",", ".")


def fmt_num(value, decimals=1):
    return f"{value:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


@st.cache_data
def load_data():
    day_df = pd.read_csv(DATA_DIR / "main_data.csv", parse_dates=["dateday"])
    hour_df = pd.read_csv(DATA_DIR / "main_data_hour.csv", parse_dates=["dateday"])
    return day_df, hour_df


def create_hourly_pattern_df(hour_df):
    return hour_df.groupby(["hour", "day_type"])["count"].mean().unstack()


def create_season_df(day_df):
    season_df = day_df.groupby("season").agg(avg_rentals=("count", "mean"), days=("count", "count"))
    season_df["gap_pct"] = (season_df["avg_rentals"] / season_df["avg_rentals"].max() - 1) * 100
    return season_df.sort_values("avg_rentals", ascending=False)


def create_weather_df(day_df):
    weather_df = day_df.groupby("weather_cond").agg(avg_rentals=("count", "mean"), days=("count", "count"))
    if "Clear" in weather_df.index:
        weather_df["gap_pct"] = (weather_df["avg_rentals"] / weather_df.loc["Clear", "avg_rentals"] - 1) * 100
    else:
        weather_df["gap_pct"] = np.nan
    return weather_df.sort_values("avg_rentals", ascending=False)


def create_season_weather_df(day_df):
    pivot = day_df.groupby(["season", "weather_cond"])["count"].mean().unstack()
    return pivot.reindex(index=SEASON_ORDER, columns=WEATHER_ORDER)


def create_monthly_df(day_df):
    monthly_df = day_df.groupby(["month", "year"])["count"].sum().unstack()
    monthly_df["growth_pct"] = (monthly_df[2012] / monthly_df[2011] - 1) * 100
    monthly_df.index = MONTH_NAMES
    return monthly_df


def create_casual_share_df(day_df):
    by_day_type = day_df.groupby("day_type")[["casual", "count"]].sum()
    by_day_type["casual_pct"] = by_day_type["casual"] / by_day_type["count"] * 100

    by_season = day_df.groupby(["season", "day_type"])[["casual", "count"]].sum()
    by_season["casual_pct"] = by_season["casual"] / by_season["count"] * 100
    by_season = by_season["casual_pct"].unstack().reindex(SEASON_ORDER)
    return by_day_type, by_season


def create_temperature_group_df(day_df):
    labels = ["Cold (<10°C)", "Cool (10-20°C)", "Warm (20-30°C)", "Hot (30°C+)"]
    temperature_group = pd.cut(day_df["temperature"], bins=[0, 10, 20, 30, 40], labels=labels, right=False)
    return day_df.groupby(temperature_group, observed=True).agg(avg_rentals=("count", "mean"), days=("count", "count"))


def style_figure(fig, height=420, show_legend=True):
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=30, b=10),
        separators=",.",
        font=dict(size=13),
        showlegend=show_legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, title=None),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.35,
    )
    fig.update_xaxes(showgrid=False, linecolor=COLOR_MUTED)
    fig.update_yaxes(gridcolor="rgba(128, 128, 128, 0.2)", zeroline=False)
    return fig


def plot_hourly_pattern(hourly_pattern):
    fig = go.Figure()
    for day_type, color in DAY_TYPE_COLORS.items():
        if day_type not in hourly_pattern.columns:
            continue
        series = hourly_pattern[day_type]
        fig.add_trace(go.Scatter(
            x=series.index, y=series.values, mode="lines", name=day_type,
            line=dict(color=color, width=3),
            hovertemplate="Pukul %{x}:00<br>%{y:,.0f} sewa per jam<extra>" + day_type + "</extra>",
        ))
        peak_hour = series.idxmax()
        fig.add_trace(go.Scatter(
            x=[peak_hour], y=[series.max()], mode="markers+text",
            text=[f"{peak_hour}:00 | {fmt_int(series.max())}"], textposition="top center",
            marker=dict(color=color, size=11, line=dict(color="white", width=2)),
            showlegend=False, hoverinfo="skip",
        ))
    fig.update_xaxes(title="Jam", dtick=1)
    fig.update_yaxes(title="Rata-rata sewa per jam", range=[0, hourly_pattern.max().max() * 1.2])
    return style_figure(fig, height=440)


def plot_gap_bars(data, base_label, title):
    colors = [COLOR_MAIN] + [COLOR_MUTED] * (len(data) - 1)
    labels = []
    for i, row in enumerate(data.itertuples()):
        if i == 0:
            gap_text = base_label
        elif np.isnan(row.gap_pct):
            gap_text = "-"
        else:
            gap_text = f"{fmt_num(row.gap_pct)}%"
        labels.append(f"{fmt_int(row.avg_rentals)}<br>({gap_text})")
    fig = go.Figure(go.Bar(
        x=[f"{name}<br>(n={days} hari)" for name, days in zip(data.index, data["days"])],
        y=data["avg_rentals"], marker_color=colors, text=labels, textposition="outside",
        customdata=np.stack([data.index, data["gap_pct"].fillna(0)], axis=-1),
        hovertemplate="%{customdata[0]}<br>%{y:,.0f} sewa per hari<extra></extra>",
    ))
    fig.update_yaxes(title="Rata-rata sewa harian", range=[0, data["avg_rentals"].max() * 1.3])
    fig.update_layout(title=dict(text=title, x=0))
    return style_figure(fig, height=420, show_legend=False)


def plot_season_weather_heatmap(season_weather_df):
    text = [[fmt_int(value) if pd.notna(value) else "" for value in row] for row in season_weather_df.values]
    fig = go.Figure(go.Heatmap(
        z=season_weather_df.values, x=season_weather_df.columns, y=season_weather_df.index,
        colorscale="Blues", showscale=False, text=text, texttemplate="%{text}",
        xgap=3, ygap=3, hovertemplate="%{y} | %{x}<br>%{z:,.0f} sewa per hari<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    return style_figure(fig, height=340, show_legend=False)


def plot_monthly_total(monthly_df):
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly_df.index, y=monthly_df[2011], name="2011", marker_color=COLOR_MUTED,
                         hovertemplate="%{x} 2011<br>%{y:,.0f} sewa<extra></extra>"))
    fig.add_trace(go.Bar(x=monthly_df.index, y=monthly_df[2012], name="2012", marker_color=COLOR_MAIN,
                         hovertemplate="%{x} 2012<br>%{y:,.0f} sewa<extra></extra>"))
    fig.update_layout(barmode="group", title=dict(text="Total sewa per bulan", x=0))
    fig.update_yaxes(title="Total sewa")
    return style_figure(fig, height=420)


def plot_monthly_growth(monthly_df):
    growth = monthly_df["growth_pct"]
    colors = [COLOR_MAIN if value in (growth.max(), growth.min()) else COLOR_MUTED for value in growth]
    fig = go.Figure(go.Bar(
        x=growth.index, y=growth.values, marker_color=colors,
        text=[f"{fmt_num(value)}%" for value in growth], textposition="outside",
        hovertemplate="%{x}<br>Pertumbuhan %{y:.1f}%<extra></extra>",
    ))
    fig.update_yaxes(title="Pertumbuhan 2012 vs 2011 (%)", range=[0, growth.max() * 1.15])
    fig.update_layout(title=dict(text="Pertumbuhan per bulan (biru: tertinggi dan terendah)", x=0))
    return style_figure(fig, height=420, show_legend=False)


def plot_casual_by_day_type(by_day_type):
    shares = by_day_type["casual_pct"]
    fig = go.Figure(go.Bar(
        x=shares.index, y=shares.values, marker_color=[DAY_TYPE_COLORS[name] for name in shares.index],
        text=[f"{fmt_num(value)}%" for value in shares.values], textposition="outside",
        hovertemplate="%{x}<br>%{y:.1f}% pengguna casual<extra></extra>",
    ))
    fig.update_yaxes(title="Pengguna casual (% dari total sewa)", range=[0, 45])
    fig.update_layout(title=dict(text="Berdasarkan tipe hari", x=0))
    return style_figure(fig, height=420, show_legend=False)


def plot_casual_by_season(by_season):
    fig = go.Figure()
    for day_type in ["Workday", "Weekend/Holiday"]:
        if day_type not in by_season.columns:
            continue
        fig.add_trace(go.Bar(
            x=by_season.index, y=by_season[day_type], name=day_type, marker_color=DAY_TYPE_COLORS[day_type],
            text=[f"{fmt_num(value)}%" if pd.notna(value) else "" for value in by_season[day_type]],
            textposition="outside", hovertemplate="%{x} | " + day_type + "<br>%{y:.1f}% pengguna casual<extra></extra>",
        ))
    fig.update_layout(barmode="group", title=dict(text="Berdasarkan musim dan tipe hari", x=0))
    fig.update_yaxes(range=[0, 45])
    return style_figure(fig, height=420)


def plot_temperature_groups(temperature_df):
    colors = [COLOR_MAIN if value == temperature_df["avg_rentals"].max() else COLOR_MUTED
              for value in temperature_df["avg_rentals"]]
    fig = go.Figure(go.Bar(
        x=temperature_df.index.astype(str), y=temperature_df["avg_rentals"], marker_color=colors,
        text=[f"{fmt_int(row.avg_rentals)}<br>(n={row.days} hari)" for row in temperature_df.itertuples()],
        textposition="outside", hovertemplate="%{x}<br>%{y:,.0f} sewa per hari<extra></extra>",
    ))
    fig.update_yaxes(title="Rata-rata sewa harian", range=[0, temperature_df["avg_rentals"].max() * 1.3])
    return style_figure(fig, height=420, show_legend=False)


day_all_df, hour_all_df = load_data()

min_date = day_all_df["dateday"].min().date()
max_date = day_all_df["dateday"].max().date()

with st.sidebar:
    st.title("🚲 Bike Sharing")
    st.caption("Capital Bikeshare, Washington D.C.")
    date_range = st.date_input(
        label="Rentang tanggal",
        min_value=min_date,
        max_value=max_date,
        value=[min_date, max_date],
        help="Filter berlaku untuk ringkasan, jam puncak, musim dan cuaca, pengguna casual, dan suhu.",
    )
    st.divider()
    st.markdown("**Tentang data**")
    st.caption(
        "Penyewaan sepeda per jam dan per hari selama 2011-2012 beserta kondisi musim dan cuaca. "
        "Pertumbuhan bulanan selalu memakai seluruh data karena membandingkan bulan penuh di dua tahun."
    )

if len(date_range) != 2:
    st.info("Pilih tanggal awal dan tanggal akhir pada filter di sebelah kiri.")
    st.stop()

start_date, end_date = pd.Timestamp(date_range[0]), pd.Timestamp(date_range[1])
day_df = day_all_df[(day_all_df["dateday"] >= start_date) & (day_all_df["dateday"] <= end_date)]
hour_df = hour_all_df[(hour_all_df["dateday"] >= start_date) & (hour_all_df["dateday"] <= end_date)]

st.title("Dashboard Penyewaan Sepeda")
st.caption(f"Periode: {start_date:%d %b %Y} sampai {end_date:%d %b %Y}")

if day_df.empty:
    st.warning("Tidak ada data pada rentang tanggal yang dipilih.")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total penyewaan", fmt_int(day_df["count"].sum()))
col2.metric("Rata-rata per hari", fmt_int(day_df["count"].mean()))
col3.metric("Porsi pengguna casual", f"{fmt_num(day_df['casual'].sum() / day_df['count'].sum() * 100)}%")
col4.metric("Jumlah hari", fmt_int(len(day_df)))

st.write("")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "Jam Puncak", "Musim & Cuaca", "Pertumbuhan Bulanan", "Pengguna Casual", "Analisis Suhu", "Rekomendasi"
])

with tab1:
    st.subheader("Jam berapa penyewaan memuncak?")
    st.caption("Perbandingan rata-rata sewa per jam pada hari kerja (Workday) dan akhir pekan/libur (Weekend/Holiday).")
    hourly_pattern_df = create_hourly_pattern_df(hour_df)
    st.plotly_chart(plot_hourly_pattern(hourly_pattern_df))
    peak_sentences = [
        f"Pada **{day_type}**, penyewaan memuncak pukul **{hourly_pattern_df[day_type].idxmax()}:00** "
        f"dengan rata-rata **{fmt_int(hourly_pattern_df[day_type].max())}** sewa per jam."
        for day_type in hourly_pattern_df.columns
    ]
    st.info(" ".join(peak_sentences))
    with st.expander("Lihat tabel data"):
        st.dataframe(hourly_pattern_df.round(1).rename_axis("Jam"))

with tab2:
    st.subheader("Seberapa besar musim dan cuaca menurunkan penyewaan?")
    st.caption("Persentase di atas batang adalah selisih terhadap kondisi terbaik: musim dengan rata-rata tertinggi dan cuaca Clear.")
    season_df = create_season_df(day_df)
    weather_df = create_weather_df(day_df)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(plot_gap_bars(season_df, "terbaik", "Berdasarkan musim"))
    with right:
        st.plotly_chart(plot_gap_bars(weather_df, "acuan", "Berdasarkan kondisi cuaca"))

    st.markdown("**Kombinasi musim dan kondisi cuaca** (rata-rata sewa per hari)")
    season_weather_df = create_season_weather_df(day_df)
    st.plotly_chart(plot_season_weather_heatmap(season_weather_df))

    sentences = [
        f"Musim **{season_df.index[0]}** memiliki rata-rata sewa harian tertinggi ({fmt_int(season_df['avg_rentals'].iloc[0])})."
    ]
    if len(season_df) > 1:
        sentences.append(
            f"Musim **{season_df.index[-1]}** paling rendah ({fmt_int(season_df['avg_rentals'].iloc[-1])}), "
            f"turun {fmt_num(abs(season_df['gap_pct'].iloc[-1]))}% dari musim terbaik."
        )
    if "Light Rain/Snow" in weather_df.index and pd.notna(weather_df.loc["Light Rain/Snow", "gap_pct"]):
        sentences.append(
            f"Cuaca **Light Rain/Snow** menurunkan penyewaan {fmt_num(abs(weather_df.loc['Light Rain/Snow', 'gap_pct']))}% "
            f"dibandingkan cuaca Clear (hanya {weather_df.loc['Light Rain/Snow', 'days']} hari)."
        )
    st.info(" ".join(sentences))
    with st.expander("Lihat tabel data"):
        st.dataframe(season_df.round(1).rename(columns={"avg_rentals": "Rata-rata sewa", "days": "Jumlah hari", "gap_pct": "Selisih (%)"}))
        st.dataframe(weather_df.round(1).rename(columns={"avg_rentals": "Rata-rata sewa", "days": "Jumlah hari", "gap_pct": "Selisih (%)"}))

with tab3:
    st.subheader("Berapa pertumbuhan penyewaan 2012 dibanding 2011?")
    st.caption("Bagian ini selalu memakai seluruh data 2011-2012, tidak terpengaruh filter tanggal.")
    monthly_df = create_monthly_df(day_all_df)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(plot_monthly_total(monthly_df))
    with right:
        st.plotly_chart(plot_monthly_growth(monthly_df))
    top_month = monthly_df["growth_pct"].idxmax()
    low_month = monthly_df["growth_pct"].idxmin()
    st.info(
        f"Semua bulan pada 2012 lebih tinggi daripada bulan yang sama pada 2011. Pertumbuhan tertinggi pada **{top_month}** "
        f"({fmt_num(monthly_df.loc[top_month, 'growth_pct'])}%) dan terendah pada **{low_month}** "
        f"({fmt_num(monthly_df.loc[low_month, 'growth_pct'])}%). Bulan awal tahun tumbuh paling besar karena basis 2011 masih rendah."
    )
    with st.expander("Lihat tabel data"):
        st.dataframe(monthly_df.round(1).rename(columns={2011: "2011", 2012: "2012", "growth_pct": "Pertumbuhan (%)"}))

with tab4:
    st.subheader("Berapa persen pengguna casual?")
    st.caption("Porsi pengguna casual terhadap total penyewaan, berdasarkan tipe hari dan musim.")
    by_day_type_df, by_season_df = create_casual_share_df(day_df)
    left, right = st.columns(2)
    with left:
        st.plotly_chart(plot_casual_by_day_type(by_day_type_df))
    with right:
        st.plotly_chart(plot_casual_by_season(by_season_df))
    if {"Workday", "Weekend/Holiday"}.issubset(by_day_type_df.index):
        st.info(
            f"Pengguna casual menyumbang **{fmt_num(by_day_type_df.loc['Weekend/Holiday', 'casual_pct'])}%** sewa pada "
            f"Weekend/Holiday, jauh di atas Workday yang hanya **{fmt_num(by_day_type_df.loc['Workday', 'casual_pct'])}%**."
        )
    with st.expander("Lihat tabel data"):
        st.dataframe(by_day_type_df.round(1).rename(columns={"casual": "Casual", "count": "Total sewa", "casual_pct": "Casual (%)"}))
        st.dataframe(by_season_df.round(1))

with tab5:
    st.subheader("Bagaimana pengaruh suhu terhadap penyewaan?")
    st.caption("Analisis lanjutan: suhu harian dikelompokkan secara manual (binning) ke dalam empat kategori.")
    temperature_df = create_temperature_group_df(day_df)
    if temperature_df.empty:
        st.info("Tidak ada data suhu pada rentang tanggal yang dipilih.")
    else:
        st.plotly_chart(plot_temperature_groups(temperature_df))
        best_group = temperature_df["avg_rentals"].idxmax()
        st.info(
            f"Rata-rata sewa harian tertinggi ada pada kelompok **{best_group}** "
            f"({fmt_int(temperature_df.loc[best_group, 'avg_rentals'])} sewa per hari)."
        )
        with st.expander("Lihat tabel data"):
            st.dataframe(temperature_df.round(0).rename(columns={"avg_rentals": "Rata-rata sewa", "days": "Jumlah hari"}))

with tab6:
    st.subheader("Rekomendasi")
    st.caption("Berdasarkan analisis seluruh data 2011-2012.")
    st.markdown(
        """
        1. **Redistribusi sepeda.** Pada hari kerja, pindahkan sepeda sebelum pukul 08.00 dan sebelum pukul 17.00 ke stasiun dekat kawasan kantor dan transit. Pada akhir pekan/libur, fokuskan stok ke stasiun wisata dan taman menjelang pukul 11.00.
        2. **Perawatan armada.** Jadwalkan perawatan pada musim Spring dan saat cuaca buruk ketika permintaan paling rendah, dan pastikan armada penuh pada musim Fall dan Summer.
        3. **Target bulanan.** Gunakan bulan awal tahun (Januari sampai Maret) untuk target pertumbuhan yang lebih agresif, dan gunakan Juni sampai September sebagai acuan kapasitas armada.
        4. **Konversi pengguna casual.** Arahkan promosi keanggotaan pada akhir pekan/libur di musim Summer dan Fall, terutama pukul 11.00 sampai 16.00.
        """
    )

st.divider()
st.caption("Sumber data: Bike Sharing Dataset (Fanaee-T & Gama, 2013)")
