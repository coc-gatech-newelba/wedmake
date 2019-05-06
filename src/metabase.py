#!/usr/bin/env python3.6


"""Command-line interface to run experiments in the Metabase runtime."""


import threading

import click
import termcolor

#import metabase_runtime
import wedmakefile_parser
import py_runtime


@click.group()
def main():
    pass


@main.command()
@click.argument("wedmakefile_path", metavar="<wedmakefile_path>")
@click.argument("config_path", metavar="<config_path>")
@click.argument("n_threads", metavar="<n_threads>", default=1)
@click.option("--log/--no-log", default=True)
@click.option("-v", "--verbose", default=False, is_flag=True)
@click.option("-i", "--interactive", default=False, is_flag=True)
@click.option("-q", "--quiet", default=False, is_flag=True)
def run_local(wedmakefile_path, config_path, n_threads, log, verbose, interactive, quiet):
    """Run an experiment on the local machine.

    wedmakefile_path -- [str] Path to the WED-Makefile containing the experiment specification.
    config_path -- [str] Path to the configuration file containing the initial state of the
                   experiment instance.
    n_threads -- [int] Number of threads to run the experiment instance.
    log -- [bool] Enable/Disable logging.
    verbose -- [bool] Enable/Disable verbose mode.
    interactive -- [bool] Enable/Disable interactive mode.
    quiet -- [bool] Enable/Disable quiet mode.
    """
    try:
        experiment_instance = py_runtime.PyExperimentInstance(
            wedmakefile_parser.WEDMakefile(wedmakefile_path),
            config_path,
            log,
            verbose
        )
        workers = []
        for i in range(n_threads):
            worker_thread = threading.Thread(target=experiment_instance.run)
            worker_thread.start()
            workers.append(worker_thread)
        for worker_thread in workers:
            worker_thread.join()
        if len(experiment_instance._exceptions):
            raise experiment_instance._exceptions[0]
    except Exception as e:
        termcolor.cprint(str(e), "white", "on_red", attrs=["bold"])
    else:
        experiment_instance.print_reached_final_state_message()
        termcolor.cprint("Success!", "white", "on_green", attrs=["bold"])


if __name__ == "__main__":
    main()
