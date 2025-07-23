import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import concurrent.futures
import time

# --- 1. Configuración Inicial de la Aplicación Streamlit ---
st.set_page_config(
    page_title="Surebets: Buscador",
    page_icon="⚽",
    layout="wide"
)

st.title("Surebets: Buscador Avanzado")
st.markdown("Detecta oportunidades de arbitraje deportivo en tiempo real en los mercados **1x2** y **Local o Visitante vs Empate** para **fútbol**.")
st.markdown("---")

# --- 2. Gestión Avanzada de 50 API Keys (Rotación Inteligente) ---
# Tus 50 API Keys de The Odds API
API_KEYS = [
    "734f30d0866696cf905029ac106cfba", "10fb6d9d7b3240906d0acea646068535",
    "a9ff72549c4910f1fa9659e175a35cc0", "25e9d8872877f5110254ff6ef42056c6",
    "6205cdb2cfd889e6fc44518f950f7dad", "d39a6f31abf6412d46b2c7185a5dfffe",
    "fbd5dece2a99c992cfd783aedfcd2ef3", "687ba857bcae9c7f33545dcbe59aeb2b",
    "f9ff83040b9d2afc1862094694f53da2", "f730fa9137a7cd927554df334af916dc",
    "9091ec0ea25e0cdfc161b91603e31a9a", "c0f7d526dd778654dfee7c0686124a77",
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

# Inicialización de st.session_state para la persistencia del estado
if 'api_key_index' not in st.session_state:
    st.session_state.api_key_index = 0
if 'api_key_status' not in st.session_state:
    # {index: {'active': True, 'remaining_requests': None, 'used_requests': None, 'key_value': API_KEYS[index]}}
    st.session_state.api_key_status = {i: {'active': True, 'remaining_requests': None, 'used_requests': None, 'key_value': API_KEYS[i]} for i in range(len(API_KEYS))}
if 'depleted_api_keys' not in st.session_state:
    st.session_state.depleted_api_keys = []
if 'current_api_key_info' not in st.session_state:
    st.session_state.current_api_key_info = None # Para mostrar la key en uso y sus créditos
if 'active_api_keys_count' not in st.session_state:
    st.session_state.active_api_keys_count = len(API_KEYS)

def get_next_available_api_key_info():
    """
    Selecciona de manera inteligente la próxima API key activa y funcional de la lista.
    Actualiza st.session_state.api_key_index.
    """
    initial_index = st.session_state.api_key_index
    num_keys = len(API_KEYS)
    for _ in range(num_keys): # Iterar a lo sumo el número de keys
        current_idx = st.session_state.api_key_index
        key_status = st.session_state.api_key_status[current_idx]

        if key_status['active']:
            st.session_state.api_key_index = (current_idx + 1) % num_keys
            return key_status['key_value'], current_idx # Devolvemos la key y su índice para referencia
        else:
            # Si la key no está activa, pasamos a la siguiente
            st.session_state.api_key_index = (current_idx + 1) % num_keys

        if st.session_state.api_key_index == initial_index:
            # Hemos dado una vuelta completa y no encontramos ninguna key activa
            break
    return None, None # No hay keys disponibles


# --- 3. Definición de Deportes y Mercados Enfocados ---
SPORTS = {
    "Fútbol": "soccer"
}

MARKETS = {
    "Ganador (1x2 / Local, Empate, Visitante)": "h2h",
    "Local o Visitante vs Empate": "double_chance_draw_combo" # Custom combo for 2-way surebet
}

# --- 4. Lógica de Filtro de Eventos por Estado y Antelación ---
def get_event_status(commence_time_str, min_hours_ahead, max_hours_ahead):
    """
    Valida si un evento está en el rango de antelación deseado.
    """
    now_utc = datetime.now(timezone.utc)
    commence_time_utc = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))

    if commence_time_utc <= now_utc:
        return None

    time_difference = commence_time_utc - now_utc
    hours_ahead = time_difference.total_seconds() / 3600

    if min_hours_ahead <= hours_ahead <= max_hours_ahead:
        return "🟢 Pre-Partido"
    return None


# --- 5. Búsqueda y Detección de Surebets 100% Reales ---
def find_surebets_task(sport_key, api_key_value, api_key_idx, market_selected_api_key_type, min_hours_ahead, max_hours_ahead):
    """
    Función que realiza la solicitud a la API y procesa las surebets para un deporte/mercado.
    Diseñada para ser ejecutada en hilos separados.
    """
    surebets_found = []
    error_message = None
    api_key_depleted = False
    
    local_used_requests_sum = 0
    local_remaining_requests_last_call = None

    ODDS_API_BASE_URL = "https://api.theoddsapi.com/v4/sports"

    def make_single_api_call(market_param):
        url = f"{ODDS_API_BASE_URL}/{sport_key}/odds"
        params = {
            "apiKey": api_key_value,
            "regions": "us,eu,uk,au",
            "markets": market_param,
            "oddsFormat": "decimal",
            "bookmakers": "all"
        }
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        return response.json(), int(response.headers.get('X-Requests-Used', 0)), int(response.headers.get('X-Requests-Remaining', 0))

    try:
        if market_selected_api_key_type == "h2h":
            events_data, used, remaining = make_single_api_call("h2h")
            local_used_requests_sum += used
            local_remaining_requests_last_call = remaining

            for event in events_data:
                event_status = get_event_status(event['commence_time'], min_hours_ahead, max_hours_ahead)
                if not event_status: continue

                best_odds = {
                    'home_team': {'odd': 0.0, 'bookmaker': ''},
                    'away_team': {'odd': 0.0, 'bookmaker': ''},
                    'draw': {'odd': 0.0, 'bookmaker': ''}
                }

                for bookmaker in event['bookmakers']:
                    for market in bookmaker['markets']:
                        if market['key'] == "h2h":
                            for outcome in market['outcomes']:
                                if outcome['name'] == event['home_team'] and outcome['price'] > best_odds['home_team']['odd']:
                                    best_odds['home_team']['odd'] = outcome['price']
                                    best_odds['home_team']['bookmaker'] = bookmaker['title']
                                elif outcome['name'] == event['away_team'] and outcome['price'] > best_odds['away_team']['odd']:
                                    best_odds['away_team']['odd'] = outcome['price']
                                    best_odds['away_team']['bookmaker'] = bookmaker['title']
                                elif outcome['name'] == 'Draw' and outcome['price'] > best_odds['draw']['odd']:
                                    best_odds['draw']['odd'] = outcome['price']
                                    best_odds['draw']['bookmaker'] = bookmaker['title']

                if all(o['odd'] > 0 for o in best_odds.values()):
                    involved_bookmakers = {
                        best_odds['home_team']['bookmaker'],
                        best_odds['away_team']['bookmaker'],
                        best_odds['draw']['bookmaker']
                    }

                    if len(involved_bookmakers) < 2:
                        continue

                    sum_inverse_odds = (1 / best_odds['home_team']['odd'] +
                                        1 / best_odds['draw']['odd'] +
                                        1 / best_odds['away_team']['odd'])

                    if sum_inverse_odds < 1:
                        utility = (1 - sum_inverse_odds) * 100
                        if utility > 0.01:
                            surebets_found.append({
                                "Deporte": event['sport_title'],
                                "Liga/Torneo": event['league'],
                                "Evento": f"{event['home_team']} vs {event['away_team']}",
                                "Fecha": datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M UTC"),
                                "Mercado": "Ganador (1x2)",
                                "Utilidad (%)": utility,
                                "Selección 1": event['home_team'],
                                "Cuota 1": best_odds['home_team']['odd'],
                                "Casa 1": best_odds['home_team']['bookmaker'],
                                "Selección X": "Empate",
                                "Cuota X": best_odds['draw']['odd'],
                                "Casa X": best_odds['draw']['bookmaker'],
                                "Selección 2": event['away_team'],
                                "Cuota 2": best_odds['away_team']['odd'],
                                "Casa 2": best_odds['away_team']['bookmaker']
                            })

        elif market_selected_api_key_type == "double_chance_draw_combo":
            # Realizar dos llamadas a la API: una para h2h (para la cuota de empate) y otra para double_chance (para Home or Away)
            events_data_h2h, used_h2h, remaining_h2h = make_single_api_call("h2h")
            local_used_requests_sum += used_h2h
            local_remaining_requests_last_call = remaining_h2h # Actualiza con los restantes de la última llamada

            events_data_dc, used_dc, remaining_dc = make_single_api_call("double_chance")
            local_used_requests_sum += used_dc
            local_remaining_requests_last_call = remaining_dc # Actualiza con los restantes de la última llamada

            # Mapear eventos de double_chance por ID para una búsqueda eficiente
            event_map_dc = {event['id']: event for event in events_data_dc}

            for event_h2h in events_data_h2h:
                event_status = get_event_status(event_h2h['commence_time'], min_hours_ahead, max_hours_ahead)
                if not event_status: continue

                event_dc = event_map_dc.get(event_h2h['id'])
                if not event_dc: continue # No hay datos double_chance para este evento

                best_draw_odd = {'odd': 0.0, 'bookmaker': ''}
                best_home_away_odd = {'odd': 0.0, 'bookmaker': ''}

                # Encontrar la mejor cuota para 'Empate' del mercado h2h
                for bookmaker_h2h in event_h2h['bookmakers']:
                    for market_h2h in bookmaker_h2h['markets']:
                        if market_h2h['key'] == "h2h":
                            for outcome_h2h in market_h2h['outcomes']:
                                if outcome_h2h['name'] == 'Draw' and outcome_h2h['price'] > best_draw_odd['odd']:
                                    best_draw_odd['odd'] = outcome_h2h['price']
                                    best_draw_odd['bookmaker'] = bookmaker_h2h['title']

                # Encontrar la mejor cuota para 'Local o Visitante' (Home or Away) del mercado double_chance
                for bookmaker_dc in event_dc['bookmakers']:
                    for market_dc in bookmaker_dc['markets']:
                        if market_dc['key'] == "double_chance":
                            for outcome_dc in market_dc['outcomes']:
                                # El nombre del resultado "Home or Away" es dinámico en The Odds API.
                                # Puede ser "{HomeTeam} or {AwayTeam}" o "{AwayTeam} or {HomeTeam}".
                                home_away_name1 = f"{event_h2h['home_team']} or {event_h2h['away_team']}"
                                home_away_name2 = f"{event_h2h['away_team']} or {event_h2h['home_team']}"
                                
                                if (outcome_dc['name'] == home_away_name1 or outcome_dc['name'] == home_away_name2) \
                                   and outcome_dc['price'] > best_home_away_odd['odd']:
                                    best_home_away_odd['odd'] = outcome_dc['price']
                                    best_home_away_odd['bookmaker'] = bookmaker_dc['title']

                if best_draw_odd['odd'] > 0 and best_home_away_odd['odd'] > 0:
                    involved_bookmakers = {
                        best_draw_odd['bookmaker'],
                        best_home_away_odd['bookmaker']
                    }

                    # Asegurarse de que las cuotas provienen de al menos dos casas de apuestas diferentes
                    if len(involved_bookmakers) < 2:
                        continue

                    # Cálculo de la surebet para 2 resultados mutuamente excluyentes
                    sum_inverse_odds = (1 / best_draw_odd['odd'] +
                                        1 / best_home_away_odd['odd'])

                    if sum_inverse_odds < 1:
                        utility = (1 - sum_inverse_odds) * 100
                        if utility > 0.01:
                            surebets_found.append({
                                "Deporte": event_h2h['sport_title'],
                                "Liga/Torneo": event_h2h['league'],
                                "Evento": f"{event_h2h['home_team']} vs {event_h2h['away_team']}",
                                "Fecha": datetime.fromisoformat(event_h2h['commence_time'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M UTC"),
                                "Mercado": "Local o Visitante vs Empate",
                                "Utilidad (%)": utility,
                                "Selección 1": "Empate",
                                "Cuota 1": best_draw_odd['odd'],
                                "Casa 1": best_draw_odd['bookmaker'],
                                "Selección X": "", # No aplica para esta surebet de 2 selecciones
                                "Cuota X": "",     # No aplica
                                "Casa X": "",      # No aplica
                                "Selección 2": "Local o Visitante",
                                "Cuota 2": best_home_away_odd['odd'],
                                "Casa 2": best_home_away_odd['bookmaker']
                            })

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            error_message = f"API Key {api_key_idx} inválida o no autorizada. La key ha sido desactivada."
            api_key_depleted = True
        elif e.response.status_code == 402:
            error_message = f"API Key {api_key_idx} agotada (créditos). La key ha sido desactivada."
            api_key_depleted = True
        else:
            error_message = f"Error HTTP {e.response.status_code} para API Key {api_key_idx}: {e.response.text}. Revisa la consola para más detalles."
            print(f"DEBUG: Error HTTP: {e.response.status_code} - {e.response.text}")
    except requests.exceptions.ConnectionError:
        error_message = f"Error de conexión para API Key {api_key_idx}. Verifica tu conexión a internet."
    except requests.exceptions.Timeout:
        error_message = f"Tiempo de espera agotado para API Key {api_key_idx}. Intenta de nuevo."
    except Exception as e:
        error_message = f"Error inesperado con API Key {api_key_idx}: {e}. Revisa la consola para más detalles."
        print(f"DEBUG: Error inesperado: {e}")

    return {
        "surebets": surebets_found,
        "api_key_depleted": api_key_depleted,
        "error_message": error_message,
        "remaining_requests": local_remaining_requests_last_call,
        "used_requests": local_used_requests_sum,
        "api_key_idx": api_key_idx
    }


# --- INTERFAZ DE USUARIO (Streamlit Sidebar y Panel Principal) ---

# Barra Lateral (st.sidebar) - El Panel de Control Principal
with st.sidebar:
    st.title("Configuración de Surebets")
    st.markdown("---")

    st.header("Filtros de Búsqueda")

    selected_sports_display = ["Fútbol"]
    selected_sports_api_keys = [SPORTS["Fútbol"]]
    st.info("Deporte seleccionado: Fútbol")

    selected_market_name = st.selectbox(
        "Selecciona el mercado a escanear:",
        options=list(MARKETS.keys()),
        index=0 # Por defecto "Ganador (1x2 / Local, Empate, Visitante)"
    )
    selected_market_api_key_type = MARKETS[selected_market_name] 

    st.markdown("---")

    st.header("Antelación del Evento")
    st.markdown("Selecciona el rango de antelación para las surebets, para evitar cambios bruscos en las cuotas.")

    min_hours_option = st.radio(
        "Mínimo de Horas de Antelación:",
        options=[6, 12],
        index=0,
        format_func=lambda x: f"{x} horas"
    )

    max_hours_option = st.radio(
        "Máximo de Horas de Antelación:",
        options=[48, 72],
        index=1,
        format_func=lambda x: f"{x} horas"
    )

    if min_hours_option >= max_hours_option:
        st.warning("El mínimo de antelación no puede ser mayor o igual al máximo. Ajustando el máximo automáticamente.")
        if min_hours_option == 6:
            max_hours_option = 48
        else:
            max_hours_option = 72
        st.info(f"Rango ajustado a {min_hours_option}-{max_hours_option} horas.")

    min_hours_ahead = min_hours_option
    max_hours_ahead = max_hours_option

    st.markdown("---")

    # Botón de Acción Principal
    if st.button("🚀 Iniciar Búsqueda de Surebets", type="primary"):
        required_api_calls_per_sport = 1
        if selected_market_api_key_type == "double_chance_draw_combo":
            required_api_calls_per_sport = 2
        
        if st.session_state.active_api_keys_count == 0:
            st.error("No hay API Keys activas disponibles. ¡Revisa tu configuración o espera a que se reinicien los créditos!")
            # st.stop() # Evitamos st.stop() para una interacción más fluida, solo mostramos el error
            st.session_state.search_in_progress = False
            # st.rerun() # Opcional: para forzar el re-renderizado
        elif st.session_state.active_api_keys_count < required_api_calls_per_sport:
             st.error(f"Se necesitan al menos **{required_api_calls_per_sport}** API Key(s) activa(s) para el mercado '{selected_market_name}'. Solo hay **{st.session_state.active_api_keys_count}** activas. Por favor, espera a que se reinicien los créditos o desactiva las agotadas.")
             st.session_state.search_in_progress = False
        else: # Solo procede si hay suficientes keys activas
            st.session_state.all_surebets = []
            st.session_state.search_in_progress = True
            st.success(f"Iniciando búsqueda de surebets de Fútbol con antelación entre {min_hours_ahead} y {max_hours_ahead} horas...")

            if 'results_placeholder' not in st.session_state:
                st.session_state.results_placeholder = st.empty()
            if 'progress_bar_placeholder' not in st.session_state:
                st.session_state.progress_bar_placeholder = st.empty()
            if 'status_message_placeholder' not in st.session_state:
                st.session_state.status_message_placeholder = st.empty()

            progress_text = "Escaneando deportes..."
            my_bar = st.session_state.progress_bar_placeholder.progress(0, text=progress_text)
            
            current_active_keys_indices = [idx for idx, status in st.session_state.api_key_status.items() if status['active']]
            st.session_state.active_api_keys_count = len(current_active_keys_indices)
            
            if selected_market_api_key_type == "double_chance_draw_combo":
                st.session_state.status_message_placeholder.info(
                    "¡Atención! El mercado 'Local o Visitante vs Empate' consume **dos créditos API** por cada búsqueda."
                )

            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                sport_name = selected_sports_display[0]
                sport_key = SPORTS[sport_name]
                
                api_key_value, api_key_idx = get_next_available_api_key_info()

                if api_key_value is None:
                    st.session_state.status_message_placeholder.error("No quedan API Keys activas para continuar el escaneo. Por favor, revisa el estado de tus keys.")
                    st.session_state.search_in_progress = False
                else:
                    st.session_state.status_message_placeholder.info(
                        f"**Iniciando búsqueda con API Key {api_key_idx}.** "
                        f"Créditos restantes (estimado antes de esta búsqueda): "
                        f"**{st.session_state.api_key_status[api_key_idx]['remaining_requests'] or 'N/A'}**"
                    )
                    
                    st.session_state.current_api_key_info = {
                        'key_id': f"Key {api_key_idx}",
                        'remaining_requests': st.session_state.api_key_status[api_key_idx]['remaining_requests'] or 'N/A',
                        'used_requests': st.session_state.api_key_status[api_key_idx]['used_requests'] or 'N/A'
                    }
                    
                    future = executor.submit(
                        find_surebets_task,
                        sport_key, api_key_value, api_key_idx, selected_market_api_key_type,
                        min_hours_ahead, max_hours_ahead
                    )
                    futures[future] = sport_name

                processed_sports_count = 0
                for future in concurrent.futures.as_completed(futures):
                    sport_name = futures[future]
                    try:
                        result = future.result()
                        st.session_state.all_surebets.extend(result["surebets"])

                        key_idx_used = result["api_key_idx"]
                        if result["api_key_depleted"]:
                            st.session_state.api_key_status[key_idx_used]['active'] = False
                            if key_idx_used not in st.session_state.depleted_api_keys:
                                st.session_state.depleted_api_keys.append(key_idx_used)
                            st.session_state.active_api_keys_count = len(API_KEYS) - len(st.session_state.depleted_api_keys)
                            st.session_state.status_message_placeholder.error(f"⚠️ {result['error_message']}")
                        
                        if result["remaining_requests"] is not None:
                            st.session_state.api_key_status[key_idx_used]['remaining_requests'] = int(result["remaining_requests"])
                        if result["used_requests"] is not None:
                            st.session_state.api_key_status[key_idx_used]['used_requests'] = int(result["used_requests"])
                        
                        if st.session_state.current_api_key_info and st.session_state.current_api_key_info['key_id'] == f"Key {key_idx_used}":
                            st.session_state.current_api_key_info['remaining_requests'] = result["remaining_requests"] or 'N/A'
                            st.session_state.current_api_key_info['used_requests'] = result["used_requests"] or 'N/A'

                        if result["error_message"] and not result["api_key_depleted"]:
                            st.session_state.status_message_placeholder.warning(f"Problema con {sport_name}: {result['error_message']}")

                    except Exception as exc:
                        st.session_state.status_message_placeholder.error(f"Error procesando {sport_name}: {exc}")

                    processed_sports_count += 1
                    progress = min(int((processed_sports_count / len(selected_sports_display)) * 100), 100)
                    my_bar.progress(progress, text=f"Escaneando Fútbol... {progress}%")
                    time.sleep(0.1)

            my_bar.progress(100, text="Escaneo completado.")
            st.session_state.status_message_placeholder.empty()
            st.session_state.search_in_progress = False
            st.rerun() # Para forzar el re-renderizado de los resultados


    st.markdown("---")

    st.header("Estado de API Keys")

    if st.session_state.current_api_key_info:
        current_key_info = st.session_state.current_api_key_info
        st.markdown(f"**API Key en Último Uso:** **`{current_key_info['key_id']}`**")
        
        col1_side, col2_side = st.columns(2)
        with col1_side:
            st.metric(label="Créditos Usados (última búsqueda)", value=current_key_info['used_requests'])
        with col2_side:
            st.metric(label="Créditos Restantes", value=current_key_info['remaining_requests'])
        st.caption("Los créditos se refieren al consumo y disponibilidad de tu API Key de The Odds API.")
    else:
        st.info("Inicia una búsqueda para ver el estado de la API Key en uso y los créditos gastados.")

    st.markdown("---")

    st.markdown(f"**API Keys Activas:** <span style='color:green;'>**{st.session_state.active_api_keys_count}**</span>", unsafe_allow_html=True)
    st.markdown(f"**API Keys Agotadas:** <span style='color:red;'>**{len(st.session_state.depleted_api_keys)}**</span>", unsafe_allow_html=True)


    with st.expander("Ver API Keys Agotadas"):
        if st.session_state.depleted_api_keys:
            for key_idx in st.session_state.depleted_api_keys:
                st.write(f"- Key {key_idx}")
        else:
            st.write("Ninguna API Key agotada hasta el momento.")

    st.markdown("---")
    st.caption("Datos actualizados por The Odds API")

# --- Panel Principal (Visualización Dinámica) ---

# Estos placeholders deben definirse fuera del bloque 'if st.button' para que Streamlit
# pueda renderizarlos en cada re-ejecución y actualizar su contenido.
if 'results_placeholder' not in st.session_state:
    st.session_state.results_placeholder = st.empty()
if 'progress_bar_placeholder' not in st.session_state:
    st.session_state.progress_bar_placeholder = st.empty()
if 'status_message_placeholder' not in st.session_state:
    st.session_state.status_message_placeholder = st.empty()


if 'search_in_progress' not in st.session_state:
    st.session_state.search_in_progress = False
if 'all_surebets' not in st.session_state:
    st.session_state.all_surebets = []


# Solo muestra los resultados si no hay una búsqueda en progreso
if not st.session_state.search_in_progress:
    if st.session_state.all_surebets:
        surebets_df = pd.DataFrame(st.session_state.all_surebets)
        surebets_df = surebets_df.sort_values(by="Utilidad (%)", ascending=False).reset_index(drop=True)

        with st.session_state.results_placeholder.container():
            st.subheader("🎉 Oportunidades de Surebet Encontradas:")
            
            def color_utility(val):
                color = 'green' if val > 0.01 else 'orange'
                return f'color: {color}; font-weight: bold;'
            
            st.dataframe(
                surebets_df[['Deporte', 'Liga/Torneo', 'Evento', 'Fecha', 'Mercado', 'Utilidad (%)']].style.applymap(color_utility, subset=['Utilidad (%)']).format({'Utilidad (%)': "{:.2f}%"}),
                use_container_width=True
            )
            st.markdown("---")
            st.write("### 🔍 Detalle de las Surebets:")

            for index, row in surebets_df.iterrows():
                st.markdown(f"#### ⚽ **{row['Evento']}**")
                st.markdown(f"**Deporte:** {row['Deporte']} | **Liga:** {row['Liga/Torneo']}")
                st.markdown(f"**Fecha:** {row['Fecha']} | **Mercado:** {row['Mercado']}")
                st.markdown(f"**Utilidad:** <span style='color:green; font-weight:bold;'>{row['Utilidad (%)']:.2f}%</span>", unsafe_allow_html=True)
                st.write("**Detalle de Apuestas:**")
                st.markdown(f"- **{row['Selección 1']}:** Cuota `{row['Cuota 1']}` en `{row['Casa 1']}`")
                
                if row['Mercado'] == "Ganador (1x2)":
                    st.markdown(f"- **{row['Selección X']}:** Cuota `{row['Cuota X']}` en `{row['Casa X']}`")
                    st.markdown(f"- **{row['Selección 2']}:** Cuota `{row['Cuota 2']}` en `{row['Casa 2']}`")
                elif row['Mercado'] == "Local o Visitante vs Empate":
                    # Para este mercado, 'Selección 1' es Empate y 'Selección 2' es Local o Visitante
                    st.markdown(f"- **{row['Selección 2']}:** Cuota `{row['Cuota 2']}` en `{row['Casa 2']}`")

                st.markdown("---")
    else:
        with st.session_state.results_placeholder.container():
            st.info("No se encontraron surebets en este momento para los criterios seleccionados. Intenta ajustar los filtros o vuelve a intentarlo más tarde.")
            st.markdown("---")
            st.header("💡 Solución de Problemas si no hay Resultados:")
            st.markdown("""
            * **Verifica el "Estado de API Keys" en la barra lateral:** Asegúrate de que tienes API Keys activas y con créditos restantes. Si todas están agotadas, deberás esperar al reinicio diario de créditos de The Odds API.
            * **Amplía el rango de "Antelación del Evento":** Un rango mayor (ej. 48 o 72 horas) te dará más eventos para escanear. Las surebets son más probables en eventos futuros.
            * **Las surebets son raras:** A veces, simplemente no hay oportunidades de arbitraje disponibles. Esto es normal.
            * **Revisa la consola de tu navegador/terminal:** Si hay errores (ej. "Error HTTP 402" por API Key agotada o "Tiempo de espera agotado"), se mostrarán allí para un diagnóstico más preciso.
            """)
