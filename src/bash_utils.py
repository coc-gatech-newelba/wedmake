"""Utilities to simplify the execution of Bash scripts."""


import subprocess


class BashScript:
    """A Bash script wrapper."""

    def __init__(self, source_code):
        """Write the specified source code into a temporary file with execution permissions.

        source_code -- [str] Source code of the wrapped Bash script.
        """
        self._path = subprocess.check_output("mktemp", shell=True).decode("utf-8").strip()
        with open(self._path, 'w') as bash_script_file:
            bash_script_file.write(source_code)
        subprocess.run("chmod +x %s" % self._path, shell=True)

    def execute(self, args=None):
        """Execute the wrapped Bash script and return the text it writes to the standard output.

        args -- [list of str/None] Command-line arguments to the wrapped Bash script.
        """
        if args is None:
            args = []
        return subprocess.check_output([self._path, *args])
