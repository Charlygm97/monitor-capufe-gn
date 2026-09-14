# -*- coding: utf-8 -*-
"""
Diccionario de referencia: kilometros y casetas de la Autopista
Mexico-Puebla (Carretera Federal 150D, tramo Mexico-Puebla).

Fuente: Wikipedia (marcadores de kilometro de entronques) + casetas.com.mx
(nombres y ubicacion aproximada de las 6 casetas del tramo).

IMPORTANTE: Las coordenadas son APROXIMADAS (ubicacion de la caseta o del
entronque mas cercano, tomadas de fuentes publicas, no de CAPUFE
directamente). Sirven para ubicar un evento "en la zona correcta" sobre
un mapa, no para precision de metros. Conviene validarlas/afinarlas con
tiempo si se van a cruzar con la ubicacion exacta de las 30 camaras.

El punto de partida (km 0) se toma como el inicio del tramo de cuota en
La Concordia, Ciudad de Mexico.
"""

REFERENCIAS_KM = [
    {"km": 0, "nombre": "La Concordia (inicio de cuota, CDMX)", "tipo": "entronque", "lat": 19.3587, "lon": -98.9977},
    {"km": 17, "nombre": "Entronque La Concordia / Ixtapaluca", "tipo": "entronque", "lat": 19.3220, "lon": -98.9250},
    {"km": 19, "nombre": "Caseta Ixtapaluca", "tipo": "caseta", "lat": 19.2904, "lon": -98.8797},
    {"km": 25, "nombre": "Caseta Chalco", "tipo": "caseta", "lat": 19.3578, "lon": -98.9944},
    {"km": 32, "nombre": "Entronque Fed. 115 (Chalco)", "tipo": "entronque", "lat": 19.3100, "lon": -98.8700},
    {"km": 32.5, "nombre": "Circuito Exterior Mexiquense (Mex 5D)", "tipo": "entronque", "lat": 19.3080, "lon": -98.8650},
    {"km": 34, "nombre": "Caseta San Marcos BIS - Circuito Exterior Mexiquense", "tipo": "caseta", "lat": 19.3077, "lon": -98.8814},
    {"km": 63, "nombre": "Rio Frio de Juarez (entronque Fed. 150)", "tipo": "entronque", "lat": 19.3350, "lon": -98.7150},
    {"km": 86, "nombre": "Caseta San Marcos", "tipo": "caseta", "lat": 19.3085, "lon": -98.8329},
    {"km": 88, "nombre": "Caseta San Marcos - San Martin Texmelucan", "tipo": "caseta", "lat": 19.3050, "lon": -98.8421},
    {"km": 92, "nombre": "San Martin Texmelucan (entronque Arco Norte / Fed. 57D)", "tipo": "entronque", "lat": 19.2850, "lon": -98.4550},
    {"km": 95, "nombre": "Caseta San Martin", "tipo": "caseta", "lat": 19.2850, "lon": -98.4450},
    {"km": 101, "nombre": "Acceso Aeropuerto Internacional de Puebla", "tipo": "entronque", "lat": 19.1500, "lon": -98.3750},
    {"km": 114, "nombre": "Entronque Anillo Periferico Ecologico / Puebla-Tlaxcala (fin de tramo)", "tipo": "entronque", "lat": 19.0810, "lon": -98.2670},
]


def km_a_referencia(km):
    if km is None or km == "":
        return None
    km_str = str(km).replace("+", ".")
    try:
        km_num = float(km_str)
    except ValueError:
        return None
    mas_cercana = min(REFERENCIAS_KM, key=lambda r: abs(r["km"] - km_num))
    return mas_cercana


if __name__ == "__main__":
    for prueba in ["32+200", "63", "8", "120"]:
        ref = km_a_referencia(prueba)
        print(f"km {prueba} -> {ref['nombre']} ({ref['lat']}, {ref['lon']})")
