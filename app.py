import streamlit as st
import plotly.express as px

import datetime

from helpers import *

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

# if logged in
if st.session_state.login:
    st.title("Zicht op Water")

    # controls
    locs = getallimei()
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
        sidebarmap = st.sidebar.expander("Kaart", expanded=True)
        sidebarmap.plotly_chart(
            pxmap(loc),
            use_container_width=True,
        )
        df = returndf(imeilist=loc, datefrom=start, dateto=end)
        if end - start > datetime.timedelta(days=14):
            df = (
                df.groupby("imei")
                .resample("d")
                .sum()
                .reset_index()
                .set_index("LogDate")
            )
            fig = pxbardaily(df, loc)
            if cumsum:
                line = pxcumsum(df)
                for i in range(len(line["data"])):
                    fig.add_trace(line["data"][i])
            st.plotly_chart(
                fig,
                use_container_width=True,
            )
            if showdf:
                st.table(df.pivot_table(values="Value", index=df.index, columns="imei"))
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
                st.table(df.pivot_table(values="Value", index=df.index, columns="imei"))
