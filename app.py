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
    showdf = controls.checkbox("Laat tabel zien")

    # plot
    print(loc)
    if loc:
        df = returndf(imeilist=loc, datefrom=start, dateto=end)
        if end - start > 10:
            df = df.resample('d').mean()
        st.plotly_chart(
            px.bar(
                df, color="imei", title=f"Gemeten onttrokken hoeveelheden in m3/uur; {imeitoname().get(loc[0])}"
            ).update_layout(
                height=600,
                yaxis_title="gemeten ontrokken hoeveelheid (m3/uur)",
                xaxis_title=None,
            ),
            use_container_width=True,
        )
    if showdf:
        st.table(df.pivot_table(values="Value", index=df.index, columns="imei"))
