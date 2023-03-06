import signal
import os
import socket
import threading
import time
from datetime import datetime
from random import randint
from multiprocessing import Process 

# Constants
N_PROCESS = 3
MESSAGE_SIZE = 4

# ports for each process' server
ports = {0: 21522, 1: 21523, 2: 21524}

# stores messages for each of the three processes; since these queues are populated via socket communications and are never
# appended to directly by a process (when an event is generated) this is not considered shared memory
messageQueue = [[], [], []]

# maintain references to all threads to prevent garbage collection
threads = []

def process_messages(pid: int, sleepDuration: float):
    """
    Simulates the event handling that occurs at each clock tick in a process. Processes messages from other processes
    if they exist and randomly sends messages to other processes.

    Args:
    pid - the process id (must be 0, 1 or 2 and must be unique)
    sleepDuration - how long the process sleeps for between responding to events; equal to 1/(# ticks per second)
    """
    clock = 1
    global messageQueue

    # sleep to give time for all processes to be started
    time.sleep(5)

    # open log file (overwriting if one already exists)
    logFile = open(f"process{pid}LOG.txt", "w")

    # get pid of the other two processes
    otherProcesses = list({0, 1, 2} - {pid})
    otherProcesses.sort()
    print(f"[{pid}] communicating with {otherProcesses}")

    # maintain reference to servers for other two processes
    sockets = [None, None, None]

    # attempt to connect to other two processes
    for process in otherProcesses:
        connected = False
        sockets[process] = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        while not connected:
            try:
                sockets[process].connect(("localhost", ports[process]))
                connected = True
                print(f"[{pid}] connected to {process}")
            # if unable to connect, just try again
            except:
                print(f"[{pid}] can't connect to {process} - sleeping")
                time.sleep(1)

    while True:
        # sleep for specified number of seconds
        print(f"[{pid}] sleeping for {sleepDuration} seconds")
        time.sleep(sleepDuration)

        # process messages from the message queue if they exist
        if messageQueue[pid]:
            # set logical clock to the maximum of local clock and received message; log event
            message = messageQueue[pid].pop(0)
            clock = max(message, clock) + 1
            logFile.write(f"[MESSAGE RECEIVED] Time: {datetime.now().strftime('%H:%M:%S')} Queue Length: {len(messageQueue)} Clock Time: {clock}\n")
        else:
            # generate random number to decide what event will occur
            num = randint(1, 10)
            print(f"[{pid}] generated number {num}")

            # send to first, second or both of the other processes depending on number generated
            toSend = []
            if num == 1:
                toSend = [0]
            elif num == 2:
                toSend = [1]
            elif num == 3:
                toSend = [0, 1]
            

            # send messages
            print(f"[{pid}] sending messages to {len(toSend)} other processes ")

            try:
                for rec in toSend:
                    print(f"sending message to {otherProcesses[rec]}")
                    sockets[otherProcesses[rec]].sendall(clock.to_bytes(MESSAGE_SIZE, "big"))
            except:
                print(f"[{pid}] there is an error communicating with the server - terminating process")
                # close all sockets
                for sock in sockets:
                    if sock:
                        sock.close()
                os.kill(os.getppid(), signal.SIGKILL)

            # update logical clock
            clock += 1

            # log message send event
            for rec in toSend:
                logFile.write(f"[MESSAGE SENT] Time: {datetime.now().strftime('%H:%M:%S')} Receiver: {otherProcesses[rec]} Clock Time: {clock}\n")
            # log internal event
            if not toSend:
                logFile.write(f"[INTERNAL] Time: {datetime.now().strftime('%H:%M:%S')} Receiver: {pid} Clock Time: {clock}\n")

        # flush the log file to ensure that everything is written before the next clock cycle
        logFile.flush()


def service_connection(pid: int, clientSocket):
    """
    Adds messages sent to the server from a client to the appropriate process' message queue.

    Args:
    pid - the process id (must be 0, 1 or 2 and must be unique)
    clientSocket - the client's socket object returned from .accept()
    """
    global messageQueue
    while True:
        try:
            # each message is a MESSAGE_SIZE length encoding the logical clock value of the sender process
            rec = clientSocket.recv(MESSAGE_SIZE)
            # if the client sends 0 that means the client has disconnected; raise an exception (to be caught later)
            if not rec:
                print(f"[{pid}] client disconnected")
                raise
        # there is an error communicating with the client; quit the program
        except Exception as e:
            print(e)
            print(f"[{pid}] there is an error communicating with a client - terminating process")
            clientSocket.close()
            os.kill(os.getppid(), signal.SIGKILL)

        message = int.from_bytes(rec, "big")
        print(f"[{pid}] received message {message}")
        messageQueue[pid].append(message)


def init_server(pid: int):
    """
    Initializes the server for each processes using sockets and waits for connections. Upon connecting with
    a client, the server offloads processing of communications to the service_connections helper function.
    
    Args:
    pid - the process id (must be 0, 1 or 2 and must be unique)
    """
    # each process is associated with a port for its server; get the appropriate port
    serverPort = ports[pid]
    print(f"[{pid}] attempting to run on port {serverPort}")

    # start the server socket, bind it, and put it into listening mode capable of accepting 2 connections
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as serverSock:
        serverSock.bind(("localhost", serverPort))
        serverSock.listen(2)

        # a forever loop until the program exits
        while True:
            try:
                # wait for connections from the other two processes
                print(f"[{pid}] server waiting to accept connection...")
                c, addr = serverSock.accept()
                print(f"[{pid}] connected to process {addr[0]}:{addr[1]}")
            # if the .accept() function throws an error this is irrecoverable; exit the process with status code 7
            except:
                print(f"[{pid}] error accepting connection - terminating process")
                os.kill(os.getppid(), signal.SIGKILL)
            # start a new thread for each client connection
            listener = threading.Thread(target=service_connection, args=(pid, c,))
            listener.start()
            threads.append(listener)

def init_process(pid: int):
    """
    Initializes a process with a server thread which waits for incoming connections and a processor thread
    that processes events.

    Args:
    pid - the process id (must be 0, 1 or 2 and must be unique)
    """
    # start the server thread for each process
    server = threading.Thread(target=init_server, args=(pid,))
    server.start()
    threads.append(server)

    # randomly generate clock speed for process in terms of number of ticks per second
    clockTicks = randint(1, 6)
    processor = threading.Thread(target=process_messages, args=(pid, 1/clockTicks))
    processor.start()
    threads.append(processor)

if __name__ == "__main__":
    processes = []

    for i in range(N_PROCESS):
        # we give the three processes being run pids of 0, 1 and 2
        processes.append(Process(target=init_process, args=(i,)))
    
    # start all processes
    for process in processes:
        process.start()
    
    # join all processes
    for process in processes:
        process.join()