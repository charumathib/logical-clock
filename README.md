# logical-clock

See our dev journal [here](https://docs.google.com/document/d/1EttB9NQpdAs-8JYJrimdUx13MBAETeq7eEAiZ5RocEs/edit?usp=sharing).

**TLDR**: Run `process.py`. Different computers are modeled as separate processes, each with their own queue for receiving messages. Each process has three threads: one for receiving messages passively from each of the other two machines, and one for the actual logic with the logical clock and sending messages. Each process’s queue is kept global in our code for easy access by threads. (This is not shared memory; none of the processes ever look into others’ queues). The processes are assigned a unique port number on localhost and they communicate via one-to-one sockets.

To visualize clock drift and message queue length, running this program will generate log files within the `logs` directory, of the form `process<pid>LOG.txt`, where `<pid>` is the process ID (0, 1, or 2). You can inspect these files yourself, or run `viz.py`, which will generate graphs based on these log files. (We also have some command-line arguments that support changing log file names, see the code for details. For example, you can run `python process.py LOGTEST`, then `python viz.py LOGTEST VIZTEST` to generate logs with filenames `process<pid>LOGTEST.txt` and charts ending with `VIZTEST.png`.) Don't run simulations that cross midnight, since that will mess up how we process timestamps.

`process_manual.py` provides an alternate method for simulating the machines, wherein you run the file in three separate terminals, and provide command-line ID arguments of 0, 1, and 2 in each terminal. You must instantiate running all programs within 10 seconds, and must supply arguments of 0, 1, or 2. This technically shows that we are indeed never using shared memory as each program is executing separately in its own terminal (and you can see each program printing in its own terminal), but we do not use this implementation for our experiments, since it's a bit bulkier to initialize, isn't functionally different, and isn't up to date with our visualization code.