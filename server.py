import socket


SERVER_HOST = '0.0.0.0'
SERVER_PORT = 8080

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server_socket.bind((SERVER_HOST, SERVER_PORT))
server_socket.listen(1)
print('Listening on port %s ...' % SERVER_PORT)

while True:
    connection, address = server_socket.accept()
    request = connection.recv(1024).decode()
    print(request)

    content = 'hello world'

    response = 'HTTP/1.0 200 OK\nContent-Length: ' + \
        str(len(content))+'\n\n' + content
    connection.sendall(response.encode())
    connection.close()

server_socket.close()
