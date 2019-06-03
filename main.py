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
sensorRequest = False
sensorRequestID = 0


def sensorLoop():
    global isExiting, sensorRequest, sensorRequestID

    while True:
        if isExiting:
            break

        if sensorRequest:
            print("sensor:", sensorRequestID)
            sensorRequest = False

        time.sleep(0.1)


def httpServer():
    global isExiting, sensorRequest, sensorRequestID

    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serverSocket.bind((serverHost, serverPort))
    serverSocket.listen(1)

    print('listening on port %s ...' % serverPort)

    while True:
        if isExiting:
            break

        connection, address = serverSocket.accept()
        request = connection.recv(1024).decode()

        print('get request from', address)
        try:
            reqID = int(request.split(' ')[1][1:])
        except ValueError:
            reqID = 0

        print("request:", reqID)

        if reqID == 0:
            print('abort')
            content = 'no'
        else:
            print('accept')
            content = 'yes'

            sensorRequest = True
            sensorRequestID = reqID

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
        time.sleep(1)
        exiting()
