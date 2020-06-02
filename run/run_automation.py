#!/bin/python

"""Run the Nginx automation using other helper scripts."""

import time
import shutil
import datetime
import signal

from common import *


# Script variables:
nginx_server = "rapid01.lab.mtl.com"
user_name = "simonra"
my_home = "/auto/mtrswgwork/simonra"
results_directory = "{my_home}/temp/nginx_automation_results".format(my_home=my_home)
remote_logs_directory = "{my_home}/temp/nginx_automation_logs".format(my_home=my_home)
run_server_cmd = "{my_home}/tools/nginx/scripts/run/run_server.py".format(my_home=my_home)
run_client_cmd = "{my_home}/tools/nginx/scripts/run/run_client.py".format(my_home=my_home)
parse_results_cmd = "{my_home}/tools/nginx/scripts/run/parse_results.py".format(my_home=my_home)
commands_log = "{my_home}/temp/nginx_automation_commands_log.txt".format(my_home=my_home)

# run_type_list = ["kernel", "vma", "vma_ref"]
# file_list = ["1KB", "10KB", "100KB", "1MB", "10MB"]
# connections_list = ["1000", "256000"]

run_type_list = ["kernel", "vma", "vma_ref"]
file_list = ["1KB", "10KB", "100KB", "1MB", "10MB"]
connections_list = ["1000", "2000", "3000", "4000", "5000", "6000", "7000", "8000", "9000", "10000", "20000", "30000", "60000", "120000", "180000", "256000"]



def signal_handler(sig, frame):
    """Signal handler for cleanups."""
    print " >>> Got Ctrl-C, running cleanup..."
    run_cleanup()
    sys.exit(0)


def kill_scripts(do_sleep=True):
    """Kill remote scripts."""
    run_cmd_get_output("ps -ef | grep run_server.py | awk '{print $2}' | xargs sudo kill -2 > /dev/null 2>&1")
    run_cmd_get_output("ps -ef | grep run_client.py | awk '{print $2}' | xargs sudo kill -2 > /dev/null 2>&1")
    run_remote_cmd(
        cmd="ps -ef | grep cpustat | awk \'\"\'{print $2}\'\"\' | xargs sudo kill -9 > /dev/null 2>&1",
        host=nginx_server)
    run_remote_cmd(
        cmd="ps -ef | grep nginx | awk \'\"\'{print $2}\'\"\' | xargs sudo kill -9 > /dev/null 2>&1",
        host=nginx_server)

    if do_sleep is True:
        time.sleep(5)


def run_cleanup():
    """Run cleanup on remote servers."""
    kill_scripts(do_sleep=False)
    timestamp = str(datetime.datetime.now())
    timestamp = timestamp.replace(" ", "_").replace("-", "_").replace(":", "_").replace(".", "_")
    last_results_source = results_directory
    last_results_destination = "{path}_backup_{timestamp}".format(path=results_directory, timestamp=timestamp)
    if os.path.isdir(last_results_source) is True:
        shutil.move(last_results_source, last_results_destination)
    os.makedirs(results_directory)


def run(run_type):
    """Run single run kernel/VMA/VMA reference."""
    run_cmd_and_wait("rm -rf {dir}".format(dir=remote_logs_directory))
    run_cmd_and_wait("mkdir {dir}".format(dir=remote_logs_directory))
    run_dir = "{results_directory}/{run_type}".format(results_directory=results_directory, run_type=run_type)
    os.makedirs(run_dir)

    for connections in connections_list:
        connections_dir = "{run_dir}/connections_{connections}".format(run_dir=run_dir, connections=connections)
        os.makedirs(connections_dir)

        for file in file_list:
            print ">> Running case - Connections: {connections} | File: {file}".format(
                file=file, connections=connections)
            iteration_dir = "{connections_dir}/file_{file}".format(connections_dir=connections_dir, file=file)
            os.makedirs(iteration_dir)
            kill_scripts()
            print ">> Running server..."
            server_cmd = "{cmd} --run_type={run_type}".format(cmd=run_server_cmd, run_type=run_type)
            run_cmd_on_background(cmd=server_cmd)
            time.sleep(5)
            print ">> Running client..."
            client_cmd = "{cmd} --file {file}.bin --connections {connections}".format(
                cmd=run_client_cmd, file=file, connections=connections)
            run_cmd_get_output(client_cmd)
            save_logs_cmd = "cp -rf {src} {dst}".format(src=remote_logs_directory, dst=iteration_dir)
            run_cmd_and_wait(save_logs_cmd)
            run_cmd_and_wait("cp -f {file} {dst}".format(file=run_server_cmd, dst=iteration_dir))
            run_cmd_and_wait("cp -f {file} {dst}".format(file=run_client_cmd, dst=iteration_dir))
            run_cmd_and_wait("mv {file} {dst}".format(file=commands_log, dst=iteration_dir))


def main():
    """Run main entry point of the script."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    print "> Running cleanup..."
    run_cleanup()
    for run_type in run_type_list:
        print "> Running {run_type} run...".format(run_type=run_type)
        run(run_type)
    print "> Running remote cleanup..."
    kill_scripts()
    print "> Running results parse..."
    run_cmd_and_wait(parse_results_cmd)
    print "> DONE"


if __name__ == "__main__":
    main()
