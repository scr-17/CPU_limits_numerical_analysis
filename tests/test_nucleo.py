"""Pruebas del núcleo numérico y de la restricción sobre el pico térmico."""

import unittest

from src.conclusion import redactar_conclusion
from src.interfaz import InterfazApp
from src.interpolacion import polinomio_unico
from src.modelo import PARAMETROS_DEFECTO
from src.polinomio import evaluar_polinomio
from src.raices import biseccion


class InterpolacionTests(unittest.TestCase):
    def test_el_polinomio_pasa_por_las_mediciones(self):
        tiempos = [0.0, 30.0, 60.0, 90.0]
        usos = [40.0, 85.0, 100.0, 90.0]

        coeficientes, _, _ = polinomio_unico(tiempos, usos)

        for tiempo, uso in zip(tiempos, usos):
            self.assertAlmostEqual(
                evaluar_polinomio(coeficientes, tiempo),
                uso,
                places=6,
            )


class RestriccionDePicoTests(unittest.TestCase):
    def setUp(self):
        self.parametros = PARAMETROS_DEFECTO.copy()
        self.parametros["t_final"] = 90.0
        tiempos = [0.0, 30.0, 60.0, 90.0]
        usos = [20.0, 100.0, 100.0, 20.0]
        self.coeficientes, _, _ = polinomio_unico(tiempos, usos)

    def pico(self, limite):
        return InterfazApp._temperatura_maxima(
            limite,
            self.coeficientes,
            self.parametros,
            1.0,
        )[0]

    def final(self, limite):
        return InterfazApp._integrar(
            limite,
            self.coeficientes,
            self.parametros,
            1.0,
        )[1][-1]

    def test_el_limite_por_pico_no_supera_la_meta(self):
        resultado = biseccion(lambda limite: self.pico(limite) - 80.0, 0.05, 1.0, 0.5)

        self.assertLessEqual(self.pico(resultado["raiz"]), 80.5)

    def test_el_limite_por_temperatura_final_puede_superar_el_pico(self):
        resultado = biseccion(lambda limite: self.final(limite) - 80.0, 0.05, 1.0, 0.5)

        self.assertGreater(self.pico(resultado["raiz"]), 80.0)


class ConclusionTests(unittest.TestCase):
    def test_el_resultado_normal_habla_del_pico(self):
        estado = {
            "estado": "normal",
            "duracion_minutos": 90,
            "temperatura_meta": 80.0,
            "limite_optimo": 0.69,
            "limite_recomendado": 0.65,
            "temperatura_maxima_sin_limite": 104.2,
            "temperatura_final_sin_limite": 104.2,
            "temperatura_maxima_con_limite": 76.8,
            "temperatura_final_con_limite": 76.8,
            "minuto_en_que_llega_a_la_meta_sin_limite": 60,
            "rendimiento_perdido": 35,
            "tolerancia": 0.5,
            "numero_iteraciones": 10,
            "error_aproximado": 0.001,
            "polinomio": "P(t) = 40 + 2t",
        }

        texto = "".join(seccion for _, seccion in redactar_conclusion(estado))

        self.assertIn("pico", texto)
        self.assertIn("65 %", texto)


if __name__ == "__main__":
    unittest.main()
