import socket
import select
import pickle

HEADER_LENGTH = 10
IP = "127.0.0.1"
PORT = 1234

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

server_socket.bind((IP, PORT))

server_socket.listen()

sockets_list = [server_socket]

clients = {}

chatrooms = {"main":[]}



def receiveMessage(client_socket):
    try:
        message_header = client_socket.recv(HEADER_LENGTH)

        if not len(message_header):
            return False

        message_length = int(message_header.decode("utf-8"))

        return {"header": message_header, "data": client_socket.recv(message_length)}

    except Exception as x:
        pass

def list_rooms(client):
    rooms = list(chatrooms.keys())
    rooms = pickle.dumps(rooms)
    rooms_header = f"{len(rooms):<{HEADER_LENGTH}}".encode("utf-8")
    client.send(rooms_header + rooms)

while True:

    read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

    for notified_socket in read_sockets:
        if notified_socket == server_socket:
            client_socket, client_address = server_socket.accept()
            user = receiveMessage(client_socket)

            if user:
                chatrooms['main'].append((client_socket, user['data']))

            sockets_list.append(client_socket)

            clients[client_socket] = user
            print(f"Accepted new connection from {client_address[0]}:{client_address[1]} username:{user['data'].decode('utf-8')}")

        else:
            rcvd_package = receiveMessage(notified_socket)

            if rcvd_package:
                if rcvd_package['data'].decode("utf-8") == "<<ListRooms>>":
                    list_rooms(notified_socket)
                    continue
                else:
                    message = pickle.loads(rcvd_package['data'])
                    room = message['room'].encode("utf-8")
                    room_header = f"{len(message['room']):<{HEADER_LENGTH}}".encode("utf-8")
                    message_header = f"{len(message['message']):<{HEADER_LENGTH}}".encode("utf-8")
                    message = message['message']
            else:
                message = False
            if message is False:
                print(f"closed connection from {clients[notified_socket]['data'].decode('utf-8')}")
                sockets_list.remove(notified_socket)
                del clients[notified_socket]
                continue
            user = clients[notified_socket]
            print(f"Received message from {user['data'].decode('utf-8')}: {message.decode('utf-8')}")

            for client_socket in clients:
                if client_socket != notified_socket:
                    client_socket.send(user['header'] + user['data'] + room_header + room + message_header + message)

    for notified_socket in exception_sockets:
        sockets_list.remove(notified_socket)
        del clients[notified_socket]