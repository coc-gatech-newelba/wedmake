"""WED-Makefile parser."""


import re
import yaml


class Variable:
    """An experiment variable.

    Variables capture the state of experiment instances. Just like variables in the Bash programming
    language, they have no type and their values are essentialy character strings. More
    specifically, such strings must have at most 2048 characters, except newlines. A variable
    identifier must have at most 64 alphanumeric and underscore characters, necessarily starting
    with an alphabetic character and not ending with an underscore character. A variable has an
    associated permission that can be read-write, allowing its value to be overwritten, or
    read-only, preventing its value to be overwritten.

    If there exists a '_' character in a variable's identifier, its namespace is the substring from
    the beginning to the last '_' character; otherwise, its namespace is an empty string. For
    example:
    - "WEB_HTTPD_VERSION": namespace is "WEB_HTTPD".
    - "WEB_HTTPD_KEEPALIVE_MAXREQUESTS": namespace is "WEB_HTTPD_KEEPALIVE".
    - "SSHKEY": namespace is an empty string "".

    Values and permissions can be assigned to variables in two ways:
    (1) in a configuration file specifying the initial state of an experiment instance;
    (2) in a task's Bash script.
    """

    # Grammar:
    IDENTIFIER = r"[a-zA-Z][_a-zA-Z0-9]{0,62}[a-zA-Z0-9]|[a-zA-Z]"
    VALUE = r".{0,2048}"

    @staticmethod
    def is_valid_identifier(identifier):
        """Return True if the specified identifier is valid. Return False, otherwise.

        identifier -- [str] Identifier to evaluate.
        """
        return re.fullmatch(Variable.IDENTIFIER, identifier) is not None

    @staticmethod
    def validate_identifier(identifier):
        """Return the specified identifier itself if it is valid. Raise a SyntaxError, otherwise.

        identifier -- [str] Identifier to validate.
        """
        if Variable.is_valid_identifier(identifier):
            return identifier
        raise SyntaxError(
            "A variable identifier must have at most 64 alphanumeric and underscore characters, "
            "necessarily starting with an alphabetic character and not ending with an underscore "
            "character."
        )

    @staticmethod
    def is_valid_value(value):
        """Return True if the specified value is valid. Return False, otherwise.

        value -- [str] Value to evaluate.
        """
        return re.fullmatch(Variable.VALUE, value) is not None

    @staticmethod
    def validate_value(value):
        """Return the specified value itself if it is valid. Raise a SyntaxError, otherwise.

        value -- [str] Value to validate.
        """
        if Variable.is_valid_value(value):
            return value
        raise SyntaxError(
            "A value assigned to a variable must have at most 2048 characters, except newlines."
        )

    def __init__(self, identifier):
        """Initialize a variable.

        identifier -- [str] Identifier of the variable.
        """
        self._identifier = self.validate_identifier(identifier)

    def __lt__(self, other):
        """Return True if the identifier is lexicographically smaller than the other variable's
        identifier. Return False, otherwise.

        other -- [Variable] Variable to compare.
        """
        return self._identifier < other._identifier

    def __eq__(self, other):
        """Return True if the identifier is equal to the other variable's identifier. Return False,
        otherwise.

        other -- [Variable] Variable to compare.
        """
        return self._identifier == other._identifier

    def __hash__(self):
        """Return the hash value of the identifier."""
        return hash(self._identifier)

    def identifier(self):
        """Return the identifier."""
        return self._identifier

    def namespace(self):
        """Return the namespace."""
        return self._identifier[:self._identifier.rfind('_')] if '_' in self._identifier else ""


class Dependency:
    """An experiment or task dependency.

    A dependency tests the value assigned to a single variable. Its clause is declared by means of a
    subset of the Bash programming language extended with Python list constructors and membership
    operators. For the sake of simplicity, variable identifiers are always on the left of the
    comparison or membership operators. Just like in Bash scripts, the value of a variable is
    retrieved by putting the '$' in front of its identifier.

    More specifically, four types of dependency clauses can be declared:
    (1) Equality (=): Test whether the value assigned to a variable is equal to a string enclosed in
    single or double quotes. For example: $WEB_HTTPD_VERSION = "2.2.22".
    (2) Inequality (!=): Test whether the value assigned to a variable is not equal to a string
    enclosed in single or double quotes. For example: $WEB_HTTPD_HOMEDIR != "".
    (3) Membership (in): Test whether the value assigned to a variable is in a list of strings
    delimited by square brackets. Such strings are enclosed in single or double quotes and separated
    by commas. For example: $WEB_HARDWARE_TYPE in ["c8220", "pc3000"].
    (4) No membership (not in): Test whether the value assigned to a variable is not in a list of
    strings delimited by square brackets. Such strings are enclosed in single or double quotes and
    separated by commas. For example: $CLIENT_JAVA_VERSION not in ["1.6", "1.7"].
    """

    # Grammar:
    EQUALITY_CLAUSE = r"\$(" + Variable.IDENTIFIER + r")\s*=\s*('" + Variable.VALUE + r"'|\""+ \
            Variable.VALUE + r"\")"
    INEQUALITY_CLAUSE = r"\$(" + Variable.IDENTIFIER + r")\s*!=\s*('" + Variable.VALUE + r"'|\"" + \
            Variable.VALUE + r"\")"
    MEMBERSHIP_CLAUSE = r"\$(" + Variable.IDENTIFIER + r")\s+in\s+(\[.+\])"
    NOMEMBERSHIP_CLAUSE = r"\$(" + Variable.IDENTIFIER + r")\s+not\s+in\s+(\[.+\])"

    @staticmethod
    def is_equality_clause(clause):
        """Return True if the specified clause is an equality comparison. Return False, otherwise.

        clause -- [str] Clause to evaluate.
        """
        return re.fullmatch(Dependency.EQUALITY_CLAUSE, clause) is not None

    @staticmethod
    def is_inequality_clause(clause):
        """Return True if the specified clause is an inequality comparison. Return False, otherwise.

        clause -- [str] Clause to evaluate.
        """
        return re.fullmatch(Dependency.INEQUALITY_CLAUSE, clause) is not None

    @staticmethod
    def is_membership_clause(clause):
        """Return True if the specified clause is a membership evaluation. Return False, otherwise.

        clause -- [str] Clause to evaluate.
        """
        return re.fullmatch(Dependency.MEMBERSHIP_CLAUSE, clause) is not None

    @staticmethod
    def is_nomembership_clause(clause):
        """Return True if the specified clause is a no membership evaluation. Return False,
        otherwise.

        clause -- [str] Clause to evaluate.
        """
        return re.fullmatch(Dependency.NOMEMBERSHIP_CLAUSE, clause) is not None

    @staticmethod
    def validate_clause(clause):
        """Return the specified clause itself if it is valid. Raise a SyntaxError, otherwise.

        clause -- [str] Clause to validate.
        """
        if Dependency.is_equality_clause(clause) or \
                Dependency.is_inequality_clause(clause) or \
                Dependency.is_membership_clause(clause) or \
                Dependency.is_nomembership_clause(clause):
            return clause
        raise SyntaxError("Invalid dependency clause.")

    def __init__(self, clause):
        """Initialize a dependency.

        clause -- [str] Clause of the dependency.
        """
        self._clause = self.validate_clause(clause)

    def clause(self):
        """Return the clause."""
        return self._clause

    def on_variable(self):
        """Return the dependent variable."""
        if Dependency.is_equality_clause(self._clause):
            return Variable(self._clause.split('=')[0].strip()[1:])
        if Dependency.is_inequality_clause(self._clause):
            return Variable(self._clause.split('!')[0].strip()[1:])
        if Dependency.is_membership_clause(self._clause):
            return Variable(self._clause.split()[0][1:])
        if Dependency.is_nomembership_clause(self._clause):
            return Variable(self._clause.split()[0][1:])


class Guard:
    """An experiment or task guard.

    A guard comprises a set of dependencies to be satisfied by the state of an experiment instance
    (i.e., by a valuation of variables). Guards control the starting and termination of experiment
    instances (e.g., an experiment can only be started if all server hostnames are specified and
    terminated after the resulting log files are archived). They may also control the execution of
    tasks (e.g., an HTTP server can only be installed after some library is both installed and
    configured). Hence, the semantics of a guard depends on its type:
    - An experiment instance can only be started if its initial state (i.e., the first valuation of
    its variables) satisfies the initial guard defined in the WED-Makefile of that experiment;
    - An experiment instance can only be successfully terminated if its state (i.e., the current
    valuation of its variables) satisfies the final guard defined in the WED-Makefile of that
    experiment;
    - If the guard associated with a task is satisfied by the state of an experiment instance, the
    execution of that task is triggered for this experiment instance.
    """

    @staticmethod
    def validate_dependencies(dependencies):
        """Return the specified list of dependencies itself if it is valid. Raise a SyntaxError,
        otherwise.

        dependencies -- [str] Dependencies to validate.
        """
        if len(dependencies) <= 256:
            return dependencies
        raise SyntaxError("A guard must have at most 256 dependencies.")

    def __init__(self, clauses):
        """Initialize a guard.

        clauses -- [str/list of str] Dependency clause(s) of the guard.
        """
        self._dependencies = self.validate_dependencies([
            Dependency(clause)
            for clause in (clauses if isinstance(clauses, list) else [clauses])
        ])

    def dependencies(self):
        """Return the dependencies."""
        return self._dependencies

    def on_variables(self, namespace=None):
        """Return a sorted list with the dependent variables, possibly filtered by the specified
        namespace.

        namespace -- [str/None] Namespace to filter the dependent variables.
        """
        return sorted([
            variable
            for variable in set([dependency.on_variable() for dependency in self._dependencies])
            if namespace is None or variable.namespace() == namespace
        ])

    def on_variables_namespaces(self):
        """Return a sorted list with the namespaces of the dependent variables."""
        return sorted(set([variable.namespace() for variable in self.on_variables()]))


class Task:
    """An experiment task.

    A task performs an activity of the experiment (e.g., installing a library, initializing servers,
    running a workload). A task name must have at most 64 alphanumeric and underscore characters,
    necessarily starting with an alphabetic character and not ending with an underscore character.
    Each task comprises a guard and a Bash script, where the guard explicits the dependencies for
    executing the associated Bash script.
    """

    # Grammar:
    NAME = r"[a-zA-Z][_a-zA-Z0-9]{0,62}[a-zA-Z0-9]|[a-zA-Z]"

    @staticmethod
    def is_valid_name(name):
        """Return True if the specified name is valid. Return False, otherwise.

        name -- [str] Name to evaluate.
        """
        return re.fullmatch(Task.NAME, name) is not None

    @staticmethod
    def validate_name(name):
        """Return the specified name itself if it is valid. Raise a SyntaxError, otherwise.

        name -- [str] Name to validate.
        """
        if Task.is_valid_name(name):
            return name
        raise SyntaxError(
            "A task name must have at most 64 alphanumeric and underscore characters, necessarily "
            "starting with an alphabetic character and not ending with an underscore character."
        )

    def __init__(self, name, guard, bash_script):
        """Initialize a task.

        name -- [str] Name of the task.
        guard -- [Guard] Guard to be satisfied for executing the associated Bash script.
        bash_script -- [str] Bash script of the task.
        """
        self._name = self.validate_name(name)
        self._guard = guard
        self._bash_script = bash_script

    def name(self):
        """Return the name."""
        return self._name

    def guard(self):
        """Return the guard."""
        return self._guard

    def bash_script(self):
        """Return the Bash script."""
        return self._bash_script


class WEDMakefile:
    """An experiment specification.

    A WED-Makefile *W* comprises an initial guard, a final guard, and a set of tasks defined by
    means of the YAML markup language.
    
    An experiment instance *i* of *W* is initialized from a configuration file written as a plain
    Bash script specifying its initial state (i.e., the first valuation of its variables). *i* is
    started if its first state satisfies the initial guard defined in *W*. If *i* is started, all
    task guards defined in *W* are evaluated with respect to the first state of *i*. Satisfied
    guards trigger the execution of their associated Bash scripts for *i*. At the end of its
    execution, such a Bash script updates the state of *i*. It is worth noting that the execution of
    a task's Bash script for *i* is encapsulated in a database transaction and thus has the classic
    ACID properties. The task guards defined in *W* are evaluated again every time the state of *i*
    is updated. Finally, *i* is successfully terminated if its state satisfies the final guard
    defined in *W* and no Bash script is being executed for it.
    """

    def __init__(self, path):
        """Initialize a WED-Makefile.

        path -- [str] Path to the WED-Makefile to parse.
        """
        with open(path) as wedmakefile_file:
            wedmakefile = yaml.load(wedmakefile_file.read())
        self._initial_guard = Guard(wedmakefile["initial_guard"])
        self._final_guard = Guard(wedmakefile["final_guard"])
        self._tasks = [
            Task(task["name"], Guard(task["guard"]), task["bash"])
            for task in wedmakefile["tasks"]
        ]

    def initial_guard(self):
        """Return the initial guard."""
        return self._initial_guard

    def final_guard(self):
        """Return the final guard."""
        return self._final_guard

    def tasks(self):
        """Return the list of tasks."""
        return self._tasks

    def variables(self, namespace=None):
        """Return a sorted list of the variables, possibly filtered by the specified namespace.

        namespace -- [str/None] Namespace to filter the variables.
        """
        return sorted([variable for variable in set(
            self._initial_guard.on_variables() + self._final_guard.on_variables() + [
                variable
                for variable_list in [task.guard().on_variables() for task in self._tasks]
                for variable in variable_list
            ]
        ) if namespace is None or variable.namespace() == namespace])

    def variables_namespaces(self):
        """Return a sorted list with the namespaces of the variables."""
        return sorted(set([variable.namespace() for variable in self.variables()]))
