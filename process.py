import sys
import socket
import threading
import time
from datetime import datetime
from random import randint

ports = {0: 21522, 1: 21523, 2: 21524}
messageQueue = []
threads = []
clock = 0

def process_messages(pid: int, sleepDuration: float):
    global clock
    # open log file (overwriting if one already exists)
    logFile = open(f"process{pid}LOG.txt", "w")

    # get pid of the other two processes
    otherProcesses = list({0, 1, 2} - {pid})
    sockets = [None, None, None]

    for process in otherProcesses:
        print(process)
        connected = False
        sockets[process] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(sockets[process])
        print(("localhost", ports[process]))
        while not connected:
            try:
                sockets[process].connect(("localhost", ports[process]))
                connected = True
                print(f"connected to {process}")
            # if unable to connect, just try again
            except Exception as e:
                continue
    
    # sleep for specified number of seconds
    time.sleep(sleepDuration)

    # process messages from the message queue
    if messageQueue:
        message = messageQueue.pop(0)
        clock = max(message, clock) + 1
        logFile.write(f"[MESSAGE RECEIVED] Time: {datetime.now().strftime('%H:%M:%S')} Queue Length: {len(messageQueue)} Clock Time: {clock}")
    else:
        # generate random number
        num = randint(1, 10)
        toSend = []
        if num == 1:
            toSend = [0]
        elif num == 2:
            toSend = [1]
        elif num == 3:
            toSend = [0, 1]
        
        # send messages
        for rec in toSend:
            print(f"sending message to {rec}")
            sockets[rec].sendall(clock.to_bytes(4, "big"))
        # update logical clock
        clock += 1
        # write log
        for rec in toSend:
            logFile.write(f"[MESSAGE SENT] Time: {datetime.now().strftime('%H:%M:%S')} Receiver: {otherProcesses[0]} Clock Time: {clock}")
        # internal event
        if not toSend:
            logFile.write(f"[INTERNAL] Time: {datetime.now().strftime('%H:%M:%S')} Receiver: {pid} Clock Time: {clock}")

def service_connection(clientSocket):
    global messageQueue
    while True:
        # TODO: add error handling
        # each message is 4 bytes encoding the logical clock value of the sender process
        val = clientSocket.recv(4)
        val = int.from_bytes(val, "big")
        messageQueue.append(val)
                
if __name__ == "__main__":
    # must specify a host and port to connect to
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <pid>")
        sys.exit(1)

    # get the port corresponding to the process's PID
    pid = int(sys.argv[1])
    serverPort = ports[pid]

    print(serverPort)
    # start the server socket, bind it, and put it into listening mode
    serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serverSock.bind(("localhost", serverPort))
    serverSock.listen(10)

    # calculate sleep duration for this process
    clockTicks = randint(1, 6)

    processor = threading.Thread(target=process_messages, args=(pid, 1/clockTicks))
    processor.daemon = True
    processor.start()
    threads.append(processor)
    
    # a forever loop until program exits
    while True:

        # TODO: add error handling
        # wait for connections from the other two processes
        print("Waiting to accept")
        c, addr = serverSock.accept()
        print(f"connected to process {addr[0]}:{addr[1]}")

        # multithreading setup for multiple concurrent client connections:
        # start a new thread for each client connection and return its identifier
        listener = threading.Thread(target=service_connection, args=(c,))
        listener.daemon = True
        listener.start()
        threads.append(listener)