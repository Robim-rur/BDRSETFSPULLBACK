import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf

from ta.trend import EMAIndicator, ADXIndicator
from ta.momentum import StochasticOscillator

# =========================
# CONFIG
# =========================
st.set_page_config(page_title="Scanner BDR/ETF AUVP", layout="wide")
st.title("📊 Scanner BDR/ETF - Modelo AUVP (+3%)")

# =========================
# ATIVOS
# =========================
ativos = [
"AAPL34","AMZO34","GOGL34","MSFT34","TSLA34","META34",
"NFLX34","NVDC34","MELI34","BABA34","DISB34","PYPL34",
"JNJB34","PGCO34","KOCH34","VISA34","WMTB34","NIKE34",
"ADBE34","AVGO34","CSCO34","COST34","CVSH34","GECO34",
"GSGI34","HDCO34","INTC34","JPMC34","MAEL34","MCDP34",
"MDLZ34","MRCK34","ORCL34","PEP334","PFIZ34","PMIC34",
"QCOM34","SBUX34","TGTB34","TMOS34","TXN34","UNHH34",
"UPSB34","VZUA34","ABTT34","AMGN34","AXPB34","BAOO34",
"C2OL34","HONB34","BICE34","BERK34","GOGL35",
"BOVA11","IVVB11","SMAL11","HASH11","GOLD11","DIVO11",
"NDIV11","SPUB11"
]

tickers = [x + ".SA" for x in ativos]

# =========================
# DATA
# =========================
@st.cache_data(ttl=3600)
def get_data(ticker):
    try:
        df = yf.download(ticker, period="1y", progress=False)

        if df is None or df.empty:
            return None

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df = df[["Open","High","Low","Close","Volume"]]
        df = df.apply(pd.to_numeric, errors='coerce')
        df.dropna(inplace=True)

        if len(df) < 100:
            return None

        return df
    except:
        return None

# =========================
# INDICADORES
# =========================
def add_indicators(df):
    try:
        close = pd.Series(df["Close"].values.flatten(), index=df.index)
        high = pd.Series(df["High"].values.flatten(), index=df.index)
        low = pd.Series(df["Low"].values.flatten(), index=df.index)

        df["ema69"] = EMAIndicator(close, 69).ema_indicator()

        stoch = StochasticOscillator(high, low, close, 14, 3)
        df["k"] = stoch.stoch()
        df["d"] = stoch.stoch_signal()

        adx = ADXIndicator(high, low, close, 14)
        df["adx"] = adx.adx()
        df["di_plus"] = adx.adx_pos()
        df["di_minus"] = adx.adx_neg()

        return df.dropna()
    except:
        return None

# =========================
# SEMANAL
# =========================
def semanal_ok(ticker):
    df = get_data(ticker)
    if df is None:
        return False

    df = df.resample("1W").last()
    df = add_indicators(df)

    if df is None or df.empty:
        return False

    last = df.iloc[-1]

    return (
        last["Close"] > last["ema69"] and
        last["di_plus"] > last["di_minus"] and
        last["k"] > last["d"]
    )

# =========================
# FALSO ROMPIMENTO
# =========================
def falso_rompimento(df):
    if len(df) < 2:
        return True
    last = df.iloc[-1]
    prev = df.iloc[-2]
    return last["High"] > prev["High"] and last["Close"] < prev["High"]

# =========================
# PROBABILIDADE +3%
# =========================
def probabilidade(df):
    ganhos = 0
    total = 0

    for i in range(len(df)-10):
        entrada = df["Close"].iloc[i]
        alvo = entrada * 1.03
        janela = df["High"].iloc[i:i+10]

        if len(janela) < 10:
            continue

        total += 1
        if janela.max() >= alvo:
            ganhos += 1

    if total == 0:
        return 0

    return round((ganhos/total)*100,1)

# =========================
# STATUS
# =========================
def status_ativo(trend, trigger):
    if not trend:
        return "Perdeu Tendência"
    elif not trigger:
        return "Observação"
    else:
        return "Setup Ativo"

# =========================
# SCANNER
# =========================
results = []

for ticker in tickers:

    df = get_data(ticker)
    if df is None:
        continue

    try:
        volume = float(df["Volume"].iloc[-1])
    except:
        volume = 0

    df = add_indicators(df)
    if df is None or df.empty:
        continue

    last = df.iloc[-1]

    trend = last["Close"] > last["ema69"]
    dmi_ok = last["di_plus"] > last["di_minus"]
    trigger = last["k"] > last["d"]
    semanal = semanal_ok(ticker)
    falso = falso_rompimento(df)

    prob = probabilidade(df)

    score = 0
    if trend: score += 25
    if dmi_ok: score += 25
    if trigger: score += 20
    if semanal: score += 20
    if volume > 300000: score += 5
    if not falso: score += 5

    results.append({
        "Ticker": ticker.replace(".SA",""),
        "Preço": round(last["Close"],2),
        "Volume": int(volume),
        "Prob +3%": prob,
        "Score": score,
        "Semanal": semanal,
        "Status": status_ativo(trend, trigger)
    })

df_res = pd.DataFrame(results)

# =========================
# OUTPUT AUVP
# =========================
if df_res.empty:
    st.warning("Nenhum ativo encontrado.")
    st.stop()

df_res = df_res.sort_values(by=["Score","Prob +3%"], ascending=False)

# CLASSIFICAÇÃO
def classificar(row):
    if row["Score"] >= 70 and row["Status"] == "Setup Ativo":
        return "ENTRADA"
    elif row["Score"] >= 40:
        return "OBSERVAR"
    else:
        return "DESCARTAR"

df_res["Classificação"] = df_res.apply(classificar, axis=1)

# =========================
# TOP 3
# =========================
st.subheader("🔥 TOP 3 OPORTUNIDADES")

top3 = df_res[df_res["Classificação"] == "ENTRADA"].head(3)

if not top3.empty:
    st.success("🚨 OPORTUNIDADES DETECTADAS")
    st.dataframe(top3, use_container_width=True)
else:
    st.info("Nenhuma entrada clara.")

# =========================
# VISÃO GERAL
# =========================
st.subheader("📊 VISÃO GERAL")

st.dataframe(
    df_res[[
        "Ticker","Preço","Volume","Prob +3%","Score","Status","Classificação"
    ]],
    use_container_width=True
)

# =========================
# DETALHADO
# =========================
with st.expander("🔎 Análise Completa"):

    df_diag = df_res.copy()
    df_diag["Semanal"] = df_diag["Semanal"].map({True:"✔", False:"❌"})

    st.dataframe(df_diag, use_container_width=True)
