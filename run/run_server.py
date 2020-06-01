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
my_home = "/auto/mtrswgwork/simonra"
dev_vma = "{my_home}/dev/libvma".format(my_home=my_home)
remote_logs_directory = "{my_home}/temp/nginx_automation_logs".format(my_home=my_home)
nginx_log = "{remote_logs_directory}/nginx_app_log.txt".format(remote_logs_directory=remote_logs_directory)
tools = "{my_home}/tools".format(my_home=my_home)
nginx_root = "{tools}/nginx".format(tools=tools)
nginx_release_bin = "{tools}/nginx/sbin/nginx_release".format(tools=tools)
nginx_debug_bin = "{tools}/nginx/sbin/nginx_debug".format(tools=tools)
nginx_conf_file = "{tools}/nginx/conf/vma_nginx.conf".format(tools=tools)
vma_log_file = "{my_home}/temp/vma_log.txt".format(my_home=my_home)
vma_library = "{dev_vma}/src/vma/.libs/libvma.so".format(dev_vma=dev_vma)
nginx_pid_file = "{nginx_root}/logs/nginx.pid".format(nginx_root=nginx_root)
numa_node = 0
nginx_server = "rapid01.lab.mtl.com"
run_types = ["kernel", "vma"]
vma_parameters = [
    "VMA_TX_SEGS_TCP=2000000",
    "VMA_RX_WRE=32000",
    "VMA_TX_BUFS=1000000",
    "VMA_TX_BUF_SIZE=1460",
    "VMA_TSO_SEGMENT_SIZE=32768",
    "VMA_CQ_POLL_BATCH_MAX=128",
    "VMA_TCP_SEND_BUFFER_SIZE=20000000",
]


def signal_handler(sig, frame):
    """Signal handler for cleanups."""
    print " >>> Got Ctrl-C, running cleanup..."
    run_cleanup()
    sys.exit(0)


def run_cleanup():
    """Run clean up."""
    remove_vma_log_file_cmd = "rm -f {file}".format(file=vma_log_file)
    run_remote_cmd_get_output(cmd=remove_vma_log_file_cmd, host=nginx_server)
    remove_nginx_pid_file_cmd = "rm -f {file}".format(file=nginx_pid_file)
    run_remote_cmd_get_output(cmd=remove_nginx_pid_file_cmd, host=nginx_server)
    clean_nginx_cmd = \
        "ps -ef | grep nginx | grep -v {pid} | awk \'\"\'{{print $2}}\'\"\' | xargs sudo kill -9 > /dev/null 2>&1".format(
            pid=os.getpid())
    run_remote_cmd_get_output(cmd=clean_nginx_cmd, host=nginx_server)
    clean_cpustat_cmd = "ps -ef | grep cpustat | awk \'\"\'{print $2}\'\"\' | xargs sudo kill -9 > /dev/null 2>&1"
    run_remote_cmd_get_output(cmd=clean_cpustat_cmd, host=nginx_server)


def init():
    """Initialize script."""
    global vma_parameters
    get_workers_cmd = "cat {nginx_conf_file} | grep worker_processes | head -n 1".format(
        nginx_conf_file=nginx_conf_file)
    output = run_cmd_get_output(get_workers_cmd)
    num_of_nginx_workers = output.split()[1].replace(";", "")
    vma_nginx_workers_num = "VMA_NGINX_WORKERS_NUM={num}".format(num=num_of_nginx_workers)
    vma_parameters.append(vma_nginx_workers_num)


def run_nginx(library):
    """Run Nginx application."""
    init()

    if "vma" in library:
        library = "LD_PRELOAD={library}".format(library=vma_library)
        env_variables = " ".join(vma_parameters)
    else:
        library = ""
        env_variables = ""

    run_nginx_cmd = ("{library} {env_variables} numactl --preferred {numa_node}"
                     " {_bin} -c {conf_file} -p {root} > {log} 2>&1")
    run_nginx_cmd = run_nginx_cmd.format(
        library=library, env_variables=env_variables,
        numa_node=numa_node, _bin=nginx_release_bin,
        conf_file=nginx_conf_file, root=nginx_root, log=nginx_log
    )
    run_remote_cmd_get_output(cmd=run_nginx_cmd, host=nginx_server)


def add_options(parser):
    """Add options to the parser."""
    parser.add_option('-r', '--run_type', type="choice", choices=run_types,
                      dest='run_type', default="vma",
                      help="Type of the run to do, valid options are: {choices}. Default: {default}".format(
                          choices=run_types, default="vma"), metavar='<ARG>')


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
