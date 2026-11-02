"""Redacción de conclusiones claras sin depender de Tkinter."""

from __future__ import annotations


def redactar_conclusion(estado):
    """Convierte resultados de simulación en secciones con estilo y texto."""
    meta = estado.get("temperatura_meta", 80.0)
    tipo = estado.get("estado", "normal")

    if tipo == "sin_limite":
        temperatura = estado.get("temperatura_maxima_sin_limite", meta)
        texto = (
            "Rendimiento: 100 %\n"
            f"Temperatura máxima estimada: {temperatura:.1f} °C\n"
            f"Límite objetivo: {meta:.1f} °C\n"
            "Interpretación: la temperatura queda por debajo del límite."
        )
    elif tipo == "meta_inalcanzable":
        temperatura = estado.get(
            "temperatura_maxima_minima",
            estado.get("temperatura_final_minima", meta),
        )
        texto = (
            f"Temperatura máxima estimada con el límite mínimo: {temperatura:.1f} °C\n"
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
        pico = estado.get(
            "temperatura_maxima_sin_limite",
            estado.get("temperatura_final_sin_limite", meta),
        )
        pico_limite = estado.get(
            "temperatura_maxima_con_limite",
            estado.get("temperatura_final_con_limite", meta),
        )
        porcentaje = round(estado["limite_recomendado"] * 100)
        texto = (
            f"Temperatura máxima sin límite: {pico:.1f} °C\n"
            f"Rendimiento recomendado: {porcentaje} %\n"
            f"Temperatura máxima con límite: {pico_limite:.1f} °C\n"
            f"Límite objetivo: {meta:.1f} °C"
        )

    return [("destacado", texto + "\n\n")]
