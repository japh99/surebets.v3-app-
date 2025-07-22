import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import time
import concurrent.futures

# --- Configuración de la Página y Título ---
st.set_page_config(
    page_title="Surebets: Buscador",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Buscador de Surebets")
st.markdown("""
Esta aplicación **detecta oportunidades de surebets (arbitraje deportivo)** en tiempo real para **varios mercados**.
""")

# --- Lista de API Keys ---
API_KEYS = [
    "734f30d0866696cf90d5029ac106cfba", "10fb6d9d7b3240906d0acea646068535",
    "a9ff72549c4910f1fa9659e175a35cc0", "25e9d8872877f5110254ff6ef42056c6",
    "6205cdb2cfd889e6fc44518f950f7dad", "d39a6f31abf6412d46b2c7185a5dfffe",
    "fbd5dece2a99c992cfd783aedfcd2ef3", "687ba857bcae9c7f33545dcbe59aeb2b",
    "f9ff83040b9d2afc1862094694f53da2", "f730fa9137a7cd927554df334af916dc",
    "9091ec0ea25e0cdcdfc161b91603e31a9a", "c0f7d526dd778654dfee7c0686124a77",
    "61a015bc1506aac11ec62901a6189dc6", "d585a73190a117c1041ccc778b92b23d9",
    "4056628d07b0b900175cb332c191cda0", "ac4d3eb2d6df42030568eadeee906770",
    "3cebba62ff5330d1a409160e686124a77", "358644d442444f95bd0b0278e4d3ea22",
    "45dff0519cde0396df06fc4bc1f9bce1", "a4f585765036f57be0966b39125f87a0",
    "349f8eff303fa0963424c54ba181535b", "f54405559ba5aaa27a9687992a84ae2f",
    "24772de60f0ebe37a554b179e0dd819f", "b7bdefecc83235f7923868a0f2e3e114",
    "3a9d3110045fd7373875bdbc7459c82c", "d2aa9011f39bfcb309b3ee1da6328573",
    "107ad40390a24eb61ee02ff976f3d3ac", "8f6358efeec75d6099147764963ae0f8",
    "672962843293d4985d0bed1814d3b716", "4b1867baf919f992554c77f493d258c5",
    "b3fd66af803adc62f00122d51da7a0e6", "53ded39e2281f16a243627673ad2ac8c",
    "bf785b4e9fba3b9cd1adb99b9905880b", "60e3b2a9a7324923d78bfc6dd6f3e5d3",
    "cc16776a60e3eee3e1053577216b7a29", "a0cc233165bc0ed04ee42feeaf2c9d30",
    "d2afc749fc6b64adb4d8361b0fe58b4b", "b351eb6fb3f5e95b019c18117e93db1b",
    "74dbc42e50dd64687dc1fad8af59c490", "7b4a5639cbe63ddf37b64d7e327d3e71",
    "20cec1e2b8c3fd9bb86d9e4fad7e6081", "1352436d9a0e223478ec83aec230b4aa",
    "29257226d1c9b6a15c141d989193ef72", "24677adc5f5ff8401c6d98ea033e0f0b",
    "54e84a82251def9696ba767d6e2ca76c", "ff3e9e3a12c2728c6c4ddea087bc51a9",
    "f3ff0fb5d7a7a683f88b8adec904e7b8", "1e0ab1ff51d111c88aebe4723020946a",
    "6f74a75a76f42fabaa815c4461c59980", "86de2f86b0b628024ef6d5546b479c0f"
]

# --- Diccionario de Deportes de Interés ---
SPORTS = {
    "Fútbol": "soccer",
    "Baloncesto": "basketball",
    "Tenis": "tennis",
    "Béisbol": "baseball_mlb",
}

# --- Diccionario de Mercados Disponibles (Ampliados para la API) ---
MARKETS = {
    "Ganador (Moneyline/H2H)": "h2h",
    "Totales (Over/Under)": "totals",
    "Spreads (Hándicap)": "spreads",
}

# --- Inicialización del Estado de Sesión de Streamlit ---
if 'api_key_index' not in st.session_state:
    st.session_state.api_key_index = 0
if 'api_key_status' not in st.session_state:
    st.session_state.api_key_status = {key: True for key in API_KEYS}
if 'depleted_api_keys' not in st.session_state:
    st.session_state.depleted_api_keys = []

# --- Funciones Auxiliares para el Buscador ---

def get_next_available_api_key_info():
    """
    Obtiene la próxima API key disponible y su índice de forma segura para Streamlit.
    Esta función DEBE ser llamada SOLAMENTE desde el hilo principal de Streamlit
    para manipular st.session_state.
    """
    initial_index = st.session_state.api_key_index
    num_keys = len(API_KEYS)
    
    for _ in range(num_keys):
        current_key_index = st.session_state.api_key_index
        current_key = API_KEYS[current_key_index]
        
        if st.session_state.api_key_status.get(current_key, True):
            st.session_state.api_key_index = (current_key_index + 1) % num_keys
            return current_key, current_key_index
        
        st.session_state.api_key_index = (current_key_index + 1) % num_keys
        
        if st.session_state.api_key_index == initial_index:
            break

    return None, None

def get_event_status(commence_time_str, min_hours_ahead, max_hours_ahead):
    """
    Clasifica un evento como 'Pre-Partido' si está dentro del rango de horas especificado.
    """
    commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
    now_utc = datetime.now(timezone.utc)
    
    if commence_time <= now_utc:
        return None
    elif now_utc + timedelta(hours=min_hours_ahead) <= commence_time <= now_utc + timedelta(hours=max_hours_ahead):
        return "🟢 Pre-Partido"
    else:
        return None

def find_surebets_task(sport_name, sport_key, market_key, api_key, api_key_idx, min_hours_ahead, max_hours_ahead):
    """
    Busca surebets para un deporte y mercado específicos, filtrando por rango de antelación.
    """
    surebets_found = []
    api_key_depleted = False
    error_message = None
    remaining_requests = None
    used_requests = None
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    
    params = {
        "apiKey": api_key,
        "regions": "us,eu,uk,au",
        "markets": market_key,
        "oddsFormat": "decimal",
        "bookmakers": "all"
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        
        if response.status_code == 401:
            api_key_depleted = True
            error_message = "API Key inválida o no autorizada."
            return surebets_found, api_key_depleted, error_message, None, None
        
        if response.status_code == 402:
            api_key_depleted = True
            error_message = "Créditos de API Key agotados."
            return surebets_found, api_key_depleted, error_message, None, None
        
        if response.status_code >= 400: # Captura otros errores HTTP
            error_message = f"Error API para '{sport_name}'. Código: {response.status_code} - {response.text}"
            return surebets_found, api_key_depleted, error_message, None, None

        response.raise_for_status()
        data = response.json()
        
        remaining_requests = response.headers.get('x-requests-remaining', 'N/A')
        used_requests = response.headers.get('x-requests-used', 'N/A')

        for event in data:
            status = get_event_status(event['commence_time'], min_hours_ahead, max_hours_ahead)
            if not status:
                continue

            home_team = event['home_team']
            away_team = event['away_team']
            
            if market_key == "h2h":
                best_odds = {
                    home_team: {'price': 0, 'bookmaker': ''}, 
                    away_team: {'price': 0, 'bookmaker': ''},
                    'Draw': {'price': 0, 'bookmaker': ''}
                }
                outcome_names_to_check = {home_team, away_team, 'Draw'} 

                for bookmaker in event['bookmakers']:
                    h2h_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
                    if not h2h_market:
                        continue

                    for outcome in h2h_market['outcomes']:
                        outcome_name = outcome['name']
                        price = outcome['price']
                        
                        if outcome_name in outcome_names_to_check and price > best_odds[outcome_name]['price']:
                            best_odds[outcome_name]['price'] = price
                            best_odds[outcome_name]['bookmaker'] = bookmaker['title']
                
                odds_home = best_odds[home_team]['price']
                odds_draw = best_odds['Draw']['price']
                odds_away = best_odds[away_team]['price']
                
                if odds_home > 0 and odds_draw > 0 and odds_away > 0:
                    bookmakers_involved = {
                        best_odds[home_team]['bookmaker'],
                        best_odds['Draw']['bookmaker'],
                        best_odds[away_team]['bookmaker']
                    }
                    if len(bookmakers_involved) < 2 or any(bm == '' for bm in bookmakers_involved):
                        continue
                        
                    utilidad = (1 - (1/odds_home + 1/odds_draw + 1/odds_away)) * 100
                else:
                    continue

                if utilidad > 0.01:
                    surebets_found.append({
                        "Deporte": sport_name,
                        "Liga/Torneo": event['sport_title'],
                        "Estado": status,
                        "Evento": f"{home_team} vs {away_team}",
                        "Fecha (UTC)": datetime.fromisoformat(event['commence_time'].replace('Z', '')).strftime('%Y-%m-%d %H:%M'),
                        "Mercado": "Ganador (1x2)",
                        "Utilidad (%)": f"{utilidad:.2f}%",
                        "Selección 1": home_team,
                        "Mejor Cuota 1": odds_home,
                        "Casa de Apuestas 1": best_odds[home_team]['bookmaker'],
                        "Selección X": "Empate", 
                        "Mejor Cuota X": odds_draw, 
                        "Casa de Apuestas X": best_odds['Draw']['bookmaker'],
                        "Selección 2": away_team,
                        "Mejor Cuota 2": odds_away,
                        "Casa de Apuestas 2": best_odds[away_team]['bookmaker'],
                    })

            elif market_key == "totals":
                best_totals_odds = {}

                for bookmaker in event['bookmakers']:
                    totals_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
                    if not totals_market:
                        continue
                    
                    for outcome in totals_market['outcomes']:
                        point = outcome['point']
                        name = outcome['name']
                        price = outcome['price']

                        if point not in best_totals_odds:
                            best_totals_odds[point] = {'over': {'price': 0, 'bookmaker': ''}, 'under': {'price': 0, 'bookmaker': ''}}
                        
                        if name.lower() == 'over' and price > best_totals_odds[point]['over']['price']:
                            best_totals_odds[point]['over']['price'] = price
                            best_totals_odds[point]['over']['bookmaker'] = bookmaker['title']
                        elif name.lower() == 'under' and price > best_totals_odds[point]['under']['price']:
                            best_totals_odds[point]['under']['price'] = price
                            best_totals_odds[point]['under']['bookmaker'] = bookmaker['title']
                
                for point, odds_data in best_totals_odds.items():
                    over_odds = odds_data['over']['price']
                    under_odds = odds_data['under']['price']

                    if over_odds > 0 and under_odds > 0:
                        bookmakers_involved = {odds_data['over']['bookmaker'], odds_data['under']['bookmaker']}
                        if len(bookmakers_involved) < 2 or any(bm == '' for bm in bookmakers_involved):
                            continue
                            
                        utilidad = (1 - (1/over_odds + 1/under_odds)) * 100
                    else:
                        continue

                    if utilidad > 0.01:
                        surebets_found.append({
                            "Deporte": sport_name,
                            "Liga/Torneo": event['sport_title'],
                            "Estado": status,
                            "Evento": f"{home_team} vs {away_team} (Total: {point})",
                            "Fecha (UTC)": datetime.fromisoformat(event['commence_time'].replace('Z', '')).strftime('%Y-%m-%d %H:%M'),
                            "Mercado": f"Totales (Over/Under {point})",
                            "Utilidad (%)": f"{utilidad:.2f}%",
                            "Selección 1": f"Over {point}",
                            "Mejor Cuota 1": over_odds,
                            "Casa de Apuestas 1": odds_data['over']['bookmaker'],
                            "Selección X": "N/A",
                            "Mejor Cuota X": 1.01,
                            "Casa de Apuestas X": "N/A",
                            "Selección 2": f"Under {point}",
                            "Mejor Cuota 2": under_odds,
                            "Casa de Apuestas 2": odds_data['under']['bookmaker'],
                        })

            elif market_key == "spreads":
                best_spreads_odds = {}

                for bookmaker in event['bookmakers']:
                    spreads_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
                    if not spreads_market:
                        continue
                    
                    for outcome in spreads_market['outcomes']:
                        point = outcome['point']
                        name = outcome['name']
                        price = outcome['price']

                        normalized_point = abs(point)

                        if normalized_point not in best_spreads_odds:
                            best_spreads_odds[normalized_point] = {
                                'home_spread': {'price': 0, 'bookmaker': '', 'point': None}, 
                                'away_spread': {'price': 0, 'bookmaker': '', 'point': None}
                            }
                        
                        if name == home_team:
                            if price > best_spreads_odds[normalized_point]['home_spread']['price']:
                                best_spreads_odds[normalized_point]['home_spread']['price'] = price
                                best_spreads_odds[normalized_point]['home_spread']['bookmaker'] = bookmaker['title']
                                best_spreads_odds[normalized_point]['home_spread']['point'] = point
                        elif name == away_team:
                            if price > best_spreads_odds[normalized_point]['away_spread']['price']:
                                best_spreads_odds[normalized_point]['away_spread']['price'] = price
                                best_spreads_odds[normalized_point]['away_spread']['bookmaker'] = bookmaker['title']
                                best_spreads_odds[normalized_point]['away_spread']['point'] = point
                
                for normalized_point, odds_data in best_spreads_odds.items():
                    home_spread_odds = odds_data['home_spread']['price']
                    away_spread_odds = odds_data['away_spread']['price']
                    home_point = odds_data['home_spread']['point']
                    away_point = odds_data['away_spread']['point']

                    if home_spread_odds > 0 and away_spread_odds > 0 and home_point is not None and away_point is not None and home_point == -away_point:
                        bookmakers_involved = {odds_data['home_spread']['bookmaker'], odds_data['away_spread']['bookmaker']}
                        if len(bookmakers_involved) < 2 or any(bm == '' for bm in bookmakers_involved):
                            continue
                            
                        utilidad = (1 - (1/home_spread_odds + 1/away_spread_odds)) * 100
                    else:
                        continue

                    if utilidad > 0.01:
                        surebets_found.append({
                            "Deporte": sport_name,
                            "Liga/Torneo": event['sport_title'],
                            "Estado": status,
                            "Evento": f"{home_team} ({home_point}) vs {away_team} ({away_point})",
                            "Fecha (UTC)": datetime.fromisoformat(event['commence_time'].replace('Z', '')).strftime('%Y-%m-%d %H:%M'),
                            "Mercado": f"Spreads (Hándicap {normalized_point})",
                            "Utilidad (%)": f"{utilidad:.2f}%",
                            "Selección 1": f"{home_team} ({home_point})",
                            "Mejor Cuota 1": home_spread_odds,
                            "Casa de Apuestas 1": odds_data['home_spread']['bookmaker'],
                            "Selección X": "N/A",
                            "Mejor Cuota X": 1.01,
                            "Casa de Apuestas X": "N/A",
                            "Selección 2": f"{away_team} ({away_point})",
                            "Mejor Cuota 2": away_spread_odds,
                            "Casa de Apuestas 2": odds_data['away_spread']['bookmaker'],
                        })

        return surebets_found, api_key_depleted, error_message, remaining_requests, used_requests

    except requests.exceptions.RequestException as e:
        error_message = f"Error de conexión o API para '{sport_name}': {e}"
        return [], api_key_depleted, error_message, None, None
    except Exception as e:
        error_message = f"Error inesperado en la tarea para '{sport_name}': {e}"
        return [], api_key_depleted, error_message, None, None

# --- Interfaz de Usuario con Streamlit ---

st.sidebar.header("Panel de Control del Buscador")

selected_sports = st.sidebar.multiselect(
    "Selecciona los deportes a escanear:",
    options=list(SPORTS.keys()),
    default=["Fútbol", "Baloncesto"]
)

selected_market_name = st.sidebar.selectbox(
    "Selecciona el mercado a escanear:",
    options=list(MARKETS.keys()),
    default="Ganador (Moneyline/H2H)"
)
selected_market_key = MARKETS[selected_market_name]

st.sidebar.markdown("---")
st.sidebar.subheader("Filtro de Tiempo de Eventos (Pre-Partido)")
min_hours_ahead = st.sidebar.radio(
    "Mostrar eventos con al menos esta antelación:",
    options=[6, 12, 24],
    index=0,
)
max_hours_ahead = st.sidebar.slider(
    "Mostrar eventos con un máximo de antelación (horas):",
    min_value=24,
    max_value=72,
    value=72,
    step=12
)

active_keys_count = sum(1 for status in st.session_state.api_key_status.values() if status)
depleted_keys_count = len(st.session_state.depleted_api_keys)
st.sidebar.info(f"🔑 **API Keys Activas:** {active_keys_count}/{len(API_KEYS)}")
if depleted_keys_count > 0:
    st.sidebar.warning(f"❌ **API Keys Agotadas:** {depleted_keys_count}")

if st.sidebar.button("🚀 Iniciar Búsqueda de Surebets"):
    if not selected_sports:
        st.warning("Por favor, selecciona al menos un deporte para buscar.")
    elif active_keys_count == 0:
        st.error("❌ No hay API Keys activas disponibles. Por favor, verifica tus claves o espera el reseteo de créditos.")
    else:
        results_placeholder = st.empty()
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        all_surebets = []
        total_searches = len(selected_sports) 
        search_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = {}
            for sport_name in selected_sports:
                api_key, api_key_idx = get_next_available_api_key_info()
                if api_key is None:
                    st.error("❌ Todas las API Keys disponibles han agotado sus créditos o están marcadas como agotadas. Por favor, actualiza tus API Keys o espera el reseteo diario.")
                    break
                
                futures[executor.submit(find_surebets_task, sport_name, SPORTS[sport_name], selected_market_key, api_key, api_key_idx, min_hours_ahead, max_hours_ahead)] = (sport_name, api_key, api_key_idx)
            
            for future in concurrent.futures.as_completed(futures):
                sport_name, used_api_key, used_api_key_idx = futures[future]
                try:
                    surebets_for_sport, key_depleted_in_thread, task_error_message, remaining_reqs, used_reqs = future.result() 
                    
                    if key_depleted_in_thread:
                        st.session_state.api_key_status[used_api_key] = False
                        if used_api_key not in st.session_state.depleted_api_keys:
                            st.session_state.depleted_api_keys.append(used_api_key)
                        st.warning(f"⚠️ La API Key #{used_api_key_idx+1} (termina en {used_api_key[-4:]}) parece haber agotado sus créditos. Error: {task_error_message}")
                    elif task_error_message:
                        st.error(f"Error para '{sport_name}' con API Key #{used_api_key_idx+1} ({used_api_key[-4:]}): {task_error_message}")

                    if surebets_for_sport:
                        all_surebets.extend(surebets_for_sport)
                    
                    search_count += 1
                    progress = search_count / total_searches if total_searches > 0 else 1
                    progress_bar.progress(progress)
                    status_text.text(f"Completado: **{sport_name}**. Procesando... {search_count}/{total_searches}")
                    
                except Exception as exc:
                    st.error(f"Error inesperado al procesar los resultados de '{sport_name}': {exc}. Por favor, revisa los logs.")
                    
        status_text.success("¡Búsqueda completada!")
        progress_bar.empty()

        with results_placeholder.container():
            if not all_surebets:
                if any(not status for status in st.session_state.api_key_status.values()):
                    st.warning("No se encontraron surebets. Es posible que algunas API Keys hayan agotado sus créditos o no haya surebets disponibles para los deportes y mercado seleccionados.")
                else:
                    st.warning(f"No se encontraron surebets para los deportes y mercado '{selected_market_name}' seleccionados, en el rango de {min_hours_ahead} a {max_hours_ahead} horas de antelación.")
            else:
                st.success(f"¡Se encontraron **{len(all_surebets)}** oportunidades de surebet!")
                
                df = pd.DataFrame(all_surebets)
                
                st.subheader("Resultados de Surebets Encontradas")
                
                for i, row in df.iterrows():
                    st.markdown(f"**Evento:** {row['Evento']} | **Deporte:** {row['Deporte']} | **Liga:** {row['Liga/Torneo']} | **Fecha:** {row['Fecha (UTC)']}")
                    st.markdown(f"**Mercado:** {row['Mercado']} | **Utilidad:** **<span style='color:green; font-size:1.1em;'>{row['Utilidad (%)']}</span>**", unsafe_allow_html=True)
                    
                    if row['Mercado'] == "Ganador (1x2)":
                        st.markdown(f"**{row['Selección 1']}:** {row['Mejor Cuota 1']} ({row['Casa de Apuestas 1']})")
                        st.markdown(f"**{row['Selección X']}:** {row['Mejor Cuota X']} ({row['Casa de Apuestas X']})")
                        st.markdown(f"**{row['Selección 2']}:** {row['Mejor Cuota 2']} ({row['Casa de Apuestas 2']})")
                    elif "Totales" in row['Mercado'] or "Spreads" in row['Mercado']:
                        st.markdown(f"**{row['Selección 1']}:** {row['Mejor Cuota 1']} ({row['Casa de Apuestas 1']})")
                        st.markdown(f"**{row['Selección 2']}:** {row['Mejor Cuota 2']} ({row['Casa de Apuestas 2']})")
                    st.markdown("---")
