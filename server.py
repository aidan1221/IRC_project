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

def list_users_in_room(client, room):
    try:
        clients_in_room = chatrooms[room]
    except KeyError as e:
        chatrooms[room] = []
    users_in_room = []
    for c in clients_in_room:
        users_in_room.append(c[1])
    if len(users_in_room) == 0:
        users_in_room = ["ROOM IS EMPTY"]
    users_in_room = pickle.dumps(users_in_room)
    users_header = f"{len(users_in_room):<{HEADER_LENGTH}}".encode("utf-8")
    client.send(users_header + users_in_room)

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
                try:

                    if rcvd_package['data'].decode("utf-8") == "<<ListRooms>>":
                        list_rooms(notified_socket)
                        continue

                    elif rcvd_package['data'].decode("utf-8")[:22] == "<<ListAllUsersInRoom>>":
                        room = rcvd_package['data'].decode("utf-8")[22:]
                        list_users_in_room(notified_socket, room)
                        continue
                    elif rcvd_package['data'].decode("utf-8")[:12] == "<<JoinRoom>>":
                        room_and_user = rcvd_package['data'].decode("utf-8")[12:].split(",")
                        room = room_and_user[0]
                        user = room_and_user[1].encode("utf-8")
                        client_info = (notified_socket, user)
                        try:
                            chatrooms[room].append(client_info)
                        except KeyError as k:
                            print(f"Creating new room: {room}")
                            chatrooms[room] = [client_info]
                        continue

                except Exception as e:

                    message = pickle.loads(rcvd_package['data'])
                    user = message['user'].encode("utf-8")

                    client_info = (notified_socket, user)

                    if "DM" in message.keys():
                        user_header = f"{len(user):<{HEADER_LENGTH}}".encode("utf-8")
                        for r in message['rooms']:
                            room_header = f"{len(r):<{HEADER_LENGTH}}".encode("utf-8")
                            message_header = f"{len(message['message']):<{HEADER_LENGTH}}".encode("utf-8")
                            message = message['message'].encode("utf-8")
                            clients_in_room = []
                            for client in chatrooms[room]:
                                clients_in_room.append(client[0])

                            for client_socket in clients_in_room:
                                if client_socket != notified_socket:
                                    client_socket.send(user_header + user + room_header + room.encode(
                                        "utf-8") + message_header + message)
                        continue

                    # manage room information - client joins room before sending message to that room
                    # if they have not joined already
                    # If room doesn't exist yet, add to dict and create new client list for new room

                    room = message['room']

                    try:
                        if client_info not in chatrooms[room]:
                            chatrooms[room].append(client_info)

                    except KeyError as k:
                        print(f"Creating new room: {room}")
                        chatrooms[room] = [client_info]
                    for r in chatrooms.keys():
                        if client_info in chatrooms[r] and r != room:
                            chatrooms[r].remove(client_info)

                    room_header = f"{len(message['room']):<{HEADER_LENGTH}}".encode("utf-8")
                    message_header = f"{len(message['message']):<{HEADER_LENGTH}}".encode("utf-8")
                    message = message['message']
            else:
                message = False
            if message is False:
                print(f"closed connection from {clients[notified_socket]['data'].decode('utf-8')}")
                sockets_list.remove(notified_socket)
                for key in chatrooms.keys():
                    if notified_socket == chatrooms[key][0]:
                        chatrooms[key].remove((notified_socket, user))
                del clients[notified_socket]
                continue
            user = clients[notified_socket]
            print(f"Received message from {user['data'].decode('utf-8')}: {message.decode('utf-8')}")

            # only broadcast message to clients in specified room
            clients_in_room = []
            for client in chatrooms[room]:
                clients_in_room.append(client[0])

            for client_socket in clients_in_room:
                if client_socket != notified_socket:
                    client_socket.send(user['header'] + user['data'] + room_header + room.encode("utf-8") + message_header + message)

    for notified_socket in exception_sockets:
        sockets_list.remove(notified_socket)
        del clients[notified_socket]