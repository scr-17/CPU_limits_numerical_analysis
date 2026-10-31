"""Evaluación y formato de polinomios con coeficientes ascendentes."""


def evaluar_polinomio(coeficientes, x):
    total = 0.0
    for coeficiente in reversed(coeficientes):
        total = total * x + coeficiente
    return total


def formatear_polinomio(coeficientes, cifras_significativas=8):
    terminos = []
    for grado, coeficiente in enumerate(coeficientes):
        if abs(coeficiente) < 1e-12:
            continue
        variable = "" if grado == 0 else ("t" if grado == 1 else f"t^{grado}")
        magnitud = format(abs(coeficiente), f".{cifras_significativas}g")
        termino = f"{magnitud}{variable}"
        if not terminos:
            terminos.append(("-" if coeficiente < 0 else "") + termino)
        else:
            terminos.append((" - " if coeficiente < 0 else " + ") + termino)
    return "P(t) = " + ("".join(terminos) if terminos else "0")
