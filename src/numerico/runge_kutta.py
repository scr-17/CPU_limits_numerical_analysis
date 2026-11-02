"""Modelo térmico e integración Runge-Kutta de cuarto orden."""

from .polinomio import evaluar_polinomio


def crear_funcion(limite_rendimiento, parametros, coeficientes):
    def ecuacion_diferencial(tiempo, temperatura):
        carga_equipo = max(0.0, min(100.0, evaluar_polinomio(coeficientes, tiempo)))
        calor_generado = parametros["alfa"] * limite_rendimiento * carga_equipo
        diferencia = temperatura - parametros["T_ambiente"]
        calor_disipado = parametros["k"] * diferencia
        return calor_generado - calor_disipado

    return ecuacion_diferencial


def runge_kutta(funcion, x_inicial, y_inicial, x_final, paso):
    if paso <= 0:
        raise ValueError("El paso de integración debe ser positivo.")
    cantidad = max(1, round(abs(x_final - x_inicial) / paso))
    paso_efectivo = (x_final - x_inicial) / cantidad
    xs = [float(x_inicial)]
    ys = [float(y_inicial)]

    for _ in range(cantidad):
        x, y = xs[-1], ys[-1]
        h = paso_efectivo
        k1 = funcion(x, y)
        k2 = funcion(x + h / 2, y + h * k1 / 2)
        k3 = funcion(x + h / 2, y + h * k2 / 2)
        k4 = funcion(x + h, y + h * k3)
        xs.append(x + h)
        ys.append(y + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6)
    return xs, ys


def runge_kutta_detallado(funcion, x_inicial, y_inicial, x_final, paso):
    """Devuelve cada paso RK4 con sus cuatro pendientes intermedias."""
    xs, ys = runge_kutta(funcion, x_inicial, y_inicial, x_final, paso)
    filas = []
    for indice in range(len(xs) - 1):
        x, y = xs[indice], ys[indice]
        h = xs[indice + 1] - x
        k1 = funcion(x, y)
        k2 = funcion(x + h / 2, y + h * k1 / 2)
        k3 = funcion(x + h / 2, y + h * k2 / 2)
        k4 = funcion(x + h, y + h * k3)
        filas.append({
            "paso": indice + 1,
            "t": x,
            "h": h,
            "T": y,
            "k1": k1,
            "k2": k2,
            "k3": k3,
            "k4": k4,
            "T_siguiente": ys[indice + 1],
        })
    return xs, ys, filas


def minuto_cruce_meta(tiempos, temperaturas, meta):
    """Estima por interpolación lineal el primer cruce ascendente de la meta."""
    if not tiempos or len(tiempos) != len(temperaturas):
        raise ValueError("Se requieren tiempos y temperaturas correspondientes.")
    if temperaturas[0] >= meta:
        return tiempos[0]
    for indice in range(1, len(tiempos)):
        anterior = temperaturas[indice - 1]
        actual = temperaturas[indice]
        if anterior < meta <= actual:
            diferencia = actual - anterior
            if abs(diferencia) < 1e-14:
                return tiempos[indice]
            fraccion = (meta - anterior) / diferencia
            return tiempos[indice - 1] + fraccion * (tiempos[indice] - tiempos[indice - 1])
    return None
