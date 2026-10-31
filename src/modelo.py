"""Valores predeterminados del modelo térmico."""

PARAMETROS_DEFECTO = {
    "T_ambiente": 25.0,
    "T_inicial": 40.0,
    "alfa": 0.027,
    "k": 0.03,
    "T_objetivo": 80.0,
}

DATOS_EJEMPLO = {
    "tiempo": [0.0, 30.0, 60.0, 90.0],
    "uso": [40.0, 85.0, 100.0, 90.0],
    "paso": 30.0,
    "paso_fino": 0.5,
    "tolerancia": 0.5,
    "intervalo": (0.5, 1.0),
    "busqueda_minima": 0.05,
    "paso_busqueda": 0.05,
}
