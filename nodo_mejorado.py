import zmq # Para los sockets
import threading as th
from enum import Enum
import sys

class Nodo:

    # Constructor del nodo
    def __init__(self, id: int, matriz_adyacencia: list) -> None:
        self.id = id
        self.matriz_adyacencia = matriz_adyacencia
        self.estado = "RELEASED"
        self.votacion = False
        self.client_th = self.crea_clientes()
        self.sockets_cl = {}
        self.queue = []
        self.soc_server = self.inicia_servidor()
        self.peticion_entrada()

    # Los sockets cliente sirven para mandar mensajes a los demas nodos
    
    # Funcion que ejecutan los hilos
    def iniciar_cliente(self, puerto: int) -> None:
        ctx = zmq.Context()
        socket = ctx.socket(zmq.PUSH)
        socket.connect("tcp://localhost:"+puerto)
        self.sockets_cl[puerto] = socket

    # Crea la lista de los demas nodos (client_th)
    def crea_clientes(self) -> list:
        threads = []
        for cl in self.matriz_adyacencia:
            thread = th.Thread(target=self.iniciar_cliente, args=(cl, ))
            threads.append(thread)
        
        return threads
 
    # Inicia cada uno de los nodos de la lista de client_th
    def inicia_clientes(self) -> None: # Se inicia los hilos
        for thread in self.client_th:
            thread.start()

    #Inicia el servidor para escuchar los demas mensajes
    #Tambien esta funcion manda a llamar la funcion inicia_clientes
    def inicia_servidor(self) -> zmq.Socket: # Se inicia el socket para escuchar mensajes
        self.inicia_clientes()
        ctx = zmq.Context()
        socket = ctx.socket(zmq.PULL)
        socket.bind("tcp://*:"+self.id)
        return socket
    
    # Funcion que escucha las peticiones de los demas nodos
    # 1.- Peticion para entrar a la region critica (Wanted)
    # 2.- Peticion de retenido (Held)
    # 3.- Peticion de liberacion de la region critica (Released)
    # def listener(self) -> None:
    #     print("Escuchando peticiones...")
    #     no_respuestas = 0
    #     while True:
    #         msg = self.soc_server.recv_json()
    #         print(f"Se recibio una peticion con la siguiente informacion: {msg}")
    #         tipo_peticion = msg['tipo']
    #         if tipo_peticion == 1: # Petición de la región critica
    #             self.procesar_peticion(msg)
    #         elif tipo_peticion == 2:
    #             if no_respuestas < len(self.matriz_adyacencia) - 1: # Se comprueba que todos los votantes hayan mandado respuesta
    #                 no_respuestas += 1
    #             else: # Una vez que se cumple esto, se procede a cambiar el estado y entrar en la región critica
    #                 self.estado = 'HELD'
    #                 no_respuestas = 0
    #                 self.entrar_seccion_critica()
    #         elif tipo_peticion == 3: # Petición de liberación de la región critica
    #             self.salir_region_critica()
    #             self.peticion_entrada()

    def listener(self) -> None:
        self.peticion_entrada()
        print("Escuchando peticiones...")
        no_respuestas = 0
        while True:
            msg = self.soc_server.recv_json()
            print(f"Se recibio una peticion con la siguiente informacion: {msg}")
            tipo_peticion = msg['tipo']
            if tipo_peticion == 1: # Petición de la región critica
                self.procesar_peticion(msg)
            elif tipo_peticion == 2:
                if no_respuestas < len(self.matriz_adyacencia) - 1: # Se comprueba que todos los votantes hayan mandado respuesta
                    no_respuestas += 1
                else: # Una vez que se cumple esto, se procede a cambiar el estado y entrar en la región critica
                    self.estado = 'HELD'
                    no_respuestas = 0
                    self.entrar_seccion_critica()
            elif tipo_peticion == 3: # Petición de liberación de la región critica
                self.salir_region_critica()
                self.peticion_entrada()
    
    # Funcion que ejecuta el hilo que ejecuta la funcion listener
    def run(self) -> None:
        thread = th.Thread(target=self.peticion_entrada)
        thread.run() # Para crear un hilo que escuche todas las peticiones

    # Para que pi entre a la seccion critica
    def pedir_seccion_critica(self) -> None:
        self.estado = 'WANTED'
        msg = {"id": self.id, "tipo": 1}
        print("Enviando peticiones a los nodos")
        for cl in self.sockets_cl.values():
            cl.send_json(msg)
        no_respuestas = 0
        print("Esperando respuestas...")
        self.listener()
        
        
    # Al recibir una peticion para entrar a la seccion critica de pi a pj
    def procesar_peticion(self, peticion) -> None or dict:
        if self.estado == 'HELD' or self.votacion == True:
            self.queue.append(peticion)
        else:
            id_destino = peticion['id']
            respuesta = {"id": self.id, "tipo": 2}
            self.sockets_cl[id_destino].send_json(respuesta)
            self.votacion = True

    # Funcion que se ejecuta cuando un proceso esta en la seccion critica
    # Esta funcion tambien realiza la tarea de salir de la seccion critica
    def entrar_seccion_critica(self) -> None:
        print("Entrando a la seccion critica...")
        region_critica = open("region_critica.txt", 'a')
        msg = f"El proceso con id {self.id} entro a la region critica\n"
        print(msg)
        region_critica.write(msg)
        region_critica.close()
        peticion = {"id": self.id, "tipo": 3}
        self.estado = "RELEASED"
        for cl in self.sockets_cl.values():
            cl.send_json(peticion)
        # self.listener()
    
    # Al recibir una peticion para salir de la seccion critica
    def salir_region_critica(self) -> None:
        if len(self.queue) > 0:
            head = self.queue.pop(0)
            self.votacion = True
            id_destino = head['id']
            respuesta = {"id": self.id, "tipo": 2}
            self.sockets_cl[id_destino].send_json(respuesta)
        else:
            self.votacion = False

    # Funcion que le pregunta al usuario si quiere entrar a la seccion critica
    def peticion_entrada(self) -> None:
        if self.estado == 'RELEASED' and self.votacion == False:
            peticion = bool(input("Desea entrar a la seccion critica? 1.-Si  0.-No\n"))
            if peticion:
                self.pedir_seccion_critica()
            

# Funcion principal del programa
if __name__ == "__main__":
    id = input("Numero de puerto: ")
    matriz_adyacencia = []
    for i in range(0, 3):
        matriz_adyacencia.append(input("Numero de puerto: "))
    
    nodo = Nodo(id, matriz_adyacencia)
    # thread = th.Thread(target=entrada)
    # thread.start()
    nodo.run() 









        