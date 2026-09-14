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

# Lista ordenada de referencias por kilometro a lo largo del tramo
# Mexico-Puebla (km 0 a km ~125). Cada entrada:
#   km: kilometraje aproximado sobre el tramo
#   nombre: nombre de la referencia (caseta o entronque)
#   tipo: "caseta" o "entronque"
#   lat/lon: coordenadas aproximadas
REFERENCIAS_KM = [
    {
        "km": 0, "nombre": "La Concordia (inicio de cuota, CDMX)",
        "tipo": "entronque", "lat": 19.3587, "lon": -98.9977,
    },
    {
        "km": 17, "nombre": "Entronque La Concordia / Ixtapaluca",
        "tipo": "entronque", "lat": 19.3220, "lon": -98.9250,
    },
    {
        "km": 19, "nombre": "Caseta Ixtapaluca",
        "tipo": "caseta", "lat": 19.2904, "lon": -98.8797,
    },
    {
        "km": 25, "nombre": "Caseta Chalco",
        "tipo": "caseta", "lat": 19.3578, "lon": -98.9944,
    },
    {
        "km": 32, "nombre": "Entronque Fed. 115 (Chalco)",
        "tipo": "entronque", "lat": 19.3100, "lon": -98.8700,
    },
    {
        "km": 32.5, "nombre": "Circuito Exterior Mexiquense (Mex 5D)",
        "tipo": "entronque", "lat": 19.3080, "lon": -98.8650,
    },
    {
        "km": 34, "nombre": "Caseta San Marcos BIS - Circuito Exterior Mexiquense",
        "tipo": "caseta", "lat": 19.3077, "lon": -98.8814,
    },
    {
        "km": 63, "nombre": "Rio Frio de Juarez (entronque Fed. 150)",
        "tipo": "entronque", "lat": 19.3350, "lon": -98.7150,
    },
    {
        "km": 86, "nombre": "Caseta San Marcos",
        "tipo": "caseta", "lat": 19.3085, "lon": -98.8329,
    },
