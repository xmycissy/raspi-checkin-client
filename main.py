import serial
import time
import threading
import sys
import RPi.GPIO as GPIO

# Pin config
WAKE_PIN = 23
RST_PIN = 24

# Bool value definition
TRUE = 1
FALSE = 0

# Basic response message definition
ACK_SUCCESS = 0x00
ACK_FAIL = 0x01
ACK_FULL = 0x04
ACK_NO_USER = 0x05
ACK_TIMEOUT = 0x08
ACK_GO_OUT = 0x0F

# User information definition
ACK_ALL_USER = 0x00
ACK_GUEST_USER = 0x01
ACK_NORMAL_USER = 0x02
ACK_MASTER_USER = 0x03
USER_MAX_CNT = 1000

# Command definition
CMD_HEAD = 0xF5
CMD_TAIL = 0xF5

# Init
GPIO.setmode(GPIO.BCM)
GPIO.setup(WAKE_PIN, GPIO.IN)
GPIO.setup(RST_PIN, GPIO.OUT)
GPIO.setup(RST_PIN, GPIO.OUT, initial=GPIO.HIGH)
SLEEPING = 0
LOCK = threading.RLock()
DEVICE = serial.Serial("/dev/ttyS0", 19200)
BUFFER = []


def init():
    GPIO.output(RST_PIN, GPIO.LOW)
    time.sleep(0.25)
    GPIO.output(RST_PIN, GPIO.HIGH)
    time.sleep(0.25)


def sendCommand(data, bytesNeed, timeout):
    global BUFFER

    checksum = 0
    sendBuffer = []

    sendBuffer.append(CMD_HEAD)
    for byte in data:
        sendBuffer.append(byte)
        checksum ^= byte
    sendBuffer.append(checksum)
    sendBuffer.append(CMD_TAIL)

    DEVICE.flushInput()
    DEVICE.write(sendBuffer)

    recvBuffer = []
    timeBefore = time.time()
    timeAfter = time.time()
    while timeAfter - timeBefore < timeout and len(recvBuffer) < bytesNeed:
        bytesCanRecv = DEVICE.inWaiting()
        if bytesCanRecv != 0:
            recvBuffer += DEVICE.read(bytesCanRecv)
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

    BUFFER = recvBuffer

    return ACK_SUCCESS


def buildResponse(status, data):
    return {
        "status": status,
        "data": data
    }


def getUserCount():
    global BUFFER

    cmdBuffer = [0x09, 0, 0, 0, 0]
    res = sendCommand(cmdBuffer, 8, 0.1)

    if res == ACK_TIMEOUT:
        return buildResponse(ACK_TIMEOUT, 0)
    if res == ACK_SUCCESS and BUFFER[4] == ACK_SUCCESS:
        return buildResponse(ACK_SUCCESS, BUFFER[3])
    else:
        return buildResponse(res, 0)


def main():
    init()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        if DEVICE != None:
            DEVICE.close()
        GPIO.cleanup()
        sys.exit()
