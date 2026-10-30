"""

Se basa en la formula de enfriamiento de newton alterada
dT/dt = alfa * limite_de_rendimiento * carga_de_la_computadora
            -  constante_de_enfriamiento * (temperatura_registrada - temperatura_ambiental)

Esta se crea en la funcion crear_funcion, donde parametros es un diccionario con todos los parametros necesitados a lo largo de las operaciones

parametros = {
    'alfa':,            Constante de proporción entre el uso de la computadora y el calor físico
    'k':,               Constante de enfriamiento del material de la computadora
    'T_ambiente':,      Temperatura ambiente a la hora de iniciar la prueba
    'T_inicial':,       Temperatura de la computadora a la hora de iniciar las pruebas
    'T_objetivo':       Teperatura que se busca conseguir con el límite de uso
}

En crear_funcion, se devuelve una función que se puede enviar como argumento a runge_kutta para evaluar como en el método numérico

La función runge_kutta devuelve dos listas, una de valores de x y otra de y, como si se aplicase el método en un intervalo

"""

from polinomio import evaluar_polinomio


def crear_funcion(limite_cpu, parametros, coeficientes):
    def ecuacion_diferencial(tiempo, temperatura):
        carga_cpu = evaluar_polinomio(tiempo, coeficientes)
        calor_generado = parametros["alfa"] * limite_cpu * carga_cpu
        calor_disipado = parametros["k"] * (temperatura - parametros["T_ambiente"])

        return calor_generado - calor_disipado

    return ecuacion_diferencial


def runge_kutta(f, x_inicial, y_inicial, x_final, altura):
    pasos = int((x_final - x_inicial) / altura)

    x_valores = [x_inicial]
    y_valores = [y_inicial]

    for i in range(pasos):
        x_i = x_valores[-1]
        y_i = y_valores[-1]

        K1 = f(x_i, y_i)
        K2 = f(x_i + altura / 2, y_i + altura / 2 * K1)
        K3 = f(x_i + altura / 2, y_i + altura / 2 * K2)
        K4 = f(x_i + altura, y_i + altura * K3)

        y_siguiente = y_i + altura / 6.0 * (K1 + 2 * K2 + 2 * K3 + K4)

        x_valores.append(x_i + altura)
        y_valores.append(y_siguiente)

    return x_valores, y_valores
