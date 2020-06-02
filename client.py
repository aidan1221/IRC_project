import socket
import select
import errno
import sys
import pickle

def print_welcome_message():
    global username
    print("Welcome to the IRC Chat server!\n")
    username = input("Enter your username: ")
    print("Here is a list of available options:\n")
    print_top_options()


def print_top_options():

    top_menu = "\tTop Menu:\n" \
               "\t1. Join \"main\" room\n" \
               "\t2. Create new room and join\n" \
               "\t3. List available rooms to join\n" \
               "\t4. Disconnect"

    print(top_menu)

def print_room_options(room):
    print(f"Room name: {room}")
    room_options = "\tRoom Menu:\n" \
                   "\t<tm> : show Top menu\n" \
                   "\t<m> : show room menu\n" \
                   "\t<r> : show current room\n" \
                   "\t<u> : list users in room\n" \
                   "\t<dm> : direct message multiple rooms\n" \
                   "\t<e> : return to room chat\n" \
                   "\t<dc> : disconnect"

    print(room_options)

def get_top_option():
    option = None
    while option not in [1, 2, 3, 4]:
        try:
            option = int(input("Enter an number from the menu\n>"))
        except:
            pass
        if option not in [1, 2, 3, 4]:
            print("Invalid input, please enter a number from the menu")
    return option

def process_top_option(option, display_name):
    if option == 1:
        room = ("main", "join")
    elif option == 2:
        valid = False
        while not valid:
            room = input("Enter a room name, max length 24 characters\n>")
            if len(room) <= 24:
                valid = True
                room = (room, "join")
                room_join_message = f"<<JoinRoom>>{room[0]},{display_name}".encode("utf-8")
                room_join_header = f"{len(room_join_message):<{HEADER_LENGTH}}".encode("utf-8")
                client_socket.send(room_join_header + room_join_message)
            else:
                print("Room name must be 24 characters or less")
    elif option == 3:
        room = ("", "list")
    elif option == 4:
        room = ("", "disconnect")
    return room

def chat_in_room(room, display_name, reconnect=False, message=None):
    global client_socket, menu_options

    print_room_options(room)

    message_package = {"room": room, "message": "", "user": display_name}
    while True:

        sockets_list = [sys.stdin, client_socket]
        read_sockets, write_socket, error_socket = select.select(sockets_list, [], [])
        try:
            for socket in read_sockets:
                if socket == client_socket:
                    username_header = client_socket.recv(HEADER_LENGTH)
                    if not len(username_header):
                        print("Connection closed by server")
                        sys.exit()
                    username_length = int(username_header.decode("utf-8"))
                    username = str(client_socket.recv(username_length).decode("utf-8"))
                    room_header = client_socket.recv(HEADER_LENGTH)
                    room_length = int(room_header.decode("utf-8"))
                    room = client_socket.recv(room_length).decode("utf-8")
                    message_header = client_socket.recv(HEADER_LENGTH)
                    message_length = int(message_header.decode("utf-8"))
                    message = client_socket.recv(message_length).decode("utf-8")

                    print(f"{username} ({room}) > {message}")
                else:
                    if reconnect:
                        if message:
                            if message.strip() in menu_options:
                                return message.strip()
                            message = message.encode("utf-8")
                            message_package["message"] = message
                            message_to_deliver = pickle.dumps(message_package)
                            message_header = bytes(f"{len(message_to_deliver):<{HEADER_LENGTH}}", "utf-8")
                            client_socket.send(message_header + message_to_deliver)
                            sys.stdout.write(f"{display_name} ({message_package['room']}) > ")
                            sys.stdout.write(message.decode("utf-8"))
                            sys.stdout.flush()
                        reconnect = False

                    else:
                        message = sys.stdin.readline()
                        if message:
                            if message.strip() in menu_options:
                                return message.strip()
                            message = message.encode("utf-8")
                            message_package["message"] = message
                            message_to_deliver = pickle.dumps(message_package)
                            message_header = bytes(f"{len(message_to_deliver):<{HEADER_LENGTH}}", "utf-8")
                            client_socket.send(message_header + message_to_deliver)
                            sys.stdout.write(f"{display_name} ({message_package['room']}) > ")
                            sys.stdout.write(message.decode("utf-8"))
                            sys.stdout.flush()
        except IOError as e:
            if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                print("Read error", str(e))
                sys.exit()
            continue

        except Exception as e:
            print('Error', str(e))
            sys.exit()




def contact_server(room, msg=None):
    if room[1] == "join":
        return chat_in_room(room[0], display_name)
    elif room[1] == "reconnect":
        return chat_in_room(room[0], reconnect=True, message=msg)
    elif room[1] == "list":
        return display_rooms_list()
    elif room[1] == "disconnect":
        try:
            client_socket.shutdown(socket.SHUT_RDWR)
            client_socket.close()
        except Exception as e:
            print(f"Socket close error - {e}")
        print("Thanks for chatting!")
        sys.exit()

def display_rooms_list():
    list_message = "<<ListRooms>>".encode("utf-8")
    list_message_header = f"{len(list_message):<{HEADER_LENGTH}}".encode("utf-8")
    client_socket.send(list_message_header + list_message)
    while True:
        try:
            room_list_length = int(client_socket.recv(HEADER_LENGTH))
            room_list = client_socket.recv(room_list_length)
            room_list = pickle.loads(room_list)
        except:
            # wait for server
            continue
        if room_list_length:
            break
    print("List of available rooms:")
    for i in range(len(room_list)):
        print(f"{i + 1}. {room_list[i]}")
    return "<tm>"

def get_rooms_list():
    list_message = "<<ListRooms>>".encode("utf-8")
    list_message_header = f"{len(list_message):<{HEADER_LENGTH}}".encode("utf-8")
    client_socket.send(list_message_header + list_message)
    while True:
        try:
            room_list_length = int(client_socket.recv(HEADER_LENGTH))
            room_list = client_socket.recv(room_list_length)
            room_list = pickle.loads(room_list)
        except:
            # wait for server
            continue
        if room_list_length:
            break
    print("List of available rooms:")
    for i in range(len(room_list)):
        print(f"{i + 1}. {room_list[i]}")
    return room_list

def handle_room_option(option, room):
    if option == "<tm>":
        print_top_options()
        return "c"
    elif option == "<m>":
        print_room_options(room)
        return "r"
    elif option == "<r>":
        print(f"You are currently in room - {room[0]}")
        return "r"
    elif option == "<u>":
        list_users_in_room(room[0])
        return "r"
    elif option == "<dm>":
        room_list = get_rooms_list()
        print("Please enter a comma separated list of the rooms you'd like to send your message to:")
        user_choice = input(">").split(",")
        room_choices = []
        try:
            for num in user_choice:
                room_choices.append(int(num))
            direct_message_multiple_rooms(room_list, room_choices)
            return "r"
        except:
            print("Invalid list selection, please try again...")
            print_room_options()
            return ""
    elif option == "<e>":
        return "r"
    elif option == "<dc>":
        print("Thanks for chatting!")
        sys.exit()
    else:
        return ("reconnect", option)



def list_users_in_room(room):
    list_message = f"<<ListAllUsersInRoom>>{room}".encode("utf-8")

    list_message_header = f"{len(list_message):<{HEADER_LENGTH}}".encode("utf-8")
    client_socket.send(list_message_header + list_message)
    while True:
        try:
            user_list_length = int(client_socket.recv(HEADER_LENGTH))
            user_list = client_socket.recv(user_list_length)
            user_list = list(set(pickle.loads(user_list)))
        except:
            # wait for server
            continue
        if user_list_length:
            break
    print(f"Current Users in {room}:")
    for i in range(len(user_list)):
        print(f"{i + 1}. {user_list[i].decode('utf-8')}")
    return "<m>"


def direct_message_multiple_rooms(room_list, room_choices):
    rooms_to_message = []
    for num in room_choices:
        rooms_to_message.append(room_list[num - 1])
    print(f"Direct Messaging Rooms - {rooms_to_message}")
    message = input("Direct Message to Multiple Rooms > ").encode("utf-8")
    message_header = f"{len(message):<{HEADER_LENGTH}}".encode("utf-8")
    message_package = {}



HEADER_LENGTH = 10

IP = "127.0.0.1"
PORT = 1234

menu_options = ["<tm>", "<m>", "<r>", "<u>", "<dm>", "<n>", "<dc>", "<e>"]

# Initialize CLI for chat client
print_welcome_message()

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((IP, PORT))
client_socket.setblocking(False)

username = username.encode("utf-8")
username_header = f"{len(username):<{HEADER_LENGTH}}".encode("utf-8")
client_socket.send(username_header + username)
display_name = str(username.decode("utf-8"))

room = ("", "connect")
while room[1] != "disconnect":
    option = get_top_option()
    room = process_top_option(option, display_name)
    room_option = contact_server(room)
    handle = ""
    while handle != "c":
        handle = handle_room_option(room_option, room)
        if handle == "r":
            room_option = contact_server(room)
        if handle[0] == "reconnect":
            room[1] = "reconnect"
            room_option = contact_server(room, msg=handle[1])














# Alternate message handling from sentdex tutorial

    # message = input(f"{display_name} > ") # blocks input from other users
    #
    # if message:
    #     message = message.encode("utf-8")
    #     message_header = f"{len(message):<{HEADER_LENGTH}}".encode("utf-8")
    #     client_socket.send(message_header + message)
    # try:
    #     while True:
    #         # receive messages
    #         username_header = client_socket.recv(HEADER_LENGTH)
    #         if not len(username_header):
    #             print("Connection closed by server")
    #             sys.exit()
    #         username_length = int(username_header.decode("utf-8"))
    #         username = str(client_socket.recv(username_length).decode("utf-8"))
    #
    #         message_header = client_socket.recv(HEADER_LENGTH)
    #         message_length = int(message_header.decode("utf-8"))
    #         message = client_socket.recv(message_length).decode("utf-8")
    #
    #         print(f"{username} > {message}")