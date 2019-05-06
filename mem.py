import datetime
import numpy
import sys


class MemEntry:
    """A memory entry."""

    def __init__(self, tot, used):
        """Initialize a MemEntry."""
        self._tot = tot
        self._used = used

    def percentage(self):
        return round(self._used / self._tot, 2) * 100


def main():
    # List of timestamps and MemEntry.
    timestamps = []
    mem_entries = []
    # Process memory raw file.
    with open(sys.argv[1]) as mem_file:
        for mem_line in mem_file:
            # Check if it is a comment.
            if mem_line[0] == '#':
                continue
            mem_entry_data = mem_line.split()
            timestamps.append(datetime.datetime.strptime(mem_entry_data[1], "%H:%M:%S.%f"))
            mem_entries.append(MemEntry(int(mem_entry_data[2]), int(mem_entry_data[3])))
    mem_utils = [mem_entry.percentage() for mem_entry in mem_entries]
    # Write memory utilization.
    with open("mem.data", 'w') as mem_util_file:
        for (timestamp, mem_util) in zip(timestamps, mem_utils):
            td = timestamp - timestamps[0]
            mem_util_file.write("%s.%s %s\n" % (td.seconds, td.microseconds, mem_util))
    # Print statistics.
    print("Min memory utilization: %s%%" % numpy.min(mem_utils))
    print("Average memory utilization: %s%%" % numpy.average(mem_utils))
    print("Median memory utilization: %s%%" % numpy.median(mem_utils))
    print("Max memory utilization: %s%%" % numpy.max(mem_utils))
    print("Std deviation of memory utilization: %s%%" % numpy.std(mem_utils))


if __name__ == "__main__":
    main()
