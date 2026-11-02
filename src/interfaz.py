"""Interfaz independiente para el simulador de límite térmico del equipo."""

from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

from .interpolacion import polinomio_unico
from .modelo import DATOS_EJEMPLO, PARAMETROS_DEFECTO
from .polinomio import evaluar_polinomio, formatear_polinomio
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
        self._datos_graficas = None
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
        ttk.Button(barra, text="Limpiar tabla", command=self._limpiar_tabla).pack(side="left", padx=3)
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
                foreground="#263238",
                spacing1=8,
                spacing3=8,
                lmargin1=10,
                lmargin2=10,
                rmargin=10,
                underline=False,
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

        panel_graficas = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(panel_graficas, text="5. Gráficas")
        panel_graficas.rowconfigure(1, weight=1)
        panel_graficas.columnconfigure(0, weight=1)
        selector = ttk.Frame(panel_graficas)
        selector.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(selector, text="Gráfica:").pack(side="left", padx=(0, 6))
        self.grafica_var = tk.StringVar(value="Uso del equipo")
        selector_graficas = ttk.Combobox(
            selector,
            textvariable=self.grafica_var,
            values=(
                "Uso del equipo",
                "Temperatura durante la sesión",
                "Temperatura final según el límite",
            ),
            state="readonly",
            width=38,
        )
        selector_graficas.pack(side="left")
        selector_graficas.bind("<<ComboboxSelected>>", self._dibujar_grafica)
        self.grafica_canvas = tk.Canvas(
            panel_graficas,
            background="white",
            highlightthickness=1,
            highlightbackground="#CFD8DC",
        )
        self.grafica_canvas.grid(row=1, column=0, sticky="nsew")
        self.grafica_canvas.bind("<Configure>", self._dibujar_grafica)
        self._dibujar_grafica()

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
        self._datos_graficas = None
        if hasattr(self, "grafica_canvas"):
            self._dibujar_grafica()

    def _actualizar_tabla(self):
        try:
            self._generar_tabla(self.n_var.get())
        except ValueError as exc:
            messagebox.showerror("Tabla inválida", str(exc), parent=self)

    def _limpiar_tabla(self):
        for x_var, y_var in self.data_vars:
            x_var.set("")
            y_var.set("")
        self._marcar_resultados_desactualizados()

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
        if any(a >= b for a, b in zip(tiempos, tiempos[1:])):
            raise ValueError("Los tiempos deben estar en orden estrictamente creciente.")
        return tiempos, usos

    @staticmethod
    def _integrar(limite, coeficientes, parametros, paso):
        funcion = crear_funcion(limite, parametros, coeficientes)
        return runge_kutta(
            funcion,
            parametros["t_inicio"],
            parametros["T_inicial"],
            parametros["t_final"],
            paso,
        )

    @classmethod
    def _temperatura_final(cls, limite, coeficientes, parametros, paso):
        return cls._integrar(limite, coeficientes, parametros, paso)[1][-1]

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

    def _dibujar_grafica(self, *_args):
        canvas = self.grafica_canvas
        canvas.delete("all")
        ancho = max(canvas.winfo_width(), 360)
        alto = max(canvas.winfo_height(), 280)
        if self._datos_graficas is None:
            canvas.create_text(
                ancho / 2,
                alto / 2,
                text="Calcula con datos válidos para generar las gráficas.",
                fill="#607D8B",
                font=("Arial", 11),
            )
            return

        nombre = self.grafica_var.get()
        datos = self._datos_graficas
        if nombre == "Uso del equipo":
            grafica = {
                "titulo": "Uso del equipo",
                "eje_x": "Tiempo (min)",
                "eje_y": "Uso (%)",
                "series": [("P(t)", datos["uso_estimado"], "#1565C0")],
                "marcadores": (datos["tiempos"], datos["usos"]),
                "rango_y": (0.0, 100.0),
            }
        elif nombre == "Temperatura durante la sesión":
            grafica = {
                "titulo": "Temperatura durante la sesión (L = 100%)",
                "eje_x": "Tiempo (min)",
                "eje_y": "Temperatura (°C)",
                "series": [("T(t)", datos["temperaturas"], "#E65100")],
                "referencia_y": (datos["meta"], "Meta"),
            }
        else:
            grafica = {
                "titulo": "Temperatura final según el límite",
                "eje_x": "Límite de rendimiento (%)",
                "eje_y": "Temperatura final (°C)",
                "series": [("T_final(L)", datos["temperaturas_limite"], "#1565C0")],
                "referencia_y": (datos["meta"], "Meta"),
                "referencia_x": datos["limite_recomendado"],
            }

        series = grafica["series"]
        puntos = [punto for _etiqueta, valores, _color in series for punto in valores]
        if grafica.get("marcadores"):
            puntos.extend(zip(*grafica["marcadores"]))
        if not puntos:
            return

        minimo_x = min(punto[0] for punto in puntos)
        maximo_x = max(punto[0] for punto in puntos)
        valores_y = [punto[1] for punto in puntos]
        referencia_y = grafica.get("referencia_y")
        if referencia_y is not None:
            valores_y.append(referencia_y[0])
        minimo_y = min(valores_y)
        maximo_y = max(valores_y)
        margen_y = max((maximo_y - minimo_y) * 0.1, 1.0)
        if "rango_y" in grafica:
            minimo_y, maximo_y = grafica["rango_y"]
        else:
            minimo_y -= margen_y
            maximo_y += margen_y
        if math.isclose(minimo_x, maximo_x):
            maximo_x = minimo_x + 1.0
        if math.isclose(minimo_y, maximo_y):
            maximo_y = minimo_y + 1.0

        izquierda, derecha = 76, ancho - 24
        arriba, abajo = 56, alto - 58
        canvas.create_text(
            ancho / 2,
            20,
            text=grafica["titulo"],
            fill="#263238",
            font=("Arial", 13, "bold"),
        )

        def proyectar(x, y):
            px = izquierda + (x - minimo_x) * (derecha - izquierda) / (maximo_x - minimo_x)
            py = abajo - (y - minimo_y) * (abajo - arriba) / (maximo_y - minimo_y)
            return px, py

        for indice in range(6):
            fraccion = indice / 5
            x = izquierda + fraccion * (derecha - izquierda)
            y = abajo - fraccion * (abajo - arriba)
            valor_x = minimo_x + fraccion * (maximo_x - minimo_x)
            valor_y = minimo_y + fraccion * (maximo_y - minimo_y)
            canvas.create_line(x, arriba, x, abajo, fill="#ECEFF1")
            canvas.create_line(izquierda, y, derecha, y, fill="#ECEFF1")
            canvas.create_text(x, abajo + 14, text=f"{valor_x:.1f}", fill="#546E7A", font=("Arial", 8))
            canvas.create_text(
                izquierda - 9,
                y,
                text=f"{valor_y:.1f}",
                anchor="e",
                fill="#546E7A",
                font=("Arial", 8),
            )

        canvas.create_line(izquierda, abajo, derecha, abajo, fill="#455A64", width=2)
        canvas.create_line(izquierda, arriba, izquierda, abajo, fill="#455A64", width=2)
        canvas.create_text(
            (izquierda + derecha) / 2,
            alto - 15,
            text=grafica["eje_x"],
            fill="#37474F",
            font=("Arial", 9),
        )
        canvas.create_text(
            18,
            (arriba + abajo) / 2,
            text=grafica["eje_y"],
            angle=90,
            fill="#37474F",
            font=("Arial", 9),
        )

        for indice, (etiqueta, valores, color) in enumerate(series):
            coordenadas = [proyectar(x, y) for x, y in valores]
            for inicio, fin in zip(coordenadas, coordenadas[1:]):
                canvas.create_line(*inicio, *fin, fill=color, width=2)
            leyenda_x = izquierda + indice * 150
            canvas.create_line(leyenda_x, 40, leyenda_x + 22, 40, fill=color, width=3)
            canvas.create_text(leyenda_x + 28, 40, text=etiqueta, anchor="w", fill="#37474F")

        if grafica.get("marcadores"):
            marcadores_x, marcadores_y = grafica["marcadores"]
            for x, y in zip(marcadores_x, marcadores_y):
                px, py = proyectar(x, y)
                canvas.create_oval(px - 4, py - 4, px + 4, py + 4, fill="#D32F2F", outline="white")
            canvas.create_oval(izquierda + 155, 36, izquierda + 163, 44, fill="#D32F2F", outline="white")
            canvas.create_text(izquierda + 168, 40, text="Mediciones", anchor="w", fill="#37474F")

        if referencia_y is not None:
            y_ref, etiqueta = referencia_y
            _x_ref, py_ref = proyectar(minimo_x, y_ref)
            canvas.create_line(izquierda, py_ref, derecha, py_ref, fill="#D32F2F", dash=(5, 3), width=2)
            canvas.create_text(
                derecha - 4,
                py_ref - 9,
                text=f"{etiqueta}: {y_ref:.1f} °C",
                anchor="e",
                fill="#B71C1C",
                font=("Arial", 8, "bold"),
            )

        limite_recomendado = grafica.get("referencia_x")
        if limite_recomendado is not None:
            valores_limite = datos["temperaturas_limite"]
            temperatura_recomendada = min(
                valores_limite,
                key=lambda punto: abs(punto[0] - limite_recomendado * 100),
            )[1]
            px_ref, py_ref = proyectar(limite_recomendado * 100, temperatura_recomendada)
            canvas.create_line(px_ref, arriba, px_ref, abajo, fill="#2E7D32", dash=(4, 3), width=2)
            canvas.create_oval(px_ref - 5, py_ref - 5, px_ref + 5, py_ref + 5, fill="#2E7D32")

    def _calcular(self):
        try:
            tiempos, usos = self._obtener_datos()
            parametros = self.parametros.copy()
            parametros["t_inicio"] = tiempos[0]
            parametros["t_final"] = tiempos[-1]
            parametros["t_duracion"] = parametros["t_final"] - parametros["t_inicio"]
            if parametros["t_duracion"] <= 0:
                raise ValueError("El intervalo entre mediciones debe ser mayor que cero.")
            coeficientes, matriz_inicial, pasos_interpolacion = polinomio_unico(
                tiempos,
                usos,
            )

            paso, _cantidad = self._paso_efectivo(parametros["t_duracion"], DATOS_EJEMPLO["paso"])

            def objetivo(limite):
                return self._temperatura_final(limite, coeficientes, parametros, paso) - parametros["T_objetivo"]

            intervalo_inicial = DATOS_EJEMPLO["intervalo"]
            f_inferior = objetivo(intervalo_inicial[0])
            f_superior = objetivo(intervalo_inicial[1])
            f_uno = objetivo(1.0)
            temperatura_uno = f_uno + parametros["T_objetivo"]

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
                parametros["t_inicio"],
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
            if temperatura_uno <= parametros["T_objetivo"]:
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
                temperatura_con_limite = self._temperatura_final(
                    limite_recomendado,
                    coeficientes,
                    parametros,
                    paso,
                )
            else:
                limite_optimo = None
                limite_recomendado = None
                temperatura_con_limite = None

            paso_fino = parametros["t_duracion"] / 360.0
            tiempos_finos, temperaturas_finas = runge_kutta(
                crear_funcion(1.0, parametros, coeficientes),
                parametros["t_inicio"],
                parametros["T_inicial"],
                parametros["t_final"],
                paso_fino,
            )
            tiempo_cruce = minuto_cruce_meta(
                tiempos_finos,
                temperaturas_finas,
                parametros["T_objetivo"],
            )
            minuto_cruce = (
                None
                if tiempo_cruce is None
                else tiempo_cruce - parametros["t_inicio"]
            )

            if estado_tipo == "meta_inalcanzable":
                temperatura_final_minima = self._temperatura_final(
                    limite_minimo,
                    coeficientes,
                    parametros,
                    paso,
                )
            else:
                temperatura_final_minima = None

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
                and temperatura_con_limite > parametros["T_objetivo"]
            )
            paso_ajustado = not math.isclose(
                paso,
                DATOS_EJEMPLO["paso"],
                rel_tol=0.0,
                abs_tol=1e-10,
            )
            estado_conclusion = {
                "estado": estado_tipo,
                "duracion_minutos": parametros["t_duracion"],
                "temperatura_meta": parametros["T_objetivo"],
                "limite_optimo": limite_optimo,
                "limite_recomendado": limite_recomendado,
                "temperatura_final_sin_limite": temperatura_uno,
                "temperatura_final_con_limite": temperatura_con_limite,
                "temperatura_final_minima": temperatura_final_minima,
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
            muestras_tiempo = [
                parametros["t_inicio"] + parametros["t_duracion"] * indice / 120
                for indice in range(121)
            ]
            self._datos_graficas = {
                "tiempos": tiempos,
                "usos": usos,
                "uso_estimado": [
                    (
                        tiempo,
                        max(0.0, min(100.0, evaluar_polinomio(coeficientes, tiempo))),
                    )
                    for tiempo in muestras_tiempo
                ],
                "temperaturas": list(zip(xs, temperaturas)),
                "meta": parametros["T_objetivo"],
                "temperaturas_limite": [
                    (
                        limite * 100,
                        self._temperatura_final(limite, coeficientes, parametros, paso),
                    )
                    for limite in (indice / 20 for indice in range(1, 21))
                ],
                "limite_recomendado": limite_recomendado,
            }
            self._dibujar_grafica()
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
            "F(L) = T_final(L) - T_meta",
            f"T_meta = {meta:.4f} °C",
            "",
            self._formatear_tabla(
                ["L (%)", "F(L) = T_final - T_meta (°C)"],
                [
                    [f"{intervalo_inicial[0] * 100:.2f}", f"{valor_inferior_inicial:.6f}"],
                    [f"{intervalo_inicial[1] * 100:.2f}", f"{valor_superior_inicial:.6f}"],
                ],
            ),
        ]
        if intervalo is None or resultado is None:
            lineas.extend([
                "",
                self._formatear_tabla(
                    ["L (%)", "F(L) (°C)"],
                    [
                        [
                            f"{limite * 100:.2f}",
                            f"{objetivo(limite):.6f}",
                        ]
                        for limite in (DATOS_EJEMPLO["busqueda_minima"], 1.0)
                    ],
                ),
            ])
            return "\n".join(lineas)

        if intervalo_cambiado:
            lineas.extend([
                "",
                "F(L_inf) * F(L_sup) >= 0",
                f"L_usado = [{intervalo[0] * 100:.2f}, {intervalo[1] * 100:.2f}] %",
            ])
        lineas.extend([
            "",
            "L_m = (L_inferior + L_superior) / 2",
            "F(L_inf) * F(L_m) < 0 -> [L_inf, L_m]",
            "F(L_inf) * F(L_m) > 0 -> [L_m, L_sup]",
            self._formatear_tabla(
                [
                    "n",
                    "L_inf (%)",
                    "L_sup (%)",
                    "F(L_inf) (°C)",
                    "F(L_sup) (°C)",
                    "L_m (%)",
                    "F(L_m) (°C)",
                    "E_a (%)",
                    "L_siguiente (%)",
                ],
                [
                    [
                        fila["paso"],
                        f"{fila['inferior'] * 100:.4f}",
                        f"{fila['superior'] * 100:.4f}",
                        f"{fila['f_inferior']:.5f}",
                        f"{fila['f_superior']:.5f}",
                        f"{fila['medio'] * 100:.4f}",
                        f"{fila['f_medio']:.5f}",
                        "---" if fila["error"] is None else f"{fila['error']:.4f}",
                        (
                            f"[{fila['medio'] * 100:.4f}, {fila['medio'] * 100:.4f}]"
                            if abs(fila["f_medio"]) <= 1e-12
                            else (
                                f"[{fila['inferior'] * 100:.4f}, {fila['medio'] * 100:.4f}]"
                                if fila["f_inferior"] * fila["f_medio"] < 0
                                else f"[{fila['medio'] * 100:.4f}, {fila['superior'] * 100:.4f}]"
                            )
                        ),
                    ]
                    for fila in resultado["detalle"]
                ],
            ),
            "",
            self._formatear_tabla(
                ["L_optimo (%)", "Error aproximado (p.p.)"],
                [[
                    f"{resultado['raiz'] * 100:.6f}",
                    f"{resultado['error_aproximado'] * 100:.6f}",
                ]],
            ),
        ])
        return "\n".join(lineas)

    def _crear_salida_interpolacion(self, tiempos, usos, coeficientes, matriz_inicial, pasos):
        variables = [f"t^{grado}" if grado > 1 else ("t" if grado == 1 else "1")
                     for grado in range(len(tiempos))]
        lineas = [
            "1. INTERPOLACIÓN",
            "P(t_i) = P_i",
            self._formatear_tabla(
                ["i", "t_i (min)", "P_i (%)"],
                [
                    [indice, f"{tiempo:.2f}", f"{uso:.2f}"]
                    for indice, (tiempo, uso) in enumerate(zip(tiempos, usos), start=1)
                ],
            ),
            "",
            "V * a = p",
            self._formatear_tabla(
                variables + ["P_i (%)"],
                [[f"{valor:.6g}" for valor in fila] for fila in matriz_inicial],
            ),
            "",
            "R_j <- R_j / pivote;  R_i <- R_i - m_ij * R_j",
        ]
        for paso in pasos:
            lineas.extend([
                "",
                f"j = {paso['columna'] + 1}",
                self._formatear_tabla(
                    variables + ["P_i (%)"],
                    [[f"{valor:.6g}" for valor in fila] for fila in paso["matriz"]],
                ),
            ])
        lineas.extend([
            "",
            self._formatear_tabla(
                ["Coeficiente", "Valor"],
                [[f"a_{i}", f"{valor:.8g}"] for i, valor in enumerate(coeficientes)],
            ),
            formatear_polinomio(coeficientes).replace("x", "t"),
        ])
        return "\n".join(lineas)

    def _crear_salida_runge_kutta(self, tiempos, temperaturas, pasos, parametros, paso):
        lineas = [
            "2. RUNGE-KUTTA DE CUARTO ORDEN",
            "dT/dt = f(t,T) = alfa * L * P(t) - k * (T - T_ambiente)",
            "",
            f"t_0 = {tiempos[0]:.4f} min;  T_0 = {parametros['T_inicial']:.4f} °C;  "
            f"T_ambiente = {parametros['T_ambiente']:.4f} °C",
            f"L = 1;  h = {paso:.6g} min;  T_meta = {parametros['T_objetivo']:.4f} °C",
            "",
            "k_1 = f(t_n, T_n)",
            "k_2 = f(t_n + h/2, T_n + h*k_1/2)",
            "k_3 = f(t_n + h/2, T_n + h*k_2/2)",
            "k_4 = f(t_n + h, T_n + h*k_3)",
            "T_(n+1) = T_n + h*(k_1 + 2*k_2 + 2*k_3 + k_4)/6",
            "",
            self._formatear_tabla(
                ["n", "t_n (min)", "h (min)", "T_n (°C)", "k_1", "k_2", "k_3", "k_4", "T_(n+1) (°C)"],
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
            self._formatear_tabla(
                ["t_n (min)", "T_n (°C)"],
                [[f"{tiempo:.3f}", f"{temperatura:.4f}"]
                 for tiempo, temperatura in zip(tiempos, temperaturas)],
            ),
        ]
        return "\n".join(lineas)

    @staticmethod
    def _paso_efectivo(t_final, paso):
        cantidad = max(1, round(t_final / paso))
        return t_final / cantidad, cantidad


def main():
    app = InterfazApp()
    app.mainloop()
