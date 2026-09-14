# -*- coding: utf-8 -*-
"""
Monitor de eventos carreteros - CAPUFE y Guardia Nacional Carreteras
======================================================================
Monitorea las cuentas @CAPUFE y @GN_Carreteras en X (Twitter) usando el
endpoint publico de sindicacion (el mismo que usa X para insertar
timelines embebidos en paginas web). No requiere login, cookies ni API key.

IMPORTANTE - Naturaleza del metodo:
Este endpoint no es una API oficial de X, es una interfaz interna que X
usa para widgets embebidos. Puede cambiar de formato o dejar de responder
sin previo aviso. Este script esta escrito para fallar de forma visible
(avisando en consola/log) en vez de fallar en silencio, para que sea facil
notar si X lo bloqueo y hay que ajustar el metodo de obtencion.

Requiere:
    pip install requests pandas openpyxl

Uso:
    python monitor_capufe_gn.py

Se puede programar para correr cada 5-10 minutos con el Programador de
tareas de Windows (ver ejecutar_monitor.bat incluido).
"""

import json
import os
import re
import sys
from datetime import datetime

import pandas as pd
import requests

from casetas_mexico_puebla import km_a_referencia

# --------------------------------------------------------------------------
# CONFIGURACION
# --------------------------------------------------------------------------

CUENTAS = ["CAPUFE", "GN_Carreteras"]

# Carpeta donde vive este script (para que funcione sin importar desde
# donde se ejecute, ej. desde una tarea programada)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_VISTOS = os.path.join(BASE_DIR, "tweets_vistos.json")
ARCHIVO_EXCEL = os.path.join(BASE_DIR, "eventos_mexico_puebla.xlsx")
ARCHIVO_LOG = os.path.join(BASE_DIR, "monitor_log.txt")

# JSON que lee el dashboard web (docs/data/eventos.json para GitHub Pages)
ARCHIVO_JSON_DASHBOARD = os.path.join(BASE_DIR, "..", "docs", "data", "eventos.json")

# Credenciales de Telegram (se configuran como variables de entorno /
# secrets de GitHub Actions, nunca escritas aqui directamente)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# Palabras clave para filtrar solo lo relevante al tramo Mexico-Puebla.
# Se puede ampliar segun se detecten mas nombres de referencia del tramo.
PALABRAS_CLAVE_TRAMO = [
    "mexico-puebla", "méxico-puebla", "mexico - puebla", "méxico - puebla",
    "autopista 150", "autopista (150)", "rio frio", "río frío",
    "amozoc", "chalco", "san martin texmelucan", "san martín texmelucan",
    "ciudad mendoza",  # ajustar/ampliar segun casetas reales del tramo
]

# Clasificacion simple por palabras clave (se puede ampliar)
TIPOS_EVENTO = {
    "accidente": ["accidente", "colision", "colisión", "volcadura", "choque"],
    "incendio": ["incendio", "fuego", "quema"],
    "robo": ["robo", "asalto"],
    "manifestacion": ["manifestacion", "manifestación", "bloqueo", "cierre por"],
    "cierre_circulacion": ["cierre parcial", "cierre total", "cierre de circulacion", "cierre de circulación"],
    "restablecimiento": ["restablecimiento", "circulacion normal", "circulación normal", "tramo opera de manera normal"],
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

TIMEOUT_SEGUNDOS = 15


# --------------------------------------------------------------------------
# UTILIDADES
# --------------------------------------------------------------------------

def log(mensaje):
    """Escribe un mensaje con timestamp a consola y a un archivo de log."""
    linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {mensaje}"
    print(linea)
    with open(ARCHIVO_LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def cargar_vistos():
    if os.path.exists(ARCHIVO_VISTOS):
        with open(ARCHIVO_VISTOS, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def guardar_vistos(vistos):
    with open(ARCHIVO_VISTOS, "w", encoding="utf-8") as f:
        json.dump(list(vistos), f)


# --------------------------------------------------------------------------
# OBTENCION DE TWEETS (endpoint de sindicacion, sin login)
# --------------------------------------------------------------------------

def obtener_tweets_cuenta(handle):
    """
    Obtiene los tweets recientes de una cuenta publica usando el endpoint
    de sindicacion de X (el que usa X para widgets embebidos).

    Devuelve una lista de dicts: {id, texto, fecha, url}
    Si el endpoint no responde con el formato esperado, regresa lista vacia
    y deja un aviso claro en el log (para detectar si X cambio el formato).
    """
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
    except requests.RequestException as e:
        log(f"[ERROR] No se pudo contactar el endpoint para @{handle}: {e}")
        return []

    # El HTML de respuesta trae un bloque <script id="__NEXT_DATA__"> con
    # un JSON que incluye los tweets. Si X cambia esta estructura, esta
    # busqueda dejara de encontrar coincidencias y se avisa en el log.
    match = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        resp.text,
        re.DOTALL,
    )
    if not match:
        log(
            f"[AVISO] El formato de respuesta para @{handle} no es el esperado "
            f"(no se encontro __NEXT_DATA__). Es posible que X haya cambiado "
            f"el endpoint. Revisar manualmente."
        )
        return []

    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        log(f"[ERROR] No se pudo parsear el JSON de @{handle}: {e}")
        return []

    # La ruta exacta dentro del JSON puede variar; se intenta de forma
    # defensiva y se avisa si no se encuentra nada util.
    tweets_crudos = _buscar_lista_tweets(data)

    if not tweets_crudos:
        log(
            f"[AVISO] Se obtuvo respuesta de @{handle} pero no se encontraron "
            f"tweets dentro del JSON. Revisar estructura manualmente "
            f"(guardado en debug_{handle}.json)."
        )
        with open(os.path.join(BASE_DIR, f"debug_{handle}.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return []

    tweets = []
    for t in tweets_crudos:
        try:
            tweets.append({
                "id": str(t.get("id_str") or t.get("id")),
                "texto": t.get("text") or t.get("full_text") or "",
                "fecha": t.get("created_at", ""),
                "url": f"https://x.com/{handle}/status/{t.get('id_str') or t.get('id')}",
                "cuenta": handle,
            })
        except Exception:
            continue

    return tweets


def _buscar_lista_tweets(data):
    """
    Busca de forma recursiva y defensiva una lista de objetos que parezcan
    tweets dentro del JSON de __NEXT_DATA__. Esto es necesario porque la
    ruta exacta (props.pageProps.timeline...) puede variar entre versiones.
    """
    encontrados = []

    def es_tweet(obj):
        return isinstance(obj, dict) and ("full_text" in obj or "text" in obj) and (
            "id_str" in obj or "id" in obj
        )

    def recorrer(obj):
        if isinstance(obj, dict):
            if es_tweet(obj):
                encontrados.append(obj)
            for v in obj.values():
                recorrer(v)
        elif isinstance(obj, list):
            for item in obj:
                recorrer(item)

    recorrer(data)
    return encontrados


# --------------------------------------------------------------------------
# FILTRADO Y CLASIFICACION
# --------------------------------------------------------------------------

def es_relevante_tramo(texto):
    texto_normalizado = texto.lower()
    return any(palabra in texto_normalizado for palabra in PALABRAS_CLAVE_TRAMO)


def clasificar_tipo_evento(texto):
    texto_normalizado = texto.lower()
    for tipo, palabras in TIPOS_EVENTO.items():
        if any(p in texto_normalizado for p in palabras):
            return tipo
    return "otro"


def extraer_km(texto):
    """Intenta extraer un numero de kilometro del texto, ej. 'km 032+200'."""
    match = re.search(r"km[.\s]*([\d]+(?:\+\d+)?)", texto, re.IGNORECASE)
    return match.group(1) if match else ""


def extraer_sentido(texto):
    match = re.search(r"direcci[oó]n\s+([A-Za-zÀ-ÿ\s]+?)(?:[.,]|$)", texto, re.IGNORECASE)
    return match.group(1).strip() if match else ""


# --------------------------------------------------------------------------
# GUARDADO EN EXCEL
# --------------------------------------------------------------------------

def guardar_eventos_excel(eventos_nuevos):
    columnas = [
        "fecha_deteccion", "cuenta", "tipo_evento", "km", "sentido",
        "referencia_cercana", "lat_aprox", "lon_aprox",
        "texto_original", "url",
    ]

    df_nuevos = pd.DataFrame(eventos_nuevos, columns=columnas)

    if os.path.exists(ARCHIVO_EXCEL):
        df_existente = pd.read_excel(ARCHIVO_EXCEL)
        df_final = pd.concat([df_existente, df_nuevos], ignore_index=True)
    else:
        df_final = df_nuevos

    df_final.to_excel(ARCHIVO_EXCEL, index=False)


# --------------------------------------------------------------------------
# NOTIFICACIONES (Telegram)
# --------------------------------------------------------------------------

def notificar_telegram(evento):
    """Envia una notificacion al celular via Telegram. No falla el script
    si Telegram no esta configurado o no responde; solo lo avisa en log."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return  # Telegram no configurado, se omite silenciosamente

    emoji_por_tipo = {
        "accidente": "🚨", "incendio": "🔥", "robo": "🚔",
        "manifestacion": "✊", "cierre_circulacion": "🟠",
        "restablecimiento": "🟢", "otro": "ℹ️",
    }
    emoji = emoji_por_tipo.get(evento["tipo_evento"], "ℹ️")

    texto = (
        f"{emoji} *{evento['tipo_evento'].replace('_', ' ').upper()}*\n"
        f"México-Puebla"
        f"{' · km ' + evento['km'] if evento['km'] else ''}"
        f"{' · direccion ' + evento['sentido'] if evento['sentido'] else ''}\n"
        f"{'📍 ' + evento['referencia_cercana'] if evento.get('referencia_cercana') else ''}\n\n"
        f"{evento['texto_original']}\n\n"
        f"{evento['url']}"
    )

    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": texto, "parse_mode": "Markdown"},
            timeout=10,
        )
    except requests.RequestException as e:
        log(f"[AVISO] No se pudo enviar notificacion de Telegram: {e}")


# --------------------------------------------------------------------------
# EXPORTACION PARA EL DASHBOARD WEB
# --------------------------------------------------------------------------

def exportar_json_dashboard():
    """Exporta todos los eventos acumulados a JSON para que el dashboard
    web (GitHub Pages) los lea y los muestre en el celular."""
    if not os.path.exists(ARCHIVO_EXCEL):
        return

    df = pd.read_excel(ARCHIVO_EXCEL)
    df = df.sort_values("fecha_deteccion", ascending=False)

    os.makedirs(os.path.dirname(ARCHIVO_JSON_DASHBOARD), exist_ok=True)
    df.to_json(ARCHIVO_JSON_DASHBOARD, orient="records", force_ascii=False, indent=2)


# --------------------------------------------------------------------------
# FLUJO PRINCIPAL
# --------------------------------------------------------------------------

def main():
    log("=== Iniciando corrida de monitoreo ===")
    vistos = cargar_vistos()
    eventos_nuevos = []

    for handle in CUENTAS:
        tweets = obtener_tweets_cuenta(handle)
        log(f"@{handle}: {len(tweets)} tweets obtenidos")

        for t in tweets:
            if t["id"] in vistos:
                continue
            vistos.add(t["id"])

            if not es_relevante_tramo(t["texto"]):
                continue

            km_detectado = extraer_km(t["texto"])
            referencia = km_a_referencia(km_detectado)

            eventos_nuevos.append({
                "fecha_deteccion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cuenta": t["cuenta"],
                "tipo_evento": clasificar_tipo_evento(t["texto"]),
                "km": km_detectado,
                "sentido": extraer_sentido(t["texto"]),
                "referencia_cercana": referencia["nombre"] if referencia else "",
                "lat_aprox": referencia["lat"] if referencia else "",
                "lon_aprox": referencia["lon"] if referencia else "",
                "texto_original": t["texto"],
                "url": t["url"],
            })

    if eventos_nuevos:
        guardar_eventos_excel(eventos_nuevos)
        log(f"Se detectaron {len(eventos_nuevos)} eventos nuevos relevantes a Mexico-Puebla. Guardados en {ARCHIVO_EXCEL}")
        for evento in eventos_nuevos:
            notificar_telegram(evento)
    else:
        log("No se detectaron eventos nuevos relevantes en esta corrida.")

    exportar_json_dashboard()
    guardar_vistos(vistos)
    log("=== Corrida finalizada ===\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"[ERROR FATAL] {e}")
        sys.exit(1)
