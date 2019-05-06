import datetime
import sys


class CpuEntry:
    """A CPU entry."""

    def __init__(self, user, nice, system, wait, irq, soft, steal, idle, total, guest, guest_n,
            intrpt):
        """Initialize a CpuEntry."""
        self._user = user
        self._nice = nice
        self._system = system
        self._wait = wait
        self._irq = irq
        self._soft = soft
        self._steal = steal
        self._idle = idle
        self._total = total
        self._guest = guest
        self._guest_n = guest_n
        self._intrpt = intrpt

    def user(self):
        return self._user

    def nice(self):
        return self._nice

    def system(self):
        return self._system

    def wait(self):
        return self._wait

    def irq(self):
        return self._irq

    def soft(self):
        return self._soft

    def steal(self):
        return self._steal

    def idle(self):
        return self._idle

    def total(self):
        return self._total

    def guest(self):
        return self._guest

    def guest_n(self):
        return self._guest_n

    def intrpt(self):
        return self._intrpt


def main():
    # List of timestamps and CpuEntry for each CPU.
    timestamps = []
    cpu_entries = []
    # Process CPU raw file.
    with open(sys.argv[1]) as cpu_file:
        for cpu_line in cpu_file:
            # Check if it is a comment.
            if cpu_line[0] == '#':
                continue
            cpu_entry_data = cpu_line.split()
            timestamps.append(datetime.datetime.strptime(cpu_entry_data[1], "%H:%M:%S.%f"))
            for cpu_no in range((len(cpu_entry_data) - 2) // 12):
                if len(cpu_entries) < cpu_no + 1:
                    cpu_entries.append([])
                cpu_entries[cpu_no].append(
                        CpuEntry(*cpu_entry_data[cpu_no * 12 + 2:cpu_no * 12 + 14])
                )
    # Write total utilization of each CPU.
    for cpu_no in range(len(cpu_entries)):
        if sum([int(cpu_entry.total()) for cpu_entry in cpu_entries[cpu_no]]) > 0:
            with open("cpu%s.data" % cpu_no, 'w') as cpu_util_file:
                for (timestamp, cpu_entry) in zip(timestamps, cpu_entries[cpu_no]):
                    td = timestamp - timestamps[0]
                    cpu_util_file.write("%s.%s %s\n" % (
                        td.seconds, td.microseconds, cpu_entry.total()
                    ))

if __name__ == "__main__":
    main()
