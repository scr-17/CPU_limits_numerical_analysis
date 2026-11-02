"""Búsqueda de intervalos y método de bisección."""


def buscar_intervalo_cambio_signo(funcion, inicio=0.05, fin=1.0, paso=0.05):
    """Busca un subintervalo con cambio de signo recorriendo [inicio, fin]."""
    if paso <= 0 or inicio >= fin:
        raise ValueError("El intervalo y el paso de búsqueda deben ser válidos.")

    anterior = inicio
    valor_anterior = funcion(anterior)
    if valor_anterior == 0:
        return anterior, anterior

    cantidad = int((fin - inicio) / paso + 1e-12)
    for indice in range(1, cantidad + 1):
        actual = min(inicio + indice * paso, fin)
        valor_actual = funcion(actual)
        if valor_actual == 0:
            return actual, actual
        if valor_anterior * valor_actual < 0:
            return anterior, actual
        anterior, valor_anterior = actual, valor_actual
    return None


def biseccion(funcion, inferior, superior, tolerancia, max_iter=80):
    f_inferior = funcion(inferior)
    f_superior = funcion(superior)
    if f_inferior == 0:
        return {
            "raiz": inferior,
            "iteraciones": [],
            "detalle": [],
            "error_aproximado": 0.0,
        }
    if f_superior == 0:
        return {
            "raiz": superior,
            "iteraciones": [],
            "detalle": [],
            "error_aproximado": 0.0,
        }
    if f_inferior * f_superior > 0:
        raise ValueError("El intervalo debe contener un cambio de signo.")

    anterior = None
    filas = []
    detalle = []
    for paso in range(max_iter):
        medio = (inferior + superior) / 2.0
        f_medio = funcion(medio)
        error = None if anterior is None else (
            abs((medio - anterior) / medio) * 100.0 if medio else abs(medio - anterior) * 100.0
        )
        filas.append((paso + 1, inferior, superior, medio, f_medio, error))
        if abs(f_medio) <= 1e-12:
            decision = "La estimación llegó a la raíz."
        elif f_inferior * f_medio < 0:
            decision = "La raíz está entre L inferior y L medio."
        else:
            decision = "La raíz está entre L medio y L superior."
        detalle.append({
            "paso": paso + 1,
            "inferior": inferior,
            "f_inferior": f_inferior,
            "superior": superior,
            "f_superior": f_superior,
            "medio": medio,
            "f_medio": f_medio,
            "error": error,
            "decision": decision,
        })
        if abs(f_medio) <= 1e-12 or (error is not None and error <= tolerancia):
            detalle[-1]["decision"] = (
                "La estimación llegó a la raíz."
                if abs(f_medio) <= 1e-12
                else "El cambio entre estimaciones ya está dentro de la tolerancia."
            )
            return {
                "raiz": medio,
                "iteraciones": filas,
                "detalle": detalle,
                "error_aproximado": abs(superior - inferior) / 2.0,
            }
        if f_inferior * f_medio < 0:
            superior, f_superior = medio, f_medio
        else:
            inferior, f_inferior = medio, f_medio
        anterior = medio
    return {
        "raiz": (inferior + superior) / 2.0,
        "iteraciones": filas,
        "detalle": detalle,
        "error_aproximado": abs(superior - inferior) / 2.0,
    }
