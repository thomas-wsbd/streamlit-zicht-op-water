import requests, pyrebase
import pandas as pd
import streamlit as st



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
    return {"358005099371707": "Frank - Eldert 001",
            "358005099376755": "Gerard - Eldert 002"}


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
    df.LogDate = pd.to_datetime(df.LogDate)
    df.set_index("LogDate", inplace=True)
    df.Value = pd.to_numeric(
        [value.strip(";-").replace(",", ".") for value in df.Value.astype(str)],
        errors="coerce",
    )
    df.Value = df.Value / 1000 # l/uur => m3/uur

    return df
