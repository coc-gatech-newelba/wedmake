import csv
import numpy
import sys

INTERVAL_SIZE = 200000

class LogEntry:
    """A TCP/IP event log entry."""

    def __init__(self, event, ts, sock_fd):
        """Initialize a LogEntry.

        event -- [str] Name of the invoked syscall: 'connect', 'sendto', or 'recvfrom'.
        ts -- [int] Timestamp generated when the syscall was invoked.
        sock_fd -- [int] File descriptor of the socket used by the syscall.
        """
        self._event = event
        self._ts = ts
        self._sock_fd = sock_fd

    def __lt__(self, other):
        """Less than comparison operator.

        other -- [LogEntry] Another LogEntry being compared against this.
        """
        return self._ts < other._ts

    def event(self):
        """Return the name."""
        return self._event

    def ts(self):
        """Return the timestamp."""
        return self._ts

    def sock_fd(self):
        """Return the socket file descriptor."""
        return self._sock_fd

    def __repr__(self):
        """Return a string representation."""
        return "[{event} -- TS: {ts}; SOCK_FD: {sock_fd}]".format(
                event=self._event, ts=str(self._ts), sock_fd=str(self._sock_fd)
        )

def main():
    log_entries = []
    # Process connect log file.
    with open('logs/milliScope_connect.csv') as connect_file:
        connect_reader = csv.DictReader(connect_file)
        for connect_row in connect_reader:
            # Check if it is an Apache HTTP server.
            if int(connect_row["PID"]) == int(sys.argv[1]) and \
                    int(connect_row["PORT"]) == int(sys.argv[2]):
                log_entries.append(
                        LogEntry("connect", int(connect_row["TS"]), int(connect_row["SOCK_FD"]))
                )
    # Process sendto log file.
    with open('logs/milliScope_sendto.csv') as sendto_file:
        sendto_reader = csv.DictReader(sendto_file)
        for sendto_row in sendto_reader:
            # Check if it is an Apache HTTP server.
            if int(sendto_row["PID"]) == int(sys.argv[1]) and \
                    int(sendto_row["PORT"]) == int(sys.argv[2]):
                log_entries.append(
                        LogEntry("sendto", int(sendto_row["TS"]), int(sendto_row["SOCK_FD"]))
                )
    # Process recvfrom log file.
    with open('logs/milliScope_recvfrom.csv') as recvfrom_file:
        recvfrom_reader = csv.DictReader(recvfrom_file)
        for recvfrom_row in recvfrom_reader:
            # Check if it is an Apache HTTP server.
            if int(recvfrom_row["PID"]) == int(sys.argv[1]) and \
                    int(recvfrom_row["PORT"]) == int(sys.argv[2]):
                log_entries.append(
                        LogEntry("recvfrom", int(recvfrom_row["TS"]), int(recvfrom_row["SOCK_FD"]))
                )
    # Sort all log entries by timestamp.
    log_entries.sort()
    # Aggregate log entries of the same request.
    requests = []
    for i in range(len(log_entries)):
        if log_entries[i].event() == "connect":
            request = [log_entries[i]]
            j = i + 1
            while j < len(log_entries) and (log_entries[j].event() != "connect" or
                    log_entries[i].sock_fd() != log_entries[j].sock_fd()):
                if log_entries[i].sock_fd() == log_entries[j].sock_fd():
                    request.append(log_entries[j])
                j += 1
            requests.append(request)
    # Calculate queue lengths.
    queue_lengths = [
        0
        for i in range(
            (max([request[-1].ts() for request in requests]) - requests[0][0].ts()) //
            INTERVAL_SIZE + 1
        )
    ]
    for request in requests:
        start_at_interval = (request[0].ts() - requests[0][0].ts()) // INTERVAL_SIZE
        finish_at_interval = (request[-1].ts() - requests[0][0].ts()) // INTERVAL_SIZE
        for interval in range(start_at_interval, finish_at_interval + 1):
            queue_lengths[interval] += 1
    with open('queue_length.data', 'w') as queue_length_file:
        for (i, queue_length) in enumerate(queue_lengths):
            queue_length_file.write("%s %s\n" % ((INTERVAL_SIZE / 1000000 * i), queue_length))
    # Print statistics.
    print("Number of intervals: %s" % len(queue_lengths))
    print("Min queue length: %s" % numpy.min(queue_lengths))
    print("Average queue length: %s" % numpy.average(queue_lengths))
    print("Median queue length: %s" % numpy.median(queue_lengths))
    print("Max queue length: %s" % numpy.max(queue_lengths))
    print("Std deviation of queue length: %s" % numpy.std(queue_lengths))

if __name__ == "__main__":
    main()
