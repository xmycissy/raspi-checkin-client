import time
import socket
import threading
import sys
import requests
import serial
import RPi.GPIO as GPIO

# 各种配置
serverHost = '0.0.0.0'
serverPort = 8080
wakePin = 23
rstPin = 24
apiBase = 'http://xxx.com/'
apiToken = 'xxx'

# 传感器响应类型
ACK_SUCCESS = 0x00  # 操作成功
ACK_FAIL = 0x01  # 操作失败
ACK_FULL = 0x04  # 指纹数据库已满
ACK_NO_USER = 0x05  # 无此用户
ACK_USER_EXIST = 0x06  # 用户已存在
ACK_TIMEOUT = 0x08  # 采集超时

# 传感器命令格式
CMD_HEAD = 0xF5
CMD_TAIL = 0xF5

# 全局变量
isExiting = False
sensorRequest = False
sensorRequestID = 0
globalBuffer = []
userList = []
signLog = []


def sensorLoop():
    global isExiting, sensorRequest, sensorRequestID

    while True:
        if isExiting:
            break

        if sensorRequest:
            print("sensor:", sensorRequestID)
            sensorRequest = False

        time.sleep(0.1)


def checkLoop():
    while True:
        if isExiting:
            break

        time.sleep(300)


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
    global apiBase, apiToken

    if method == 'get':
        r = requests.get(apiBase + url, headers={'Token': apiToken})
        return (r.status_code, r.json())
    elif method == 'post':
        r = requests.post(apiBase + url, json=data,
                          headers={'Token': apiToken})
        return (r.status_code, r.json())
    else:
        return (0, {})


def getUserList():
    global isExiting, userList

    res = httpClient('get', 'users')
    if res[0] != 200:
        isExiting = True
        exiting()
        return

    for item in res[1]:
        userList.append({
            'id': item['id'],
            'feature': item['fingerprint'],
            'mac': item['mac']
        })


def sensorInit():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(wakePin, GPIO.IN)
    GPIO.setup(rstPin, GPIO.OUT)
    GPIO.setup(rstPin, GPIO.OUT, initial=GPIO.HIGH)
    GPIO.output(rstPin, GPIO.LOW)
    time.sleep(0.25)
    GPIO.output(rstPin, GPIO.HIGH)
    time.sleep(0.25)


def sendCommand(cmd, bytesNeed, timeout, data=[]):
    global globalBuffer

    checksum = 0
    sendBuffer = []
    dataSendBuffer = []

    sendBuffer.append(CMD_HEAD)
    for byte in cmd:
        sendBuffer.append(byte)
        checksum ^= byte
    sendBuffer.append(checksum)
    sendBuffer.append(CMD_TAIL)

    if len(data) > 0:
        checksum = 0
        dataSendBuffer.append(CMD_HEAD)
        for index, byte in enumerate(data):
            dataSendBuffer.append(byte)
            if index >= len(data) - 3:
                continue
            checksum ^= byte
        dataSendBuffer.append(checksum)
        dataSendBuffer.append(CMD_TAIL)

    sensorSerial.flushInput()
    sensorSerial.write(sendBuffer + dataSendBuffer)

    recvBuffer = []
    timeBefore = time.time()
    timeAfter = time.time()
    while timeAfter - timeBefore < timeout and len(recvBuffer) < bytesNeed:
        bytesCanRecv = sensorSerial.inWaiting()
        if bytesCanRecv != 0:
            recvBuffer += sensorSerial.read(bytesCanRecv)
        timeAfter = time.time()

    if len(recvBuffer) != bytesNeed:
        return ACK_TIMEOUT

    if recvBuffer[0] != CMD_HEAD:
        return ACK_FAIL
    if recvBuffer[bytesNeed - 1] != CMD_TAIL:
        return ACK_FAIL
    if recvBuffer[1] != sendBuffer[1]:
        return ACK_FAIL

    checksum = 0
    for index, byte in enumerate(recvBuffer):
        if index == 0:
            continue
        if index == 6:
            if checksum != byte:
                return ACK_FAIL
            else:
                break
        checksum ^= byte

    globalBuffer = recvBuffer

    return ACK_SUCCESS


# 取用户总数
def getUserCount():
    global globalBuffer

    cmdBuffer = [0x09, 0, 0, 0, 0]
    res = sendCommand(cmdBuffer, 8, 0.1)

    if res == ACK_TIMEOUT:
        return (ACK_TIMEOUT, 0)

    if res == ACK_SUCCESS and globalBuffer[4] == ACK_SUCCESS:
        return (ACK_SUCCESS, globalBuffer[3])
    else:
        return (res, 0)


# 删除所有用户
def clearAllUser():
    global globalBuffer

    cmdBuffer = [0x05, 0, 0, 0, 0]
    res = sendCommand(cmdBuffer, 8, 1)

    if res == ACK_TIMEOUT:
        return (ACK_TIMEOUT, False)

    if res == ACK_SUCCESS and globalBuffer[4] == ACK_SUCCESS:
        return (ACK_SUCCESS, True)
    else:
        return (ACK_FAIL, False)


# 比对 1:N
def compareOneToN():
    global globalBuffer

    cmdBuffer = [0x0C, 0, 0, 0, 0]
    res = sendCommand(cmdBuffer, 8, 10)

    if res == ACK_TIMEOUT:
        return (ACK_TIMEOUT, 0)

    if res == ACK_SUCCESS:
        if globalBuffer[4] == ACK_NO_USER:
            return (ACK_NO_USER, 0)
        elif globalBuffer[4] == ACK_TIMEOUT:
            return (ACK_TIMEOUT, 0)

        userID = (globalBuffer[2] << 8) + globalBuffer[3]
        return (ACK_SUCCESS, userID)
    else:
        return (ACK_FAIL, 0)


# 取指纹特征值并上传
def getFeature():
    global globalBuffer

    cmdBuffer = [0x23, 0, 0, 0, 0]
    res = sendCommand(cmdBuffer, 207, 10)

    if res == ACK_TIMEOUT:
        return (ACK_TIMEOUT, 0)

    if res == ACK_SUCCESS:
        if globalBuffer[4] == ACK_TIMEOUT:
            return (ACK_TIMEOUT, 0)
        elif globalBuffer[4] == ACK_FAIL:
            return (ACK_FAIL, 0)

        feature = globalBuffer[12:205]
        return (ACK_SUCCESS, feature)
    else:
        return (ACK_FAIL, 0)


# 按用户号存储特征值到存储芯片
def storeFeature(userID, feature):
    global globalBuffer

    dataBuffer = [(userID & 0x0FF00) >> 8, userID & 0x0FF, 1] + feature
    cmdBuffer = [0x41, 0, 196, 0, 0]
    res = sendCommand(cmdBuffer, 8, 1, dataBuffer)

    if res == ACK_TIMEOUT:
        return (ACK_TIMEOUT, 0)

    if res == ACK_SUCCESS:
        if globalBuffer[4] == ACK_FAIL:
            return (ACK_FAIL, 0)

        saveUserID = (globalBuffer[2] << 8) + globalBuffer[3]
        return (ACK_SUCCESS, saveUserID)
    else:
        return (ACK_FAIL, 0)


def storeUserList():
    global userList

    for user in userList:
        res = storeFeature(user['id'], user['feature'])
        if res[0] != ACK_SUCCESS:
            print("user %d store failed" % user['id'])


def exiting():
    serverSocket.close()
    sensorThread.join()
    checkThread.join()
    sys.exit()


def start():
    sensorInit()
    clearAllUser()
    getUserList()
    storeUserList()
    res = getUserCount()
    print("total %d users" % res[1])
    sensorThread.start()
    checkThread.start()
    httpServer()


# 线程和设备控制变量
serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sensorThread = threading.Thread(target=sensorLoop, name='SensorThread')
checkThread = threading.Thread(target=checkLoop, name='CheckThread')
sensorSerial = serial.Serial(
    port="/dev/ttyS0",
    baudrate=19200,
    bytesize=serial.EIGHTBITS,
    timeout=1
)

if __name__ == "__main__":
    try:
        start()
    except:
        isExiting = True
        print("exiting ...")
        time.sleep(1)
        exiting()
