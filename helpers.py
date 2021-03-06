import requests, datetime
import pandas as pd
import streamlit as st
import plotly.express as px

# metadata
meta = pd.read_csv(st.secrets["URL_DOCS"], decimal=",")
meta["IMEI"] = meta.IMEI.astype(str).str.strip(".0")
meta["lat"], meta["lon"] = meta["lat"].astype(float), meta["lon"].astype(float)
meta["label"] = meta.apply(lambda x: f"{x.Naam} - {x.Locatie}" if (str(x.Locatie) != "nan") else x.Naam, axis=1)

def user_login(email, passwd):
    url = "%s?key=%s" % ("https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword", st.secrets["apikeyfirebase"])
    data = {"email": email,
            "password": passwd,
            "returnSecureToken": True}
    result = requests.post(url, json=data)
    return result.ok

def returnmeta():
    return meta

def imeitoname():
    return dict(zip(meta.IMEI, meta.Naam))

def getname(imei):
    return imeitoname().get(imei)

def labelnames(name):
    return meta.set_index("Naam")["label"].to_dict().get(name)

def format_datetime(dt):
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def getserie(imei: int, dv: datetime.datetime, dt: datetime.datetime) -> pd.DataFrame:
    API_KEY = st.secrets["API_KEY"]
    BASE_URL = "https://gps.monitech.nl/api/api.php?"

    json = {
    "api": "user",
    "key": API_KEY,
    "cmd": f"OBJECT_GET_MESSAGES,{imei},{format_datetime(dv)},{format_datetime(dt)}"
    }
    r = requests.get(BASE_URL, params=json)
    df = pd.DataFrame(r.json(), columns=["dt", "lat", "lon", 3, 4, 5, "data"])
    df["dt"] = pd.to_datetime(df["dt"])
    df.set_index("dt", inplace=True)
    df["value"] = pd.to_numeric(df["data"].apply(lambda x: x.get("io5"))) / 10 # 1 pulse => 100 l => 0.1 m3
    df["locatie"] = getname(imei)
    df["latlon"] = list(zip(pd.to_numeric(df["lat"]), pd.to_numeric(df["lon"])))
    df["latlon"] = df["latlon"].astype(str)
    return df[["locatie", "value", "latlon"]]

def returndf(imeilist, dv, dt):
    listdf = []
    for imei in imeilist:
        try:
            listdf.append(getserie(imei, dv, dt))
        except:
            continue
    df = pd.concat(listdf).set_index("locatie", append=True)
    df = df.groupby([pd.Grouper(level="locatie"), pd.Grouper(level="dt", freq="1H")]).agg({"value": "sum", "latlon": "first"})
    return df.reset_index(level=0)
    
def pxmap(loc):
    m = meta[meta.Naam.isin(loc)]
    px.set_mapbox_access_token(st.secrets["mapboxtoken"])
    return (
        px.scatter_mapbox(
            m,
            lat="lat",
            lon="lon",
            hover_name="Naam",
            text="Naam",
            mapbox_style="light",
            hover_data=[
                "IMEI",
                "Klant",
                "Locatie",
            ],
            zoom=12,
            color_discrete_sequence=["DarkSlateGrey"]
        )
        .update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=300)
        .update_traces(marker=dict(size=15, symbol="drinking-water", allowoverlap=True))
    )


def pxbardaily(df, loc):
    return px.bar(
        df,
        y="value",
        color="locatie",
        title=f"Gemeten onttrokken hoeveelheden in m3; {', '.join(loc)}",
    ).update_layout(
        height=600,
        yaxis_title="gemeten ontrokken hoeveelheid (m3)",
        xaxis_title=None,
    )


def pxbarhourly(df, loc):
    return px.bar(
        df,
        y="value",
        color="locatie",
        title=f"Gemeten onttrokken hoeveelheden in m3; {', '.join(loc)}",
    ).update_layout(
        height=600,
        yaxis_title="gemeten ontrokken hoeveelheid (m3)",
        xaxis_title=None,
    )


def pxcumsum(df):
    return px.line(
        df.set_index([df.index, "locatie"])[["value"]]
        .unstack()
        .cumsum()
        .stack()
        .reset_index()
        .set_index("dt"),
        y="value",
        color="locatie",
    )
