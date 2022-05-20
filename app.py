import streamlit as st
import pandas as pd

import datetime

from helpers import *
from azure.storage.blob import ContainerClient
from io import BytesIO

idx = pd.IndexSlice

# set session state
if "login" not in st.session_state:
    st.session_state.login = False

# page config
st.set_page_config(
    page_title="Zicht op Water - App",
    page_icon=":droplet:",
    layout="wide",
    initial_sidebar_state="expanded",
)

conn_str = st.secrets["AZURE_CONNECTION_STRING"]
# get data from azure blob storage
@st.cache(ttl=60*60*6)
def load_parquet(conn_str):
    container = ContainerClient.from_connection_string(conn_str=conn_str, container_name="zichtopwaterdb")
    client = container.get_blob_client(blob="zichtopwaterdb.parquet")
    bytes = BytesIO(client.download_blob().readall())
    data = pd.read_parquet(bytes)
    return data
data = load_parquet(conn_str)

# login
login = st.sidebar.expander("Inloggen", expanded=True)

# authentication
email = login.text_input("E-mailadres")
passwd = login.text_input("Wachtwoord", type="password")
if login.button("Inloggen"):
    loginbool = user_login(email, passwd)
    if loginbool:
        login.success("Je bent ingelogd")
        st.session_state.login = True
        login.expanded = False
    else:
        login.warning("Verkeerd e-mailadres of wachtwoord")

meta = returnmeta()
if email == "zichtopwater@zichtopwater.nl":
    locs = meta.Naam.tolist()
else:
    locs = meta.loc[meta.Mailadres == email, "Naam"].tolist()

# if logged in
if st.session_state.login:
    st.title("Zicht op Water")

    # controls
    controls = st.sidebar.expander("Filters", expanded=True)
    loc = controls.multiselect("Locatie", options=locs, default=[locs[0]])
    start = controls.date_input(
        "Start datum", value=(datetime.date.today() - datetime.timedelta(days=5))
    )
    end = controls.date_input("Eind datum")
    cumsum = controls.checkbox("Cumulatief toevoegen")
    showdf = controls.checkbox("Laat tabel zien")

    # uitleg
    uitleg = st.sidebar.expander("Uitleg", expanded=False)
    uitleg.markdown(
        "Bij een periode **kleiner dan twee weken** wordt de onttrokken hoeveelheid **per uur** gerapporteerd in m3/uur. Bij een periode **groter dan twee weken** wordt de onttrokken hoeveelheid **per dag** gerapporteerd in m3/dag."
    )

    # plot
    if loc:
        print(loc)
        df = data.loc[idx[start:end, loc], :].reset_index(level=1)

        sidebarmap = st.sidebar.expander("Kaart", expanded=True)
        sidebarmap.plotly_chart(
            pxmap(loc),
            use_container_width=True,
        )

        if df.empty:
            st.warning("Geen data voor geselecteerde periode en/of locatie, selecteer een andere periode en/of locatie")
        else:
            if end - start > datetime.timedelta(days=14):
                df = (
                    df.groupby("locatie")
                    .resample("d")
                    .sum()
                    .reset_index()
                    .set_index("dt")
                )
                fig = pxbardaily(df, y=loc)
                if cumsum:
                    line = pxcumsum(df)
                    for i in range(len(line["data"])):
                        fig.add_trace(line["data"][i])
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )
                if showdf:
                    st.download_button(
                        "CSV Downloaden",
                        df.to_csv().encode("utf-8"),
                        "zichtopwater-metingen.csv",
                        "text/csv",
                        key="download-csv"
                    )
                    st.table(df)
            else:
                fig = pxbarhourly(df, loc)
                if cumsum:
                    line = pxcumsum(df)
                    for i in range(len(line["data"])):
                        fig.add_trace(line["data"][i])
                st.plotly_chart(
                    fig,
                    use_container_width=True,
                )
                if showdf:
                    st.table(df)
                    st.download_button(
                        "CSV Downloaden",
                        df.to_csv().encode("utf-8"),
                        "zichtopwater-metingen.csv",
                        "text/csv",
                        key="download-csv"
                    )
