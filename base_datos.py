import random
from datetime import datetime

from pymongo import MongoClient # libreria oficial para usar MongoDB desde Python
# Las cuatro colecciones donde tengo las cartas (las que cargue con las semillas)
# Sus nombres tienen que ser iguales a los de MongoDB

CATEGORIAS = ["situaciones", "objetos", "emociones", "lugares"]

# ---------- b) Conexion con la base local cardo ----------
# Me conecto al MongoDB que tengo instalado en mi compu localhost, puerto 27017,
# que es el puerto por defecto Puse serverSelectionTimeoutMS=3000 para que, si
# MongoDB esta apagado, falle en 3 segundos y no se quede esperando como 30.
cliente = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
# Selecciono la base de datos "cardo". Si no existiera, MongoDB la crea
# hasta que guarde algo en ella.
db = cliente["cardo"]


def probar_conexion():
    """Lanza un error si MongoDB no está disponible."""
    # Le mando un ping al servidor, Si responde todo bien si no
    # pymongo lanza una excepción que puedo atrapar en el programa principal
    # para avisarle al usuario que prenda MongoDB.
    cliente.admin.command("ping")


# ---------- a) Obtención de cartas aleatorias para la ronda ----------
def obtener_cartas_ronda():
    """Devuelve 3 cartas de 3 categorías distintas, sorteadas con $sample."""
# random.sample elige 3 categorías SIN repetir, así en una ronda nunca
# salen dos cartas de la misma categoría (de las 4 se queda con 3)   
    categorias = random.sample(CATEGORIAS, 3)
    cartas = []
    for categoria in categorias:
        # $sample con size 1 le pide a MongoDB un documento al azar,
        # asi el sorteo lo hace la base y no tengo que traer todas las cartas.
        # aggregate regresa un cursor, y con next() saco el primer y unico resultado 
        doc = next(db[categoria].aggregate([{"$sample": {"size": 1}}]))
# Del documento guardo solo lo que necesita el juego y le agrego
# la categoria para saber de que coleccion salio cada carta.       
        cartas.append({
            "categoria": categoria,
            "id_carta": doc["_id"],
            "descripcion": doc["descripcion"],
            "puntaje": doc["puntaje"],
        })
    return cartas


# ---------- b) Registro de la partida ----------

def registrar_partida(jugadores, num_rondas):
# Al empezar el juego creo el documento de la partida en la colección partidas.
# Los jugadores arrancan con 0 puntos y las rondas con una lista vacia
# que se va llenando conforme se juega. El ganador queda en None
# (null en MongoDB) hasta que termine la partida.
    resultado = db.partidas.insert_one({
        "fecha_inicio": datetime.now(),
        "num_rondas": num_rondas,
        # List comprehension: convierte cada nombre en { nombre, puntos: 0 }
        "jugadores": [{"nombre": nombre, "puntos": 0} for nombre in jugadores],
        "rondas": [],
        "ganador": None,
        "puntos_ganador": 0,
    })
    # Regreso el _id que genero MongoDB porque lo necesito despues para
    # saber a que partida agregarle las rondas y cual cerrar.
    return resultado.inserted_id


# ---------- c) Actualización de la partida ----------
def agregar_ronda(id_partida, ronda):
     # Busco la partida por su _id y con $push agrego la ronda al final del
     # arr o sea las rondas sin tocar el resto del documento.
    db.partidas.update_one({"_id": id_partida}, {"$push": {"rondas": ronda}})


def cerrar_partida(id_partida, jugadores, ganador, puntos_ganador):
     # Al terminar todas las rondas actualizo la partida con $set que
     # reemplaza solo los campos que le indico los puntajes finales de los
     # jugadores, quien gano y con cuantos puntos
    db.partidas.update_one(
        {"_id": id_partida},
        {"$set": {
            "jugadores": jugadores,
            "ganador": ganador,
            "puntos_ganador": puntos_ganador,
        }},
    )