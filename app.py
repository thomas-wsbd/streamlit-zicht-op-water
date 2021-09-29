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
auth = firebaseauth()
login = st.sidebar.expander("Inloggen", False)

# authentication
emailvalue = ""
passwordvalue = ""
email = login.text_input("E-mailadres")
password = login.text_input("Wachtwoord", type="password")
if login.button("Inloggen"):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        login.success("Je bent ingelogd")
        st.session_state.login = True
    except:
        login.warning("Verkeerd e-mailadres of wachtwoord")

# if logged in #
if st.session_state.login:
    login.expanded = False
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
    uitleg = st.sidebar.expander("Uitleg", expanded=True)
    uitleg.markdown(
        "Bij een periode **kleiner dan twee weken** wordt de onttrokken hoeveelheid **per uur** gerapporteerd in m3/uur. Bij een periode **groter dan twee weken** wordt de onttrokken hoeveelheid **per dag** gerapporteerd in m3/dag."
    )

    # plot
    if loc:
        df = returndf(imeilist=loc, datefrom=start, dateto=end)
        if end - start > datetime.timedelta(days=14):
            df = (
                df.groupby("imei")
                .resample("d")
                .sum()
                .reset_index()
                .set_index("LogDate")
            )
            fig = px.bar(
                df,
                color="imei",
                title=f"Gemeten onttrokken hoeveelheden in m3/dag; {imeitoname().get(loc[0])}",
            ).update_layout(
                height=600,
                yaxis_title="gemeten ontrokken hoeveelheid (m3/dag)",
                xaxis_title=None,
            )
            if cumsum:
                fig.add_trace(px.line(df.set_index([df.index, "imei"]).unstack().cumsum().stack().reset_index().set_index("LogDate"), color="imei")["data"][0])
            st.plotly_chart(
                fig,
                use_container_width=True,
            )
        else:
            fig = px.bar(
                df,
                color="imei",
                title=f"Gemeten onttrokken hoeveelheden in m3/uur; {imeitoname().get(loc[0])}",
            ).update_layout(
                height=600,
                yaxis_title="gemeten ontrokken hoeveelheid (m3/uur)",
                xaxis_title=None,
            )
            if cumsum:
                fig.add_trace(px.line(df.set_index([df.index, "imei"]).unstack().cumsum().stack().reset_index().set_index("LogDate"), color="imei")["data"][0])
            st.plotly_chart(
                fig,
                use_container_width=True,
            )
        if showdf:
            st.table(df.pivot_table(values="Value", index=df.index, columns="imei"))
