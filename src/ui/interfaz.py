"""Interfaz independiente para el simulador de límite térmico del equipo."""

from __future__ import annotations

import json
import math
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

from ..configuracion import DATOS_EJEMPLO, PARAMETROS_DEFECTO
from ..numerico.interpolacion import polinomio_unico
from ..numerico.polinomio import evaluar_polinomio, formatear_polinomio
from ..numerico.raices import biseccion, buscar_intervalo_cambio_signo
from ..numerico.runge_kutta import (
    crear_funcion,
    minuto_cruce_meta,
    runge_kutta,
    runge_kutta_detallado,
)
from ..reportes.conclusion import redactar_conclusion


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
        self._ultimo_calculo = None
        self._graficas = {}
        self._datos_modificados = False
        self._estado_resultado_var = tk.StringVar(value="Ingresa datos y calcula.")
        self._crear_interfaz()
        self._crear_menu()
        self._generar_tabla(len(DATOS_EJEMPLO["tiempo"]))
        self._cargar_ejemplo()
        self._datos_modificados = False

    def _crear_interfaz(self):
        estilo = ttk.Style(self)
        if "clam" in estilo.theme_names():
            estilo.theme_use("clam")

        principal = ttk.Frame(self, padding=12)
        principal.pack(fill="both", expand=True)
        principal.columnconfigure(0, weight=1)
        principal.rowconfigure(4, weight=1)

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

        archivo_bar = ttk.Frame(principal)
        archivo_bar.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(archivo_bar, text="Archivo:").pack(side="left")
        ttk.Button(
            archivo_bar,
            text="Cargar datos...",
            command=self._cargar_datos,
        ).pack(side="left", padx=3)
        ttk.Button(
            archivo_bar,
            text="Guardar datos...",
            command=self._guardar_datos,
        ).pack(side="left", padx=3)
        ttk.Button(
            archivo_bar,
            text="Exportar informe...",
            command=self._exportar_informe,
        ).pack(side="left", padx=3)

        tabla = ttk.LabelFrame(principal, text="Uso del equipo por minuto", padding=6)
        tabla.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        self.table_inner = tabla

        acciones = ttk.Frame(principal)
        acciones.grid(row=4, column=0, sticky="nsew")
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

        self._crear_panel_graficas()
        self.notebook.bind(
            "<<NotebookTabChanged>>",
            lambda _event: self.after_idle(self._redibujar_graficas),
        )

    def _crear_panel_graficas(self):
        panel = ttk.Frame(self.notebook)
        self.notebook.add(panel, text="5. Gráficas")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(0, weight=1)
        panel.rowconfigure(1, weight=1)

        for clave, fila, relleno in (
            ("temperatura", 0, (0, 6)),
            ("carga", 1, 0),
        ):
            canvas = tk.Canvas(
                panel,
                background="white",
                highlightthickness=1,
                highlightbackground="#B0BEC5",
            )
            canvas.grid(row=fila, column=0, sticky="nsew", pady=relleno)
            canvas.bind("<Configure>", lambda _event: self._redibujar_graficas())
            self._graficas[clave] = canvas

        self._dibujar_mensaje_graficas("Calcula para ver las gráficas.")

    def _crear_menu(self):
        barra = tk.Menu(self, tearoff=False)
        archivo = tk.Menu(barra, tearoff=False)
        archivo.add_command(
            label="Cargar datos...",
            accelerator="Ctrl+O",
            command=self._cargar_datos,
        )
        archivo.add_command(
            label="Guardar datos...",
            accelerator="Ctrl+S",
            command=self._guardar_datos,
        )
        archivo.add_command(
            label="Exportar informe...",
            accelerator="Ctrl+E",
            command=self._exportar_informe,
        )
        archivo.add_separator()
        archivo.add_command(label="Salir", command=self.destroy)
        barra.add_cascade(label="Archivo", menu=archivo)
        self.config(menu=barra)
        self.bind("<Control-o>", lambda _event: self._cargar_datos())
        self.bind("<Control-s>", lambda _event: self._guardar_datos())
        self.bind("<Control-e>", lambda _event: self._exportar_informe())

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
        self._datos_modificados = True
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

    def _guardar_datos(self):
        try:
            tiempos, usos = self._obtener_datos()
        except ValueError as exc:
            messagebox.showerror("Datos inválidos", str(exc), parent=self)
            return
        ruta = filedialog.asksaveasfilename(
            parent=self,
            title="Guardar datos",
            defaultextension=".json",
            filetypes=[("Datos JSON", "*.json"), ("Todos los archivos", "*.*")],
            initialfile="datos_termicos.json",
        )
        if not ruta:
            return
        contenido = {
            "version": 1,
            "parametros": self.parametros,
            "mediciones": {"tiempo": tiempos, "uso": usos},
        }
        try:
            with open(ruta, "w", encoding="utf-8") as archivo:
                json.dump(contenido, archivo, ensure_ascii=False, indent=2)
        except OSError as exc:
            messagebox.showerror("No se pudo guardar", str(exc), parent=self)
            return
        self._estado_resultado_var.set("Datos guardados.")

    def _cargar_datos(self):
        ruta = filedialog.askopenfilename(
            parent=self,
            title="Cargar datos",
            filetypes=[("Datos JSON", "*.json"), ("Todos los archivos", "*.*")],
        )
        if not ruta:
            return
        try:
            with open(ruta, "r", encoding="utf-8") as archivo:
                contenido = json.load(archivo)
            tiempos, usos, parametros = self._leer_datos_json(contenido)
        except (OSError, ValueError) as exc:
            messagebox.showerror("No se pudo cargar", str(exc), parent=self)
            return
        if self._dialogo_parametros is not None and self._dialogo_parametros.winfo_exists():
            self._dialogo_parametros.destroy()
            self._dialogo_parametros = None
        self.parametros = parametros
        self._generar_tabla(len(tiempos))
        for (x_var, y_var), tiempo, uso in zip(self.data_vars, tiempos, usos):
            x_var.set(f"{tiempo:g}")
            y_var.set(f"{uso:g}")
        self._ultimo_calculo = None
        self._datos_modificados = True
        self._estado_resultado_var.set("Datos cargados; vuelve a calcular.")
        self._redibujar_graficas()

    @staticmethod
    def _leer_datos_json(contenido):
        if not isinstance(contenido, dict):
            raise ValueError("El archivo debe contener un objeto JSON.")
        mediciones = contenido.get("mediciones")
        if not isinstance(mediciones, dict):
            raise ValueError("Falta la sección 'mediciones'.")
        tiempos = mediciones.get("tiempo")
        usos = mediciones.get("uso")
        if not isinstance(tiempos, list) or not isinstance(usos, list):
            raise ValueError("Las mediciones deben incluir listas 'tiempo' y 'uso'.")
        if len(tiempos) != len(usos) or len(tiempos) < 2:
            raise ValueError("Debe haber al menos dos mediciones con tiempo y uso.")
        try:
            tiempos = [float(valor) for valor in tiempos]
            usos = [float(valor) for valor in usos]
        except (TypeError, ValueError) as exc:
            raise ValueError("Los tiempos y usos deben ser numéricos.") from exc
        if any(not math.isfinite(valor) for valor in tiempos + usos):
            raise ValueError("Los tiempos y usos deben ser finitos.")
        if tiempos[0] != 0:
            raise ValueError("La primera medición debe iniciar en el minuto 0.")
        if any(anterior >= actual for anterior, actual in zip(tiempos, tiempos[1:])):
            raise ValueError("Los tiempos deben estar en orden estrictamente creciente.")
        if any(tiempo < 0 or not 0 <= uso <= 100 for tiempo, uso in zip(tiempos, usos)):
            raise ValueError("Se requiere tiempo >= 0 y uso entre 0 y 100 %.")

        parametros = PARAMETROS_DEFECTO.copy()
        recibidos = contenido.get("parametros", {})
        if not isinstance(recibidos, dict):
            raise ValueError("La sección 'parametros' debe ser un objeto.")
        for clave in parametros:
            if clave not in recibidos:
                continue
            try:
                valor = float(recibidos[clave])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"El parámetro '{clave}' debe ser numérico.") from exc
            if not math.isfinite(valor):
                raise ValueError(f"El parámetro '{clave}' debe ser finito.")
            if clave in ("alfa", "k") and valor < 0:
                raise ValueError(f"El parámetro '{clave}' no puede ser negativo.")
            if clave == "T_objetivo" and valor <= 0:
                raise ValueError("La temperatura objetivo debe ser mayor que cero.")
            parametros[clave] = valor
        return tiempos, usos, parametros

    def _exportar_informe(self):
        if self._ultimo_calculo is None:
            messagebox.showinfo(
                "Sin resultados",
                "Primero calcula para poder exportar el informe.",
                parent=self,
            )
            return
        ruta = filedialog.asksaveasfilename(
            parent=self,
            title="Exportar informe",
            defaultextension=".txt",
            filetypes=[("Informe de texto", "*.txt"), ("Todos los archivos", "*.*")],
            initialfile="informe_termico.txt",
        )
        if not ruta:
            return
        try:
            with open(ruta, "w", encoding="utf-8") as archivo:
                archivo.write(self._crear_informe_texto())
        except OSError as exc:
            messagebox.showerror("No se pudo exportar", str(exc), parent=self)
            return
        self._estado_resultado_var.set("Informe exportado.")

    def _crear_informe_texto(self):
        datos = self._ultimo_calculo
        estado = datos["estado_conclusion"]
        parametros = datos["parametros"]
        lineas = [
            "SIMULADOR TÉRMICO DE LAPTOP",
            "=" * 40,
            f"Fecha: {datetime.now():%Y-%m-%d %H:%M}",
            "",
            "PARÁMETROS",
            "-" * 40,
            f"Temperatura ambiente: {parametros['T_ambiente']:.2f} °C",
            f"Temperatura inicial: {parametros['T_inicial']:.2f} °C",
            f"Calor por uso (alfa): {parametros['alfa']:.4f} °C/min",
            f"Enfriamiento (k): {parametros['k']:.4f} 1/min",
            f"Temperatura meta: {parametros['T_objetivo']:.2f} °C",
            "",
            "MEDICIONES",
            "-" * 40,
            self._formatear_tabla(
                ["Punto", "Tiempo (min)", "Uso (%)"],
                [
                    [indice, f"{tiempo:.2f}", f"{uso:.2f}"]
                    for indice, (tiempo, uso) in enumerate(
                        zip(datos["tiempos"], datos["usos"]),
                        start=1,
                    )
                ],
            ),
            "",
            "RESULTADOS",
            "-" * 40,
        ]
        if estado.get("limite_recomendado") is not None:
            lineas.extend([
                f"Límite recomendado: {estado['limite_recomendado'] * 100:.0f} %",
                f"Pico sin límite: {estado['temperatura_maxima_sin_limite']:.2f} °C",
                f"Pico con límite: {estado['temperatura_maxima_con_limite']:.2f} °C",
                f"Temperatura final con límite: {estado['temperatura_final_con_limite']:.2f} °C",
                f"Rendimiento perdido: {estado['rendimiento_perdido']:.0f} %",
            ])
        else:
            lineas.append("No se encontró un límite recomendado para estos datos.")
        lineas.extend([
            "",
            "CONCLUSIÓN",
            "-" * 40,
            self.texts["4. Resultado"].get("1.0", tk.END).strip(),
        ])
        for titulo in ("1. Interpolación", "2. Runge-Kutta", "3. Búsqueda de raíz"):
            lineas.extend([
                "",
                titulo.upper(),
                "-" * len(titulo),
                self.texts[titulo].get("1.0", tk.END).strip(),
            ])
        return "\n".join(lineas) + "\n"

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

    def _dibujar_mensaje_graficas(self, texto):
        for canvas in self._graficas.values():
            canvas.delete("all")
            ancho = canvas.winfo_width()
            alto = canvas.winfo_height()
            if ancho < 20 or alto < 20:
                ancho, alto = 300, 120
            canvas.create_text(
                ancho / 2,
                alto / 2,
                text=texto,
                fill="#78909C",
                font=("Arial", 11),
            )

    def _redibujar_graficas(self):
        if not self._graficas:
            return
        if self._ultimo_calculo is None:
            self._dibujar_mensaje_graficas("Calcula para ver las gráficas.")
            return
        self._dibujar_temperaturas(self._ultimo_calculo)
        self._dibujar_carga(self._ultimo_calculo)
        if self._datos_modificados:
            canvas = self._graficas["temperatura"]
            ancho = canvas.winfo_width()
            alto = canvas.winfo_height()
            if ancho > 320 and alto > 60:
                canvas.create_rectangle(
                    ancho - 300,
                    alto - 34,
                    ancho - 8,
                    alto - 12,
                    fill="#FFF3E0",
                    outline="#FB8C00",
                )
                canvas.create_text(
                    ancho - 14,
                    alto - 23,
                    text="Datos modificados; vuelve a calcular.",
                    anchor="e",
                    fill="#E65100",
                    font=("Arial", 9, "bold"),
                )

    def _dibujar_temperaturas(self, datos):
        series = [
            (
                "100 % del rendimiento",
                list(zip(datos["xs_uno"], datos["temperaturas_uno"])),
                "#C62828",
            )
        ]
        if datos.get("xs_con_limite") is not None:
            limite = datos["estado_conclusion"].get("limite_recomendado")
            etiqueta = (
                f"Límite {round(limite * 100)} %"
                if limite is not None
                else "Con límite"
            )
            series.append(
                (
                    etiqueta,
                    list(zip(datos["xs_con_limite"], datos["temperaturas_con_limite"])),
                    "#1565C0",
                )
            )
        self._dibujar_grafica(
            self._graficas["temperatura"],
            series,
            "Tiempo (min)",
            "Temperatura (°C)",
            "Temperatura durante la sesión",
            objetivo=datos["parametros"]["T_objetivo"],
            marcar_picos=True,
        )

    def _dibujar_carga(self, datos):
        coeficientes = datos["coeficientes"]
        t_final = datos["parametros"]["t_final"]
        cantidad = max(2, int(round(t_final)) + 1)
        xs = [t_final * indice / (cantidad - 1) for indice in range(cantidad)]
        ys = [
            max(0.0, min(100.0, evaluar_polinomio(coeficientes, x)))
            for x in xs
        ]
        self._dibujar_grafica(
            self._graficas["carga"],
            [("Carga efectiva", list(zip(xs, ys)), "#6A1B9A")],
            "Tiempo (min)",
            "Uso (%)",
            "Carga del equipo durante la sesión",
            y_minimo=0.0,
            y_maximo=100.0,
        )

    def _dibujar_grafica(
        self,
        canvas,
        series,
        x_label,
        y_label,
        titulo,
        objetivo=None,
        y_minimo=None,
        y_maximo=None,
        marcar_picos=False,
    ):
        canvas.delete("all")
        ancho = canvas.winfo_width()
        alto = canvas.winfo_height()
        if ancho < 120 or alto < 80:
            return

        margen_izq, margen_der, margen_sup, margen_inf = 62, 24, 34, 38
        area_ancho = ancho - margen_izq - margen_der
        area_alto = alto - margen_sup - margen_inf
        if area_ancho <= 0 or area_alto <= 0:
            return

        puntos = [punto for _, datos, _ in series for punto in datos]
        if not puntos:
            canvas.create_text(
                ancho / 2,
                alto / 2,
                text="Sin datos para graficar.",
                fill="#78909C",
                font=("Arial", 11),
            )
            return

        xs = [x for x, _ in puntos]
        ys = [y for _, y in puntos]
        x_min, x_max = min(xs), max(xs)
        if math.isclose(x_max, x_min):
            x_max = x_min + 1.0
        y_min = min(ys) if y_minimo is None else y_minimo
        y_max = max(ys) if y_maximo is None else y_maximo
        if objetivo is not None:
            y_min = min(y_min, objetivo)
            y_max = max(y_max, objetivo)
        if math.isclose(y_max, y_min):
            y_max = y_min + 1.0
        if y_minimo is None or y_maximo is None:
            margen_y = (y_max - y_min) * 0.08
            if y_minimo is None:
                y_min -= margen_y
            if y_maximo is None:
                y_max += margen_y
        if objetivo is not None:
            y_min = min(y_min, objetivo)
            y_max = max(y_max, objetivo)

        def px(x):
            return margen_izq + (x - x_min) / (x_max - x_min) * area_ancho

        def py(y):
            return margen_sup + (y_max - y) / (y_max - y_min) * area_alto

        canvas.create_rectangle(
            margen_izq,
            margen_sup,
            margen_izq + area_ancho,
            margen_sup + area_alto,
            outline="",
            fill="#FAFAFA",
        )

        pasos = 5
        for indice in range(pasos + 1):
            x = x_min + (x_max - x_min) * indice / pasos
            y = y_min + (y_max - y_min) * indice / pasos
            x_pix = px(x)
            y_pix = py(y)
            canvas.create_line(
                x_pix,
                margen_sup,
                x_pix,
                margen_sup + area_alto,
                fill="#ECEFF1",
            )
            canvas.create_line(
                margen_izq,
                y_pix,
                margen_izq + area_ancho,
                y_pix,
                fill="#ECEFF1",
            )
            canvas.create_text(
                x_pix,
                margen_sup + area_alto + 6,
                text=self._formatear_tick(x, x_max - x_min),
                anchor="n",
                fill="#546E7A",
                font=("Arial", 8),
            )
            canvas.create_text(
                margen_izq - 6,
                y_pix,
                text=f"{y:.1f}",
                anchor="e",
                fill="#546E7A",
                font=("Arial", 8),
            )

        canvas.create_line(
            margen_izq,
            margen_sup,
            margen_izq,
            margen_sup + area_alto,
            fill="#90A4AE",
        )
        canvas.create_line(
            margen_izq,
            margen_sup + area_alto,
            margen_izq + area_ancho,
            margen_sup + area_alto,
            fill="#90A4AE",
        )
        canvas.create_text(
            margen_izq + area_ancho / 2,
            12,
            text=titulo,
            anchor="n",
            fill="#263238",
            font=("Arial", 11, "bold"),
        )
        canvas.create_text(
            margen_izq + area_ancho / 2,
            alto - 8,
            text=x_label,
            anchor="s",
            fill="#37474F",
            font=("Arial", 9),
        )
        canvas.create_text(
            8,
            margen_sup - 8,
            text=y_label,
            anchor="sw",
            fill="#37474F",
            font=("Arial", 9),
        )

        if objetivo is not None:
            y_objetivo = py(objetivo)
            canvas.create_line(
                margen_izq,
                y_objetivo,
                margen_izq + area_ancho,
                y_objetivo,
                fill="#2E7D32",
                dash=(5, 4),
            )
            canvas.create_text(
                margen_izq + area_ancho - 4,
                y_objetivo - 4,
                text=f"Meta {objetivo:.1f} °C",
                anchor="se",
                fill="#2E7D32",
                font=("Arial", 8, "bold"),
            )

        for _etiqueta, datos, color in series:
            if len(datos) < 2:
                continue
            coordenadas = []
            for x, y in datos:
                coordenadas.extend([px(x), py(y)])
            canvas.create_line(*coordenadas, fill=color, width=2)
            if marcar_picos:
                x_pico, y_pico = max(datos, key=lambda punto: punto[1])
                x_pix, y_pix = px(x_pico), py(y_pico)
                canvas.create_oval(
                    x_pix - 4,
                    y_pix - 4,
                    x_pix + 4,
                    y_pix + 4,
                    fill=color,
                    outline="white",
                )
                canvas.create_text(
                    x_pix,
                    y_pix - 8,
                    text=f"{y_pico:.1f} °C",
                    anchor="s",
                    fill=color,
                    font=("Arial", 8, "bold"),
                )

        self._dibujar_leyenda(canvas, series, margen_izq + 10, margen_sup + 10)

    @staticmethod
    def _formatear_tick(valor, rango):
        if abs(rango) >= 10:
            return f"{valor:.0f}"
        if abs(rango) >= 1:
            return f"{valor:.1f}"
        return f"{valor:.2f}"

    def _dibujar_leyenda(self, canvas, series, x, y):
        if not series:
            return
        alto_linea = 18
        ancho = max(len(etiqueta) for etiqueta, _, _ in series) * 6 + 44
        alto = alto_linea * len(series) + 10
        canvas.create_rectangle(
            x,
            y,
            x + ancho,
            y + alto,
            fill="white",
            outline="#CFD8DC",
        )
        for indice, (etiqueta, _datos, color) in enumerate(series):
            y_linea = y + 8 + indice * alto_linea
            canvas.create_line(
                x + 8,
                y_linea + 5,
                x + 28,
                y_linea + 5,
                fill=color,
                width=2,
            )
            canvas.create_text(
                x + 34,
                y_linea,
                text=etiqueta,
                anchor="nw",
                fill="#263238",
                font=("Arial", 8),
            )

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

            xs_con_limite = None
            temperaturas_con_limite = None
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
            self._ultimo_calculo = {
                "tiempos": tiempos,
                "usos": usos,
                "coeficientes": coeficientes,
                "parametros": parametros.copy(),
                "xs_uno": xs_uno,
                "temperaturas_uno": temperaturas_uno,
                "xs_con_limite": xs_con_limite,
                "temperaturas_con_limite": temperaturas_con_limite,
                "estado_conclusion": estado_conclusion,
                "fecha": datetime.now(),
            }
            self._datos_modificados = False
            self._estado_resultado_var.set("Resultados actualizados.")
            self.notebook.select(3)
            self.after_idle(self._redibujar_graficas)
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
