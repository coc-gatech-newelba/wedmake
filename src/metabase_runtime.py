"""Utilities to run experiments in the Metabase runtime."""


# TODO: Replace double quotes with single quotes (SQL standard) in lists.
# TODO: Parameterize the database "wedmake".
# TODO: Store the content written to stdout and stderr by tasks' Bash scripts.
# TODO: Handle tasks' Bash script errors.
# TODO: Sleep in method run.
# TODO: Write test cases.


import random
import re

import psycopg2
from psycopg2.extras import Json

import py_runtime
import wedmakefile_parser


class MetabaseDependency:
    """A dependency adapter to the Metabase runtime."""

    def __init__(self, dependency):
        """Wrap a wedmakefile_parser.Dependency.

        dependency -- [wedmakefile_parser.Dependency] Dependency to wrap.
        """
        self._dependency = dependency

    def to_sql(self):
        """Return the SQL code equivalent to the wrapped dependency."""
        equality_match = re.fullmatch(
            wedmakefile_parser.Dependency.EQUALITY_CLAUSE,
            self._dependency.clause()
        )
        if equality_match is not None:
            return "\"_value_%s\" = '%s'" % (
                equality_match.groups()[0],
                equality_match.groups()[1][1:-1].replace("'", "''")
            )
        inequality_match = re.fullmatch(
            wedmakefile_parser.Dependency.INEQUALITY_CLAUSE,
            self._dependency.clause()
        )
        if inequality_match is not None:
            return "\"_value_%s\" != '%s'" % (
                inequality_match.groups()[0],
                inequality_match.groups()[1][1:-1].replace("'", "''")
            )
        membership_match = re.fullmatch(
            wedmakefile_parser.Dependency.MEMBERSHIP_CLAUSE,
            self._dependency.clause()
        )
        if membership_match is not None:
            return "\"_value_%s\" IN (%s)" % (
                membership_match.groups()[0],
                membership_match.groups()[1][1:-1]
            )
        nomembership_match = re.fullmatch(
            wedmakefile_parser.Dependency.NOMEMBERSHIP_CLAUSE,
            self._dependency.clause()
        )
        if nomembership_match is not None:
            return "\"_value_%s\" NOT IN (%s)" % (
                nomembership_match.groups()[0],
                nomembership_match.groups()[1][1:-1]
            )


class MetabaseInterface:
    """An interface to manage experiments in the Metabase runtime."""

    def __init__(self, host, user, password):
        """Set the Metabase server connection parameters.

        host -- [str] Metabase server hostname.
        user -- [str] Metabase server username.
        password -- [str] Metabase server password.
        """
        self._host = host
        self._user = user
        self._password = password

    def push(self, wedmakefile, message):
        """Initialize or update the experiment specification.

        wedmakefile -- [wedmakefile_parser.WEDMakefile] Parsed WED-Makefile containing the
                       experiment specification.
        message -- [str] A message describing the experiment or its updates.
        """
        sql = []
        sql.append("""
            -- Store guard.
            CREATE TABLE IF NOT EXISTS guard(
                _id SERIAL NOT NULL,
                PRIMARY KEY(_id)
            );
        """)
        sql.append("""
            -- Store guard logical predicate.
            CREATE TABLE IF NOT EXISTS guard_dependency(
                _id SERIAL NOT NULL,
                _clause TEXT NOT NULL,
                _gid INTEGER REFERENCES guard(_id),
                PRIMARY KEY(_id)
            );
        """)
        sql.append("""
            -- Store experiment version.
            CREATE TABLE IF NOT EXISTS experiment_version(
                _no SERIAL NOT NULL,
                _message TEXT NOT NULL,
                _created_at TIMESTAMP DEFAULT NOW(),
                _initial_gid INTEGER REFERENCES guard(_id),
                _final_gid INTEGER REFERENCES guard(_id),
                PRIMARY KEY(_no)
            );
        """)
        sql.append("""
            -- Store task.
            CREATE TABLE IF NOT EXISTS task(
                _id SERIAL NOT NULL,
                _name TEXT NOT NULL,
                _language CHAR(8) NOT NULL,
                _body TEXT NOT NULL,
                _gid INTEGER REFERENCES guard(_id),
                _eno INTEGER REFERENCES experiment_version(_no),
                PRIMARY KEY(_id)
            );
        """)
        sql.append("""
            -- Execute an anonymous code block to initialize or update the experiment.
            DO $$
            DECLARE
                initial_gid integer;
                final_gid integer;
                task_gid integer;
                eno integer;
            BEGIN
                INSERT INTO guard DEFAULT VALUES RETURNING _id INTO initial_gid;
                {initial_guard_dependencies_insertion}
                INSERT INTO guard DEFAULT VALUES RETURNING _id INTO final_gid;
                {final_guard_dependencies_insertion}
                INSERT INTO experiment_version(_message, _initial_gid, _final_gid)
                    VALUES ('{message}', initial_gid, final_gid) RETURNING _no INTO eno;
                {tasks_insertion}
            END$$;
        """.format(
            initial_guard_dependencies_insertion="\n                ".join([
                "INSERT INTO guard_dependency(_clause, _gid) VALUES ('{clause}', initial_gid);".format(
                    clause=dependency.clause().replace("'", "''")
                )
                for dependency in wedmakefile.initial_guard().dependencies()
            ]),
            final_guard_dependencies_insertion="\n                ".join([
                "INSERT INTO guard_dependency(_clause, _gid) VALUES ('{clause}', final_gid);".format(
                    clause=dependency.clause().replace("'", "''")
                )
                for dependency in wedmakefile.final_guard().dependencies()
            ]),
            message=message.replace("'", "''"),
            tasks_insertion="\n                ".join([
                """INSERT INTO guard DEFAULT VALUES RETURNING _id INTO task_gid;
                {task_guard_dependencies_insertion}
                """.format(
                    task_guard_dependencies_insertion="\n                ".join([
                        "INSERT INTO guard_dependency(_clause, _gid) VALUES ('{clause}', task_gid);".format(
                            clause=dependency.clause().replace("'", "''")
                        )
                        for dependency in task.guard().dependencies()
                    ])
                ) +
                """INSERT INTO task(_name, _language, _body, _gid, _eno)
                    VALUES ('{name}', 'bash', '{body}', task_gid, eno);""".format(
                    name=task.name(),
                    body=task.bash_script()
                )
                for task in wedmakefile.tasks()
            ])
        ))
        sql.append("""
            -- Store experiment instance metadata.
            CREATE TABLE IF NOT EXISTS experiment_instance(
                _id SERIAL NOT NULL,
                _eno INTEGER REFERENCES experiment_version(_no),
                _created_at TIMESTAMP DEFAULT NOW(),
                PRIMARY KEY(_id)
            );
        """)
        sql.append("".join(["""
            -- Store experiment instance state (namespace: {namespace}).
            CREATE TABLE IF NOT EXISTS "experiment_instance_state_{namespace}"(
                _eid INTEGER REFERENCES experiment_instance(_id),
                PRIMARY KEY(_eid)
            );
        """.format(namespace=namespace) for namespace in wedmakefile.variables_namespaces()]))
        sql.append("".join(["""
            -- Add columns to store the values and permissions of variable {variable}.
            ALTER TABLE "experiment_instance_state_{namespace}"
                ADD COLUMN IF NOT EXISTS "value_{variable}" TEXT;
            ALTER TABLE "experiment_instance_state_{namespace}"
                ADD COLUMN IF NOT EXISTS "perm_{variable}" CHAR(2);
        """.format(
            variable=variable.identifier(),
            namespace=variable.namespace()
        ) for variable in wedmakefile.variables()]))
        sql.append("""
            -- Instantiate the experiment and return the newly created experiment instance id.
            -- Args:
                -- $1 is a JSON array of dictionaries with variable identifiers, values, and
                --     permissions.
            CREATE OR REPLACE FUNCTION _instantiate(json) RETURNS integer AS $$
            DECLARE
                {variables_declaration}
                _it integer;
                _eid integer;
            BEGIN
                {variables_initialization}
                _it := 0;
                WHILE _it < json_array_length($1) LOOP
                    {variables_update}
                    RAISE EXCEPTION '% is not an experiment variable.', ($1->_it)->>'identifier';
                END LOOP;
                IF {initial_guard} THEN
                    INSERT INTO experiment_instance DEFAULT VALUES RETURNING _id INTO _eid;
                    {variables_persistence}
                    RETURN _eid;
                END IF;
                RAISE EXCEPTION 'Initial state must satisfy the initial guard.';
            END;
            $$ LANGUAGE plpgsql;
        """.format(
            variables_declaration="\n                ".join([
                "\"_value_{variable}\" text; \"_perm_{variable}\" text;".format(
                    variable=variable.identifier()
                )
                for variable in wedmakefile.variables()
            ]),
            variables_initialization="\n                ".join([
                "\"_value_{variable}\" = ''; \"_perm_{variable}\" = 'rw';".format(
                    variable=variable.identifier()
                )
                for variable in wedmakefile.variables()
            ]),
            variables_update='\n'.join(["""
                    IF ($1->_it)->>'identifier' = '{variable}' THEN
                        "_value_{variable}" := ($1->_it)->>'value';
                        "_perm_{variable}" := ($1->_it)->>'perm';
                        _it := _it + 1;
                        CONTINUE;
                    END IF;
            """.format(variable=variable.identifier()) for variable in wedmakefile.variables()]),
            initial_guard=" AND ".join([
                MetabaseDependency(dependency).to_sql()
                for dependency in wedmakefile.initial_guard().dependencies()
            ]),
            variables_persistence='\n'.join(["""
                    INSERT INTO "experiment_instance_state_{namespace}"(_eid, {columns})
                        VALUES (_eid, {variables});
            """.format(
                namespace=namespace,
                columns=", ".join([
                    "\"value_{variable}\", \"perm_{variable}\"".format(
                        variable=variable.identifier()
                    )
                    for variable in wedmakefile.variables(namespace=namespace)
                ]),
                variables=", ".join([
                    "\"_value_{variable}\", \"_perm_{variable}\"".format(
                        variable=variable.identifier()
                    )
                    for variable in wedmakefile.variables(namespace=namespace)
                ])
            ) for namespace in wedmakefile.variables_namespaces()])
        ))
        sql.append("""
            -- Check whether the specified experiment instance reached a final state.
            -- Args:
                -- $1 is the experiment instance id.
            -- Implementation:
                -- A per-instance advisory lock is held through the entire transaction to guarantee
                --     that no other transaction grabs locks concurrently.
                -- All variables are initialized (not only the ones the final guard depends on) to
                --     guarantee that no task is being executed.
            CREATE OR REPLACE FUNCTION _is_in_final_state(integer) RETURNS boolean AS $$
            DECLARE
                {variables_declaration}
            BEGIN
                PERFORM pg_advisory_xact_lock($1);
                {variables_initialization}
                IF {final_guard} THEN
                    RETURN TRUE;
                END IF;
                RETURN FALSE;
            END;
            $$ LANGUAGE plpgsql;
        """.format(
            variables_declaration="\n                ".join([
                "\"_value_{variable}\" text;".format(variable=variable.identifier())
                for variable in wedmakefile.variables()
            ]),
            variables_initialization='\n'.join(["""
                BEGIN
                    EXECUTE 'SELECT {columns} FROM "experiment_instance_state_{namespace}" '
                            'WHERE _eid = ' || $1 || ' FOR UPDATE NOWAIT' INTO {variables};
                EXCEPTION WHEN lock_not_available THEN
                    RETURN FALSE;
                END;
            """.format(
                columns=", ".join([
                    "\"value_%s\"" % variable.identifier()
                    for variable in wedmakefile.variables(namespace=namespace)
                ]),
                namespace=namespace,
                variables=", ".join([
                    "\"_value_%s\"" % variable.identifier()
                    for variable in wedmakefile.variables(namespace=namespace)
                ])
            ) for namespace in wedmakefile.variables_namespaces()]),
            final_guard=" AND ".join([
                MetabaseDependency(dependency).to_sql()
                for dependency in wedmakefile.final_guard().dependencies()
            ])
        ))
        sql.append("""
            -- Check whether the specified experiment instance reached an inconsistent state.
            -- Args:
                -- $1 is the experiment instance id.
            -- Implementation:
                -- A per-instance advisory lock is held through the entire transaction to guarantee
                --     that no other transaction grabs locks concurrently.
                -- All variables are initialized (not only the ones the final guard depends on) to
                --     guarantee that no task is being executed.
            CREATE OR REPLACE FUNCTION _is_in_inconsistent_state(integer) RETURNS boolean AS $$
            DECLARE
                {variables_declaration}
            BEGIN
                PERFORM pg_advisory_xact_lock($1);
                {variables_initialization}
                IF {final_guard} THEN
                    RETURN FALSE;
                END IF;
                {evaluate_tasks_guards}
                RETURN TRUE;
            END;
            $$ LANGUAGE plpgsql;
        """.format(
            variables_declaration="\n                ".join([
                "\"_value_{variable}\" text;".format(variable=variable.identifier())
                for variable in wedmakefile.variables()
            ]),
            variables_initialization='\n'.join(["""
                BEGIN
                    EXECUTE 'SELECT {columns} FROM "experiment_instance_state_{namespace}" '
                            'WHERE _eid = ' || $1 || ' FOR UPDATE NOWAIT' INTO {variables};
                EXCEPTION WHEN lock_not_available THEN
                    RETURN FALSE;
                END;
            """.format(
                columns=", ".join([
                    "\"value_%s\"" % variable.identifier()
                    for variable in wedmakefile.variables(namespace=namespace)
                ]),
                namespace=namespace,
                variables=", ".join([
                    "\"_value_%s\"" % variable.identifier()
                    for variable in wedmakefile.variables(namespace=namespace)
                ])
            ) for namespace in wedmakefile.variables_namespaces()]),
            final_guard=" AND ".join([
                MetabaseDependency(dependency).to_sql()
                for dependency in wedmakefile.final_guard().dependencies()
            ]),
            evaluate_tasks_guards='\n'.join(["""
                IF {task_guard} THEN
                    RETURN FALSE;
                END IF;
            """.format(
                task_guard=" AND ".join([
                    MetabaseDependency(dependency).to_sql()
                    for dependency in task.guard().dependencies()
                ])
            ) for task in wedmakefile.tasks()])
        ))
        sql.append("".join(["""
            -- Check whether task {task} is ready to be executed for the specified experiment
            --     instance.
            -- Args:
                -- $1 is the experiment instance id.
            -- Implementation:
                -- A per-instance advisory lock is held through the entire transaction to guarantee
                --     that no other transaction grabs locks concurrently.
            CREATE OR REPLACE FUNCTION "_is_{task}_ready_to_execute"(integer) RETURNS boolean AS $$
            DECLARE
                {variables_declaration}
            BEGIN
                PERFORM pg_advisory_xact_lock($1);
                {variables_initialization}
                IF {task_guard} THEN
                    RETURN TRUE;
                END IF;
                RETURN FALSE;
            END;
            $$ LANGUAGE plpgsql;
        """.format(
            task=task.name(),
            variables_declaration="\n                ".join([
                "\"_value_{variable}\" text;".format(variable=variable.identifier())
                for variable in task.guard().on_variables()
            ]),
            variables_initialization='\n'.join(["""
                BEGIN
                    EXECUTE 'SELECT {columns} FROM "experiment_instance_state_{namespace}" '
                            'WHERE _eid = ' || $1 || ' FOR UPDATE NOWAIT' INTO {variables};
                EXCEPTION WHEN lock_not_available THEN
                    RETURN FALSE;
                END;
            """.format(
                columns=", ".join([
                    "\"value_%s\"" % variable.identifier()
                    for variable in task.guard().on_variables(namespace=namespace)
                ]),
                namespace=namespace,
                variables=", ".join([
                    "\"_value_%s\"" % variable.identifier()
                    for variable in task.guard().on_variables(namespace=namespace)
                ])
            ) for namespace in task.guard().on_variables_namespaces()]),
            task_guard=" AND ".join([
                MetabaseDependency(dependency).to_sql()
                for dependency in task.guard().dependencies()
            ])
        ) for task in wedmakefile.tasks()]))
        sql.append("""
            -- Return a JSON list with the names of the tasks ready to be executed for the specified
            --     experiment instance.
            -- Args:
                -- $1 is the experiment instance id.
            -- Implementation:
                -- A per-instance advisory lock is held through the entire transaction to guarantee
                --     that no other transaction grabs locks concurrently.
            CREATE OR REPLACE FUNCTION _ready_to_execute(integer) RETURNS json AS $$
            DECLARE
                _res text[];
            BEGIN
                PERFORM pg_advisory_xact_lock($1);
                {tasks_evaluation}
                RETURN array_to_json(_res);
            END;
            $$ LANGUAGE plpgsql;
        """.format(
            tasks_evaluation='\n'.join(["""
                IF "_is_{task}_ready_to_execute"($1) THEN
                    _res = array_append(_res, '{task}');
                END IF;
            """.format(task=task.name()) for task in wedmakefile.tasks()])
        ))
        sql.append("".join(["""
            -- Return the values and permissions of variables updated by task {task}'s Bash script.
            CREATE OR REPLACE FUNCTION "_bash_{task}"(text) RETURNS text AS $$\n{bash_script}
            $$ LANGUAGE plsh;
        """.format(
            task=task.name(),
            bash_script=py_runtime.PyExperimentInstanceState.render_capture_bash_script(
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
                main="main 1> /dev/null 2> /dev/null"
            )
        ) for task in wedmakefile.tasks()]))
        sql.append("".join(["""
            -- Return true if task {task} is successfully and promptly executed for the specified
            --     experiment instance. Return false, otherwise.
            -- Args:
                -- $1 is the experiment instance id.
            -- Implementation:
                -- A per-instance advisory lock is held while variables are being initialized to
                --     guarantee that no other transaction grabs locks concurrently.
            CREATE OR REPLACE FUNCTION "_execute_{task}"(integer) RETURNS boolean AS $$
            DECLARE
                {variables_declaration}
                _it integer;
                _counter integer;
                _res text[];
                _params text[8];
            BEGIN
                PERFORM pg_advisory_lock($1);
                {variables_initialization}
                PERFORM pg_advisory_unlock($1);
                IF {task_guard} THEN
                    _params[1] := concat_ws(',', {params1});
                    _params[2] := concat_ws(',', {params2});
                    _params[3] := concat_ws(',', {params3});
                    _params[4] := concat_ws(',', {params4});
                    _params[5] := concat_ws(',', {params5});
                    _params[6] := concat_ws(',', {params6});
                    _params[7] := concat_ws(',', {params7});
                    _params[8] := concat_ws(',', {params8});
                    _counter := 2;
                    WHILE length(_params[_counter]) > 0 AND _counter <= 8 LOOP
                        _params[1] := concat_ws(',', _params[1], _params[_counter]);
                        _counter := _counter + 1;
                    END LOOP;
                    _res := string_to_array("_bash_{task}"(_params[1]), E'\\n');
                    _it := 1;
                    WHILE _it <= array_length(_res, 1) LOOP
                        {variables_update}
                        RAISE EXCEPTION 'Variable % must be declared as a dependency of task '
                                        '{task}.', _res[_it];
                    END LOOP;
                    {variables_persistence}
                    RETURN TRUE;
                END IF;
                RETURN FALSE;
            END;
            $$ LANGUAGE plpgsql;
        """.format(
            task=task.name(),
            variables_declaration="\n                ".join([
                "\"_value_{variable}\" text; \"_perm_{variable}\" text;".format(
                    variable=variable.identifier()
                )
                for variable in task.guard().on_variables()
            ]),
            variables_initialization='\n'.join(["""
                BEGIN
                    EXECUTE 'SELECT {columns} FROM "experiment_instance_state_{namespace}" '
                            'WHERE _eid = ' || $1 || ' FOR UPDATE NOWAIT' INTO {variables};
                EXCEPTION WHEN lock_not_available THEN
                    PERFORM pg_advisory_unlock($1);
                    RETURN FALSE;
                END;
            """.format(
                columns=", ".join([
                    "\"value_{variable}\", \"perm_{variable}\"".format(
                        variable=variable.identifier()
                    )
                    for variable in task.guard().on_variables(namespace=namespace)
                ]),
                namespace=namespace,
                variables=", ".join([
                    "\"_value_{variable}\", \"_perm_{variable}\"".format(
                        variable=variable.identifier()
                    )
                    for variable in task.guard().on_variables(namespace=namespace)
                ])
            ) for namespace in task.guard().on_variables_namespaces()]),
            task_guard=" AND ".join([
                MetabaseDependency(dependency).to_sql()
                for dependency in task.guard().dependencies()
            ]),
            params1=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[0:32]
            ]) if len(task.guard().on_variables()) > 0 else "''",
            params2=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[32:64]
            ]) if len(task.guard().on_variables()) > 32 else "''",
            params3=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[64:96]
            ]) if len(task.guard().on_variables()) > 64 else "''",
            params4=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[96:128]
            ]) if len(task.guard().on_variables()) > 96 else "''",
            params5=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[128:160]
            ]) if len(task.guard().on_variables()) > 128 else "''",
            params6=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[160:192]
            ]) if len(task.guard().on_variables()) > 160 else "''",
            params7=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[192:224]
            ]) if len(task.guard().on_variables()) > 192 else "''",
            params8=", ".join([
                "'{variable}', replace(\"_value_{variable}\", ',', E'\\\,'), \"_perm_{variable}\"".\
                        format(variable=variable.identifier())
                for variable in task.guard().on_variables()[224:256]
            ]) if len(task.guard().on_variables()) > 224 else "''",
            variables_update='\n'.join(["""
                        IF _res[_it] = '{variable}' THEN
                            "_value_{variable}" := _res[_it + 1];
                            "_perm_{variable}" := _res[_it + 2];
                            _it := _it + 3;
                            CONTINUE;
                        END IF;
            """.format(variable=variable.identifier()) for variable in task.guard().on_variables()]),
            variables_persistence='\n'.join(["""
                    UPDATE "experiment_instance_state_{namespace}" SET {assignments} WHERE _eid = $1;
            """.format(
                namespace=namespace,
                assignments=", ".join([
                    "\"value_{variable}\" = \"_value_{variable}\", "
                    "\"perm_{variable}\" = \"_perm_{variable}\"".format(
                        variable=variable.identifier()
                    ) for variable in task.guard().on_variables(namespace=namespace)
                ])
            ) for namespace in task.guard().on_variables_namespaces()])
        ) for task in wedmakefile.tasks()]))
        sql_str = '\n'.join([
            line[12:] if line.startswith(12 * ' ') else line
            for line in "".join(sql).split('\n')
            if line.strip()
        ])
        conn = psycopg2.connect("host={host} dbname={dbname} user={user} password={password}".format(
            host=self._host,
            dbname="wedmake",
            user=self._user,
            password=self._password
        ))
        cur = conn.cursor()
        cur.execute(sql_str)
        conn.commit()

    def instantiate(self, config_path):
        """Instantiate the specified experiment and return the newly created experiment instance id.

        config_path -- [str] Path to the configuration file containing the initial state of the
                       experiment instance.
        """
        with open(config_path) as config_file:
            initial_state = py_runtime.PyExperimentInstanceState.from_bash_script(
                setup="",
                main=config_file.read().strip()
            )
        conn = psycopg2.connect("host={host} dbname={dbname} user={user} password={password}".format(
            host=self._host,
            dbname="wedmake",
            user=self._user,
            password=self._password
        ))
        cur = conn.cursor()
        cur.execute("SELECT _instantiate({initial_state})".format(
            initial_state=Json([{
                "identifier": variable_identifier,
                "perm": "ro" if initial_state.is_readonly(variable_identifier) else "rw",
                "value": initial_state[variable_identifier]
            } for variable_identifier in sorted(initial_state.keys())])
        ))
        eid = int(cur.fetchone()[0])
        conn.commit()
        return eid

    def run(self, eid):
        """A thread to run the specified experiment instance.

        eid -- [int] Id of the experiment instance to run.
        """
        conn = psycopg2.connect("host={host} dbname={dbname} user={user} password={password}".format(
            host=self._host,
            dbname="wedmake",
            user=self._user,
            password=self._password
        ))
        cur = conn.cursor()
        is_in_final_state = False
        is_in_inconsistent_state = False
        while not is_in_final_state and not is_in_inconsistent_state:
            cur.execute("SELECT _ready_to_execute({eid})".format(eid=eid))
            ready_tasks = cur.fetchone()[0]
            conn.commit()
            if ready_tasks is not None and len(ready_tasks):
                cur.execute("SELECT \"_execute_{task}\"({eid})".format(
                    eid=eid,
                    task=random.choice(ready_tasks)
                ))
                cur.fetchone()
                conn.commit()
            cur.execute("SELECT _is_in_inconsistent_state({eid})".format(eid=eid))
            is_in_inconsistent_state = bool(cur.fetchone()[0])
            conn.commit()
            cur.execute("SELECT _is_in_final_state({eid})".format(eid=eid))
            is_in_final_state = bool(cur.fetchone()[0])
            conn.commit()
