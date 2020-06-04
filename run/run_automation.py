#!/bin/python

"""Run the Nginx automation using other helper scripts."""

import time
import shutil
import datetime
import signal

from common import *


# Script variables:
sleep_sec = 5


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
        host=config[Keys.SERVER][Keys.NGINX_SERVER])
    run_remote_cmd(
        cmd="ps -ef | grep nginx | awk \'\"\'{print $2}\'\"\' | xargs sudo kill -9 > /dev/null 2>&1",
        host=config[Keys.SERVER][Keys.NGINX_SERVER])

    if do_sleep is True:
        time.sleep(sleep_sec)


def run_cleanup():
    """Run cleanup on remote servers."""
    kill_scripts(do_sleep=False)
    timestamp = str(datetime.datetime.now())
    timestamp = timestamp.replace(" ", "_").replace("-", "_").replace(":", "_").replace(".", "_")
    last_results_source = config[Keys.GENERAL][Keys.RES_DIR]
    last_results_destination = "{path}_backup_{timestamp}".format(
        path=config[Keys.GENERAL][Keys.RES_DIR], timestamp=timestamp)
    if os.path.isdir(last_results_source) is True:
        shutil.move(last_results_source, last_results_destination)
    os.makedirs(config[Keys.GENERAL][Keys.RES_DIR])


def run(run_type):
    """Run single run kernel/VMA/VMA reference."""
    run_cmd_and_wait("rm -rf {dir}".format(dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR]))
    run_cmd_and_wait("mkdir {dir}".format(dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR]))
    run_dir = "{res_dir}/{run_type}".format(res_dir=config[Keys.GENERAL][Keys.RES_DIR], run_type=run_type)
    os.makedirs(run_dir)

    for workers in config[Keys.TEST_PARAMS][Keys.NGINX_WORKERS]:
        workers_dir = "{run_dir}/workers_{workers}".format(run_dir=run_dir, workers=workers)
        os.makedirs(workers_dir)

        for connections in config[Keys.TEST_PARAMS][Keys.CONNECTIONS]:
            connections_dir = "{workers_dir}/connections_{connections}".format(
                workers_dir=workers_dir, connections=connections)
            os.makedirs(connections_dir)

            for file in config[Keys.TEST_PARAMS][Keys.FILES]:
                print ">> Running case - Workers: {workers} | Connections: {connections} | File: {file}".format(
                    workers=workers, connections=connections, file=file)
                iteration_dir = "{connections_dir}/file_{file}".format(connections_dir=connections_dir, file=file)
                os.makedirs(iteration_dir)
                kill_scripts()

                print ">> Running server..."
                run_server_script = "{path}/run_server.py".format(path=os.path.dirname(os.path.abspath(__file__)))
                server_cmd = "{script} --run_type={run_type} --workers={workers}".format(
                    script=run_server_script, run_type=run_type, workers=workers)
                run_cmd_on_background(cmd=server_cmd)
                time.sleep(sleep_sec)

                print ">> Running client..."
                run_client_script = "{path}/run_client.py".format(path=os.path.dirname(os.path.abspath(__file__)))
                client_cmd = "{script} --file {file}.bin --connections {connections} --duration {duration}".format(
                    script=run_client_script, file=file, connections=connections, duration=config[Keys.TEST_PARAMS][Keys.DURATION])
                run_cmd_get_output(client_cmd)

                save_automation_config_cmd = "cp -f {file} {dst}".format(
                    file=config[Keys.SERVER][Keys.NGINX_CONF], dst=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR])
                run_cmd_and_wait(save_automation_config_cmd)
                save_commands_log_cmd = "mv {file} {dst}".format(
                    file=config[Keys.GENERAL][Keys.CMD_LOG_FILE], dst=iteration_dir)
                run_cmd_and_wait(save_commands_log_cmd)
                save_logs_cmd = "cp -rf {file} {dst}".format(
                    file=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR], dst=iteration_dir)
                run_cmd_and_wait(save_logs_cmd)


def get_total_cases_num():
    """Return total number of cases."""
    return (len(config[Keys.TEST_PARAMS][Keys.RUN_TYPES]) *
            len(config[Keys.TEST_PARAMS][Keys.NGINX_WORKERS]) *
            len(config[Keys.TEST_PARAMS][Keys.FILES]) *
            len(config[Keys.TEST_PARAMS][Keys.CONNECTIONS]))


def get_run_time():
    """Return the duration of the total run."""
    num_of_cases = get_total_cases_num()
    sleep_between_cases = 2 * sleep_sec
    case_duration_s = sleep_between_cases + config[Keys.TEST_PARAMS][Keys.DURATION] + 3
    total_duration_s = num_of_cases * case_duration_s
    total_duration_m = total_duration_s / 60.0
    total_duration_h = total_duration_m / 60.0
    return total_duration_s, total_duration_m, total_duration_h


def print_run_parameters():
    """Print parameters of the run."""
    seperator = "{:-^80}".format("")
    table_seperator =  "{:=^80}".format("")
    print table_seperator
    print "{:^80}".format("Test Parameters")
    print table_seperator

    duration = "| Single case duration: {duration} seconds".format(duration=config[Keys.TEST_PARAMS][Keys.DURATION])
    print duration
    print seperator

    total_duration = "| Total duration estimation time: {0} seconds = {1:.2f} minutes = {2:.2f} hours".format(
        *get_run_time())
    print total_duration
    print seperator

    cases = "| Number of cases: {num}".format(num=get_total_cases_num())
    print cases
    print seperator

    run_types = "| Run types: {types}".format(types=",".join(config[Keys.TEST_PARAMS][Keys.RUN_TYPES]))
    print run_types
    print seperator

    workers = "| Nginx workers: {workers}".format(workers=",".join(config[Keys.TEST_PARAMS][Keys.NGINX_WORKERS]))
    print workers
    print seperator

    files = "| Files: {files}".format(files=",".join(config[Keys.TEST_PARAMS][Keys.FILES]))
    print files
    print seperator

    connections = "| Connections: {connections}".format(connections=",".join(config[Keys.TEST_PARAMS][Keys.CONNECTIONS]))
    print connections

    print table_seperator


def main():
    """Run main entry point of the script."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print_run_parameters()

    print "> Running cleanup..."
    run_cleanup()

    for run_type in config[Keys.TEST_PARAMS][Keys.RUN_TYPES]:
        print "> Running {run_type} run...".format(run_type=run_type)
        run(run_type)

    save_automation_config_cmd = "cp -f {file} {dst}".format(
        file=config_file,
        dst=config[Keys.GENERAL][Keys.RES_DIR])
    run_cmd_and_wait(save_automation_config_cmd)
    save_nginx_config_cmd = "cp -f {file} {dst}".format(
        file=config[Keys.SERVER][Keys.NGINX_CONF],
        dst=config[Keys.GENERAL][Keys.RES_DIR])
    run_cmd_and_wait(save_nginx_config_cmd)

    print "> Running remote cleanup..."
    kill_scripts()
    print "> Running results parse..."
    parse_results_cmd = "{path}/parse_results.py".format(path=os.path.dirname(os.path.abspath(__file__)))
    run_cmd_and_wait(parse_results_cmd)
    print "> Results directory location: {path}".format(path=config[Keys.GENERAL][Keys.RES_DIR])
    print "> DONE"


if __name__ == "__main__":
    main()
