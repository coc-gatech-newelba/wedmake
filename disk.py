import datetime
import sys


class DiskEntry:
    """A disk entry."""

    def __init__(self, read_in_kb, write_in_kb):
        """Initialize a DiskEntry."""
        self._read_in_kb = read_in_kb
        self._write_in_kb = write_in_kb

    def read_in_kb(self):
        return self._read_in_kb

    def write_in_kb(self):
        return self._write_in_kb


def main():
    # List of timestamps and DiskEntry.
    timestamps = []
    disk_entries = []
    # Process disk raw file.
    with open(sys.argv[1]) as disk_file:
        for disk_line in disk_file:
            # Check if it is a comment.
            if disk_line[0] == '#':
                continue
            disk_entry_data = disk_line.split()
            timestamps.append(datetime.datetime.strptime(disk_entry_data[1], "%H:%M:%S.%f"))
            total_read_in_kb = 0
            total_write_in_kb = 0
            for disk_no in range((len(disk_entry_data) - 2) // 14):
                total_read_in_kb += int(disk_entry_data[disk_no * 14 + 5])
                total_write_in_kb += int(disk_entry_data[disk_no * 14 + 9])
            disk_entries.append(DiskEntry(total_read_in_kb, total_write_in_kb))
    # Write disk reads in kb.
    disk_reads_in_kb = [disk_entry.read_in_kb() for disk_entry in disk_entries]
    with open("diskread.data", 'w') as disk_read_file:
        for (timestamp, disk_read_in_kb) in zip(timestamps, disk_reads_in_kb):
            td = timestamp - timestamps[0]
            disk_read_file.write("%s.%s %s\n" % (td.seconds, td.microseconds, disk_read_in_kb))
    # Write disk writes in kb.
    disk_writes_in_kb = [disk_entry.write_in_kb() for disk_entry in disk_entries]
    with open("diskwrite.data", 'w') as disk_write_file:
        for (timestamp, disk_write_in_kb) in zip(timestamps, disk_writes_in_kb):
            td = timestamp - timestamps[0]
            disk_write_file.write("%s.%s %s\n" % (td.seconds, td.microseconds, disk_write_in_kb))


if __name__ == "__main__":
    main()
