#!/bin/python

"""Common helper functions for Nginx automation."""

import os
import sys
import subprocess
import re
import json


config_file = "{path}/{file}".format(path=os.path.dirname(os.path.abspath(__file__)), file="configuration.json")


class Keys(object):
    """Represent configuration file keys."""

    GENERAL = "general_section"
    CMD_LOG_FILE = "commands_log_file"
    USER = "ssh_username"
    RES_DIR = "results_directory"
    REMOTE_LOGS_DIR = "remote_logs_directory"
    DURATION = "duration"
    SERVER = "server_section"
    NGINX_SERVER = "nginx_server"
    TEST_PARAMS = "test_parameters_section"
    RUN_TYPES = "run_types"
    FILES = "files"
    CONNECTIONS = "connections"
    NGINX_STDOUT = "nginx_app_stdout"
    NUMA = "nic_numa_node"
    INTERFACE = "interface"
    NGINX_ROOT = "nginx_root"
    NGINX_BIN = "nginx_bin"
    NGINX_CONF = "nginx_conf_file"
    NGINX_IP = "nginx_ip"
    NGINX_PORT = "nginx_port"
    VMA_LIB = "vma_library"
    VMA_REF_LIB = "vma_library_ref"
    VMA_PARAMS = "vma_parameters"
    VMA_REF_PARAMS = "vma_parameters_ref"
    CLIENT = "client_section"
    CPUSTAT_BIN = "cpustat_bin"
    WRK_BIN = "wrk_bin"
    WRK_SERVERS = "wrk_servers"
    NGINX_WORKERS = "nginx_workers"


def get_config():
    """Return automation configuration structure."""
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)
    return config


config = get_config()
processes = dict()


def log_common(line, log_file):
    """Log line to the log file."""
    with open(log_file, 'a') as log:
        log.write(line + "\n")


def log_command(line):
    """Log line to the commands log file."""
    log_common(line=line, log_file=config[Keys.GENERAL][Keys.CMD_LOG_FILE])


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
    remote_cmd = "ssh {user}@{host} \"{command}\"".format(user=config[Keys.GENERAL][Keys.USER], host=host, command=cmd)
    pid = run_cmd_on_background(remote_cmd)
    return pid


def run_remote_cmd(cmd, host):
    """Run command remotely through SSH and wait to answer."""
    remote_cmd = "ssh {user}@{host} \"{command}\"".format(user=config[Keys.GENERAL][Keys.USER], host=host, command=cmd)
    pid = run_cmd_and_wait(remote_cmd)
    return pid


def run_remote_cmd_get_output(cmd, host, timeout=None):
    """Run command remotely through SSH and get the output."""
    if timeout is not None:
        timeout_str = "timeout {seconds} ".format(seconds=timeout)
    else:
        timeout_str = ""
    remote_cmd = "{timeout_str}ssh {user}@{host} \"{command}\"".format(
        timeout_str=timeout_str, user=config[Keys.GENERAL][Keys.USER], host=host, command=cmd)
    pid = run_cmd_on_background(remote_cmd)
    output = get_output_from_pipe(pid)
    return output
