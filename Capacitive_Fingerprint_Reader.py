#!/usr/bin/env python3.5
# -*- coding:utf-8 -*-

import serial
import time
import threading
import sys
import RPi.GPIO as GPIO



TRUE         =  1
FALSE        =  0

# Basic response message definition
ACK_SUCCESS           = 0x00
ACK_FAIL              = 0x01
ACK_FULL              = 0x04
ACK_NO_USER           = 0x05
ACK_TIMEOUT           = 0x08
ACK_GO_OUT            = 0x0F     # The center of the fingerprint is out of alignment with sensor

# User information definition
ACK_ALL_USER          = 0x00
ACK_GUEST_USER        = 0x01
ACK_NORMAL_USER       = 0x02
ACK_MASTER_USER       = 0x03

USER_MAX_CNT          = 1000        # Maximum fingerprint number

# Command definition
CMD_HEAD              = 0xF5
CMD_TAIL              = 0xF5
CMD_ADD_1             = 0x01
CMD_ADD_2             = 0x02
CMD_ADD_3             = 0x03
CMD_MATCH             = 0x0C
CMD_DEL               = 0x04
CMD_DEL_ALL           = 0x05
CMD_USER_CNT          = 0x09
CMD_COM_LEV           = 0x28
CMD_LP_MODE           = 0x2C
CMD_TIMEOUT           = 0x2E

CMD_FINGER_DETECTED   = 0x14



Finger_WAKE_Pin   = 23
Finger_RST_Pin    = 24

GPIO.setmode(GPIO.BCM)
GPIO.setup(Finger_WAKE_Pin, GPIO.IN)  
GPIO.setup(Finger_RST_Pin, GPIO.OUT) 
GPIO.setup(Finger_RST_Pin, GPIO.OUT, initial=GPIO.HIGH)

g_rx_buf            = []
PC_Command_RxBuf    = []
Finger_SleepFlag    = 0

rLock = threading.RLock()
ser = serial.Serial("/dev/ttyS0", 19200)



#***************************************************************************
# @brief    send a command, and wait for the response of module
#***************************************************************************/
def  TxAndRxCmd(command_buf, rx_bytes_need, timeout):
    global g_rx_buf
    CheckSum = 0
    tx_buf = []
    
    tx_buf.append(CMD_HEAD)         
    for byte in command_buf:
        tx_buf.append(byte)  
        CheckSum ^= byte
        
    tx_buf.append(CheckSum)  
    tx_buf.append(CMD_TAIL)  
         
    ser.flushInput()
    ser.write(tx_buf)
    
    g_rx_buf = [] 
    time_before = time.time()
    time_after = time.time()
    while time_after - time_before < timeout and len(g_rx_buf) < rx_bytes_need:  # Waiting for response
        bytes_can_recv = ser.inWaiting()
        if bytes_can_recv != 0:
            g_rx_buf += ser.read(bytes_can_recv)    
        time_after = time.time()
              
    if len(g_rx_buf) != rx_bytes_need:
        return ACK_TIMEOUT
    if g_rx_buf[0] != CMD_HEAD:       
        return ACK_FAIL
    if g_rx_buf[rx_bytes_need - 1] != CMD_TAIL:
        return ACK_FAIL
    if g_rx_buf[1] != tx_buf[1]:     
        return ACK_FAIL

    CheckSum = 0
    for index, byte in enumerate(g_rx_buf):
        if index == 0:
            continue
        if index == 6:
            if CheckSum != byte:
                return ACK_FAIL
        CheckSum ^= byte
            
    return  ACK_SUCCESS;


#***************************************************************************
# @brief    Get Compare Level
#***************************************************************************/    
def  GetCompareLevel():
    global g_rx_buf
    command_buf = [CMD_COM_LEV, 0, 0, 1, 0]
    r = TxAndRxCmd(command_buf, 8, 0.1)
    if r == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if r == ACK_SUCCESS and g_rx_buf[4] == ACK_SUCCESS:
        return g_rx_buf[3]
    else:
        return 0xFF
 

 #***************************************************************************
# @brief    Set Compare Level,the default value is 5, 
#           can be set to 0-9, the bigger, the stricter
#***************************************************************************/
def SetCompareLevel(level):
    global g_rx_buf
    command_buf = [CMD_COM_LEV, 0, level, 0, 0]
    r = TxAndRxCmd(command_buf, 8, 0.1)   
       
    if r == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if r == ACK_SUCCESS and g_rx_buf[4] == ACK_SUCCESS:	
        return  g_rx_buf[3]
    else:
        return 0xFF

#***************************************************************************
# @brief   Query the number of existing fingerprints
#***************************************************************************/
def GetUserCount():
    global g_rx_buf
    command_buf = [CMD_USER_CNT, 0, 0, 0, 0]
    r = TxAndRxCmd(command_buf, 8, 0.1)
    if r == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if r == ACK_SUCCESS and g_rx_buf[4] == ACK_SUCCESS:
        return g_rx_buf[3]
    else:
        return 0xFF

        
#***************************************************************************
# @brief   Get the time that fingerprint collection wait timeout
#***************************************************************************/        
def GetTimeOut():
    global g_rx_buf
    command_buf = [CMD_TIMEOUT, 0, 0, 1, 0]
    r = TxAndRxCmd(command_buf, 8, 0.1)
    if r == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if r == ACK_SUCCESS and g_rx_buf[4] == ACK_SUCCESS:
        return g_rx_buf[3]
    else:
        return 0xFF


#***************************************************************************
# @brief    Register fingerprint
#***************************************************************************/
def AddUser():
    global g_rx_buf
    r = GetUserCount()
    if r >= USER_MAX_CNT:
        return ACK_FULL	
        
    command_buf = [CMD_ADD_1, 0, r+1, 3, 0]
    r = TxAndRxCmd(command_buf, 8, 6)
    if r == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if r == ACK_SUCCESS and g_rx_buf[4] == ACK_SUCCESS:
        command_buf[0] = CMD_ADD_3
        r = TxAndRxCmd(command_buf, 8, 2)
        if r == ACK_TIMEOUT:
            return ACK_TIMEOUT
        if r == ACK_SUCCESS and g_rx_buf[4] == ACK_SUCCESS:
            return ACK_SUCCESS
        else:
            return ACK_FAIL 
    else:
        return ACK_FAIL


#***************************************************************************
# @brief    Clear fingerprints
#***************************************************************************/
def ClearAllUser():
    global g_rx_buf
    command_buf = [CMD_DEL_ALL, 0, 0, 0, 0]
    r = TxAndRxCmd(command_buf, 8, 5)
    if r == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if r == ACK_SUCCESS and g_rx_buf[4] == ACK_SUCCESS:  
        return ACK_SUCCESS
    else:
        return ACK_FAIL

        
 #***************************************************************************
# @brief    Check if user ID is between 1 and 3
#***************************************************************************/         
def IsMasterUser(user_id):
    if user_id == 1 or user_id == 2 or user_id == 3: 
        return TRUE
    else: 
        return FALSE

#***************************************************************************
# @brief    Fingerprint matching
#***************************************************************************/        
def VerifyUser():
    global g_rx_buf
    command_buf = [CMD_MATCH, 0, 0, 0, 0]
    r = TxAndRxCmd(command_buf, 8, 5);
    if r == ACK_TIMEOUT:
        return ACK_TIMEOUT
    if r == ACK_SUCCESS and IsMasterUser(g_rx_buf[4]) == TRUE:
        return ACK_SUCCESS
    elif g_rx_buf[4] == ACK_NO_USER:
        return ACK_NO_USER
    elif g_rx_buf[4] == ACK_TIMEOUT:
        return ACK_TIMEOUT
    else:
        return ACK_GO_OUT   # The center of the fingerprint is out of alignment with sensor

        
#***************************************************************************
# @brief    Analysis the command from PC terminal
#***************************************************************************/       
def Analysis_PC_Command():
    global Finger_SleepFlag
    
    if  PC_Command_RxBuf[0] == "CMD1" and Finger_SleepFlag != 1:
        print ("Number of fingerprints already available:  %d"  % GetUserCount())
    elif PC_Command_RxBuf[0] == "CMD2" and Finger_SleepFlag != 1:
        print ("Add fingerprint  (Each entry needs to be read two times: \"beep\",put the finger on sensor, \"beep\", put up ,\"beep\", put on again) ")
        r = AddUser()
        if r == ACK_SUCCESS:
            print ("Fingerprint added successfully !")
        elif r == ACK_FAIL:
            print ("Failed: Please try to place the center of the fingerprint flat to sensor, or this fingerprint already exists !")
        elif r == ACK_FULL:
            print ("Failed: The fingerprint library is full !")           
    elif PC_Command_RxBuf[0] == "CMD3" and Finger_SleepFlag != 1:
        print ("Waiting Finger......Please try to place the center of the fingerprint flat to sensor !")
        r = VerifyUser()
        if r == ACK_SUCCESS:
            print ("Matching successful !")
        elif r == ACK_NO_USER:
            print ("Failed: This fingerprint was not found in the library !")
        elif r == ACK_TIMEOUT:
            print ("Failed: Time out !")
        elif r == ACK_GO_OUT:
            print ("Failed: Please try to place the center of the fingerprint flat to sensor !")
    elif PC_Command_RxBuf[0] == "CMD4" and Finger_SleepFlag != 1:
        ClearAllUser()
        print ("All fingerprints have been cleared !")
    elif PC_Command_RxBuf[0] == "CMD5" and Finger_SleepFlag != 1:
        GPIO.output(Finger_RST_Pin, GPIO.LOW)
        Finger_SleepFlag = 1
        print ("Module has entered sleep mode: you can use the finger Automatic wake-up function, in this mode, only CMD6 is valid, send CMD6 to pull up the RST pin of module, so that the module exits sleep !")
    elif PC_Command_RxBuf[0] == "CMD6":
        if rLock.acquire(blocking=True, timeout=0.6) == True: 
            Finger_SleepFlag = 0
            GPIO.output(Finger_RST_Pin, GPIO.HIGH)
            time.sleep(0.25)    # Wait for module to start
            print ("The module is awake. All commands are valid !")
            rLock.release()
        
        
#***************************************************************************
# @brief   If you enter the sleep mode, then open the Automatic wake-up function of the finger,
#         begin to check if the finger is pressed, and then start the module and match
#***************************************************************************/
def Auto_Verify_Finger():
    while True:
        if rLock.acquire() == True:     
            # If you enter the sleep mode, then open the Automatic wake-up function of the finger,
            # begin to check if the finger is pressed, and then start the module and match
            if Finger_SleepFlag == 1:     
                if GPIO.input(Finger_WAKE_Pin) == 1:   # If you press your finger  
                    time.sleep(0.01)
                    if GPIO.input(Finger_WAKE_Pin) == 1: 
                        GPIO.output(Finger_RST_Pin, GPIO.HIGH)   # Pull up the RST to start the module and start matching the fingers
                        time.sleep(0.25)	   # Wait for module to start
                        print ("Waiting Finger......Please try to place the center of the fingerprint flat to sensor !")
                        r = VerifyUser()
                        if r == ACK_SUCCESS:
                            print ("Matching successful !")
                        elif r == ACK_NO_USER:
                            print ("Failed: This fingerprint was not found in the library !")
                        elif r == ACK_TIMEOUT:
                            print ("Failed: Time out !")
                        elif r == ACK_GO_OUT:
                            print ("Failed: Please try to place the center of the fingerprint flat to sensor !")
                            
                        #After the matching action is completed, drag RST down to sleep
                        #and continue to wait for your fingers to press
                        GPIO.output(Finger_RST_Pin, GPIO.LOW)

            rLock.release()
    
    

      
     
        