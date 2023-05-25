import requests, datetime
import pandas as pd
import streamlit as st
import plotly.express as px

# metadata
meta = pd.read_csv(st.secrets["URL_DOCS"], decimal=",")
meta["IMEI"] = meta.IMEI.astype(str).str.strip(".0")
meta["lat"], meta["lon"] = meta["lat"].astype(float), meta["lon"].astype(float)
meta["label"] = meta.apply(
    lambda x: f"{x.Naam} - {x.Locatie}" if (str(x.Locatie) != "nan") else x.Naam, axis=1
)


def user_login(email: str, passwd: str) -> bool:
    url = "%s?key=%s" % (
        "https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword",
        st.secrets["apikeyfirebase"],
    )
    data = {"email": email, "password": passwd, "returnSecureToken": True}
    result = requests.post(url, json=data)
    return result.ok


def returnmeta() -> pd.DataFrame:
    return meta


def imeitoname() -> dict:
    return dict(zip(meta.IMEI, meta.Naam))


def getname(imei: int) -> str:
    return imeitoname().get(imei)


def labelnames(name: str) -> str:
    return meta.set_index("Naam")["label"].to_dict().get(name)


def format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def pxmap(loc: str):
    m = meta.query("Naam in @loc")
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
            color_discrete_sequence=["DarkSlateGrey"],
        )
        .update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0}, height=300)
        .update_traces(marker=dict(size=15, symbol="drinking-water", allowoverlap=True))
    )


def pxbardaily(df: pd.DataFrame, loc: str):
    return px.bar(
        df,
        y="value",
        color="locatie",
        facet_row="var",
        title=f"Gemeten onttrokken hoeveelheden in m3; {', '.join(loc)}",
    ).update_layout(
        height=1200,
        yaxis_title="gemeten ontrokken hoeveelheid (m3)",
        xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


def pxbarhourly(df: pd.DataFrame, loc: str):
    return px.bar(
        df,
        y="value",
        color="locatie",
        facet_row="var",
        title=f"Gemeten onttrokken hoeveelheden in m3; {', '.join(loc)}",
    ).update_layout(
        height=1200,
        yaxis_title="gemeten ontrokken hoeveelheid (m3)",
        xaxis_title=None,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )


def pxcumsum(df: pd.DataFrame):
    return px.line(
        df.set_index([df.index, "locatie", "var"])[["value"]]
        .unstack()
        .cumsum()
        .stack()
        .reset_index()
        .set_index("dt"),
        y="value",
        color="locatie",
        facet_row="var",
    )
