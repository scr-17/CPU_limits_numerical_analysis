"""Interpolación polinómica mediante eliminación de Gauss-Jordan."""


def polinomio_unico(xs, ys):
    if len(xs) != len(ys):
        raise ValueError("Debe haber la misma cantidad de tiempos y usos.")
    if len(xs) < 2:
        raise ValueError("Se requieren al menos dos mediciones.")

    n = len(xs)
    aumentada = [[float(x) ** grado for grado in range(n)] + [float(y)] for x, y in zip(xs, ys)]
    matriz_inicial = [fila[:] for fila in aumentada]
    pasos = []
    for columna in range(n):
        pivote = max(range(columna, n), key=lambda fila: abs(aumentada[fila][columna]))
        if abs(aumentada[pivote][columna]) < 1e-12:
            raise ValueError("No se puede construir un polinomio único con estos tiempos.")
        aumentada[columna], aumentada[pivote] = aumentada[pivote], aumentada[columna]
        divisor = aumentada[columna][columna]
        aumentada[columna] = [valor / divisor for valor in aumentada[columna]]
        for fila in range(n):
            if fila == columna:
                continue
            factor = aumentada[fila][columna]
            aumentada[fila] = [
                valor - factor * pivote_valor
                for valor, pivote_valor in zip(aumentada[fila], aumentada[columna])
            ]
        pasos.append({
            "columna": columna,
            "matriz": [fila[:] for fila in aumentada],
        })

    coeficientes = [aumentada[fila][-1] for fila in range(n)]
    return coeficientes, matriz_inicial, pasos
