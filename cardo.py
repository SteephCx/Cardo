# Este es el archivo principal de mi juego Cardo. Aquí está todo lo que ve
# y usa el jugador: los menús, las rondas, los puntos y el resultado final.
# La parte de MongoDB la dejé en otro archivo (base_datos.py), que importo
# como "bd", para no mezclar la lógica del juego con la base de datos.
import os
import sys

from pymongo.errors import PyMongoError

import base_datos as bd

sys.stdout.reconfigure(encoding="utf-8")  # para que se vea el emoji en Windows


def limpiar():
# Borra la pantalla. En Windows el comando es "cls" y en Linux/Mac "clear",
# y con os.name veo en qué sistema estoy. Lo uso para que el otro jugador
# no vea la carta que eligió el primero.
    os.system("cls" if os.name == "nt" else "clear")


def pedir_numero_rondas():
 # Le pregunto al usuario cuántas rondas quiere jugar, entre 3 y 10.
    try:
        n = int(input("¿Cuántas rondas quieren jugar? (3 a 10): "))
# Si el número está fuera del rango, uso 5 rondas por defecto.
        return n if 3 <= n <= 10 else 5
    except ValueError:
 # Si escriben letras en vez de un número, int() truena con ValueError.
# Lo atrapo y también dejo 5 rondas por defecto, así el juego no se cae.
        return 5


def calcular_puntos(carta, acierto):
    """Devuelve (puntos_cardoelector, puntos_cardomante)."""
# Reglas de puntos que programé:
# - Si el cardomante ACERTÓ la carta, él gana puntos y el cardoelector 0.
#   Gana el puntaje de la carta, pero si vale 2 o 3 le resto 1.
# - Si NO acertó, el cardoelector gana el puntaje completo de su carta
#   y el cardomante 0.
# La función regresa los dos valores juntos, como una tupla.
    if acierto:
        pts = carta["puntaje"] - 1 if carta["puntaje"] in (2, 3) else carta["puntaje"]
        return 0, pts
    return carta["puntaje"], 0


def elegir_carta(titulo, nombre, cartas):
# Esta función la uso dos veces: para que el cardoelector escoja su carta
# y para que el cardomante adivine. Por eso recibe el título como parámetro.
# El while True repite la pregunta hasta que el usuario escriba una opción válida.
    while True:
        print(f"{titulo} {nombre}\n")
        # enumerate con start=1 me da el número de cada carta empezando en 1
        # en vez de 0, que es más natural para quien juega.
        for i, carta in enumerate(cartas, start=1):
            print(f"{i}) {carta['descripcion']} ({carta['puntaje']})")
        eleccion = input("\n> ").strip()
        if eleccion in ("1", "2", "3"):
            return cartas[int(eleccion) - 1]
        # Si escribió otra cosa, limpio la pantalla, aviso y el ciclo vuelve a preguntar.
        limpiar()
        print("Opción no válida, elige 1, 2 o 3.\n")


def jugar_ronda(numero, cardoelector, cardomante):
# Aquí se juega una ronda completa y regreso un diccionario con todo lo que pasó,
# para guardarlo en MongoDB y usarlo después en el resultado final.
# Pido a la base las 3 cartas al azar de la ronda (de 3 categorías distintas).
        
    cartas = bd.obtener_cartas_ronda()
    # Primero elige el cardoelector. Limpio la pantalla después para que el
    # otro jugador no vea qué escogió.
    limpiar()
    carta_elegida = elegir_carta("Hora de elegir", cardoelector, cartas)
    limpiar()
    # Luego el cardomante intenta adivinar cuál fue, viendo las mismas 3 cartas.
    carta_adivinada = elegir_carta("Hora de adivinar", cardomante, cartas)
    limpiar()
    # Comparo por id_carta (no por la descripción) porque el id es único.
    # El resultado es True o False.
    acierto = carta_elegida["id_carta"] == carta_adivinada["id_carta"]
    # Desempaqueto la tupla que regresa calcular_puntos en dos variables.
    pts_elector, pts_mante = calcular_puntos(carta_elegida, acierto)

    return {
        "numero": numero,
        "cardoelector": cardoelector,
        "cardomante": cardomante,
        "cartas": cartas,
        "carta_elegida": carta_elegida,
        "carta_adivinada": carta_adivinada,
        "acierto": acierto,
        "puntos_cardoelector": pts_elector,
        "puntos_cardomante": pts_mante,
    }


def mostrar_resultado(ganador, rondas, totales):
    # Si ganador es None quiere decir que quedaron empatados:
    # muestro los puntos de cada jugador y salgo de la función con return.
    if ganador is None:
        print("¡Empate!\n")
        for nombre, pts in totales.items():
            print(f"{nombre}: {pts} puntos")
        return
# Armo dos listas con las cartas que le dieron puntos al ganador.
# Uso list comprehensions (un for dentro de una lista con filtro if).
# Las que ganó como cardomante: rondas donde él adivinó y acertó. 
    adivinadas = [
        f"{r['carta_elegida']['descripcion']} (+{r['puntos_cardomante']})"
        for r in rondas if r["cardomante"] == ganador and r["acierto"]
    ]
# Las que ganó como cardoelector: rondas donde él eligió y el otro falló.
    no_adivinadas = [
        f"{r['carta_elegida']['descripcion']} (+{r['puntos_cardoelector']})"
        for r in rondas if r["cardoelector"] == ganador and not r["acierto"]
    ]

    print(f"¡Gana {ganador}!\n")
    print('Puntos como "cardomante":')
# "\n".join(lista) junta los elementos en un solo texto, uno por renglón.
# Si la lista está vacía (que es falsa en Python), imprimo "(ninguno)".   
    print("\n".join(adivinadas) if adivinadas else "(ninguno)")
    print('\nPuntos como "cardoelector":')
    print("\n".join(no_adivinadas) if no_adivinadas else "(ninguno)")
    print(f"\nTotal de puntos:\n{totales[ganador]}")


def main():
# Primero verifico que MongoDB esté prendido. Si no, aviso qué hacer
# y termino con return, porque sin base de datos no se puede jugar.  
    try:
        bd.probar_conexion()
    except PyMongoError:
        print("No se pudo conectar con MongoDB en localhost:27017.")
        print("Revisa que el servicio MongoDB esté en ejecución.")
        return
# Pantalla de inicio y captura de los nombres.
# Con "or" dejo un nombre por defecto si el jugador solo da Enter.
    limpiar()
    print("Cardo \n")
    j1 = input("Nombre/alias del Jugador 1: ").strip() or "Jugador 1"
    j2 = input("Nombre/alias del Jugador 2: ").strip() or "Jugador 2"
# Si los dos escriben el mismo nombre, le agrego "(2)" al segundo.
# Esto es importante porque uso los nombres como llaves del diccionario
# de totales, y si fueran iguales se sumarían los puntos de los dos juntos.
    if j2 == j1:
        j2 = f"{j2} (2)"
    num_rondas = pedir_numero_rondas()

    jugadores = [j1, j2]
 # Creo la partida en MongoDB y guardo su _id para poder actualizarla después.
    id_partida = bd.registrar_partida(jugadores, num_rondas)

    rondas = [] #Se guarda cada ronda
    totales = {j1: 0, j2: 0}#marcador de cada jugador incializado en 0

    for i in range(num_rondas):
# Los roles se alternan cada ronda con el operador módulo (%):
# en las rondas pares (0, 2, 4...) elige el jugador 1 y en las impares
# elige el jugador 2. El cardomante siempre es el otro.
        cardoelector = jugadores[i % 2]        # los roles se alternan cada ronda
        cardomante = jugadores[(i + 1) % 2]
        # i empieza en 0, por eso le paso i + 1 como número de ronda.
        ronda = jugar_ronda(i + 1, cardoelector, cardomante)
        bd.agregar_ronda(id_partida, ronda) #se guarda al momento en la bd
        rondas.append(ronda) #y tambien en memoria para el resultado
        # Sumo los puntos de la ronda al marcador de cada uno.
        totales[cardoelector] += ronda["puntos_cardoelector"]
        totales[cardomante] += ronda["puntos_cardomante"]
        
# Defino el ganador. Si los totales son iguales es empate y dejo
# ganador en None. Si no, max() con key=totales.get me da el nombre
# del jugador que tiene más puntos.
    if totales[j1] == totales[j2]:
        ganador, puntos_ganador = None, totales[j1]
    else:
        ganador = max(totales, key=totales.get)
        puntos_ganador = totales[ganador]
# Cierro la partida en MongoDB con los puntos finales, el ganador
# y sus puntos (el empate queda guardado como ganador null).
    bd.cerrar_partida(
        id_partida,
        [{"nombre": nombre, "puntos": totales[nombre]} for nombre in jugadores],
        ganador,
        puntos_ganador,
    )

    limpiar()
    mostrar_resultado(ganador, rondas, totales)

# Esta condición hace que main() solo se ejecute si corro este archivo
# directamente (python cardo.py) y no cuando otro archivo lo importe.
if __name__ == "__main__":
    main()