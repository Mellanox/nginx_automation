#!/bin/python

"""Nginx automation from server side."""

import os
import time
import shutil
import datetime
import signal

from optparse import OptionParser, OptionGroup
from common import *

# Variables:
supported_run_types = ["kernel", "vma", "vma_ref"]
nginx_log = "{remote_logs_dir}/nginx_app_stdout.txt".format(remote_logs_dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR])


def signal_handler(sig, frame):
    """Signal handler for cleanups."""
    print " >>> Got Ctrl-C, running cleanup..."
    run_cleanup()
    sys.exit(0)


def run_cleanup():
    """Run clean up."""
    clean_nginx_cmd = \
        "ps -ef | grep nginx | grep -v {pid} | awk \'\"\'{{print $2}}\'\"\' | xargs sudo kill -9 > /dev/null 2>&1".format(
            pid=os.getpid())
    run_remote_cmd_get_output(cmd=clean_nginx_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])
    clean_cpustat_cmd = "ps -ef | grep cpustat | awk \'\"\'{print $2}\'\"\' | xargs sudo kill -9 > /dev/null 2>&1"
    run_remote_cmd_get_output(cmd=clean_cpustat_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])


def init():
    """Initialize script."""
    get_workers_cmd = "cat {config_file} | grep worker_processes | head -n 1".format(
        config_file=config[Keys.SERVER][Keys.NGINX_CONF])
    output = run_cmd_get_output(get_workers_cmd)
    num_of_nginx_workers = output.split()[1].replace(";", "")
    vma_nginx_workers_num = "VMA_NGINX_WORKERS_NUM={num}".format(num=num_of_nginx_workers)
    config[Keys.SERVER][Keys.VMA_PARAMS].append(vma_nginx_workers_num)
    config[Keys.SERVER][Keys.VMA_REF_PARAMS].append(vma_nginx_workers_num)


def run_nginx(run_type):
    """Run Nginx application."""
    init()

    if "vma_ref" in run_type:
        library = "LD_PRELOAD={library}".format(library=config[Keys.SERVER][Keys.VMA_REF_LIB])
        env_variables = " ".join(config[Keys.SERVER][Keys.VMA_REF_PARAMS])
    elif "vma" in run_type:
        library = "LD_PRELOAD={library}".format(library=config[Keys.SERVER][Keys.VMA_LIB])
        env_variables = " ".join(config[Keys.SERVER][Keys.VMA_PARAMS])
    else:
        library = ""
        env_variables = ""

    run_nginx_cmd = ("{library} {env_variables} numactl --preferred {numa_node}"
                     " {_bin} -c {conf_file} -p {root} > {log} 2>&1")
    run_nginx_cmd = run_nginx_cmd.format(
        library=library, env_variables=env_variables,
        numa_node=config[Keys.SERVER][Keys.NUMA], _bin=config[Keys.SERVER][Keys.NGINX_BIN],
        conf_file=config[Keys.SERVER][Keys.NGINX_CONF], root=config[Keys.SERVER][Keys.NGINX_ROOT], log=nginx_log
    )
    run_remote_cmd_get_output(cmd=run_nginx_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])


def add_options(parser):
    """Add options to the parser."""
    parser.add_option('-r', '--run_type', type="choice", choices=supported_run_types,
                      dest='run_type', default="vma",
                      help="Type of the run to do, valid options are: {choices}. Default: {default}".format(
                          choices=supported_run_types, default="vma"), metavar='<ARG>')


def main():
    """Run main entry point of the script."""
    signal.signal(signal.SIGINT, signal_handler)

    usage = "usage: %prog options\n"
    parser = OptionParser(usage=usage)
    add_options(parser)
    (options, args) = parser.parse_args()

    print "> Running cleanup..."
    run_cleanup()

    print "> Running Nginx - Run type: {run_type}...".format(run_type=options.run_type)
    run_nginx(options.run_type)


if __name__ == "__main__":
    main()
