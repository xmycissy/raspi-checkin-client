import time
import socket
import threading
import sys
import requests

# 各种配置
serverHost = '0.0.0.0'
serverPort = 8080

# 全局变量
isExiting = False
sensorActive = False


def sensorLoop():
    global isExiting, sensorActive

    while True:
        if isExiting:
            break

        if sensorActive:
            print("sensor!")
            sensorActive = False

        time.sleep(1)


def httpServer():
    global isExiting, sensorActive

    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind((serverHost, serverPort))
    serverSocket.listen(1)

    print('Listening on port %s ...' % serverPort)

    while True:
        if isExiting:
            break

        connection, address = serverSocket.accept()
        request = connection.recv(1024).decode()

        sensorActive = True

        print('Get request from ', address, ':')
        print('---\n', request, '\n---')

        content = 'hello world'

        response = 'HTTP/1.0 200 OK\nContent-Length: ' + \
            str(len(content))+'\n\n' + content
        connection.sendall(response.encode())
        connection.close()


def httpClient(method, url, data={}):
    if method == 'get':
        r = requests.get(url)
        return (r.status_code, r.json())
    elif method == 'post':
        r = requests.post(url, json=data)
        return (r.status_code, r.json())
    else:
        return (0, {})


def exiting():
    serverSocket.close()
    sensorThread.join()
    sys.exit()


def start():
    sensorThread.start()
    httpServer()


# 线程控制变量
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sensorThread = threading.Thread(target=sensorLoop, name='SensorThread')


if __name__ == "__main__":
    try:
        start()
    except:
        isExiting = True
        print("exiting ...")
        time.sleep(3)
        exiting()
