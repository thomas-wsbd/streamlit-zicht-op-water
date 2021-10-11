import requests, pyrebase
import pandas as pd
import streamlit as st
import plotly.express as px

# metadata
url_docs = "https://docs.google.com/spreadsheets/d/1NJZKBFoDwH_iiS3kBj-lxRW0K6396VDI0Um43vQVfEM/export?format=csv"
meta = pd.read_csv(url_docs, decimal=",")
meta.imei = meta.imei.astype(str)

def returnmeta():
    return meta

def firebaseauth():
    # firebase config
    firebaseConfig = {
        "apiKey": st.secrets["apikeyfirebase"],
        "authDomain": "users-passwords-streamlit.firebaseapp.com",
        "projectId": "users-passwords-streamlit",
        "databaseURL": "https://users-passwords-streamlit-default-rtdb.europe-west1.firebasedatabase.app/",
        "storageBucket": "users-passwords-streamlit.appspot.com",
        "messagingSenderId": "631896730641",
        "appId": "1:631896730641:web:bb90c25404c7e1ecb555b0",
    }

    # initialize auth
    firebase = pyrebase.initialize_app(firebaseConfig)
    return firebase.auth()


def gettoken():
    url = "https://api.mymobeye.com/Token"
    params = {
        "grant_type": "password",
        "username": st.secrets["username"],
        "password": st.secrets["password"],
    }
    r = requests.post(
        url, data=params, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    return r.json()["access_token"]


def getallimei(access_token=gettoken()):
    url = "https://api.mymobeye.com/api/logdata"
    header = {"Authorization": f"Bearer {access_token}"}

    params = {
        "ApiKey": st.secrets["apikey"],
        "UserName": st.secrets["email"],
        "DateFrom": (pd.Timestamp.today() - pd.Timedelta(days=1)).strftime(
            "%Y-%m-%dT00:00:00"
        ),
        "DateTo": (pd.Timestamp.today()).strftime("%Y-%m-%dT00:00:00"),
        "ImeiList": "ALL",
    }

    r = requests.get(url, data=params, headers=header)
    return pd.DataFrame(r.json())["Imei"].to_list()


def imeitoname():
    return dict(zip(meta.imei, meta.naam))

def getname(imei):
    return imeitoname().get(imei)

def returndf(datefrom, dateto, access_token=gettoken(), imeilist="ALL"):
    url = "https://api.mymobeye.com/api/logdata"
    header = {"Authorization": f"Bearer {access_token}"}
    params = {
        "ApiKey": st.secrets["apikey"],
        "UserName": st.secrets["email"],
        "DateFrom": datefrom.strftime("%Y-%m-%dT00:00:00"),
        "DateTo": dateto.strftime("%Y-%m-%dT00:00:00"),
        "ImeiList": imeilist,
    }

    r = requests.get(url, data=params, headers=header)
    df = pd.DataFrame(r.json())
    df = pd.DataFrame(
        [
            {**val, **{"imei": imei}}
            for val, imei in zip(
                df.explode("Values")["Values"], df.explode("Values")["Imei"]
            )
        ]
    )
    df.LogDate = pd.to_datetime(df.LogDate).dt.round("1H")
    df.set_index("LogDate", inplace=True)
    df.Value = pd.to_numeric(
        [value.strip(";-").replace(",", ".") for value in df.Value.astype(str)],
        errors="coerce",
    )
    df.Value = df.Value / 1000  # l/uur => m3/uur

    return df


def pxmap(loc):
    m = meta[meta.imei.isin(loc)]
    print(m)
    px.set_mapbox_access_token(st.secrets["mapboxtoken"])
    return (
        px.scatter_mapbox(
            m,
            lat="lat",
            lon="lon",
            hover_name="naam",
            text="naam",
            mapbox_style="light",
            hover_data=[
                "imei",
                "locatie",
                "vergunning",
                "vermogen",
                "bron",
                "diepte",
                "teelt",
                "beregeningsmethode",
            ],
            zoom=12,
        )
        .update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=300)
        .update_traces(marker=dict(size=15, symbol="drinking-water", allowoverlap=True))
    )


def pxbardaily(df, loc):
    return px.bar(
        df,
        color="imei",
        title=f"Gemeten onttrokken hoeveelheden in m3/dag; {', '.join([getname(l) for l in loc])}",
    ).update_layout(
        height=600,
        yaxis_title="gemeten ontrokken hoeveelheid (m3/dag)",
        xaxis_title=None,
    )


def pxbarhourly(df, loc):
    return px.bar(
        df,
        color="imei",
        title=f"Gemeten onttrokken hoeveelheden in m3/uur; {', '.join([getname(l) for l in loc])}",
    ).update_layout(
        height=600,
        yaxis_title="gemeten ontrokken hoeveelheid (m3/uur)",
        xaxis_title=None,
    )


def pxcumsum(df):
    return px.line(
        df.set_index([df.index, "imei"])
        .unstack()
        .cumsum()
        .stack()
        .reset_index()
        .set_index("LogDate"),
        color="imei",
    )
