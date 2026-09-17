# -*- coding: utf-8 -*-
"""
Script de PRUEBA: envia una notificacion push de ejemplo para confirmar
que la configuracion (VAPID_PRIVATE_KEY + PUSH_SUBSCRIPTION) funciona,
sin depender de que haya un evento real de CAPUFE/GN en este momento.

Uso: python probar_push.py
Requiere las mismas variables de entorno que el monitor principal:
VAPID_PRIVATE_KEY y PUSH_SUBSCRIPTION.
"""

import json
import os
import sys

from pywebpush import webpush, WebPushException

VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
PUSH_SUBSCRIPTION_JSON = os.environ.get("PUSH_SUBSCRIPTION", "")
VAPID_CLAIMS = {"sub": "mailto:notificaciones@monitor-capufe-gn.local"}


def main():
    if not VAPID_PRIVATE_KEY or not PUSH_SUBSCRIPTION_JSON:
        print("[ERROR] Faltan VAPID_PRIVATE_KEY o PUSH_SUBSCRIPTION en el entorno.")
        sys.exit(1)

    try:
        subscription_info = json.loads(PUSH_SUBSCRIPTION_JSON)
    except json.JSONDecodeError:
        print("[ERROR] PUSH_SUBSCRIPTION no es un JSON valido.")
        sys.exit(1)

    payload = {
        "title": "🚨 Notificación de prueba",
        "body": "Si ves esto en tu celular, las notificaciones push ya funcionan correctamente.",
        "url": ".",
    }

    try:
        webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=dict(VAPID_CLAIMS),
        )
        print("[OK] Notificacion de prueba enviada correctamente.")
    except WebPushException as e:
        print(f"[ERROR] No se pudo enviar la notificacion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
