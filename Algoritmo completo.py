# surebets_app.py
# Versión de prueba más sensible - para verificar funcionamiento de lógica y mostrar resultados aunque la utilidad sea baja

import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import concurrent.futures
import time

# --- CONFIGURACIÓN STREAMLIT ---
st.set_page_config(page_title="Surebets Test", layout="wide")
st.title("🧪 Prueba de Surebets (Versión de Diagnóstico)")

# --- API KEY DE PRUEBA TEMPORAL (usa una sola para test) ---
API_KEY = "f487a9a7de0ca18a9c4ce68e550b951f"

# --- FUNCIONES ---
def get_odds(sport):
    url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "eu",
        "markets": "h2h",
        "oddsFormat": "decimal"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"❌ Error obteniendo cuotas: {e}")
        return []

def calcular_surebet(c1, c2):
    inv = (1 / c1) + (1 / c2)
    return inv < 1, round((1 - inv) * 100, 2)

def calcular_montos(c1, c2, total):
    inv1 = 1 / c1
    inv2 = 1 / c2
    total_inv = inv1 + inv2
    stake1 = round((inv1 / total_inv) * total, 2)
    stake2 = round((inv2 / total_inv) * total, 2)
    ganancia = round(min(stake1 * c1, stake2 * c2) - total, 2)
    return stake1, stake2, ganancia

# --- INTERFAZ USUARIO ---
st.sidebar.header("⚙️ Parámetros de prueba")
sport = st.sidebar.selectbox("Deporte", ["soccer", "basketball", "tennis"])
presupuesto = st.sidebar.number_input("Presupuesto (€)", 10.0, 1000.0, 100.0, 10.0)

if st.sidebar.button("🔍 Buscar Surebets"):
    eventos = get_odds(sport)
    total_encontradas = 0
    for evento in eventos:
        teams = evento.get("teams", [])
        if len(teams) < 2:
            continue
        equipo1, equipo2 = teams[0], teams[1]
        hora = datetime.fromisoformat(evento['commence_time'].replace("Z", "+00:00"))
        nombre_evento = f"{equipo1} vs {equipo2}"

        mejores = {}
        for casa in evento.get("bookmakers", []):
            for mercado in casa.get("markets", []):
                if mercado['key'] != "h2h":
                    continue
                for o in mercado.get("outcomes", []):
                    n = o['name']
                    if n not in mejores or o['price'] > mejores[n]['price']:
                        mejores[n] = {
                            "cuota": o['price'],
                            "casa": casa['title']
                        }

        if len(mejores) < 2:
            continue
        nombres = list(mejores.keys())
        for i in range(len(nombres)):
            for j in range(i+1, len(nombres)):
                o1, o2 = nombres[i], nombres[j]
                c1 = mejores[o1]['cuota']
                c2 = mejores[o2]['cuota']
                es_surebet, roi = calcular_surebet(c1, c2)
                if es_surebet:
                    stake1, stake2, ganancia = calcular_montos(c1, c2, presupuesto)
                    st.markdown(f"""
### ⚽ {nombre_evento}
**Fecha:** {hora.strftime('%d/%m/%Y %H:%M')} UTC

🏠 **{o1}** en `{mejores[o1]['casa']}` a cuota `{c1}` → Apostar: `{stake1}€`
🏠 **{o2}** en `{mejores[o2]['casa']}` a cuota `{c2}` → Apostar: `{stake2}€`

💰 **Ganancia estimada:** `{ganancia}€`  
📈 **ROI:** `{roi}%`
---
""")
                    total_encontradas += 1

    if total_encontradas == 0:
        st.warning("No se encontraron surebets en este momento.")
