# Simulador térmico de laptop

Aplicación para estimar la temperatura de una laptop bajo distintas cargas de trabajo y encontrar un límite de rendimiento que alcance la temperatura objetivo. La aplicación de consumo de datos móviles se conserva por separado en `segunda opcion/`.

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
PROMPT.md
segunda opcion/
  main.py
  README.md
  src/
```

Los parámetros de temperatura ambiente e inicial, alfa, k y temperatura objetivo se encuentran en la ventana **Configuración térmica...**, no en la pantalla principal. El enfriamiento se modela de forma lineal usando k.

## Ejecutar

Desde la carpeta raíz:

```powershell
python -m src.main
```

El programa usa solamente la biblioteca estándar de Python y Tkinter. El archivo `requirements.txt` documenta que no hay paquetes de terceros que instalar.

## Seguir el cálculo

1. **Interpolación:** muestra las mediciones, el sistema de ecuaciones, las matrices resultantes de Gauss-Jordan y el polinomio que estima el uso entre puntos.
2. **Runge-Kutta:** enseña las cuatro pendientes `k1` a `k4` de cada intervalo y la tabla de temperaturas resultante.
3. **Búsqueda de raíz:** usa únicamente bisección, muestra la tabla de pruebas y busca automáticamente un intervalo con cambio de signo si el rango inicial no contiene la respuesta.
4. **Resultado:** presenta una recomendación redondeada hacia abajo a múltiplos de 5 %, explica qué significa y cómo aplicarla. El detalle técnico queda al final.

La conclusión se redacta con `src/conclusion.py`, una función independiente de Tkinter que facilita probar los mensajes. El simulador incluye estimaciones del cruce de la meta y avisa cuando la respuesta requiere un intervalo distinto o un paso de cálculo ajustado.

Con la ecuación térmica actual, la temperatura final cambia linealmente con el límite `L`. Por eso, la raíz podría obtenerse con una interpolación lineal de dos simulaciones. Se mantiene bisección para practicar el método solicitado y porque también funciona si después se incorpora un modelo no lineal.

Al finalizar, puedes ejecutar **Cargar ejemplo** para restablecer las mediciones de demostración. Las estimaciones no sustituyen las protecciones térmicas del equipo ni equivalen a mediciones reales.

La otra aplicación de este repositorio, para control de consumo de datos móviles, tiene su propio código e instrucciones dentro de `segunda opcion/`.

Para abrir esa aplicación, entra en `segunda opcion/` y ejecuta `python main.py`. Desde la misma carpeta puedes ejecutar sus pruebas con `python -m src.pruebas`.
