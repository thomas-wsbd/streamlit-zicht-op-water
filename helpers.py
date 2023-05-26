import requests, datetime
import pandas as pd
import streamlit as st
import plotly.express as px
from plotly.subplots import make_subplots

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


def return_meta() -> pd.DataFrame:
    return meta


def label_names(name: str) -> str:
    return meta.set_index("Naam")["label"].to_dict().get(name)


def var_to_text(var) -> str:
    return dict(
        ontdebiet="gemeten onttrokken hoeveelheden (m3)",
        humext="luchtvochtigheid (%)",
        tempext="luchttemperatuur (°C)",
        soilmoist1="bodemvocht ondiep (%)",
        soilmoist2="bodemvocht diep (%)",
        soiltemp1="bodemtemperatuur ondiep (°C)",
        soiltemp2="bodemtemperatuur diep (°C)",
        precp="neerslag (mm)",
    ).get(var)


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


def pxbar(df: pd.DataFrame, loc: str):
    vars = df["var"].unique()
    if len(vars) == 1:
        return px.bar(
            df,
            y="value",
            color="locatie",
            title=f"{var_to_text(vars[0])}; {', '.join(loc)}",
        ).update_layout(
            height=800,
            yaxis_title=var_to_text(vars[0]),
            xaxis_title=None,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title_text="",
            ),
        )
    else:
        fig = make_subplots(
            rows=len(vars),
            cols=1,
            subplot_titles=[var_to_text(var) for var in vars],
        )
        figures = []
        for var in vars:
            if var in ["ontdebiet", "precp"]:
                figures.append(px.bar(df[df["var"] == var], y="value", color="locatie"))
            else:
                figures.append(
                    px.scatter(df[df["var"] == var], y="value", color="locatie")
                )
        for i, figure in enumerate(figures):
            for trace in range(len(figure["data"])):
                fig.append_trace(figure["data"][trace], row=i + 1, col=1)
        names = set()
        fig.for_each_trace(
            lambda trace: trace.update(showlegend=False)
            if (trace.name in names)
            else names.add(trace.name)
        )
        return fig.update_layout(
            title=f"gemeten parameters; {', '.join(loc)}",
            height=800,
            xaxis_title=None,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                title_text="",
            ),
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
