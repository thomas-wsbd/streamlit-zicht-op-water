import streamlit as st
import pandas as pd

import datetime

from numerize.numerize import numerize
from helpers import *
from azure.storage.blob import ContainerClient
from io import BytesIO

idx = pd.IndexSlice

# set session state
if "login" not in st.session_state:
    st.session_state.login = False
if "loginexpanded" not in st.session_state:
    st.session_state.loginexpanded = True

# page config
st.set_page_config(
    page_title="Zicht op Water - App",
    page_icon=":droplet:",
    layout="wide",
    initial_sidebar_state="expanded",
)

url = st.secrets["URL_AZURE"]


# get data from azure blob storage
@st.cache_data(ttl=60 * 60 * 6)
def load_parquet(url):
    data = pd.read_parquet(url)
    total_sum = data.query("var == 'ontdebiet'")["value"].sum()
    diff_sum = (
        total_sum
        - data.query("var == 'ontdebiet'")
        .loc[idx[: datetime.date.today() - datetime.timedelta(days=1), :], "value"]
        .sum()
    )
    return data, numerize(total_sum), numerize(diff_sum)


data, total_sum, diff_sum = load_parquet(url)
st.sidebar.title("Zicht op Water")
# login
login = st.sidebar.expander("Inloggen", expanded=st.session_state.loginexpanded)

# authentication
email = login.text_input("E-mailadres")
passwd = login.text_input("Wachtwoord", type="password")
if login.button("Inloggen"):
    login_bool = user_login(email, passwd)
    if login_bool:
        login.success("Je bent ingelogd")
        st.session_state.login = True
        st.session_state.loginexpanded = False
    else:
        login.warning("Verkeerd e-mailadres of wachtwoord")

meta = return_meta()
if email == "zichtopwater@zichtopwater.nl":
    locs = sorted(meta.Naam.tolist())
else:
    locs = sorted(meta.loc[meta.Mailadres == email, "Naam"].tolist())

# if logged in
if st.session_state.login:
    # metrics
    metrics = st.sidebar.expander("Metrics", expanded=True)
    metrics.metric(
        label="Totaal gemeten onttrekking Zicht op Water",
        value=f"{total_sum} m³",
        delta=f"{diff_sum} m³ tov gisteren",
    )

    # controls
    controls = st.sidebar.expander("Filters", expanded=True)
    loc = controls.multiselect(
        "Locatie", options=locs, default=[locs[0]], format_func=label_names
    )
    start = controls.date_input(
        "Start datum", value=(datetime.date.today() - datetime.timedelta(days=3))
    )
    end = controls.date_input("Eind datum")

    extra = st.sidebar.expander("Extra", expanded=False)
    cumsum = extra.checkbox("Cumulatief toevoegen")
    show_df = extra.checkbox("Laat tabel zien")
    if email == "zichtopwater@zichtopwater.nl":
        status_rapport = extra.checkbox("Statusrapport 🚦")
    # uitleg
    uitleg = st.sidebar.expander("Uitleg", expanded=False)
    uitleg.markdown(
        """
        Debietmeters  
        Bij een periode **kleiner dan twee weken** wordt de variabele **per uur** gerapporteerd. Bij een periode **groter dan twee weken** wordt de variabele **per dag** gerapporteerd.  
        
        Meetstations  
        Meetstations bevatten verschillen parameters; luchtvochtigheid (%), luchttemperatuur (°C), bodemvocht ondiep (%), bodemvocht diep (%), bodemtemperatuur ondiep (°C), bodemtemperatuur diep (°C) en de neerslagsom (mm).
        """
    )

    if email == "zichtopwater@zichtopwater.nl":
        # download
        download = st.sidebar.expander("Download", expanded=False)
        download.download_button(
            "Download alles",
            data.to_csv().encode("utf-8"),
            "zichtopwater-metingen-alles.csv",
            "text/csv",
            key="download-all-csv",
        )

    # plot
    if loc:
        try:
            df = data.loc[idx[start:end, loc, :], :].reset_index(
                level=["locatie", "var"]
            )
            vars = list(df["var"].unique())
        except:
            df = pd.DataFrame()

        try:
            # metrics
            sel_total_sum = df.query("var == 'ontdebiet'")["value"].sum()
            sel_diff_sum = (
                df.query("var == 'ontdebiet'")
                .loc[
                    (datetime.datetime.today() - datetime.timedelta(days=1)) :, "value"
                ]
                .sum()
            )
            metrics.metric(
                label="Totaal onttrekkingen in selectie/periode",
                value=f"{numerize(sel_total_sum)} m³",
                delta=f"{numerize(sel_diff_sum)} m³ tov gisteren",
            )
        except:
            print("geen metrics")

        sidebar_map = st.sidebar.expander("Kaart", expanded=True)
        sidebar_map.plotly_chart(
            pxmap(loc),
            use_container_width=True,
        )

        if df.empty:
            st.warning(
                "Geen data voor geselecteerde periode en/of locatie, selecteer een andere periode en/of locatie"
            )
        else:
            filter_list = ["ontdebiet", "precp"]
            if end - start > datetime.timedelta(days=14):
                if any(map(lambda x: x in filter_list, vars)):
                    df_sum = (
                        df.query("var in @filter_list")
                        .groupby(["locatie", "var"])
                        .resample("d")["value"]
                        .sum()
                        .reset_index()
                        .set_index("dt")
                    )
                else:
                    df_sum = pd.DataFrame()

                if any(
                    map(
                        lambda x: x
                        in [
                            "humext",
                            "soilmoist1",
                            "soilmoist2",
                            "soiltemp1",
                            "soiltemp2",
                            "tempext",
                        ],
                        vars,
                    )
                ):
                    df_mean = (
                        df.query("var not in @filter_list")
                        .groupby(["locatie", "var"])
                        .resample("d")["value"]
                        .mean()
                        .reset_index()
                        .set_index("dt")
                    )
                else:
                    df_mean = pd.DataFrame()

                df = pd.concat(
                    [df_sum, df_mean],
                    axis="index",
                )
                fig = pxbar(df, loc)
                if cumsum:
                    line = pxcumsum(df)
                    for i in range(len(line["data"])):
                        fig.add_trace(line["data"][i])
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )
                if show_df:
                    st.download_button(
                        "CSV Selectie",
                        df.to_csv().encode("utf-8"),
                        "zichtopwater-metingen.csv",
                        "text/csv",
                        key="download-csv",
                    )
                    st.table(df)
            else:
                fig = pxbar(df, loc)
                if cumsum:
                    line = pxcumsum(df)
                    for i in range(len(line["data"])):
                        fig.add_trace(line["data"][i])
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )
                if show_df:
                    st.table(df)
                    st.download_button(
                        "CSV Selectie",
                        df.to_csv().encode("utf-8"),
                        "zichtopwater-metingen.csv",
                        "text/csv",
                        key="download-select-csv",
                    )
    if status_rapport:
        last3 = datetime.date.today() - datetime.timedelta(days=3)
        df_status = (
            data.query('var == "ontdebiet"')
            .reset_index("dt")
            .groupby(["locatie"])
            .last()
            .join(
                data.query(
                    'var == "ontdebiet" and dt > @last3 and value > 0 and value < 1'
                )
                .reset_index("var")["value"]
                .groupby(["locatie"])
                .agg(aantal_flags="count"),
            )
            .fillna(0)
            .astype({"aantal_flags": "int"})
            .sort_values(by="aantal_flags", ascending=False)
            .drop(columns=["latlon"])
        )

        st.write(
            df_status.style.bar(subset=["aantal_flags"]).to_html(escape=False),
            unsafe_allow_html=True,
        )
