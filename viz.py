import matplotlib.pyplot as plt
from datetime import datetime
import sys

# code to visualize everything

# variable to indicate the suffix of the log file from which to read data
LOG_NAME = "LOG"
# variable to indicate the suffix of the names for the charts
CHART_TAG = ""

# function to read in a date time string and convert it to a datetime object
# NOTE: don't run simulations across changes in days (across midnight), since we only record hour and below!
def get_datetime(s):
    return datetime.strptime(s, '%H:%M:%S.%f')

# function to get difference in two datetime objects in seconds (as a float)
def get_diff(d1, d2):
    return (d1 - d2).total_seconds()

# from the log file, this function calculates the logical clock values of the logged process, with global timestamps relative to
# some start dates; the timestamp is the seconds elapsed after the system starts
# returns a list of tuples of the form (timestamp, logical clock value)
def get_clock_updates(log_file, start_time):
    clock_updates = []
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines[1:]:
            data = line.split('|')
            date = data[1].split(' - ')[1].strip()
            t = get_diff(get_datetime(date), start_time)
            clock_val = int(data[-1].split(' - ')[1].strip())
            clock_updates.append((t, clock_val))
    return clock_updates

# this function does the same as above, but records the message queue lengths from the specified log
def get_queue_lengths(log_file, start_time):
    queue_lengths = []
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines[1:]:
            data = line.split('|')
            if 'MESSAGE RECEIVED' not in data[0]:
                continue
            date = data[1].split(' - ')[1].strip()
            t = get_diff(get_datetime(date), start_time)
            l = int(data[2].split(' - ')[1].strip())
            queue_lengths.append((t, l))
    return queue_lengths

# get the earliest recorded global timestamp for operations from the log file
def get_start_time(log_file):
    with open(log_file, 'r') as f:
        f.readline()
        line = f.readline()
        data = line.split('|')
        date = data[1].split(' - ')[1].strip()
        return get_datetime(date)
    
# find the number of ticks per second for the process that is logged in the file
def get_ticks(log_file):
    with open(log_file, 'r') as f:
        line = f.readline()
        data = line.split(':')
        return int(float(data[-1].strip()))

if __name__ == "__main__":
    # optionally specify the log file suffix
    if len(sys.argv) >= 2:
        LOG_NAME = str(sys.argv[1])
        
    # optionally provide a chart title suffix
    if len(sys.argv) >= 3:
        CHART_TAG = str(sys.argv[2])
            
    # get the log filenames
    process_filenames = []
    for i in range(3):
        process_filenames.append(f"logs/process{i}" + LOG_NAME + ".txt")
    # find ticks/sec for each logged process
    ticks = [get_ticks(f) for f in process_filenames]
    # set the start time for the entire system to be the earliest recorded global timestamp across all processes
    st = min([get_start_time(f) for f in process_filenames])
    print(f"global start time: {st.strftime('%H:%M:%S.%f')}")
    
    # PLOT THE CLOCK VALUES
    plt.figure()
    for i in range(3):
        process_clock_updates = get_clock_updates(process_filenames[i], st)
        xs = [x[0] for x in process_clock_updates]
        ys = [x[1] for x in process_clock_updates]
        plt.step(xs, ys, label=f"Machine {i}, {ticks[i]} ticks/s")
    plt.legend(loc=2)
    plt.xlabel("Global Time (s)")
    plt.ylabel("Logical Clock Value")
    plt.title("Machine Logical Clock Values")
    plt.savefig(f"figures/clock_updates{CHART_TAG}.png")
    
    # PLOT THE MESSAGE QUEUE LENGTHS
    plt.figure()
    for i in range(3):
        queue_lengths = get_queue_lengths(process_filenames[i], st)
        xs = [x[0] for x in queue_lengths]
        ys = [x[1] for x in queue_lengths]
        plt.step(xs, ys, label=f"Machine {i}, {ticks[i]} ticks/s")
    plt.legend(loc=2)
    plt.xlabel("Global Time (s)")
    plt.ylabel("Queue Length")
    plt.title("Machine Message Queue Lengths")
    plt.savefig(f"figures/queue_lengths{CHART_TAG}.png")