#!/bin/python

"""Common helper functions for Nginx automation."""

import os
import sys
import subprocess
import re


processes = dict()
home_dir = "/auto/mtrswgwork/simonra"
commands_log_file = "{home_dir}/{log_path}".format(home_dir=home_dir, log_path="temp/nginx_automation_commands_log.txt")
host_username = "simonra"


def log_common(line, log_file):
    """Log line to the log file."""
    with open(log_file, 'a') as log:
        log.write(line + "\n")


def log_command(line):
    """Log line to the commands log file."""
    log_common(line=line, log_file=commands_log_file)


def run_cmd_and_wait(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """Run command and wait to answer."""
    log_command(cmd)
    process = subprocess.Popen([cmd], stdout=stdout, stderr=stderr, shell=True)
    pid = process.pid
    processes[str(pid)] = process
    process.wait()
    return pid


def run_cmd_on_background(cmd, stdin=None, stdout=subprocess.PIPE):
    """Run command and send output to pipe."""
    log_command(cmd)
    process = subprocess.Popen(
        [cmd], shell=True, stdout=stdout,
        stdin=stdin, stderr=subprocess.PIPE)
    pid = process.pid
    processes[str(pid)] = process
    return pid


def run_cmd_get_output(cmd):
    """Run command and get the output."""
    pid = run_cmd_on_background(cmd)
    output = get_output_from_pipe(pid)
    return output


def get_output_from_pipe(pid, get_errors=False):
    """
    Return output from the pipe.

    In case the get_errors flag set to True, the
    method will return a tuple (stdout_data, stderr_data, rc).
    Otherwise, will return the standard output only.
    """
    try:
        process = processes[str(pid)]
        (stdout_data, stderr_data) = process.communicate()
        rc = process.returncode
        stdout_data = '' if stdout_data is None else stdout_data
        stderr_data = '' if stderr_data is None else stderr_data
    except:
        stdout_data = ""

    stdout_data = re.compile("\033\[[0-9;]+m").sub("", stdout_data)

    if get_errors is True:
        return (stdout_data, stderr_data, rc)
    return stdout_data


def run_remote_cmd_on_backround(cmd, host):
    """Run command remotely through SSH."""
    remote_cmd = "ssh {user}@{host} \"{command}\"".format(user=host_username, host=host, command=cmd)
    pid = run_cmd_on_background(remote_cmd)
    return pid


def run_remote_cmd(cmd, host):
    """Run command remotely through SSH and wait to answer."""
    remote_cmd = "ssh {user}@{host} \"{command}\"".format(user=host_username, host=host, command=cmd)
    pid = run_cmd_and_wait(remote_cmd)
    return pid


def run_remote_cmd_get_output(cmd, host):
    """Run command remotely through SSH and get the output."""
    remote_cmd = "ssh {user}@{host} \"{command}\"".format(user=host_username, host=host, command=cmd)
    pid = run_cmd_on_background(remote_cmd)
    output = get_output_from_pipe(pid)
    return output
