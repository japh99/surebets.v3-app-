import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import concurrent.futures
import time # Para simular el progreso y manejar timeouts


# --- 1. Configuración Inicial de la Aplicación Streamlit ---
st.set_page_config(
    page_title="Surebets: Buscador",
    page_icon="⚽",
    layout="wide"
)

st.title("Surebets: Buscador Avanzado")
st.markdown("Detecta oportunidades de arbitraje deportivo en tiempo real en el mercado **1x2** para **fútbol**.")
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
    "Ganador (Moneyline/1x2)": "h2h"
}

# --- 4. Lógica de Filtro de Eventos por Estado y Antelación ---
def get_event_status(commence_time_str, min_hours_ahead, max_hours_ahead):
    """
    Valida si un evento está en el rango de antelación deseado.
    """
    now_utc = datetime.now(timezone.utc)
    # The Odds API devuelve la hora de inicio en formato ISO 8601 con zona horaria Z (UTC)
    commence_time_utc = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))

    # Asegurarse de que el evento no ha comenzado
    if commence_time_utc <= now_utc:
        return None

    time_difference = commence_time_utc - now_utc
    hours_ahead = time_difference.total_seconds() / 3600

    if min_hours_ahead <= hours_ahead <= max_hours_ahead:
        return "🟢 Pre-Partido"
    return None


# --- 5. Búsqueda y Detección de Surebets 100% Reales ---
def find_surebets_task(sport_key, api_key_value, api_key_idx, market_key, min_hours_ahead, max_hours_ahead):
    """
    Función que realiza la solicitud a la API y procesa las surebets para un deporte/mercado.
    Diseñada para ser ejecutada en hilos separados.
    """
    surebets_found = []
    api_key_depleted = False
    error_message = None
    remaining_requests = None
    used_requests = None

    ODDS_API_BASE_URL = "https://api.theoddsapi.com/v4/sports"
    url = f"{ODDS_API_BASE_URL}/{sport_key}/odds"
    params = {
        "apiKey": api_key_value,
        "regions": "us,eu,uk,au", # Puedes ajustar las regiones según tu interés
        "markets": market_key,
        "oddsFormat": "decimal",
        "bookmakers": "all" # Escanear todas las casas de apuestas
    }

    try:
        response = requests.get(url, params=params, timeout=10) # 10 segundos de timeout
        response.raise_for_status() # Lanza un HTTPError para respuestas de error (4xx o 5xx)

        # Captura información de créditos de los encabezados
        remaining_requests = response.headers.get('X-Requests-Remaining')
        used_requests = response.headers.get('X-Requests-Used')

        events = response.json()

        for event in events:
            event_status = get_event_status(event['commence_time'], min_hours_ahead, max_hours_ahead)
            if not event_status:
                continue # Saltar eventos fuera del rango de antelación

            # Solo procesar si el mercado "h2h" está disponible
            if 'bookmakers' in event:
                best_odds = {
                    'home_team': {'odd': 0.0, 'bookmaker': ''},
                    'away_team': {'odd': 0.0, 'bookmaker': ''},
                    'draw': {'odd': 0.0, 'bookmaker': ''}
                }

                # Buscar la mejor cuota para cada resultado (1, X, 2)
                for bookmaker in event['bookmakers']:
                    for market in bookmaker['markets']:
                        if market['key'] == market_key: # Nos aseguramos que sea el mercado 1x2 (h2h)
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

                # Verificar que se encontraron cuotas válidas para los TRES resultados
                if (best_odds['home_team']['odd'] > 0 and
                    best_odds['away_team']['odd'] > 0 and
                    best_odds['draw']['odd'] > 0):

                    # --- Validación CRÍTICA: Casas de Apuestas Diferentes ---
                    # Para que sea una surebet real (arbitraje), las mejores cuotas deben venir
                    # de al menos dos casas de apuestas diferentes.
                    involved_bookmakers = {
                        best_odds['home_team']['bookmaker'],
                        best_odds['away_team']['bookmaker'],
                        best_odds['draw']['bookmaker']
                    }

                    if len(involved_bookmakers) < 2:
                        continue # No es una surebet de arbitraje si todas las cuotas son de la misma casa o solo de una.

                    # Cálculo de Utilidad (Fórmula de Arbitraje)
                    # Suma de las probabilidades inversas
                    sum_inverse_odds = (1 / best_odds['home_team']['odd'] +
                                        1 / best_odds['draw']['odd'] +
                                        1 / best_odds['away_team']['odd'])

                    # Si la suma es menor que 1, hay una oportunidad de arbitraje (utilidad positiva)
                    if sum_inverse_odds < 1:
                        utility = (1 - sum_inverse_odds) * 100
                        if utility > 0.01: # Solo surebets con utilidad positiva significativa
                            surebets_found.append({
                                "Deporte": event['sport_title'],
                                "Liga/Torneo": event['league'],
                                "Evento": f"{event['home_team']} vs {event['away_team']}",
                                "Fecha": datetime.fromisoformat(event['commence_time'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M UTC"),
                                "Mercado": MARKETS[selected_market_display], # Usamos el nombre legible del mercado
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

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            error_message = f"API Key {api_key_idx} inválida o no autorizada."
            api_key_depleted = True # Considerarla agotada si falla por auth
        elif e.response.status_code == 402:
            error_message = f"API Key {api_key_idx} agotada (créditos)."
            api_key_depleted = True
        else:
            error_message = f"Error HTTP {e.response.status_code} para API Key {api_key_idx}: {e.response.text}"
            print(f"DEBUG: Error HTTP: {e.response.text}") # Para depuración
    except requests.exceptions.ConnectionError:
        error_message = f"Error de conexión para API Key {api_key_idx}. Verifica tu conexión a internet."
    except requests.exceptions.Timeout:
        error_message = f"Tiempo de espera agotado para API Key {api_key_idx}."
    except Exception as e:
        error_message = f"Error inesperado con API Key {api_key_idx}: {e}"

    return {
        "surebets": surebets_found,
        "api_key_depleted": api_key_depleted,
        "error_message": error_message,
        "remaining_requests": remaining_requests,
        "used_requests": used_requests,
        "api_key_idx": api_key_idx # Devolver el índice de la key usada
    }


# --- INTERFAZ DE USUARIO (Streamlit Sidebar y Panel Principal) ---

# Barra Lateral (st.sidebar) - El Panel de Control Principal
with st.sidebar:
    st.title("Configuración de Surebets")
    st.markdown("---")

    st.header("Filtros de Búsqueda")

    # Deporte: Solo Fútbol
    selected_sports_display = ["Fútbol"]
    selected_sports_api_keys = [SPORTS["Fútbol"]]
    st.info("Deporte seleccionado: Fútbol")

    # Mercado: Enfocado en 1x2 (h2h)
    selected_market_display = st.selectbox(
        "Selecciona el Mercado:",
        options=list(MARKETS.keys()),
        index=0, # Por defecto selecciona el primero (Ganador)
        help="Actualmente, el buscador se enfoca en el mercado 1x2 (Ganador/Moneyline)."
    )
    selected_market_api_key = MARKETS[selected_market_display]

    st.markdown("---")

    # Control de Antelación
    st.header("Antelación del Evento")
    st.markdown("Selecciona el rango de antelación para las surebets, para evitar cambios bruscos en las cuotas.")

    min_hours_option = st.radio(
        "Mínimo de Horas de Antelación:",
        options=[6, 12],
        index=0, # Por defecto 6 horas
        format_func=lambda x: f"{x} horas"
    )

    max_hours_option = st.radio(
        "Máximo de Horas de Antelación:",
        options=[48, 72],
        index=1, # Por defecto 72 horas
        format_func=lambda x: f"{x} horas"
    )

    # Ajuste automático si el mínimo es mayor o igual que el máximo
    if min_hours_option >= max_hours_option:
        st.warning("El mínimo de antelación no puede ser mayor o igual al máximo. Ajustando el máximo automáticamente.")
        if min_hours_option == 6:
            max_hours_option = 48
        else: # min_hours_option == 12
            max_hours_option = 72
        st.info(f"Rango ajustado a {min_hours_option}-{max_hours_option} horas.")

    min_hours_ahead = min_hours_option
    max_hours_ahead = max_hours_option

    st.markdown("---")

    # Botón de Acción Principal
    if st.button("🚀 Iniciar Búsqueda de Surebets", type="primary"):
        if st.session_state.active_api_keys_count == 0:
            st.error("No hay API Keys activas disponibles. ¡Revisa tu configuración o espera a que se reinicien los créditos!")
        else:
            st.session_state.all_surebets = [] # Resetear resultados anteriores
            st.session_state.search_in_progress = True # Bandera para indicar búsqueda activa
            st.success(f"Iniciando búsqueda de surebets de Fútbol con antelación entre {min_hours_ahead} y {max_hours_ahead} horas...")

            # Inicializar placeholders para mensajes dinámicos en el panel principal
            results_placeholder = st.empty()
            progress_bar_placeholder = st.empty()
            status_message_placeholder = st.empty()

            progress_text = "Escaneando deportes..."
            my_bar = progress_bar_placeholder.progress(0, text=progress_text)
            
            # Resetear el conteo de API Keys activas para este ciclo de búsqueda
            current_active_keys = [idx for idx, status in st.session_state.api_key_status.items() if status['active']]
            st.session_state.active_api_keys_count = len(current_active_keys)

            # Usar ThreadPoolExecutor para concurrencia
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                for sport_name in selected_sports_display: # Solo Fútbol en este caso
                    sport_key = SPORTS[sport_name]
                    
                    # Obtener la próxima API key disponible
                    api_key_value, api_key_idx = get_next_available_api_key_info()

                    if api_key_value is None:
                        status_message_placeholder.warning("No quedan API Keys activas para continuar el escaneo.")
                        break # Salir del bucle si no hay más keys
                    
                    status_message_placeholder.info(f"Usando API Key {api_key_idx}. Solicitudes restantes: {st.session_state.api_key_status[api_key_idx]['remaining_requests'] or 'N/A'}")
                    
                    # Actualizar la información de la API Key actual en la sesión para mostrarla en la UI
                    st.session_state.current_api_key_info = {
                        'key_id': f"Key {api_key_idx}",
                        'remaining_requests': st.session_state.api_key_status[api_key_idx]['remaining_requests'] or 'N/A',
                        'used_requests': st.session_state.api_key_status[api_key_idx]['used_requests'] or 'N/A'
                    }
                    
                    future = executor.submit(
                        find_surebets_task,
                        sport_key, api_key_value, api_key_idx, selected_market_api_key,
                        min_hours_ahead, max_hours_ahead
                    )
                    futures[future] = sport_name

                processed_sports_count = 0
                for future in concurrent.futures.as_completed(futures):
                    sport_name = futures[future]
                    try:
                        result = future.result()
                        st.session_state.all_surebets.extend(result["surebets"])

                        # Actualizar el estado de la API key utilizada en st.session_state (en el hilo principal)
                        key_idx_used = result["api_key_idx"]
                        if result["api_key_depleted"]:
                            st.session_state.api_key_status[key_idx_used]['active'] = False
                            if key_idx_used not in st.session_state.depleted_api_keys:
                                st.session_state.depleted_api_keys.append(key_idx_used)
                            st.session_state.active_api_keys_count = len(API_KEYS) - len(st.session_state.depleted_api_keys)
                            status_message_placeholder.error(f"⚠️ {result['error_message']}")
                        
                        # Actualizar los contadores de requests de la API Key
                        if result["remaining_requests"] is not None:
                            st.session_state.api_key_status[key_idx_used]['remaining_requests'] = int(result["remaining_requests"])
                        if result["used_requests"] is not None:
                            st.session_state.api_key_status[key_idx_used]['used_requests'] = int(result["used_requests"])
                        
                        # Actualizar la info de la key actual mostrada si es la que se acaba de procesar
                        if st.session_state.current_api_key_info and st.session_state.current_api_key_info['key_id'] == f"Key {key_idx_used}":
                            st.session_state.current_api_key_info['remaining_requests'] = result["remaining_requests"] or 'N/A'
                            st.session_state.current_api_key_info['used_requests'] = result["used_requests"] or 'N/A'

                        if result["error_message"] and not result["api_key_depleted"]:
                            status_message_placeholder.warning(f"Problema con {sport_name}: {result['error_message']}")

                    except Exception as exc:
                        status_message_placeholder.error(f"Error procesando {sport_name}: {exc}")

                    processed_sports_count += 1
                    progress = min(int((processed_sports_count / len(selected_sports_display)) * 100), 100)
                    my_bar.progress(progress, text=f"Escaneando Fútbol... {progress}%")
                    time.sleep(0.1) # Pequeña pausa para que la UI se actualice

            my_bar.progress(100, text="Escaneo completado.")
            status_message_placeholder.empty() # Limpiar mensaje de estado

            st.session_state.search_in_progress = False # Búsqueda finalizada
            st.rerun() # Volver a ejecutar para mostrar los resultados finales y actualizar la sidebar


    st.markdown("---")

    # Estado de API Keys (Información Crítica) - Actualización de visualización en la barra lateral
    st.header("Estado de API Keys")

    # Mostrar la API Key en uso y sus créditos justo debajo del botón o en una sección propia
    if st.session_state.current_api_key_info:
        current_key_info = st.session_state.current_api_key_info
        st.markdown(f"**API Key en Último Uso:** `{current_key_info['key_id']}`")
        col1_side, col2_side = st.columns(2)
        with col1_side:
            st.markdown(f"**Usadas:** `{current_key_info['used_requests']}`")
        with col2_side:
            st.markdown(f"**Restantes:** `{current_key_info['remaining_requests']}`")
    else:
        st.info("Inicia una búsqueda para ver el estado de la API Key en uso.")

    st.markdown("---") # Separador

    st.markdown(f"**API Keys Activas:** <span style='color:green;'>**{st.session_state.active_api_keys_count}**</span>", unsafe_allow_html=True)
    st.markdown(f"**API Keys Agotadas:** <span style='color:red;'>**{len(st.session_state.depleted_api_keys)}**</span>", unsafe_allow_html=True)


    with st.expander("Ver API Keys Agotadas"):
        if st.session_state.depleted_api_keys:
            for key_idx in st.session_state.depleted_api_keys:
                st.write(f"- Key {key_idx}") # Mostrar el índice de la key agotada
        else:
            st.write("Ninguna API Key agotada hasta el momento.")

    st.markdown("---")
    st.caption("Datos actualizados por The Odds API")

# --- Panel Principal (Visualización Dinámica) ---

# Estos placeholders deben definirse fuera del bloque 'if st.button' para que Streamlit
# pueda renderizarlos en cada re-ejecución y actualizar su contenido.
results_placeholder = st.empty()
progress_bar_placeholder = st.empty() # En caso de que se use para otros mensajes
status_message_placeholder = st.empty()


if 'search_in_progress' not in st.session_state:
    st.session_state.search_in_progress = False
if 'all_surebets' not in st.session_state:
    st.session_state.all_surebets = []


if not st.session_state.search_in_progress:
    if st.session_state.all_surebets:
        surebets_df = pd.DataFrame(st.session_state.all_surebets)
        # Ordenar por utilidad de mayor a menor
        surebets_df = surebets_df.sort_values(by="Utilidad (%)", ascending=False).reset_index(drop=True)

        with results_placeholder.container():
            st.subheader("🎉 Oportunidades de Surebet Encontradas:")
            
            # Función para aplicar color a la utilidad
            def color_utility(val):
                color = 'green' if val > 0.01 else 'orange' # Solo verde si es significativamente positiva
                return f'color: {color}; font-weight: bold;'
            
            # Mostrar DataFrame de resumen
            st.dataframe(
                surebets_df[['Deporte', 'Liga/Torneo', 'Evento', 'Fecha', 'Mercado', 'Utilidad (%)']].style.applymap(color_utility, subset=['Utilidad (%)']).format({'Utilidad (%)': "{:.2f}%"}),
                use_container_width=True
            )
            st.markdown("---")
            st.write("### 🔍 Detalle de las Surebets:")

            # Mostrar cada surebet individualmente para mayor claridad
            for index, row in surebets_df.iterrows():
                st.markdown(f"#### ⚽ **{row['Evento']}**")
                st.markdown(f"**Deporte:** {row['Deporte']} | **Liga:** {row['Liga/Torneo']}")
                st.markdown(f"**Fecha:** {row['Fecha']} | **Mercado:** {row['Mercado']}")
                st.markdown(f"**Utilidad:** <span style='color:green; font-weight:bold;'>{row['Utilidad (%)']:.2f}%</span>", unsafe_allow_html=True)
                st.write("**Detalle de Apuestas:**")
                st.markdown(f"- **{row['Selección 1']}:** Cuota `{row['Cuota 1']}` en `{row['Casa 1']}`")
                st.markdown(f"- **{row['Selección X']}:** Cuota `{row['Cuota X']}` en `{row['Casa X']}`")
                st.markdown(f"- **{row['Selección 2']}:** Cuota `{row['Cuota 2']}` en `{row['Casa 2']}`")
                st.markdown("---") # Separador entre surebets
    else:
        with results_placeholder.container():
            st.info("No se encontraron surebets en los criterios seleccionados. Inicia una búsqueda o ajusta los filtros.")
