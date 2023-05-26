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

conn_str = st.secrets["AZURE_CONNECTION_STRING"]


# get data from azure blob storage
@st.cache(ttl=60 * 60 * 6)
def load_parquet(conn_str):
    container = ContainerClient.from_connection_string(
        conn_str=conn_str, container_name="zichtopwaterdb"
    )
    client = container.get_blob_client(blob="zichtopwaterdb.parquet")
    bytes = BytesIO(client.download_blob().readall())
    data = pd.read_parquet(bytes)
    total_sum = data.query("var == 'ontdebiet'")["value"].sum()
    diff_sum = (
        total_sum
        - data.query("var == 'ontdebiet'")
        .loc[idx[: datetime.date.today() - datetime.timedelta(days=1), :], "value"]
        .sum()
    )
    return data, numerize(total_sum), numerize(diff_sum)


data, total_sum, diff_sum = load_parquet(conn_str)

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
    st.title("Zicht op Water")

    # metrics
    metrics = st.sidebar.expander("Metrics", expanded=True)
    metrics.metric(
        label="Totaal gemeten onttrekking Zicht op Water",
        value=f"{total_sum} m³",
        delta=f"{diff_sum} m³ tov gisteren",
    )
    sel_total_sum = 0
    sel_diff_sum = 0
    metrics.metric(
        label="Totaal geselecteerde onttrekkingen",
        value=f"{sel_total_sum} m³",
        delta=f"{sel_diff_sum} m³",
    )

    # controls
    controls = st.sidebar.expander("Filters", expanded=True)
    loc = controls.multiselect(
        "Locatie", options=locs, default=[locs[0]], format_func=label_names
    )
    start = controls.date_input(
        "Start datum", value=(datetime.date.today() - datetime.timedelta(days=5))
    )
    end = controls.date_input("Eind datum")

    extra = st.sidebar.expander("Extra", expanded=False)
    cumsum = extra.checkbox("Cumulatief toevoegen")
    show_df = extra.checkbox("Laat tabel zien")

    # uitleg
    uitleg = st.sidebar.expander("Uitleg", expanded=False)
    uitleg.markdown(
        """
        Bij een periode **kleiner dan twee weken** wordt de variabele **per uur** gerapporteerd. Bij een periode **groter dan twee weken** wordt de variabele **per dag** gerapporteerd.  
        
        Er zitten verschillende variabele in dit dashboard; 
        - ontdebiet = som van onttrokken hoeveelheid (m3)  
        - humext = luchtvochtigheid (%)  
        - tempext = luchttemperatuur (°C)  
        - soilmoist1 = bodemvocht ondiep (%)  
        - soilmoist2 = bodemvocht diep (%)  
        - soiltemp1 = bodemtemperatuur ondiep (°C)  
        - soiltemp2 = bodemtemperatuur diep (°C)  
        - precp = neerslagsom (mm)
        """
    )

    # download
    download = st.sidebar.expander("Download", expanded=False)

    if email == "zichtopwater@zichtopwater.nl":
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
            df = data.loc[idx[start:end, loc], :]
            variables = df.index.get_level_values("var").unique()
            var = controls.multiselect(
                "Variabele", options=variables, default=variables[0]
            )
            df = data.loc[idx[start:end, loc, var], :].reset_index(
                level=["locatie", "var"]
            )
        except:
            df = pd.DataFrame()

        # metrics
        sel_total_sum = numerize(df.query("var == 'ontdebiet'")["value"].sum())
        sel_diff_sum = numerize(
            sel_total_sum
            - df.query("var == 'ontdebiet'")
            .loc[datetime.date.today() - datetime.timedelta(days=1), "value"]
            .sum()
        )

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
            if end - start > datetime.timedelta(days=14):
                if any(map(lambda x: x in ["ontdebiet", "precp"], var)):
                    df_sum = (
                        df.loc[
                            df["var"].isin(["ontdebiet", "precp"]),
                        ]
                        .groupby(["locatie", "var"])
                        .resample("d")
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
                        var,
                    )
                ):
                    df_mean = (
                        df.loc[~df["var"].isin(["ontdebiet", "precp"])]
                        .groupby(["locatie", "var"])
                        .resample("d")
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
