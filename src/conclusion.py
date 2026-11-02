from __future__ import annotations


def redactar_conclusion(estado):
    meta = estado.get("temperatura_meta", 80.0)
    tipo = estado.get("estado", "normal")

    if tipo == "sin_limite":
        temperatura = estado.get("temperatura_final_sin_limite", meta)
        texto = (
            "Rendimiento: 100 %\n"
            f"Temperatura estimada: {temperatura:.1f} °C\n"
            f"Límite objetivo: {meta:.1f} °C\n"
            "Interpretación: la temperatura queda por debajo del límite."
        )
    elif tipo == "meta_inalcanzable":
        temperatura = estado.get("temperatura_final_minima", meta)
        texto = (
            f"Temperatura estimada con el límite mínimo: {temperatura:.1f} °C\n"
            f"Límite objetivo: {meta:.1f} °C\n"
            "Interpretación: la temperatura queda por encima del límite."
        )
    elif tipo == "sin_intervalo" or estado.get("limite_recomendado") is None:
        texto = (
            f"Límite objetivo: {meta:.1f} °C\n"
            "Interpretación: con estos datos no se encontró un límite de rendimiento "
            "que mantenga la temperatura bajo el valor objetivo."
        )
    else:
        sin_limite = estado["temperatura_final_sin_limite"]
        con_limite = estado["temperatura_final_con_limite"]
        porcentaje = round(estado["limite_recomendado"] * 100)
        texto = (
            f"Temperatura sin límite: {sin_limite:.1f} °C\n"
            f"Rendimiento recomendado: {porcentaje} %\n"
            f"Temperatura con límite: {con_limite:.1f} °C\n"
            f"Límite objetivo: {meta:.1f} °C"
        )

    return [("destacado", texto + "\n\n")]
