"""Interfaz independiente para el simulador de límite térmico del equipo."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

from .interpolacion import polinomio_unico
from .modelo import DATOS_EJEMPLO, PARAMETROS_DEFECTO
from .polinomio import formatear_polinomio
from .raices import biseccion, buscar_intervalo_cambio_signo
from .runge_kutta import (
    crear_funcion,
    minuto_cruce_meta,
    runge_kutta,
    runge_kutta_detallado,
)
from .conclusion import redactar_conclusion


class InterfazApp(tk.Tk):
    """Calculadora térmica con configuración avanzada en una ventana aparte."""

    def __init__(self):
        super().__init__()
        self.title("Límite de uso seguro del equipo")
        self.geometry("1080x760")
        self.minsize(850, 620)
        self.parametros = PARAMETROS_DEFECTO.copy()
        self.data_vars = []
        self._dialogo_parametros = None
        self._estado_resultado_var = tk.StringVar(value="Ingresa datos y calcula.")
        self._crear_interfaz()
        self._generar_tabla(len(DATOS_EJEMPLO["tiempo"]))
        self._cargar_ejemplo()

    def _crear_interfaz(self):
        estilo = ttk.Style(self)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")

        principal = ttk.Frame(self, padding=12)
        principal.pack(fill="both", expand=True)
        principal.columnconfigure(0, weight=1)
        principal.rowconfigure(3, weight=1)

        ttk.Label(
            principal,
            text="LÍMITE DE USO SEGURO DEL EQUIPO",
            font=("Arial", 16, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        barra = ttk.Frame(principal)
        barra.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(barra, text="Número de mediciones:").pack(side="left")
        self.n_var = tk.StringVar(value="4")
        self.n_var.trace_add("write", self._marcar_resultados_desactualizados)
        ttk.Entry(barra, width=5, textvariable=self.n_var).pack(side="left", padx=5)
        ttk.Button(barra, text="Actualizar tabla", command=self._actualizar_tabla).pack(side="left", padx=3)
        ttk.Button(barra, text="Cargar ejemplo", command=self._cargar_ejemplo).pack(side="left", padx=3)
        ttk.Label(barra, textvariable=self._estado_resultado_var).pack(side="right", padx=8)
        ttk.Button(barra, text="Configuración térmica...", command=self._abrir_parametros).pack(
            side="right",
        )

        tabla = ttk.LabelFrame(principal, text="Uso del equipo por minuto", padding=6)
        tabla.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        self.table_inner = tabla

        acciones = ttk.Frame(principal)
        acciones.grid(row=3, column=0, sticky="nsew")
        acciones.rowconfigure(1, weight=1)
        acciones.columnconfigure(0, weight=1)
        ttk.Button(acciones, text="CALCULAR", command=self._calcular).grid(
            row=0, column=0, pady=(0, 8),
        )

        self.notebook = ttk.Notebook(acciones)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        self.texts = {}
        for titulo in ("1. Interpolación", "2. Runge-Kutta", "3. Búsqueda de raíz", "4. Resultado"):
            panel = ttk.Frame(self.notebook)
            self.notebook.add(panel, text=titulo)
            salida = tk.Text(panel, wrap="none", font=("Consolas", 10), padx=10, pady=8)
            salida.tag_configure(
                "titulo_grande",
                font=("Arial", 18, "bold"),
                foreground="#263238",
                spacing1=8,
                spacing3=12,
            )
            salida.tag_configure(
                "destacado",
                font=("Arial", 11, "bold"),
                foreground="#1B5E20",
                background="#E8F5E9",
                spacing1=8,
                spacing3=8,
                lmargin1=10,
                lmargin2=10,
                rmargin=10,
            )
            salida.tag_configure(
                "subtitulo",
                font=("Arial", 12, "bold"),
                foreground="#37474F",
                spacing1=8,
                spacing3=4,
            )
            salida.tag_configure(
                "normal",
                font=("Arial", 10),
                foreground="#263238",
                spacing3=5,
                lmargin1=6,
                lmargin2=6,
            )
            salida.tag_configure(
                "nota",
                font=("Arial", 9),
                foreground="#607D8B",
                spacing3=6,
                lmargin1=6,
                lmargin2=6,
            )
            salida.tag_configure(
                "tecnico",
                font=("Consolas", 9),
                foreground="#455A64",
                spacing3=4,
                lmargin1=6,
                lmargin2=6,
            )
            scroll_y = ttk.Scrollbar(panel, orient="vertical", command=salida.yview)
            scroll_x = ttk.Scrollbar(panel, orient="horizontal", command=salida.xview)
            salida.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set, state="disabled")
            salida.grid(row=0, column=0, sticky="nsew")
            scroll_y.grid(row=0, column=1, sticky="ns")
            scroll_x.grid(row=1, column=0, sticky="ew")
            panel.rowconfigure(0, weight=1)
            panel.columnconfigure(0, weight=1)
            self.texts[titulo] = salida

    def _generar_tabla(self, cantidad):
        try:
            cantidad = int(cantidad)
        except (TypeError, ValueError) as exc:
            raise ValueError("El número de mediciones debe ser un entero.") from exc
        if cantidad < 2:
            raise ValueError("Se requieren por lo menos dos mediciones.")

        anteriores = [(x.get(), y.get()) for x, y in self.data_vars]
        for widget in self.table_inner.winfo_children():
            widget.destroy()
        self.data_vars = []

        ttk.Label(self.table_inner, text="Punto").grid(row=0, column=0, padx=5)
        ttk.Label(self.table_inner, text="Tiempo (min)").grid(row=1, column=0, padx=5)
        ttk.Label(self.table_inner, text="Uso del equipo (%)").grid(row=2, column=0, padx=5)
        for indice in range(cantidad):
            ttk.Label(self.table_inner, text=str(indice + 1)).grid(row=0, column=indice + 1, padx=3)
            x_var = tk.StringVar(value=anteriores[indice][0] if indice < len(anteriores) else "")
            y_var = tk.StringVar(value=anteriores[indice][1] if indice < len(anteriores) else "")
            x_var.trace_add("write", self._marcar_resultados_desactualizados)
            y_var.trace_add("write", self._marcar_resultados_desactualizados)
            self.data_vars.append((x_var, y_var))
            ttk.Entry(self.table_inner, width=9, justify="center", textvariable=x_var).grid(
                row=1, column=indice + 1, padx=2, pady=2,
            )
            ttk.Entry(self.table_inner, width=9, justify="center", textvariable=y_var).grid(
                row=2, column=indice + 1, padx=2, pady=2,
            )
        self.n_var.set(str(cantidad))

    def _marcar_resultados_desactualizados(self, *_args):
        self._estado_resultado_var.set("Datos modificados; vuelve a calcular.")

    def _actualizar_tabla(self):
        try:
            self._generar_tabla(self.n_var.get())
        except ValueError as exc:
            messagebox.showerror("Tabla inválida", str(exc), parent=self)

    def _cargar_ejemplo(self):
        self._generar_tabla(len(DATOS_EJEMPLO["tiempo"]))
        for (x_var, y_var), tiempo, uso in zip(
            self.data_vars,
            DATOS_EJEMPLO["tiempo"],
            DATOS_EJEMPLO["uso"],
        ):
            x_var.set(str(tiempo))
            y_var.set(str(uso))

    def _abrir_parametros(self):
        if self._dialogo_parametros is not None and self._dialogo_parametros.winfo_exists():
            self._dialogo_parametros.deiconify()
            self._dialogo_parametros.lift()
            self._dialogo_parametros.focus_force()
            return

        dialogo = tk.Toplevel(self)
        self._dialogo_parametros = dialogo
        dialogo.title("Configuración térmica")
        dialogo.transient(self)
        dialogo.resizable(False, False)
        dialogo.protocol("WM_DELETE_WINDOW", dialogo.destroy)

        nombres = (
            ("Temperatura ambiente (°C)", "T_ambiente"),
            ("Temperatura inicial (°C)", "T_inicial"),
            ("Calor por uso, alfa (°C/min)", "alfa"),
            ("Enfriamiento natural, k (1/min)", "k"),
            ("Temperatura máxima deseada (°C)", "T_objetivo"),
        )
        variables = {}
        for fila, (etiqueta, clave) in enumerate(nombres):
            ttk.Label(dialogo, text=etiqueta).grid(
                row=fila, column=0, sticky="w", padx=12, pady=5,
            )
            variable = tk.StringVar(value=str(self.parametros[clave]))
            variables[clave] = variable
            ttk.Entry(dialogo, textvariable=variable, width=14).grid(
                row=fila, column=1, padx=12, pady=5,
            )

        ttk.Label(
            dialogo,
            text="Los parámetros solo se muestran en esta ventana de configuración.",
            font=("Arial", 9, "italic"),
        ).grid(row=len(nombres), column=0, columnspan=2, padx=12, pady=(4, 8))

        botones = ttk.Frame(dialogo)
        botones.grid(row=len(nombres) + 1, column=0, columnspan=2, pady=(0, 12))

        def restaurar():
            for clave, variable in variables.items():
                variable.set(str(PARAMETROS_DEFECTO[clave]))

        def guardar():
            nuevos = {}
            corregidos = []
            for _etiqueta, clave in nombres:
                texto = variables[clave].get().strip()
                try:
                    valor = float(texto)
                except ValueError:
                    valor = PARAMETROS_DEFECTO[clave]
                    valido = False
                else:
                    valido = math.isfinite(valor)
                    if clave in ("alfa", "k"):
                        valido = valido and valor >= 0
                    if clave == "T_objetivo":
                        valido = valido and valor > 0
                if not valido:
                    valor = PARAMETROS_DEFECTO[clave]
                    corregidos.append(clave)
                    variables[clave].set(str(valor))
                nuevos[clave] = valor
            parametros_cambiaron = nuevos != self.parametros
            self.parametros = nuevos
            if parametros_cambiaron:
                self._marcar_resultados_desactualizados()
            dialogo.destroy()
            if corregidos:
                messagebox.showwarning(
                    "Parámetros corregidos",
                    "Se usaron los valores predeterminados para: " + ", ".join(corregidos),
                    parent=self,
                )

        ttk.Button(botones, text="Restaurar predeterminados", command=restaurar).pack(
            side="left", padx=4,
        )
        ttk.Button(botones, text="Guardar", command=guardar).pack(side="left", padx=4)
        ttk.Button(botones, text="Cancelar", command=dialogo.destroy).pack(side="left", padx=4)
        dialogo.grab_set()
        dialogo.focus_set()

    def _obtener_datos(self):
        tiempos, usos = [], []
        for indice, (x_var, y_var) in enumerate(self.data_vars, start=1):
            try:
                tiempo = float(x_var.get())
                uso = float(y_var.get())
            except ValueError as exc:
                raise ValueError(f"El punto {indice} debe tener tiempo y uso numéricos.") from exc
            if not math.isfinite(tiempo) or not math.isfinite(uso):
                raise ValueError(f"El punto {indice} debe contener números finitos.")
            if tiempo < 0 or not 0 <= uso <= 100:
                raise ValueError(f"El punto {indice} requiere tiempo >= 0 y uso entre 0 y 100%.")
            tiempos.append(tiempo)
            usos.append(uso)
        if not tiempos or tiempos[0] != 0:
            raise ValueError("La primera medición debe iniciar en el minuto 0.")
        if any(a >= b for a, b in zip(tiempos, tiempos[1:])):
            raise ValueError("Los tiempos deben estar en orden estrictamente creciente.")
        return tiempos, usos

    @staticmethod
    def _integrar(limite, coeficientes, parametros, paso):
        funcion = crear_funcion(limite, parametros, coeficientes)
        return runge_kutta(
            funcion,
            0.0,
            parametros["T_inicial"],
            parametros["t_final"],
            paso,
        )

    @classmethod
    def _temperatura_maxima(cls, limite, coeficientes, parametros, paso):
        tiempos, temperaturas = cls._integrar(limite, coeficientes, parametros, paso)
        indice = max(range(len(temperaturas)), key=temperaturas.__getitem__)
        return temperaturas[indice], tiempos[indice]

    @staticmethod
    def _formatear_tabla(encabezados, filas):
        anchos = [
            max(
                [len(str(encabezado))]
                + [len(str(fila[i])) for fila in filas]
            )
            for i, encabezado in enumerate(encabezados)
        ]
        lineas = [
            " | ".join(str(valor).ljust(anchos[i]) for i, valor in enumerate(encabezados)),
            "-+-".join("-" * ancho for ancho in anchos),
        ]
        lineas.extend(
            " | ".join(str(valor).ljust(anchos[i]) for i, valor in enumerate(fila))
            for fila in filas
        )
        return "\n".join(lineas)

    def _mostrar(self, titulo, texto):
        salida = self.texts[titulo]
        salida.configure(state="normal")
        salida.delete("1.0", tk.END)
        salida.insert("1.0", texto)
        salida.configure(state="disabled")

    def _mostrar_conclusion(self, secciones):
        salida = self.texts["4. Resultado"]
        salida.configure(state="normal", wrap="word")
        salida.delete("1.0", tk.END)
        for estilo, texto in secciones:
            salida.insert(tk.END, texto, estilo)
        salida.configure(state="disabled")

    def _calcular(self):
        try:
            tiempos, usos = self._obtener_datos()
            parametros = self.parametros.copy()
            parametros["t_final"] = tiempos[-1]
            if parametros["t_final"] <= 0:
                raise ValueError("El tiempo final debe ser mayor que cero.")
            coeficientes, matriz_inicial, pasos_interpolacion = polinomio_unico(
                tiempos,
                usos,
            )

            paso, _cantidad = self._paso_efectivo(parametros["t_final"], DATOS_EJEMPLO["paso"])
            paso_objetivo = min(paso, 1.0)

            def objetivo(limite):
                temperatura_maxima, _ = self._temperatura_maxima(
                    limite,
                    coeficientes,
                    parametros,
                    paso_objetivo,
                )
                return temperatura_maxima - parametros["T_objetivo"]

            intervalo_inicial = DATOS_EJEMPLO["intervalo"]
            f_inferior = objetivo(intervalo_inicial[0])
            f_superior = objetivo(intervalo_inicial[1])
            xs_uno, temperaturas_uno = self._integrar(1.0, coeficientes, parametros, paso_objetivo)
            indice_pico_uno = max(
                range(len(temperaturas_uno)),
                key=temperaturas_uno.__getitem__,
            )
            temperatura_maxima_uno = temperaturas_uno[indice_pico_uno]
            temperatura_final_uno = temperaturas_uno[-1]
            minuto_pico_uno = xs_uno[indice_pico_uno]

            self._mostrar(
                "1. Interpolación",
                self._crear_salida_interpolacion(
                    tiempos,
                    usos,
                    coeficientes,
                    matriz_inicial,
                    pasos_interpolacion,
                ),
            )

            funcion_rk = crear_funcion(1.0, parametros, coeficientes)
            xs, temperaturas, pasos_rk = runge_kutta_detallado(
                funcion_rk,
                0.0,
                parametros["T_inicial"],
                parametros["t_final"],
                paso,
            )
            self._mostrar(
                "2. Runge-Kutta",
                self._crear_salida_runge_kutta(xs, temperaturas, pasos_rk, parametros, paso),
            )

            resultado_biseccion = None
            intervalo = None
            intervalo_cambiado = False
            estado_tipo = "normal"
            if temperatura_maxima_uno <= parametros["T_objetivo"]:
                estado_tipo = "sin_limite"
            else:
                limite_minimo = DATOS_EJEMPLO["busqueda_minima"]
                if objetivo(limite_minimo) > 0:
                    estado_tipo = "meta_inalcanzable"
                elif abs(f_inferior) <= 1e-12:
                    intervalo = (intervalo_inicial[0], intervalo_inicial[0])
                elif abs(f_superior) <= 1e-12:
                    intervalo = (intervalo_inicial[1], intervalo_inicial[1])
                elif f_inferior * f_superior < 0:
                    intervalo = intervalo_inicial
                else:
                    intervalo = buscar_intervalo_cambio_signo(
                        objetivo,
                        inicio=limite_minimo,
                        fin=1.0,
                        paso=DATOS_EJEMPLO["paso_busqueda"],
                    )
                    intervalo_cambiado = intervalo is not None

                if estado_tipo == "normal" and intervalo is not None:
                    if intervalo[0] == intervalo[1]:
                        resultado_biseccion = {
                            "raiz": intervalo[0],
                            "iteraciones": [],
                            "detalle": [],
                            "error_aproximado": 0.0,
                        }
                    else:
                        resultado_biseccion = biseccion(
                            objetivo,
                            intervalo[0],
                            intervalo[1],
                            DATOS_EJEMPLO["tolerancia"],
                        )
                elif estado_tipo == "normal":
                    estado_tipo = "sin_intervalo"

            if resultado_biseccion is not None:
                limite_optimo = resultado_biseccion["raiz"]
                limite_recomendado = max(
                    limite_minimo,
                    math.floor(limite_optimo * 20.0 + 1e-12) / 20.0,
                )
                xs_con_limite, temperaturas_con_limite = self._integrar(
                    limite_recomendado,
                    coeficientes,
                    parametros,
                    paso_objetivo,
                )
                indice_pico_con_limite = max(
                    range(len(temperaturas_con_limite)),
                    key=temperaturas_con_limite.__getitem__,
                )
                temperatura_maxima_con_limite = temperaturas_con_limite[indice_pico_con_limite]
                temperatura_final_con_limite = temperaturas_con_limite[-1]
                minuto_pico_con_limite = xs_con_limite[indice_pico_con_limite]
            else:
                limite_optimo = None
                limite_recomendado = None
                temperatura_maxima_con_limite = None
                temperatura_final_con_limite = None
                minuto_pico_con_limite = None

            paso_fino = parametros["t_final"] / 360.0
            tiempos_finos, temperaturas_finas = runge_kutta(
                crear_funcion(1.0, parametros, coeficientes),
                0.0,
                parametros["T_inicial"],
                parametros["t_final"],
                paso_fino,
            )
            minuto_cruce = minuto_cruce_meta(
                tiempos_finos,
                temperaturas_finas,
                parametros["T_objetivo"],
            )

            if estado_tipo == "meta_inalcanzable":
                temperatura_maxima_minima, _ = self._temperatura_maxima(
                    limite_minimo,
                    coeficientes,
                    parametros,
                    paso_objetivo,
                )
            else:
                temperatura_maxima_minima = None

            self._mostrar(
                "3. Búsqueda de raíz",
                self._crear_salida_biseccion(
                    objetivo,
                    intervalo,
                    resultado_biseccion,
                    intervalo_cambiado,
                    f_inferior,
                    f_superior,
                    intervalo_inicial,
                    parametros["T_objetivo"],
                ),
            )

            limite_recomendado_supera_meta = (
                limite_recomendado is not None
                and temperatura_maxima_con_limite > parametros["T_objetivo"]
            )
            paso_ajustado = not math.isclose(
                paso,
                DATOS_EJEMPLO["paso"],
                rel_tol=0.0,
                abs_tol=1e-10,
            )
            estado_conclusion = {
                "estado": estado_tipo,
                "duracion_minutos": parametros["t_final"],
                "temperatura_meta": parametros["T_objetivo"],
                "limite_optimo": limite_optimo,
                "limite_recomendado": limite_recomendado,
                "temperatura_maxima_sin_limite": temperatura_maxima_uno,
                "temperatura_final_sin_limite": temperatura_final_uno,
                "minuto_del_pico_sin_limite": minuto_pico_uno,
                "temperatura_maxima_con_limite": temperatura_maxima_con_limite,
                "temperatura_final_con_limite": temperatura_final_con_limite,
                "minuto_del_pico_con_limite": minuto_pico_con_limite,
                "temperatura_maxima_minima": temperatura_maxima_minima,
                "minuto_en_que_llega_a_la_meta_sin_limite": minuto_cruce,
                "rendimiento_perdido": (
                    (1.0 - limite_recomendado) * 100.0
                    if limite_recomendado is not None
                    else None
                ),
                "numero_iteraciones": (
                    len(resultado_biseccion["iteraciones"])
                    if resultado_biseccion is not None
                    else 0
                ),
                "tolerancia": DATOS_EJEMPLO["tolerancia"],
                "error_aproximado": (
                    resultado_biseccion["error_aproximado"]
                    if resultado_biseccion is not None
                    else None
                ),
                "polinomio": formatear_polinomio(coeficientes),
                "intervalo_cambiado_automaticamente": intervalo_cambiado,
                "tiempo_extrapolado": parametros["t_final"] > tiempos[-1],
                "paso_ajustado": paso_ajustado,
                "limite_recomendado_supera_meta": limite_recomendado_supera_meta,
            }
            self._mostrar_conclusion(redactar_conclusion(estado_conclusion))
            self._ultimo_estado_conclusion = estado_conclusion
            self._estado_resultado_var.set("Resultados actualizados.")
            self.notebook.select(3)
        except (ValueError, ArithmeticError, OverflowError) as exc:
            messagebox.showerror("No se pudo calcular", str(exc), parent=self)

    def _crear_salida_biseccion(
        self,
        objetivo,
        intervalo,
        resultado,
        intervalo_cambiado,
        valor_inferior_inicial,
        valor_superior_inicial,
        intervalo_inicial,
        meta,
    ):
        lineas = [
            "BÚSQUEDA DEL LÍMITE DE RENDIMIENTO",
            f"Meta de temperatura máxima: {meta:.2f} °C",
            "",
            "Para encontrar el límite, el programa probó un valor a la mitad del rango. "
            "Según el resultado, conservó la mitad donde está la solución y repitió el proceso. "
            "La meta se evalúa sobre el pico de temperatura de toda la sesión, no solo sobre el final. "
            "Así, la bisección resuelve un problema no lineal y busca que el equipo no se sobrecaliente en ningún momento. "
            "La búsqueda usa un paso interno más fino que la tabla de Runge-Kutta.",
            "",
            f"Rango inicial probado: {intervalo_inicial[0] * 100:.0f}% a {intervalo_inicial[1] * 100:.0f}%.",
            f"Diferencia en el primer extremo: {valor_inferior_inicial:.4f} °C.",
            f"Diferencia en el segundo extremo: {valor_superior_inicial:.4f} °C.",
        ]
        if intervalo is None or resultado is None:
            lineas.extend([
                "",
                "No se ejecutó bisección porque no se encontró un intervalo con cambio de signo.",
                f"En L = {DATOS_EJEMPLO['busqueda_minima'] * 100:.0f}%: "
                f"{objetivo(DATOS_EJEMPLO['busqueda_minima']):.4f} °C respecto a la meta.",
                f"En L = 100%: {objetivo(1.0):.4f} °C respecto a la meta.",
            ])
            return "\n".join(lineas)

        if intervalo_cambiado:
            lineas.extend([
                "",
                "El intervalo inicial no contenía la respuesta.",
                "Se buscó automáticamente entre 5% y 100%, en pasos de 5%.",
            ])
        lineas.extend([
            "",
            f"Intervalo que contiene la respuesta: {intervalo[0] * 100:.2f}% a "
            f"{intervalo[1] * 100:.2f}%.",
            "",
            "Tabla de bisección: cada fila muestra el punto medio probado y el rango que se conserva.",
            self._formatear_tabla(
                [
                    "Paso",
                    "Desde (%)",
                    "Hasta (%)",
                    "Prueba (%)",
                    "Pico - meta (°C)",
                    "Cambio (%)",
                    "Decisión",
                ],
                [
                    [
                        fila["paso"],
                        f"{fila['inferior'] * 100:.4f}",
                        f"{fila['superior'] * 100:.4f}",
                        f"{fila['medio'] * 100:.4f}",
                        f"{fila['f_medio']:.5f}",
                        "---" if fila["error"] is None else f"{fila['error']:.4f}",
                        fila["decision"],
                    ]
                    for fila in resultado["detalle"]
                ],
            ),
            "",
            f"Límite óptimo: {resultado['raiz'] * 100:.4f}%.",
            f"Error aproximado final: ±{resultado['error_aproximado'] * 100:.6f} puntos porcentuales.",
        ])
        return "\n".join(lineas)

    def _crear_salida_interpolacion(self, tiempos, usos, coeficientes, matriz_inicial, pasos):
        lineas = [
            "PASO 1: INTERPOLACIÓN DE LAS MEDICIONES",
            "Usamos los puntos de tiempo y uso para construir una curva P(t).",
            "P(t) estima el uso del equipo entre las mediciones registradas.",
            "",
            "Mediciones ingresadas:",
            self._formatear_tabla(
                ["Punto", "Tiempo (min)", "Uso del equipo (%)"],
                [
                    [indice, f"{tiempo:.2f}", f"{uso:.2f}"]
                    for indice, (tiempo, uso) in enumerate(zip(tiempos, usos), start=1)
                ],
            ),
            "",
            "1A. Sistema que se resuelve",
            "Cada fila representa a_i + a_1*t + a_2*t^2 + ... = uso medido.",
            self._formatear_tabla(
                [f"a{i}" for i in range(len(tiempos))] + ["Uso (%)"],
                [[f"{valor:.6g}" for valor in fila] for fila in matriz_inicial],
            ),
            "",
            "1B. Eliminación de Gauss-Jordan, columna por columna",
            "En cada paso se normaliza el pivote y se elimina esa incógnita de las demás filas.",
        ]
        for paso in pasos:
            lineas.extend([
                "",
                f"Después de procesar la columna a{paso['columna']}:",
                self._formatear_tabla(
                    [f"a{i}" for i in range(len(tiempos))] + ["Uso"],
                    [[f"{valor:.6g}" for valor in fila] for fila in paso["matriz"]],
                ),
            ])
        lineas.extend([
            "",
            "1C. Polinomio obtenido:",
            formatear_polinomio(coeficientes),
            "",
            "Los coeficientes corresponden a a0 + a1*t + a2*t^2 + ...",
            "La curva pasa por las mediciones; entre ellas el programa estima el uso.",
        ])
        return "\n".join(lineas)

    def _crear_salida_runge_kutta(self, tiempos, temperaturas, pasos, parametros, paso):
        lineas = [
            "PASO 2: CÁLCULO DE LA TEMPERATURA CON RUNGE-KUTTA 4",
            "Partimos de la temperatura inicial y avanzamos en intervalos de tiempo.",
            "La fórmula calcula el calor que genera el equipo menos el calor que se disipa.",
            "dT/dt = alfa * L * P(t) - k * (T - T_ambiente)",
            "",
            f"Temperatura inicial: {parametros['T_inicial']:.2f} °C",
            f"Temperatura ambiente: {parametros['T_ambiente']:.2f} °C",
            f"Uso del equipo para esta tabla: 100%; tamaño de paso: {paso:.4g} min.",
            "",
            "2A. Qué significan k1, k2, k3 y k4:",
            "Son cuatro estimaciones de cuánto cambia la temperatura dentro de cada paso.",
            "RK4 las combina para calcular la siguiente temperatura con mayor precisión.",
            "",
            "2B. Desarrollo de cada paso:",
            self._formatear_tabla(
                ["Paso", "Minuto t", "Paso h", "T inicio (°C)", "k1", "k2", "k3", "k4", "T siguiente (°C)"],
                [
                    [
                        fila["paso"],
                        f"{fila['t']:.3f}",
                        f"{fila['h']:.3f}",
                        f"{fila['T']:.4f}",
                        f"{fila['k1']:.5f}",
                        f"{fila['k2']:.5f}",
                        f"{fila['k3']:.5f}",
                        f"{fila['k4']:.5f}",
                        f"{fila['T_siguiente']:.4f}",
                    ]
                    for fila in pasos
                ],
            ),
            "",
            "2C. Temperatura estimada durante toda la sesión:",
            self._formatear_tabla(
                ["Tiempo (min)", "Temperatura (°C)"],
                [[f"{tiempo:.3f}", f"{temperatura:.4f}"]
                 for tiempo, temperatura in zip(tiempos, temperaturas)],
            ),
            "",
            f"Sin limitar el rendimiento, el pico estimado es {max(temperaturas):.4f} °C "
            f"en el minuto {tiempos[temperaturas.index(max(temperaturas))]:.2f}.",
            f"La temperatura final estimada es {temperaturas[-1]:.4f} °C.",
        ]
        return "\n".join(lineas)

    @staticmethod
    def _paso_efectivo(t_final, paso):
        cantidad = max(1, round(t_final / paso))
        return t_final / cantidad, cantidad


def main():
    app = InterfazApp()
    app.mainloop()
