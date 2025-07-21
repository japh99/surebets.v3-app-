import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import time
import concurrent.futures

# --- Configuración de la Página y Título ---
st.set_page_config(
    page_title="Surebets: Buscador & Calculadora",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ Buscador y Calculadora de Surebets")
st.markdown("""
Esta aplicación **detecta oportunidades de surebets (arbitraje deportivo)** en tiempo real para **varios mercados** y te permite **calcularlas** de forma sencilla.
""")

# --- Lista de API Keys (incluyendo las 50 proporcionadas) ---
# Es crucial mantener estas keys actualizadas y con créditos.
# Si tus keys se agotan, la aplicación no funcionará correctamente.
# NOTA: Por seguridad, en un entorno de producción real, estas keys NO deberían estar hardcodeadas aquí.
# Se recomienda usar variables de entorno (secrets) de Streamlit o un servicio de gestión de secretos.
API_KEYS = [
    "734f30d0866696cf90d5029ac106cfba", "10fb6d9d7b3240906d0acea646068535",
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
# Se utilizan para mantener el estado de la aplicación entre recargas
if 'api_key_index' not in st.session_state:
    st.session_state.api_key_index = 0
if 'api_key_status' not in st.session_state:
    # Inicializa todas las keys como activas
    st.session_state.api_key_status = {key: True for key in API_KEYS}
if 'depleted_api_keys' not in st.session_state:
    st.session_state.depleted_api_keys = []

# Estado inicial para la calculadora, cargado con valores por defecto H2H
if 'calc_event_data' not in st.session_state:
    st.session_state.calc_event_data = {
        'Evento': 'Ej: Equipo A vs Equipo B',
        'Fecha (UTC)': 'N/A',
        'Mercado': 'Ganador (Moneyline/H2H)',
        'Cuota Local': 1.01,
        'Cuota Empate': 1.01, # Mantenido para flexibilidad si el usuario cambia el mercado en la calculadora
        'Cuota Visitante': 1.01,
        'Selección 1': 'Equipo Local',
        'Selección 2': 'Equipo Visitante',
        'Selección X': 'Empate', # Añadido para la carga de 1x2
        'Casa Local': 'Casa de Apuestas 1',
        'Casa Empate': 'N/A', # No aplica por defecto para H2H
        'Casa Visitante': 'Casa de Apuestas 2'
    }

# Estado para la calculadora manual: Nombres de casas y cuotas
if 'nombres_casas_manual' not in st.session_state:
    # Casas predeterminadas para COP, con facilidad de edición
    st.session_state.nombres_casas_manual = ["BetPlay", "Wplay", "Stake", "Bwin", "Betsson", "Luckia"]
if 'cuotas_local_manual' not in st.session_state:
    st.session_state.cuotas_local_manual = [1.01] * 6
if 'cuotas_empate_manual' not in st.session_state:
    st.session_state.cuotas_empate_manual = [1.01] * 6
if 'cuotas_visitante_manual' not in st.session_state:
    st.session_state.cuotas_visitante_manual = [1.01] * 6
if 'last_moneda_manual' not in st.session_state:
    st.session_state.last_moneda_manual = "COP" # Guarda la última moneda seleccionada

# --- Funciones Auxiliares para el Buscador ---

def get_next_available_api_key_info():
    """
    Obtiene la próxima API key disponible y su índice de forma segura para Streamlit.
    Esta función DEBE ser llamada SOLAMENTE desde el hilo principal de Streamlit
    para manipular st.session_state.
    """
    initial_index = st.session_state.api_key_index
    num_keys = len(API_KEYS)
    
    # Intentar encontrar una clave activa en el rango actual
    for _ in range(num_keys): # Iterar a través de todas las claves si es necesario
        current_key_index = st.session_state.api_key_index
        current_key = API_KEYS[current_key_index]
        
        # Verificar si la clave actual está activa
        if st.session_state.api_key_status.get(current_key, True):
            # Si está activa, avanzamos el índice para la próxima vez y la devolvemos
            st.session_state.api_key_index = (current_key_index + 1) % num_keys
            return current_key, current_key_index
        
        # Si la clave actual no está activa, simplemente avanzamos al siguiente índice
        st.session_state.api_key_index = (current_key_index + 1) % num_keys
        
        # Si hemos dado una vuelta completa y no encontramos ninguna clave activa, salimos
        if st.session_state.api_key_index == initial_index:
            break

    return None, None # No hay keys disponibles

def get_event_status(commence_time_str, min_hours_ahead, max_hours_ahead):
    """
    Clasifica un evento como 'Pre-Partido' si está dentro del rango de horas especificado
    (mínimo y máximo antes del inicio). Excluye eventos 'En Vivo'.
    """
    # Manejar el formato Z para que datetime.fromisoformat funcione correctamente
    commence_time = datetime.fromisoformat(commence_time_str.replace('Z', '+00:00'))
    now_utc = datetime.now(timezone.utc)
    
    if commence_time <= now_utc: # Excluir eventos que ya han comenzado (En Vivo)
        return None
    elif now_utc + timedelta(hours=min_hours_ahead) <= commence_time <= now_utc + timedelta(hours=max_hours_ahead):
        return "🟢 Pre-Partido"
    else:
        return None # Eventos fuera del rango de antelación no son relevantes

def find_surebets_task(sport_name, sport_key, market_key, api_key, api_key_idx, min_hours_ahead, max_hours_ahead):
    """
    Busca surebets para un deporte y mercado específicos, filtrando por rango de antelación.
    Esta función se ejecutará en un hilo secundario.
    Devuelve las surebets encontradas y el estado de la API key utilizada.
    NO DEBE ACCEDER DIRECTAMENTE A st.session_state.
    """
    surebets_found = []
    api_key_depleted = False # Bandera para indicar si esta API key se agotó
    error_message = None
    remaining_requests = None
    used_requests = None
    
    url = f"https://api.the-odds-api.com/v4/sports/{sport_key}/odds"
    
    params = {
        "apiKey": api_key,
        "regions": "us,eu,uk,au", # Regiones de casas de apuestas a consultar
        "markets": market_key,
        "oddsFormat": "decimal",
        "bookmakers": "all" # Busca en todas las casas disponibles para el deporte
    }
    
    try:
        response = requests.get(url, params=params, timeout=30) # Timeout de 30 segundos
        
        # --- Lógica de Manejo de Errores de la API ---
        if response.status_code == 401: # Unauthorized - API Key inválida
            api_key_depleted = True
            error_message = "API Key inválida o no autorizada."
            return surebets_found, api_key_depleted, error_message, None, None
        
        if response.status_code == 402: # Payment Required - Límite de créditos alcanzado
            api_key_depleted = True
            error_message = "Créditos de API Key agotados."
            return surebets_found, api_key_depleted, error_message, None, None
        
        if response.status_code == 404: # Not Found - Deporte o mercado no encontrado
            error_message = f"Deporte o mercado '{sport_key}' no encontrado."
            return surebets_found, api_key_depleted, error_message, None, None
        
        if response.status_code == 422: # Unprocessable Entity - Parámetros inválidos
            error_message = f"Parámetros de solicitud inválidos para '{sport_key}'. Verifica que la combinación deporte/mercado sea válida."
            return surebets_found, api_key_depleted, error_message, None, None
        
        if response.status_code >= 500: # Server Error
            error_message = f"Error del servidor API para '{sport_key}'. Código: {response.status_code}"
            return surebets_found, api_key_depleted, error_message, None, None

        response.raise_for_status() # Lanza una excepción para otros errores HTTP >= 400
        data = response.json()
        
        # Obtener información de uso de la API para devolverla
        remaining_requests = response.headers.get('x-requests-remaining', 'N/A')
        used_requests = response.headers.get('x-requests-used', 'N/A')

        # --- Lógica Principal de Búsqueda de Surebets por Mercado ---
        for event in data:
            # Filtrar eventos por el estado de pre-partido y el rango de antelación
            status = get_event_status(event['commence_time'], min_hours_ahead, max_hours_ahead)
            if not status:
                continue # Saltar eventos no relevantes (En Vivo o fuera de rango)

            home_team = event['home_team']
            away_team = event['away_team']
            
            # Lógica para H2H (Moneyline/1x2 para fútbol)
            if market_key == "h2h":
                best_odds = {
                    home_team: {'price': 0, 'bookmaker': ''}, 
                    away_team: {'price': 0, 'bookmaker': ''},
                    'Draw': {'price': 0, 'bookmaker': ''} # ¡Añadido el empate para 1x2!
                }
                # Conjunto de nombres de resultados a buscar, incluyendo 'Draw'
                outcome_names_to_check = {home_team, away_team, 'Draw'} 

                for bookmaker in event['bookmakers']:
                    h2h_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
                    if not h2h_market:
                        continue

                    for outcome in h2h_market['outcomes']:
                        outcome_name = outcome['name']
                        price = outcome['price']
                        
                        # Actualizar la mejor cuota si es superior para el resultado específico
                        if outcome_name in outcome_names_to_check and price > best_odds[outcome_name]['price']:
                            best_odds[outcome_name]['price'] = price
                            best_odds[outcome_name]['bookmaker'] = bookmaker['title']
                
                odds_home = best_odds[home_team]['price']
                odds_draw = best_odds['Draw']['price']
                odds_away = best_odds[away_team]['price']
                
                # Verificar que tenemos cuotas válidas para los 3 resultados
                # y que provienen de al menos dos casas de apuestas distintas
                if odds_home > 0 and odds_draw > 0 and odds_away > 0:
                    bookmakers_involved = {
                        best_odds[home_team]['bookmaker'],
                        best_odds['Draw']['bookmaker'],
                        best_odds[away_team]['bookmaker']
                    }
                    # Si todas las cuotas provienen de la misma casa, o alguna no tiene bookmaker (precio 0.0), no es surebet.
                    if len(bookmakers_involved) < 2 or any(bm == '' for bm in bookmakers_involved):
                        continue # No es una surebet válida si no hay al menos 2 casas distintas o faltan datos
                        
                    utilidad = (1 - (1/odds_home + 1/odds_draw + 1/odds_away)) * 100
                else:
                    continue # No hay cuotas completas para 1x2

                if utilidad > 0.01: # Solo surebets con utilidad positiva
                    surebets_found.append({
                        "Deporte": sport_name,
                        "Liga/Torneo": event['sport_title'],
                        "Estado": status,
                        "Evento": f"{home_team} vs {away_team}",
                        "Fecha (UTC)": datetime.fromisoformat(event['commence_time'].replace('Z', '')).strftime('%Y-%m-%d %H:%M'),
                        "Mercado": "Ganador (1x2)", # Más específico para fútbol
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

            # Lógica para Totales (Over/Under)
            elif market_key == "totals":
                best_totals_odds = {} # {point: {'over': {'price': X, 'bookmaker': Y}, 'under': {'price': A, 'bookmaker': B}}}

                for bookmaker in event['bookmakers']:
                    totals_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
                    if not totals_market:
                        continue
                    
                    for outcome in totals_market['outcomes']:
                        point = outcome['point']
                        name = outcome['name'] # 'Over' or 'Under'
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
                        # Verificar que las cuotas provienen de casas distintas
                        bookmakers_involved = {odds_data['over']['bookmaker'], odds_data['under']['bookmaker']}
                        if len(bookmakers_involved) < 2 or any(bm == '' for bm in bookmakers_involved):
                            continue # No es una surebet válida si no hay 2 casas distintas o faltan datos
                            
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
                            "Selección X": "N/A",  # No aplica
                            "Mejor Cuota X": 1.01, # Valor neutro
                            "Casa de Apuestas X": "N/A", # No aplica
                            "Selección 2": f"Under {point}",
                            "Mejor Cuota 2": under_odds,
                            "Casa de Apuestas 2": odds_data['under']['bookmaker'],
                        })

            # Lógica para Spreads (Hándicap)
            elif market_key == "spreads":
                best_spreads_odds = {} # {point: {'home_spread': {'price': X, 'bookmaker': Y, 'point': P_H}, 'away_spread': {'price': A, 'bookmaker': B, 'point': P_A}}}

                for bookmaker in event['bookmakers']:
                    spreads_market = next((m for m in bookmaker['markets'] if m['key'] == market_key), None)
                    if not spreads_market:
                        continue
                    
                    for outcome in spreads_market['outcomes']:
                        point = outcome['point']
                        name = outcome['name'] # Nombre del equipo
                        price = outcome['price']

                        # Normalizar el 'point' usando su valor absoluto como clave para agrupar spreads opuestos
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
                                best_spreads_odds[normalized_point]['home_spread']['point'] = point # Guardar el punto original del hándicap
                        elif name == away_team:
                            if price > best_spreads_odds[normalized_point]['away_spread']['price']:
                                best_spreads_odds[normalized_point]['away_spread']['price'] = price
                                best_spreads_odds[normalized_point]['away_spread']['bookmaker'] = bookmaker['title']
                                best_spreads_odds[normalized_point]['away_spread']['point'] = point # Guardar el punto original del hándicap
                
                for normalized_point, odds_data in best_spreads_odds.items():
                    home_spread_odds = odds_data['home_spread']['price']
                    away_spread_odds = odds_data['away_spread']['price']
                    home_point = odds_data['home_spread']['point']
                    away_point = odds_data['away_spread']['point']

                    # Asegurarse de que tenemos cuotas para ambos lados del spread, que los puntos son opuestos y válidos
                    if home_spread_odds > 0 and away_spread_odds > 0 and home_point is not None and away_point is not None and home_point == -away_point:
                        # Verificar que las cuotas provienen de casas distintas
                        bookmakers_involved = {odds_data['home_spread']['bookmaker'], odds_data['away_spread']['bookmaker']}
                        if len(bookmakers_involved) < 2 or any(bm == '' for bm in bookmakers_involved):
                            continue # No es una surebet válida si no hay 2 casas distintas o faltan datos
                            
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
                            "Mercado": f"Spreads (Hándicap {normalized_point})", # Más específico
                            "Utilidad (%)": f"{utilidad:.2f}%",
                            "Selección 1": f"{home_team} ({home_point})",
                            "Mejor Cuota 1": home_spread_odds,
                            "Casa de Apuestas 1": odds_data['home_spread']['bookmaker'],
                            "Selección X": "N/A",  # No aplica
                            "Mejor Cuota X": 1.01, # Valor neutro
                            "Casa de Apuestas X": "N/A", # No aplica
                            "Selección 2": f"{away_team} ({away_point})",
                            "Mejor Cuota 2": away_spread_odds,
                            "Casa de Apuestas 2": odds_data['away_spread']['bookmaker'],
                        })

        # Devolver las surebets, si la key se agotó, el mensaje de error y la info de requests
        return surebets_found, api_key_depleted, error_message, remaining_requests, used_requests

    except requests.exceptions.RequestException as e:
        error_message = f"Error de conexión o API para '{sport_name}': {e}"
        return [], api_key_depleted, error_message, None, None
    except Exception as e:
        error_message = f"Error inesperado en la tarea para '{sport_name}': {e}"
        return [], api_key_depleted, error_message, None, None

# --- Funciones de Cálculo de Surebets Manuales ---

def calcular_surebet_2_resultados(c1_local, c2_visit, presupuesto):
    """Calcula surebet para 2 resultados (Local/Visitante o Jugador1/Jugador2)."""
    if c1_local <= 1.01 or c2_visit <= 1.01: # Cuotas mínimas para evitar divisiones por cero o cuotas irreales
        return None, None, None, None, None, None
    
    inv1 = 1 / c1_local
    inv2 = 1 / c2_visit
    total_inv = inv1 + inv2

    if total_inv < 1: # Si la suma de las inversas de las cuotas es menor a 1, hay una surebet
        stake1 = round((inv1 / total_inv) * presupuesto)
        stake2 = round((inv2 / total_inv) * presupuesto)
        
        # Calcular la ganancia mínima garantizada
        ganancia = round(min(stake1 * c1_local, stake2 * c2_visit) - presupuesto)
        roi = round((1 - total_inv) * 100, 2)
        return stake1, stake2, ganancia, roi, c1_local, c2_visit
    return None, None, None, None, None, None

def calcular_surebet_3_resultados(c_local, c_empate, c_visitante, presupuesto):
    """Calcula surebet para 3 resultados (Local/Empate/Visitante)."""
    if c_local <= 1.01 or c_empate <= 1.01 or c_visitante <= 1.01:
        return None, None, None, None, None, None, None, None
    
    inv_local = 1 / c_local
    inv_empate = 1 / c_empate
    inv_visitante = 1 / c_visitante
    total_inv = inv_local + inv_empate + inv_visitante

    if total_inv < 1:
        stake_local = round((inv_local / total_inv) * presupuesto)
        stake_empate = round((inv_empate / total_inv) * presupuesto)
        stake_visitante = round((inv_visitante / total_inv) * presupuesto)
        
        # Calcular la ganancia mínima garantizada
        ganancia = round(min(stake_local * c_local, stake_empate * c_empate, stake_visitante * c_visitante) - presupuesto)
        roi = round((1 - total_inv) * 100, 2)
        return stake_local, stake_empate, stake_visitante, ganancia, roi, c_local, c_empate, c_visitante
    return None, None, None, None, None, None, None, None

# --- Definición de Casas de Apuestas Predeterminadas por Divisa ---
casas_predefinidas_manual = {
    "COP": ["BetPlay", "Wplay", "Stake", "Bwin", "Betsson", "Luckia"],
    "EUR": ["Bet365", "Unibet", "Bwin", "Pinnacle", "William Hill", "888sport"],
    "USD": ["DraftKings", "FanDuel", "BetMGM", "Caesars", "PointsBet", "Barstool"],
}


# --- Interfaz de Usuario con Streamlit (Tabs) ---
tab1, tab2 = st.tabs(["🔎 Buscador de Surebets", "🧮 Calculadora Manual"])

# --- TAB 1: Buscador de Surebets ---
with tab1:
    st.header("🔎 Buscador de Surebets (Múltiples Mercados)")
    st.markdown("""
    Aquí puedes buscar surebets en tiempo real para diferentes mercados
    entre una amplia gama de casas de apuestas y los deportes seleccionados.
    """)

    st.sidebar.header("Panel de Control del Buscador")

    selected_sports = st.sidebar.multiselect(
        "Selecciona los deportes a escanear:",
        options=list(SPORTS.keys()),
        default=["Fútbol", "Baloncesto"] # Cambiado a fútbol y baloncesto por defecto
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
        options=[6, 12, 24], # Añadida opción de 24 horas
        index=0, # Por defecto 6 horas
    )
    max_hours_ahead = st.sidebar.slider(
        "Mostrar eventos con un máximo de antelación (horas):",
        min_value=24,
        max_value=72,
        value=72,
        step=12
    )
    
    # Mostrar el conteo de API Keys disponibles y agotadas
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
            results_placeholder = st.empty() # Placeholder para mostrar los resultados
            progress_bar = st.progress(0) # Barra de progreso de la búsqueda
            status_text = st.empty() # Texto de estado de la búsqueda
            
            all_surebets = []
            total_searches = len(selected_sports) 
            search_count = 0

            # Usar ThreadPoolExecutor para paralelizar las solicitudes API
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = {}
                # PREPARACIÓN DE TAREAS: Asignar una API key a cada deporte antes de enviar la tarea
                for sport_name in selected_sports:
                    api_key, api_key_idx = get_next_available_api_key_info()
                    if api_key is None:
                        st.error("❌ Todas las API Keys disponibles han agotado sus créditos o están marcadas como agotadas. Por favor, actualiza tus API Keys o espera el reseteo diario.")
                        break # Salir del bucle si no hay más keys activas
                    
                    # Enviar la tarea al executor. La función find_surebets_task recibe la key y su índice.
                    futures[executor.submit(find_surebets_task, sport_name, SPORTS[sport_name], selected_market_key, api_key, api_key_idx, min_hours_ahead, max_hours_ahead)] = (sport_name, api_key, api_key_idx)
                
                # PROCESAR RESULTADOS: A medida que los futuros se completan, manejar los resultados en el hilo principal
                for future in concurrent.futures.as_completed(futures):
                    sport_name, used_api_key, used_api_key_idx = futures[future]
                    try:
                        # Los resultados de find_surebets_task son: surebets_found, api_key_depleted, error_message, remaining_requests, used_requests
                        surebets_for_sport, key_depleted_in_thread, task_error_message, remaining_reqs, used_reqs = future.result() 
                        
                        # AHORA, en el HILO PRINCIPAL, actualizamos st.session_state y mostramos mensajes
                        if key_depleted_in_thread:
                            st.session_state.api_key_status[used_api_key] = False
                            if used_api_key not in st.session_state.depleted_api_keys:
                                st.session_state.depleted_api_keys.append(used_api_key)
                            st.warning(f"⚠️ La API Key #{used_api_key_idx+1} (termina en {used_api_key[-4:]}) parece haber agotado sus créditos. Error: {task_error_message}")
                        elif task_error_message:
                            st.error(f"Error para '{sport_name}' con API Key #{used_api_key_idx+1} ({used_api_key[-4:]}): {task_error_message}")
                        else:
                            pass # Ya no es necesario mostrar por cada key usada individualmente si ya tenemos el conteo total

                        if surebets_for_sport:
                            all_surebets.extend(surebets_for_sport)
                        
                        search_count += 1
                        progress = search_count / total_searches if total_searches > 0 else 1
                        progress_bar.progress(progress)
                        status_text.text(f"Completado: **{sport_name}**. Procesando... {search_count}/{total_searches}")
                        
                    except Exception as exc:
                        # Captura cualquier otro error inesperado que pueda ocurrir al procesar el resultado del futuro
                        st.error(f"Error inesperado al procesar los resultados de '{sport_name}': {exc}. Por favor, revisa los logs.")
                        
            # --- FIN DE LA LÓGICA DE PARALELIZACIÓN ---

            # Mensaje final al terminar todas las búsquedas
            status_text.success("¡Búsqueda completada!")
            progress_bar.empty() # Ocultar barra de progreso al finalizar

            with results_placeholder.container():
                if not all_surebets:
                    # Mensaje más específico si no hay resultados debido a keys o no-surebets
                    if any(not status for status in st.session_state.api_key_status.values()):
                        st.warning("No se encontraron surebets. Es posible que algunas API Keys hayan agotado sus créditos o no haya surebets disponibles para los deportes y mercado seleccionados.")
                    else:
                        st.warning(f"No se encontraron surebets para los deportes y mercado '{selected_market_name}' seleccionados, en el rango de {min_hours_ahead} a {max_hours_ahead} horas de antelación.")
                else:
                    st.success(f"¡Se encontraron **{len(all_surebets)}** oportunidades de surebet!")
                    
                    df = pd.DataFrame(all_surebets)
                    
                    st.subheader("Resultados de Surebets Encontradas")
                    st.info("Haz clic en 'Cargar en Calculadora' para llevar los datos de una surebet específica a la calculadora manual.")
                    
                    # Mostrar resultados individuales con botón para cargar en calculadora
                    for i, row in df.iterrows():
                        col1, col2 = st.columns([0.8, 0.2])
                        with col1:
                            st.markdown(f"**Evento:** {row['Evento']} | **Deporte:** {row['Deporte']} | **Liga:** {row['Liga/Torneo']} | **Fecha:** {row['Fecha (UTC)']}")
                            st.markdown(f"**Mercado:** {row['Mercado']} | **Utilidad:** **<span style='color:green; font-size:1.1em;'>{row['Utilidad (%)']}</span>**", unsafe_allow_html=True)
                            
                            # Formato específico para H2H (1x2), Totals o Spreads
                            if row['Mercado'] == "Ganador (1x2)":
                                st.markdown(f"**{row['Selección 1']}:** {row['Mejor Cuota 1']} ({row['Casa de Apuestas 1']})")
                                st.markdown(f"**{row['Selección X']}:** {row['Mejor Cuota X']} ({row['Casa de Apuestas X']})")
                                st.markdown(f"**{row['Selección 2']}:** {row['Mejor Cuota 2']} ({row['Casa de Apuestas 2']})")
                            elif "Totales" in row['Mercado'] or "Spreads" in row['Mercado']:
                                st.markdown(f"**{row['Selección 1']}:** {row['Mejor Cuota 1']} ({row['Casa de Apuestas 1']})")
                                st.markdown(f"**{row['Selección 2']}:** {row['Mejor Cuota 2']} ({row['Casa de Apuestas 2']})")
                        with col2:
                            if st.button("Cargar en Calculadora", key=f"load_calc_{i}"):
                                st.session_state.calc_event_data = {
                                    'Evento': row['Evento'],
                                    'Fecha (UTC)': row['Fecha (UTC)'],
                                    'Mercado': row['Mercado'],
                                    'Cuota Local': row['Mejor Cuota 1'],
                                    'Cuota Empate': row['Mejor Cuota X'] if "1x2" in row['Mercado'] else 1.01, # Ajuste para 2 o 3 resultados
                                    'Cuota Visitante': row['Mejor Cuota 2'],
                                    'Selección 1': row['Selección 1'],
                                    'Selección 2': row['Selección 2'],
                                    'Selección X': row['Selección X'] if "1x2" in row['Mercado'] else 'N/A', # Ajuste para 2 o 3 resultados
                                    'Casa Local': row['Casa de Apuestas 1'],
                                    'Casa Empate': row['Casa de Apuestas X'] if "1x2" in row['Mercado'] else 'N/A', # Ajuste para 2 o 3 resultados
                                    'Casa Visitante': row['Casa de Apuestas 2']
                                }
                                st.switch_tab("🧮 Calculadora Manual")
                                st.toast(f"Surebet cargada: {row['Evento']}")
                        st.markdown("---") # Separador visual

# --- TAB 2: Calculadora Manual ---
with tab2:
    st.header("🧮 Calculadora Manual de Surebets")
    st.markdown("Ingresa las cuotas manualmente para calcular una surebet.")

    col_input1, col_input2 = st.columns(2)
    with col_input1:
        st.subheader("Detalles del Evento")
        st.text_input("Evento", value=st.session_state.calc_event_data['Evento'], key="manual_evento")
        st.text_input("Fecha (UTC)", value=st.session_state.calc_event_data['Fecha (UTC)'], key="manual_fecha")
        
        # Selección de tipo de mercado para la calculadora
        # Determinar el índice inicial basado en el mercado cargado
        initial_calc_market_index = 0
        if "1x2" in st.session_state.calc_event_data['Mercado']:
            initial_calc_market_index = 1
        elif "Totales" in st.session_state.calc_event_data['Mercado']:
            initial_calc_market_index = 2
        elif "Spreads" in st.session_state.calc_event_data['Mercado']:
            initial_calc_market_index = 3

        calc_market_option = st.selectbox(
            "Tipo de Mercado:",
            ["Ganador (2 Resultados)", "Ganador (1x2)", "Totales (Over/Under)", "Spreads (Hándicap)"],
            index=initial_calc_market_index,
            key="calc_market_type"
        )
        
        presupuesto = st.number_input("Presupuesto total para la apuesta (ej: 100000 COP):", min_value=1000, value=100000, step=10000, format="%d")
        
        # Selección de divisa
        moneda_seleccionada = st.selectbox(
            "Selecciona la divisa para las casas de apuestas:",
            list(casas_predefinidas_manual.keys()),
            index=list(casas_predefinidas_manual.keys()).index(st.session_state.last_moneda_manual),
            key="calc_currency"
        )
        
        # Si la moneda cambia, actualiza las casas predeterminadas
        if moneda_seleccionada != st.session_state.last_moneda_manual:
            st.session_state.nombres_casas_manual = casas_predefinidas_manual[moneda_seleccionada]
            st.session_state.cuotas_local_manual = [1.01] * len(st.session_state.nombres_casas_manual)
            st.session_state.cuotas_empate_manual = [1.01] * len(st.session_state.nombres_casas_manual)
            st.session_state.cuotas_visitante_manual = [1.01] * len(st.session_state.nombres_casas_manual)
            st.session_state.last_moneda_manual = moneda_seleccionada # Actualiza la última moneda seleccionada
            st.experimental_rerun() # Rerun para que los campos se actualicen
            
        # Cuotas de la surebet cargada se inicializan aquí
        # La lógica para 'default_cuota_empate', 'default_sel_empate', 'default_casa_empate'
        # dependerá del 'calc_market_option' que el usuario seleccione.
        # Por defecto, se usa el valor cargado de session_state, si aplica.
        default_cuota_local = st.session_state.calc_event_data['Cuota Local']
        default_cuota_empate = st.session_state.calc_event_data['Cuota Empate']
        default_cuota_visitante = st.session_state.calc_event_data['Cuota Visitante']
        default_sel_local = st.session_state.calc_event_data['Selección 1']
        default_sel_empate = st.session_state.calc_event_data['Selección X']
        default_sel_visitante = st.session_state.calc_event_data['Selección 2']
        default_casa_local = st.session_state.calc_event_data['Casa Local']
        default_casa_empate = st.session_state.calc_event_data['Casa Empate']
        default_casa_visitante = st.session_state.calc_event_data['Casa Visitante']


    with col_input2:
        st.subheader("Ingreso Manual de Cuotas")

        if calc_market_option == "Ganador (1x2)":
            st.text_input("Nombre Equipo Local / Selección 1", value=default_sel_local, key="manual_sel1")
            cuota_local = st.number_input("Mejor Cuota Local:", min_value=1.01, value=default_cuota_local, step=0.01, format="%.2f", key="manual_cuota_local")
            st.text_input("Casa de Apuestas Local:", value=default_casa_local, key="manual_casa_local")
            
            st.text_input("Nombre Empate / Selección X", value=default_sel_empate, key="manual_selX")
            cuota_empate = st.number_input("Mejor Cuota Empate:", min_value=1.01, value=default_cuota_empate, step=0.01, format="%.2f", key="manual_cuota_empate")
            st.text_input("Casa de Apuestas Empate:", value=default_casa_empate, key="manual_casa_empate")
            
            st.text_input("Nombre Equipo Visitante / Selección 2", value=default_sel_visitante, key="manual_sel2")
            cuota_visitante = st.number_input("Mejor Cuota Visitante:", min_value=1.01, value=default_cuota_visitante, step=0.01, format="%.2f", key="manual_cuota_visitante")
            st.text_input("Casa de Apuestas Visitante:", value=default_casa_visitante, key="manual_casa_visitante")

            if st.button("Calcular Surebet 1x2"):
                # Para la calculadora manual, asumimos que el usuario sabe lo que hace y no validamos casas distintas aquí.
                stake_local, stake_empate, stake_visitante, ganancia, roi, c_local, c_empate, c_visitante = \
                    calcular_surebet_3_resultados(cuota_local, cuota_empate, cuota_visitante, presupuesto)
                
                if roi is not None:
                    st.success(f"¡Surebet encontrada! ROI: **{roi:.2f}%**")
                    st.write(f"**Apostar {moneda_seleccionada} {stake_local:,}** en **{st.session_state.manual_sel1}** (Cuota: {c_local}) en **{st.session_state.manual_casa_local}**")
                    st.write(f"**Apostar {moneda_seleccionada} {stake_empate:,}** en **{st.session_state.manual_selX}** (Cuota: {c_empate}) en **{st.session_state.manual_casa_empate}**")
                    st.write(f"**Apostar {moneda_seleccionada} {stake_visitante:,}** en **{st.session_state.manual_sel2}** (Cuota: {c_visitante}) en **{st.session_state.manual_casa_visitante}**")
                    st.write(f"**Ganancia Mínima Garantizada:** {moneda_seleccionada} {ganancia:,}")
                else:
                    st.warning("No se encontró una surebet con las cuotas ingresadas para 3 resultados.")

        else: # Para 2 resultados (H2H sin empate, Totales, Spreads)
            st.text_input("Nombre Selección 1", value=default_sel_local, key="manual_sel1_2")
            cuota_local = st.number_input("Mejor Cuota Selección 1:", min_value=1.01, value=default_cuota_local, step=0.01, format="%.2f", key="manual_cuota_local_2")
            st.text_input("Casa de Apuestas Selección 1:", value=default_casa_local, key="manual_casa_local_2")

            st.text_input("Nombre Selección 2", value=default_sel_visitante, key="manual_sel2_2")
            cuota_visitante = st.number_input("Mejor Cuota Selección 2:", min_value=1.01, value=default_cuota_visitante, step=0.01, format="%.2f", key="manual_cuota_visitante_2")
            st.text_input("Casa de Apuestas Selección 2:", value=default_casa_visitante, key="manual_casa_visitante_2")

            if st.button("Calcular Surebet 2 Resultados"):
                # Para la calculadora manual, asumimos que el usuario sabe lo que hace y no validamos casas distintas aquí.
                stake1, stake2, ganancia, roi, c1, c2 = calcular_surebet_2_resultados(cuota_local, cuota_visitante, presupuesto)
                
                if roi is not None:
                    st.success(f"¡Surebet encontrada! ROI: **{roi:.2f}%**")
                    st.write(f"**Apostar {moneda_seleccionada} {stake1:,}** en **{st.session_state.manual_sel1_2}** (Cuota: {c1}) en **{st.session_state.manual_casa_local_2}**")
                    st.write(f"**Apostar {moneda_seleccionada} {stake2:,}** en **{st.session_state.manual_sel2_2}** (Cuota: {c2}) en **{st.session_state.manual_casa_visitante_2}**")
                    st.write(f"**Ganancia Mínima Garantizada:** {moneda_seleccionada} {ganancia:,}")
                else:
                    st.warning("No se encontró una surebet con las cuotas ingresadas para 2 resultados.")
