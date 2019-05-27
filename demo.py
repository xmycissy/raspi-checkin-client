#!/usr/bin/env python3.5
# -*- coding:utf-8 -*-

from Capacitive_Fingerprint_Reader import *



def main():
   
    GPIO.output(Finger_RST_Pin, GPIO.LOW)
    time.sleep(0.25) 
    GPIO.output(Finger_RST_Pin, GPIO.HIGH)
    time.sleep(0.25)    # Wait for module to start
    while SetCompareLevel(5) != 5:                 
        print ("***ERROR***: Please ensure that the module power supply is 3.3V or 5V, the serial line connection is correct, the baud rate defaults to 19200, and finally the power is switched off, and then power on again")
        time.sleep(1)  
    print ("***************************** WaveShare Capacitive Fingerprint Reader Test *****************************")
    print ("Compare Level:  5    (can be set to 0-9, the bigger, the stricter)")
    print ("Number of fingerprints already available:  %d "  % GetUserCount())
    print (" send commands to operate the module: ")
    print ("  CMD1 : Query the number of existing fingerprints")
    print ("  CMD2 : Registered fingerprint  (Each entry needs to be read two times: \"beep\",put the finger on sensor, \"beep\", put up ,\"beep\", put on again) ")
    print ("  CMD3 : Fingerprint matching  (Send the command, put your finger on sensor after \"beep\".Each time you send a command, module waits and matches once) ")
    print ("  CMD4 : Clear fingerprints ")
    print ("  CMD5 : Switch to sleep mode, you can use the finger Automatic wake-up function (In this state, only CMD6 is valid. When a finger is placed on the sensor,the module is awakened and the finger is matched, without sending commands to match each time. The CMD6 can be used to wake up) ")
    print ("  CMD6 : Wake up and make all commands valid ")
    print ("***************************** WaveShare Capacitive Fingerprint Reader Test ***************************** ")

    thread_Auto_Verify_Finger = threading.Thread(target=Auto_Verify_Finger,args=())
    thread_Auto_Verify_Finger.setDaemon(True)
    thread_Auto_Verify_Finger.start()
    
    
    while  True:     
        print ("Please input command (CMD1-CMD6):", end=' ')
        PC_Command_RxBuf.append(input())
        Analysis_PC_Command()    
        del PC_Command_RxBuf[:]    # Clear PC_Command_RxBuf and prepare for the next time
        
         
if __name__ == '__main__':
        try:
            main()
        except KeyboardInterrupt:
            if ser != None:
                ser.close()               
            GPIO.cleanup()
            print("\n\n Test finished ! \n") 
            sys.exit()
        
      
      
      