import signal
import sys
import os
import socket
import threading
import time
from datetime import datetime
from random import randint
from multiprocessing import Process 

# Constants
# we run 3 processes with pids 0, 1, 2, which will also be used as indexes
N_PROCESS = 3
MESSAGE_SIZE = 4
LOG_NAME = "LOG"

# change these constants to try different variants, e.g. differences in internal tick rates/probability of internal events
TICK_RANGE = [1, 6]
FIXED_TICKS = True
TICKS = [1, 5, 6]
INTERNAL_EVENT_CAP = 25

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

    # get pids of the other two processes
    otherProcesses = list({0, 1, 2} - {pid})
    otherProcesses.sort()
    print(f"[{pid}] communicating with {otherProcesses}")

    # maintain reference to servers for other two processes, indexed via their pid
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
                print(f"[{pid}] can't connect to {process} - terminating process")
                os.kill(os.getppid(), signal.SIGKILL)

    # open log file (overwriting if one already exists), with LOG_NAME suffix
    with open(f"logs/process{pid}{LOG_NAME}.txt", "w") as logFile:
        # mark down the number of ticks per second for this process
        logFile.write(f"ticks per second: {1/sleepDuration}\n")

        while True:
            # sleep for specified number of seconds
            print(f"[{pid}] sleeping for {sleepDuration} seconds")
            time.sleep(sleepDuration)

            # process messages from the message queue if they exist
            if messageQueue[pid]:
                # set logical clock to the maximum of local clock and received message; log event
                message = messageQueue[pid].pop(0)
                # logical clock IR2, then IR1
                clock = max(message, clock) + 1
                print(f"[{pid}] processed message, updated clock value to {clock}")
                logFile.write(f"[MESSAGE RECEIVED] | Global Time - {datetime.now().strftime('%H:%M:%S.%f')} | Queue Length - {len(messageQueue[pid])} | Clock Time - {clock}\n")
                # the operation was reading the message, time to sleep again after flushing
                logFile.flush()
                continue 

            # generate random number to decide what event will occur
            num = randint(1, INTERNAL_EVENT_CAP)
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
            print(f"[{pid}] sending messages to {len(toSend)} other process(es)")

            try:
                for rec in toSend:
                    print(f"[{pid}] sending message to {otherProcesses[rec]}")
                    sockets[otherProcesses[rec]].sendall(clock.to_bytes(MESSAGE_SIZE, "big"))
            except:
                print(f"[{pid}] there is an error communicating with the server - terminating process")
                # close all sockets
                for sock in sockets:
                    if sock:
                        sock.close()
                os.kill(os.getppid(), signal.SIGKILL)

            # update logical clock (IR1)
            clock += 1

            # log message send event
            if toSend:
                logFile.write(f"[MESSAGE(S) SENT] | Global Time - {datetime.now().strftime('%H:%M:%S.%f')} | Receiver(s) - {[otherProcesses[rec] for rec in toSend]} | Clock Time - {clock}\n")
            # log internal event
            else:
                logFile.write(f"[INTERNAL] | Global Time - {datetime.now().strftime('%H:%M:%S.%f')} | No Messages Sent | Clock Time - {clock}\n")

            # flush the log file to ensure that everything is written before the next clock cycle
            logFile.flush()


def service_connection(pid: int, clientSocket):
    """
    Adds messages sent to the server from a client to the appropriate process's message queue.

    Args:
    pid - the process id (must be 0, 1 or 2 and must be unique)
    clientSocket - the processes's client's socket object returned from .accept()
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
            print(f"[{pid}] there is an error communicating with a client - terminating process: {e}")
            clientSocket.close()
            os.kill(os.getppid(), signal.SIGKILL)

        # add message to the process's message queue
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
            except Exception as e:
                print(f"[{pid}] error accepting connection - terminating process: {e}")
                os.kill(os.getppid(), signal.SIGKILL)
            # start a new thread for each client connection
            listener = threading.Thread(target=service_connection, args=(pid, c,))
            listener.start()
            threads.append(listener)

def init_process(pid: int):
    """
    Initializes a process with a server thread which waits for incoming connections and adds
    incoming messages to the process's queue, and a processor thread that processes events and
    maintains the logical clock.

    Args:
    pid - the process id (must be 0, 1 or 2 and must be unique)
    """
    # start the server thread for each process
    server = threading.Thread(target=init_server, args=(pid,))
    server.start()
    threads.append(server)

    # randomly generate clock speed for process in terms of number of ticks per second
    clockTicks = randint(TICK_RANGE[0], TICK_RANGE[1])
    if FIXED_TICKS:
        clockTicks = TICKS[pid]
    processor = threading.Thread(target=process_messages, args=(pid, 1/clockTicks))
    processor.start()
    threads.append(processor)

if __name__ == "__main__":
    # optionally specify a suffix for the log file; the log name will be process<pid><LOG_NAME>.txt
    if len(sys.argv) >= 2:
        LOG_NAME = str(sys.argv[1])
    
    try:
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
    
    # catch interrupts; we do not currently close file descriptors 
    except KeyboardInterrupt:
        print("\nExiting...")
        os._exit(0)
        
    except:
        print("\nUnexpected error...")
        os._exit(1)