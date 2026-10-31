"""Redacción de conclusiones claras sin depender de Tkinter."""

from __future__ import annotations

import math


def redactar_conclusion(estado):
    """Convierte resultados de simulación en secciones con estilo y texto."""
    resultado = []
    duracion = round(estado.get("duracion_minutos", 90))
    meta = estado.get("temperatura_meta", 80.0)
    limite = estado.get("limite_recomendado")
    estado_especial = estado.get("estado", "normal")

    def agregar(estilo, texto):
        resultado.append((estilo, texto.rstrip() + "\n\n"))

    if estado_especial == "sin_limite":
        temperatura = estado.get("temperatura_final_sin_limite", meta)
        agregar("titulo_grande", "No necesitas limitar tu laptop")
        agregar(
            "destacado",
            f"Con el 100 % del rendimiento, termina en {temperatura:.1f} °C, "
            f"por debajo de tu meta de {meta:.1f} °C.",
        )
        _agregar_avisos(resultado, estado)
        agregar(
            "nota",
            "Puedes jugar con el rendimiento completo y revisar la temperatura real durante la sesión.",
        )
        agregar("subtitulo", "¿Qué tan confiable es?")
        agregar("nota", _NOTA_CONFIABILIDAD)
        agregar("subtitulo", "Detalle técnico (para la clase)")
        agregar("tecnico", _detalle_tecnico(estado))
        return resultado

    if estado_especial == "meta_inalcanzable":
        temperatura = estado.get("temperatura_final_minima", meta)
        agregar("titulo_grande", "Con estos datos no se alcanza esa temperatura")
        agregar(
            "destacado",
            f"Aunque limites la laptop al mínimo, termina en {temperatura:.1f} °C. "
            f"Tu meta es {meta:.1f} °C.",
        )
        agregar(
            "normal",
            "Prueba una meta más alta o revisa la temperatura ambiente y los datos del modelo.",
        )
        _agregar_avisos(resultado, estado)
        agregar("subtitulo", "¿Qué tan confiable es?")
        agregar("nota", _NOTA_CONFIABILIDAD)
        agregar("subtitulo", "Detalle técnico (para la clase)")
        agregar("tecnico", _detalle_tecnico(estado))
        return resultado

    if estado_especial == "sin_intervalo":
        agregar("titulo_grande", "No pudimos encontrar un límite con estos datos")
        agregar(
            "destacado",
            "Probamos distintos porcentajes de rendimiento, pero ninguno quedó dentro del rango "
            "necesario para alcanzar tu meta.",
        )
        agregar(
            "normal",
            "Revisa las mediciones y la temperatura que elegiste como meta. "
            "También puedes probar con una meta menos estricta.",
        )
        _agregar_avisos(resultado, estado)
        agregar("subtitulo", "¿Qué tan confiable es?")
        agregar("nota", _NOTA_CONFIABILIDAD)
        agregar("subtitulo", "Detalle técnico (para la clase)")
        agregar("tecnico", _detalle_tecnico(estado))
        return resultado

    if limite is None:
        agregar("titulo_grande", "No pudimos calcular un límite")
        agregar(
            "destacado",
            "El programa no encontró un rango que contenga la respuesta. "
            "Revisa las mediciones y la meta de temperatura.",
        )
        agregar("nota", "No cambies la configuración del equipo basándote en este resultado.")
        _agregar_avisos(resultado, estado)
        agregar("subtitulo", "Detalle técnico (para la clase)")
        agregar("tecnico", _detalle_tecnico(estado))
        return resultado

    recomendado_porcentaje = round(estado["limite_recomendado"] * 100)
    sin_limite = estado["temperatura_final_sin_limite"]
    con_limite = estado["temperatura_final_con_limite"]
    minuto = estado.get("minuto_en_que_llega_a_la_meta_sin_limite")
    perdida = round(estado["rendimiento_perdido"])

    agregar(
        "titulo_grande",
        f"Para jugar {duracion} minutos sin pasar tu meta, limita el rendimiento al "
        f"{recomendado_porcentaje} %.",
    )
    if minuto is None:
        primera_linea = (
            f"Si no haces nada: termina en {sin_limite:.1f} °C y no llega a tu meta "
            f"de {meta:.1f} °C."
        )
    else:
        primera_linea = (
            f"Si no haces nada: termina en {sin_limite:.1f} °C y pasa tu meta "
            f"de {meta:.1f} °C cerca del minuto {round(minuto)}."
        )
    agregar(
        "destacado",
        f"{primera_linea}\n"
        f"Con el límite recomendado: termina en {con_limite:.1f} °C, "
        f"por debajo de tu meta de {meta:.1f} °C.\n"
        f"Lo que pierdes: cerca del {perdida} % del rendimiento máximo.",
    )
    _agregar_avisos(resultado, estado)
    agregar("subtitulo", "¿Qué significa límite de rendimiento?")
    agregar(
        "normal",
        "Es como el límite de velocidad de un auto. Tu laptop puede ir más rápido.\n"
        "Le pides que use solo parte de su capacidad para calentarse menos.\n"
        f"Al {recomendado_porcentaje} %, usa como máximo {recomendado_porcentaje} de cada "
        "100 unidades de potencia del procesador y la gráfica.",
    )
    agregar("subtitulo", "¿Cómo lo aplico?")
    agregar(
        "normal",
        "• Activa un tope de cuadros por segundo (FPS) dentro del juego.\n"
        "• En Windows, abre Opciones de energía. Elige Cambiar la configuración del plan.\n"
        "• Abre la configuración avanzada y busca Administración de energía del procesador.\n"
        f"• Fija el estado máximo del procesador en {recomendado_porcentaje} %.\n"
        "• Si puedes, limita la potencia de la tarjeta gráfica desde la aplicación del fabricante.",
    )
    agregar("nota", "Los pasos exactos cambian según tu laptop.")
    agregar("subtitulo", "¿Cómo lo calculó el programa?")
    agregar(
        "normal",
        "1. Con tus mediciones calculó cuánto exiges a la laptop en cada minuto.\n"
        "2. Calculó cómo se calienta y cómo la enfría el ventilador durante la sesión.\n"
        "3. Probó límites a la mitad del rango hasta encontrar uno que llega a tu meta.",
    )
    agregar("subtitulo", "¿Qué tan confiable es?")
    agregar("nota", _NOTA_CONFIABILIDAD)
    agregar("subtitulo", "Detalle técnico (para la clase)")
    agregar("tecnico", _detalle_tecnico(estado))
    return resultado


def _agregar_avisos(resultado, estado):
    if estado.get("intervalo_cambiado_automaticamente"):
        resultado.append((
            "nota",
            "El programa buscó por su cuenta el rango correcto, porque el que escribiste no contenía la respuesta.\n\n",
        ))
    if estado.get("tiempo_extrapolado"):
        resultado.append((
            "nota",
            "La sesión termina después de tus últimas mediciones. La temperatura de ese tramo es una estimación.\n\n",
        ))
    if estado.get("paso_ajustado"):
        resultado.append((
            "nota",
            "El programa ajustó un poco los intervalos de tiempo para completar la sesión justo al final.\n\n",
        ))
    if estado.get("limite_recomendado_supera_meta"):
        resultado.append((
            "nota",
            "Aun con el límite mínimo, la temperatura supera tu meta. "
            "Prueba una meta más alta o revisa la ventilación y los datos.\n\n",
        ))


def _detalle_tecnico(estado):
    limite = estado.get("limite_optimo")
    iteraciones = estado.get("numero_iteraciones", 0)
    tolerancia = estado.get("tolerancia", 0.5)
    error = estado.get("error_aproximado")
    polinomio = estado.get("polinomio", "No disponible")
    limite_texto = "No se encontró" if limite is None else f"{limite:.4f}"
    error_texto = "No disponible" if error is None or not math.isfinite(error) else f"{error:.8f}"
    return (
        f"Límite óptimo exacto: {limite_texto}\n"
        f"Iteraciones de bisección: {iteraciones}\n"
        f"Tolerancia relativa: {tolerancia:.4f} %\n"
        f"Error aproximado final: {error_texto}\n"
        f"Polinomio P(t): {polinomio}"
    )


_NOTA_CONFIABILIDAD = (
    "El calentamiento y el enfriamiento son estimaciones, no mediciones de tu laptop.\n"
    "Úsalo como guía y revisa la temperatura real con un programa de monitoreo.\n"
    "También influyen el polvo, la ventilación, la temperatura del cuarto y los programas abiertos."
)
