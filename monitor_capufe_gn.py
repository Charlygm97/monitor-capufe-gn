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
    pip install requests pandas openpyxl pywebpush

Uso:
    python monitor_capufe_gn.py
"""

import json
import os
import re
import sys
import unicodedata
from datetime import datetime

import pandas as pd
import requests

from casetas_mexico_puebla import km_a_referencia

# --------------------------------------------------------------------------
# CONFIGURACION
# --------------------------------------------------------------------------

CUENTAS = ["CAPUFE", "GN_Carreteras"]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARCHIVO_VISTOS = os.path.join(BASE_DIR, "tweets_vistos.json")
ARCHIVO_EXCEL = os.path.join(BASE_DIR, "eventos_mexico_puebla.xlsx")
ARCHIVO_LOG = os.path.join(BASE_DIR, "monitor_log.txt")

ARCHIVO_JSON_DASHBOARD = os.path.join(BASE_DIR, "..", "docs", "data", "eventos.json")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
PUSH_SUBSCRIPTION_JSON = os.environ.get("PUSH_SUBSCRIPTION", "")
VAPID_CLAIMS = {"sub": "mailto:notificaciones@monitor-capufe-gn.local"}

# Palabras clave para filtrar solo lo relevante al tramo Mexico-Puebla.
# Se comparan de forma normalizada (sin acentos, espacios ni guiones), asi
# que "Mexico-Puebla", "Mexico Puebla" y "#AutMexicoPuebla" hacen match
# igual. Se puede ampliar segun se detecten mas nombres de referencia.
PALABRAS_CLAVE_TRAMO = [
    "mexico-puebla",
    "autopista 150",
    "rio frio",
    "amozoc",
    "chalco",
    "san martin texmelucan",
    "ciudad mendoza",
]

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


def log(mensaje):
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


def obtener_tweets_cuenta(handle):
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{handle}"

    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
    except requests.RequestException as e:
        log(f"[ERROR] No se pudo contactar el endpoint para @{handle}: {e}")
        return []

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


def _normalizar(texto):
    """Quita acentos, mayusculas, espacios y guiones para poder comparar
    'Mexico-Puebla', 'Mexico Puebla' y '#AutMexicoPuebla' como si fueran
    lo mismo."""
    texto = texto.lower()
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9]", "", texto)
    return texto


PALABRAS_CLAVE_NORMALIZADAS = [_normalizar(p) for p in PALABRAS_CLAVE_TRAMO]


def es_relevante_tramo(texto):
    texto_normalizado = _normalizar(texto)
    return any(palabra in texto_normalizado for palabra in PALABRAS_CLAVE_NORMALIZADAS)


def clasificar_tipo_evento(texto):
    texto_normalizado = texto.lower()
    for tipo, palabras in TIPOS_EVENTO.items():
        if any(p in texto_normalizado for p in palabras):
            return tipo
    return "otro"


def extraer_km(texto):
    match = re.search(r"km[.\s]*([\d]+(?:\+\d+)?)", texto, re.IGNORECASE)
    return match.group(1) if match else ""


def extraer_sentido(texto):
    match = re.search(r"direcci[oó]n\s+([A-Za-zÀ-ÿ\s]+?)(?:[.,]|$)", texto, re.IGNORECASE)
    return match.group(1).strip() if match else ""


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


def notificar_telegram(evento):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return

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


def notificar_push(evento):
    """Envia una notificacion push directamente a la app instalada en el
    celular (vía el navegador), usando el estandar Web Push + VAPID.
    No falla el script si no esta configurado; solo lo omite."""
    if not VAPID_PRIVATE_KEY or not PUSH_SUBSCRIPTION_JSON:
        return

    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        log("[AVISO] pywebpush no esta instalado, se omite notificacion push.")
        return

    try:
        subscription_info = json.loads(PUSH_SUBSCRIPTION_JSON)
    except json.JSONDecodeError:
        log("[AVISO] PUSH_SUBSCRIPTION no es JSON valido, se omite notificacion push.")
        return

    emoji_por_tipo = {
        "accidente": "🚨", "incendio": "🔥", "robo": "🚔",
        "manifestacion": "✊", "cierre_circulacion": "🟠",
        "restablecimiento": "🟢", "otro": "ℹ️",
    }
    emoji = emoji_por_tipo.get(evento["tipo_evento"], "ℹ️")

    payload = {
        "title": f"{emoji} {evento['tipo_evento'].replace('_', ' ').upper()} · México-Puebla",
        "body": evento["texto_original"][:180],
        "url": evento["url"],
    }

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=dict(VAPID_CLAIMS),
        )
    except WebPushException as e:
        log(f"[AVISO] No se pudo enviar notificacion push: {e}")


def exportar_json_dashboard():
    if not os.path.exists(ARCHIVO_EXCEL):
        return

    df = pd.read_excel(ARCHIVO_EXCEL)
    df = df.sort_values("fecha_deteccion", ascending=False)

    os.makedirs(os.path.dirname(ARCHIVO_JSON_DASHBOARD), exist_ok=True)
    df.to_json(ARCHIVO_JSON_DASHBOARD, orient="records", force_ascii=False, indent=2)


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
            notificar_push(evento)
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
