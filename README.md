# Simulador térmico de laptop

Aplicación para estimar la temperatura de una laptop bajo distintas cargas de trabajo y encontrar un límite de rendimiento que evite superar una temperatura objetivo durante toda la sesión.

## Estructura

```text
src/
  interfaz.py
  conclusion.py
  interpolacion.py
  modelo.py
  polinomio.py
  raices.py
  runge_kutta.py
  main.py
requirements.txt
README.md
tests/
  test_nucleo.py
```

Los parámetros de temperatura ambiente e inicial, alfa, k y temperatura objetivo se encuentran en la ventana **Configuración térmica...**, no en la pantalla principal. El enfriamiento se modela de forma lineal usando k.

## Ejecutar

Desde la carpeta raíz:

```powershell
python -m src.main
```

El programa usa solamente la biblioteca estándar de Python y Tkinter. El archivo `requirements.txt` documenta que no hay paquetes de terceros que instalar.

Para ejecutar las pruebas:

```powershell
python -m unittest discover -s tests -v
```

## Seguir el cálculo

1. **Interpolación:** muestra las mediciones, el sistema de ecuaciones, las matrices resultantes de Gauss-Jordan y el polinomio que estima el uso entre puntos.
2. **Runge-Kutta:** enseña las cuatro pendientes `k1` a `k4` de cada intervalo y la tabla de temperaturas resultante.
3. **Búsqueda de raíz:** usa únicamente bisección, muestra la tabla de pruebas y busca automáticamente un intervalo con cambio de signo si el rango inicial no contiene la respuesta.
4. **Resultado:** presenta una recomendación redondeada hacia abajo a múltiplos de 5 %, explica qué significa y cómo aplicarla. El detalle técnico queda al final.

La búsqueda de raíz se hace sobre la **temperatura máxima de la sesión**, no solo sobre la temperatura final. Así se evita recomendar un límite que termine por debajo de la meta pero que haga un pico por encima de ella cuando la carga baja al final.

La conclusión se redacta con `src/conclusion.py`, una función independiente de Tkinter que facilita probar los mensajes. El simulador incluye estimaciones del cruce de la meta y avisa cuando la respuesta requiere un intervalo distinto o un paso de cálculo ajustado.

## Caso de ejemplo

Con los datos y parámetros predeterminados:

- Mediciones de uso: `40 %`, `85 %`, `100 %` y `90 %` en los minutos `0`, `30`, `60` y `90`.
- Sin límite, el pico estimado es **104.2 °C**.
- El límite recomendado es **65 %**, con un pico estimado de **76.8 °C** y una temperatura final similar.

El límite se redondea hacia abajo a múltiplos de 5 % para ser conservador. Por eso puede quedar algo por debajo del valor exacto que igualaría la meta.

Al finalizar, puedes ejecutar **Cargar ejemplo** para restablecer las mediciones de demostración. Las estimaciones no sustituyen las protecciones térmicas del equipo ni equivalen a mediciones reales.
