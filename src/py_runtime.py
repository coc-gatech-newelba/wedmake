"""Utilities to run experiments in the Python runtime."""


import os
import random
import re
import threading
import time

import bash_utils
import wedmakefile_parser


class PyExperimentInstanceState(dict):
    """An associative array to store the values and permissions assigned to experiment variables."""

    @staticmethod
    def render_capture_bash_script(setup, main):
        """Return a Bash script that first executes setup commands, then executes main commands, and
        finally writes the values and permissions assigned to global variables by main commands to
        the standard output.

        For each global variable updated by main commands, three lines are sequentially written to
        the standard output:
        1) [variable_identifier]
        2) [variable_value]
        3) [variable_permission], which can be either 'rw' (read-write) or 'ro' (read-only)

        setup -- [str] Bash commands to execute first whose updates to global variables are not
                 captured.
        main -- [str] Bash commands to execute last whose updates to global variables are captured.
        """
        return """#!/bin/bash
        env -i bash --noprofile --norc -c "
            # Treat unset variables as an error when substituting.
            set -u
            # Exit immediately if a command exits with a non-zero status.
            set -e
            {setup}
            ENV0=\$(mktemp)
            ENVF=\$(mktemp)
            (set -o posix; BASH_EXECUTION_STRING=; IFS=; :; set > \$ENV0)
            {main}
            (set -o posix; BASH_EXECUTION_STRING=; IFS=; :; set > \$ENVF)
            IFS=\$(echo -en '\n\b')
            attrs=\$(comm -13 \$ENV0 \$ENVF |
                grep -v '^PIPESTATUS=' |
                grep -v '^_=' |
                grep -v '^BASH_LINENO=' |
                grep -v '^FUNCNAME=' |
                grep -v '^SHELLOPTS=' |
                xargs -I{{lin}} echo \\"{{lin}}\\")
            for attr in \$attrs; do
                attr_assign=(\${{attr//=/\n}})
                echo \${{attr_assign[0]}}
                if [ \${{#attr_assign[@]}} = 2 ]; then
                    echo \${{attr_assign[1]}}
                else
                    echo
                fi
                (unset \${{attr_assign[0]}} 2> /dev/null) && echo rw
                (unset \${{attr_assign[0]}} 2> /dev/null) || echo ro
            done
        "
        """.format(
            setup=setup.replace(r'\"', r'\\"').replace(r'"', r'\"'),
            main=main.replace(r'\"', r'\\"').replace(r'"', r'\"')
        )

    @classmethod
    def from_bash_script(cls, setup, main, args=None):
        """Return a PyExperimentInstanceState initialized with the values and permissions assigned
        to global variables by main commands, which execute after setup commands.

        setup -- [str] Bash commands to execute first whose updates to global variables are not
                 captured.
        main -- [str] Bash commands to execute last whose updates to global variables are captured.
        args -- [list of str/None] Command-line arguments to setup and main commands.
        """
        ei_state = cls()
        bash_script = bash_utils.BashScript(
            PyExperimentInstanceState.render_capture_bash_script(setup, main)
        )
        variables = bash_script.execute(args).decode("utf-8").strip().split('\n')
        for identifier, value, permission in zip(variables[0::3], variables[1::3], variables[2::3]):
            identifier = wedmakefile_parser.Variable.validate_identifier(identifier)
            value = wedmakefile_parser.Variable.validate_value(value)
            assert permission in ("rw", "ro")
            ei_state[identifier] = value
            ei_state._permission[identifier] = permission
        return ei_state

    def __init__(self):
        """Initialize an empty PyExperimentInstanceState."""
        super().__init__()
        self._permission = dict()

    def is_readonly(self, variable_identifier):
        """Return True if the specified variable can only be read. Return False, otherwise.

        variable_identifier -- [str] Identifier of the variable to evaluate.
        """
        return self._permission.get(variable_identifier, "rw") == "ro"

    def is_readwrite(self, variable_identifier):
        """Return True if the specified variable can be read and written. Return False, otherwise.

        variable_identifier -- [str] Identifier of the variable to evaluate.
        """
        return not self.is_readonly(variable_identifier)

    def update(self, other):
        """Update the values and permissions of variables.

        other -- [PyExperimentInstanceState] Another PyExperimentInstanceState to update the values
                 and permissions of variables.
        """
        super().update(other)
        self._permission.update(other._permission)

    def diff(self, other):
        """Return a PyExperimentInstanceState initialized with the values and permissions of
        variables that differ from those of the other PyExperimentInstanceState.

        other -- [PyExperimentInstanceState] Another PyExperimentInstanceState to serve as a
                 reference for comparison.
        """
        diff_state = PyExperimentInstanceState()
        for variable_identifier, variable_value in self.items():
            if other.get(variable_identifier, None) != variable_value or \
                    other._permission[variable_identifier] != self._permission[variable_identifier]:
                diff_state[variable_identifier] = variable_value
                diff_state._permission[variable_identifier] = self._permission[variable_identifier]
        return diff_state


class PyDependency:
    """A dependency adapter to the Python runtime."""

    def __init__(self, dependency):
        """Wrap a wedmakefile_parser.Dependency.

        dependency -- [wedmakefile_parser.Dependency] Dependency to wrap.
        """
        self._dependency = dependency

    def is_satisfied_by(self, ei_state):
        """Return True if the specified PyExperimentInstanceState satisfies the wrapped dependency.
        Return False, otherwise.

        ei_state -- [PyExperimentInstanceState] PyExperimentInstanceState to evaluate.
        """
        equality_match = re.fullmatch(
            wedmakefile_parser.Dependency.EQUALITY_CLAUSE,
            self._dependency.clause()
        )
        if equality_match is not None:
            variable_identifier = equality_match.groups()[0]
            variable_value = equality_match.groups()[1][1:-1]
            if ei_state.get(variable_identifier, "") != variable_value:
                return False
            return True
        inequality_match = re.fullmatch(
            wedmakefile_parser.Dependency.INEQUALITY_CLAUSE,
            self._dependency.clause()
        )
        if inequality_match is not None:
            variable_identifier = inequality_match.groups()[0]
            variable_value = inequality_match.groups()[1][1:-1]
            if ei_state.get(variable_identifier, "") == variable_value:
                return False
            return True
        membership_match = re.fullmatch(
            wedmakefile_parser.Dependency.MEMBERSHIP_CLAUSE,
            self._dependency.clause()
        )
        if membership_match is not None:
            variable_identifier = membership_match.groups()[0]
            variable_values = membership_match.groups()[1]
            if ei_state.get(variable_identifier, "") not in eval(variable_values):
                return False
            return True
        nomembership_match = re.fullmatch(
            wedmakefile_parser.Dependency.NOMEMBERSHIP_CLAUSE,
            self._dependency.clause()
        )
        if nomembership_match is not None:
            variable_identifier = nomembership_match.groups()[0]
            variable_values = nomembership_match.groups()[1]
            if ei_state.get(variable_identifier, "") in eval(variable_values):
                return False
            return True


class CSDecorator:
    """A critical section decorator."""

    def __init__(self, lock):
        """Initialize a CSDecorator with the specified lock.

        lock -- [threading.Lock] Lock to acquire for entering the critical section.
        """
        self._lock = lock

    def __call__(self, f):
        """Wrap the specified function in a critical section.

        f -- [function] Function to wrap in a critical section.
        """
        def wrapped(*args):
            self._lock.acquire()
            res = f(*args)
            self._lock.release()
            return res
        return wrapped


class PyExperimentInstance:
    """An experiment instance to run in the Python runtime."""

    _ei_lock = threading.Lock()

    def __init__(self, wedmakefile, config_path, log, verbose):
        """Initialize a PyExperimentInstance with the specified parsed WED-Makefile, configuration
        file, and options.

        wedmakefile -- [wedmakefile_parser.WEDMakefile] Parsed WED-Makefile containing the
                       experiment specification.
        config_path -- [str] Path to the configuration file containing the initial state of the
                       experiment instance.
        log -- [bool] Enable/Disable logging.
        verbose -- [bool] Enable/Disable verbose mode.
        """
        self._wedmakefile = wedmakefile
        with open(config_path) as config_file:
            self._state = PyExperimentInstanceState.from_bash_script(
                setup="",
                main=config_file.read().strip()
            )
        for dependency in wedmakefile.initial_guard().dependencies():
            if not PyDependency(dependency).is_satisfied_by(self._state):
                raise RuntimeError(
                    "UnsatisfiedInitialGuard: The initial state does not satisfy dependency "
                    "{dependency_clause}.".format(
                        dependency_clause=dependency.clause()
                    )
                )
        self._logdir_path = None if log is False else ("log-" + time.strftime("%Y-%m-%d-%H-%M-%S"))
        if log:
            os.mkdir(self._logdir_path)
        self._verbose = verbose
        self._exceptions = []
        self._variable_locks = dict([
            (variable.identifier(), threading.Lock())
            for variable in wedmakefile.variables()
        ])

    def print_triggered_task_message(self, task):
        """Write a message to the standard output about triggering the execution of the specified
        task.

        task -- [wedmakefile_parser.Task] Task whose execution was triggered.
        """
        if self._verbose:
            print("{timestamp} - Triggered the execution of task {task}.".format(
                timestamp=time.strftime("%Y-%m-%d-%H-%M-%S"),
                task=task.name()
            ))
        else:
            print("-- Triggered the execution of task {task}.".format(task=task.name()))

    def print_finished_task_message(self, task, diff_state):
        """Write a message to the standard output about finishing the execution of the specified
        task.

        task -- [wedmakefile_parser.Task] Task whose execution was finished.
        diff_state -- [PyExperimentInstanceState] Values and permissions of variables updated by the
                      specified task.
        """
        if self._verbose:
            print("{timestamp} - Finished the execution of task {task}, "
                  "updating variable(s):".format(
                timestamp=time.strftime("%Y-%m-%d-%H-%M-%S"),
                task=task.name()
            ))
            for variable_identifier, variable_value in diff_state.items():
                print("    ({permission}) {identifier}=\"{value}\"".format(
                    permission="ro" if diff_state.is_readonly(variable_identifier) else "rw",
                    identifier=variable_identifier,
                    value=variable_value.replace(r'\"', r'\\"').replace(r'"', r'\"')
                ))
        else:
            print("-- Finished the execution of task {task}.".format(task=task.name()))

    def print_reached_final_state_message(self):
        """Write a message to the standard output about reaching a final state."""
        if self._verbose:
            print("{timestamp} - Reached final state:".format(
                timestamp=time.strftime("%Y-%m-%d-%H-%M-%S")
            ))
            for variable_identifier, variable_value in self._state.items():
                print("    ({permission}) {identifier}=\"{value}\"".format(
                    permission="ro" if self._state.is_readonly(variable_identifier) else "rw",
                    identifier=variable_identifier,
                    value=variable_value.replace(r'\"', r'\\"').replace(r'"', r'\"')
                ))
        else:
            print("-- Reached a final state.")

    @CSDecorator(_ei_lock)
    def is_in_final_state(self):
        """Return True if in a final state (i.e., reached a state that satisfies the final guard and
        no other thread is executing a task). Return False, otherwise."""
        # Try to grab all the locks to guarantee no other thread is executing a task.
        for (i, variable) in enumerate(self._wedmakefile.variables()):
            if not self._variable_locks[variable.identifier()].acquire(blocking=False):
                j = 0
                while j < i:
                    self._variable_locks[self._wedmakefile.variables()[j].identifier()].release()
                    j += 1
                return False
        is_in_final_state = True
        for dependency in self._wedmakefile.final_guard().dependencies():
            if not PyDependency(dependency).is_satisfied_by(self._state):
                is_in_final_state = False
        for variable in self._wedmakefile.variables():
            self._variable_locks[variable.identifier()].release()
        return is_in_final_state

    @CSDecorator(_ei_lock)
    def is_in_inconsistent_state(self):
        """Return True if in an inconsistent state (i.e., reached a state that does not satisfy the
        final guard nor the guard of any task and no other thread is executing a task). Return
        False, otherwise."""
        # Try to grab all the locks to guarantee no other thread is executing a task.
        for (i, variable) in enumerate(self._wedmakefile.variables()):
            if not self._variable_locks[variable.identifier()].acquire(blocking=False):
                j = 0
                while j < i:
                    self._variable_locks[self._wedmakefile.variables()[j].identifier()].release()
                    j += 1
                return False
        is_in_final_state = True
        for dependency in self._wedmakefile.final_guard().dependencies():
            if not PyDependency(dependency).is_satisfied_by(self._state):
                is_in_final_state = False
        trigger_task = False
        for task in self._wedmakefile.tasks():
            for dependency in task.guard().dependencies():
                if not PyDependency(dependency).is_satisfied_by(self._state):
                    break
            else:
                trigger_task = True
        for variable in self._wedmakefile.variables():
            self._variable_locks[variable.identifier()].release()
        return not is_in_final_state and not trigger_task

    @CSDecorator(_ei_lock)
    def is_ready_to_execute_task(self, task):
        """Return True if the specified task can be promptly executed (i.e., if the current state
        satisfies the task's guard and no other thread is executing a task that shares a common
        variable namespace). Return False, otherwise.

        task -- [wedmakefile_parser.Task] Task to evaluate.
        """
        for (i, variable) in enumerate(task.guard().on_variables()):
            if not self._variable_locks[variable.identifier()].acquire(blocking=False):
                j = 0
                while j < i:
                    self._variable_locks[task.guard().on_variables()[j].identifier()].release()
                    j += 1
                return False
        is_ready_to_execute_task = True
        for dependency in task.guard().dependencies():
            if not PyDependency(dependency).is_satisfied_by(self._state):
                is_ready_to_execute_task = False
        for variable in task.guard().on_variables():
            self._variable_locks[variable.identifier()].release()
        return is_ready_to_execute_task

    def ready_to_execute_tasks(self):
        """Return a list of tasks ready to be promptly executed."""
        return [task for task in self._wedmakefile.tasks() if self.is_ready_to_execute_task(task)]

    def execute_task(self, task):
        """Return True if the specified task is successfully and promptly executed. Return False,
        otherwise.

        task -- [wedmakefile_parser.Task] Task to execute.
        """
        PyExperimentInstance._ei_lock.acquire()
        for (i, variable) in enumerate(task.guard().on_variables()):
            if not self._variable_locks[variable.identifier()].acquire(blocking=False):
                j = 0
                while j < i:
                    self._variable_locks[task.guard().on_variables()[j].identifier()].release()
                    j += 1
                PyExperimentInstance._ei_lock.release()
                return False
        PyExperimentInstance._ei_lock.release()
        execute_task = True
        for dependency in task.guard().dependencies():
            if not PyDependency(dependency).is_satisfied_by(self._state):
                execute_task = False
                break
        else:
            self.print_triggered_task_message(task)
            try:
                stdout=os.path.join(
                    self._logdir_path,
                    "{task}_{timestamp}.out".format(
                        task=task.name(),
                        timestamp=time.strftime("%Y%m%d%H%M%S")
                    )
                ) if self._logdir_path else "/dev/null"
                stderr=os.path.join(
                    self._logdir_path,
                    "{task}_{timestamp}.err".format(
                        task=task.name(),
                        timestamp=time.strftime("%Y%m%d%H%M%S")
                    )
                ) if self._logdir_path else "/dev/null"
                other_state = PyExperimentInstanceState.from_bash_script(
                    setup="function main {{\n{variables}\n{body}\n}}".format(
                        variables="""
                            local _IFS_BACKUP=\$IFS
                            IFS=,
                            local _params
                            read -a _params <<< "$1"
                            local _it=0
                            while [ \$_it -lt \${#_params[@]} ]; do
                                if [ \${_params[\$_it+2]} = "ro" ]; then
                                    readonly \${_params[\$_it]}="\${_params[\$_it+1]}"
                                else
                                    eval "\${_params[\$_it]}=\\\"\${_params[\$_it+1]}\\\""
                                fi
                                let _it=_it+3
                            done
                            IFS=\$_IFS_BACKUP
                            unset _IFS_BACKUP
                            unset _params
                            unset _it
                        """,
                        body=task.bash_script().replace(r'\$', r'\\$').replace(r'$', r'\$')
                    ),
                    main="main 1> {stdout} 2> {stderr}".format(stdout=stdout, stderr=stderr),
                    args=[','.join([
                        arg.replace(",", "\\,")
                        for var_id_val_perm in [[
                            variable.identifier(),
                            self._state.get(variable.identifier(), ""),
                            "ro" if self._state.is_readonly(variable.identifier()) else "rw"
                        ] for variable in task.guard().on_variables()]
                        for arg in var_id_val_perm
                    ])]
                )
            except Exception as exception:
                self._exceptions.append(RuntimeError(
                    "TaskExecutionError: Error while executing "
                    "task {task}.".format(task=task.name())
                ))
                execute_task = False
            else:
                for variable_identifier, variable_value in other_state.items():
                    if wedmakefile_parser.Variable(variable_identifier) not in \
                            task.guard().on_variables():
                        self._exceptions.append(RuntimeError(
                            "UndeclaredDependency: Variable {variable_identifier} was not declared "
                            "as a dependency of task {task}.".format(
                                task=task.name(),
                                variable_identifier=variable_identifier
                            )
                        ))
                        execute_task = False
                        break
                else:
                    self.print_finished_task_message(task, other_state.diff(self._state))
                    PyExperimentInstance._ei_lock.acquire()
                    self._state.update(other_state)
                    PyExperimentInstance._ei_lock.release()
        for variable in task.guard().on_variables():
            self._variable_locks[variable.identifier()].release()
        return execute_task

    def run(self):
        while not self.is_in_final_state() and len(self._exceptions) == 0:
            if self.is_in_inconsistent_state():
                self._exceptions.append(RuntimeError(
                    "InconsistentState: Reached an inconsistent state."
                ))
            ready_tasks = self.ready_to_execute_tasks()
            if len(ready_tasks):
                self.execute_task(random.choice(ready_tasks))
            time.sleep(0.1)
        return self.is_in_final_state()
