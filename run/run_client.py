#!/bin/python

"""Nginx automation from client side."""

import os
import time
import shutil
import signal
import json
import math

from optparse import OptionParser, OptionGroup
from common import *

##### Script parameters #####


# General:
server_results = dict()
client_results = dict()
total_results = dict()
client_details = dict()

# Durations used in the script:
wrk_socket_timeout = 2
command_timeout = 15

# Log files:
wrk_output_file = "/tmp/wrk_out.log"
wrk_log_dir = "/tmp/wrk_logs"
all_wrk_logs_dir = "/tmp/all_wrk_logs_dir"
cpustat_log_file = "/tmp/cpustat_log.txt"
script_output_log_file = "{dir}/{name}".format(
    dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR], name="wrk_client_script_stdout.txt")
server_results_log_file = "{dir}/{name}".format(
    dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR], name="server_results_log_file.json")
client_results_log_file = "{dir}/{name}".format(
    dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR], name="client_results_log_file.json")
total_results_summary_log_file = "{dir}/{name}".format(
    dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR], name="total_results_summary_log_file.json")

# Setup details:
server_url = "http://{ip}:{port}".format(
    ip=config[Keys.SERVER][Keys.NGINX_IP], port=config[Keys.SERVER][Keys.NGINX_PORT])


### Helper functions ###


def signal_handler(sig, frame):
    """Signal handler for cleanups."""
    print " >>> Got Ctrl-C, running cleanup..."
    run_cleanup()
    sys.exit(0)


def log(line):
    """Log wrapper function with this script log file."""
    log_common(line=line, log_file=script_output_log_file)


def run_cleanup():
    """Run cleanup on remote servers."""
    run_cmd_and_wait("rm -rf {dir}".format(dir=all_wrk_logs_dir))
    run_cmd_and_wait("rm -f {file}".format(file=script_output_log_file))
    run_cmd_and_wait("mkdir {dir}".format(dir=all_wrk_logs_dir))
    run_cmd_and_wait("mkdir -p {dir}".format(dir=config[Keys.GENERAL][Keys.REMOTE_LOGS_DIR]))

    # Cleanup server:
    run_remote_cmd(cmd="pkill -9 cpustat", host=config[Keys.SERVER][Keys.NGINX_SERVER])

    # Cleanup clients:
    for client in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        run_remote_cmd_get_output(cmd="pkill -9 wrk", host=client)
        run_remote_cmd_get_output(cmd="rm -rf {wrk_log_dir}".format(wrk_log_dir=wrk_log_dir), host=client)
        run_remote_cmd_get_output(cmd="rm -f {wrk_output_file}".format(wrk_output_file=wrk_output_file), host=client)
        run_remote_cmd_get_output(cmd="mkdir {wrk_log_dir}".format(wrk_log_dir=wrk_log_dir), host=client)


def build_result_structures():
    """Build remote hosts results structures."""
    global server_results, client_results, total_results
    server_results = {
        "connections_num_before": 0,
        "connections_num_after": 0,
        "connections_num_total": 0,
        "num_of_vma_irqs_before": 0,
        "num_of_vma_irqs_after": 0,
        "num_of_vma_irqs_total": 0,
        "cpu_utilization": 0
    }

    client_results = {
        "total": {
            "results": {
                "bw_gbps": 0,
                "rps": 0,
                "lat_avg": 0,
                "lat_max": 0,
                "sock_err_connect": 0,
                "sock_err_read": 0,
                "sock_err_write": 0,
                "sock_err_timeout": 0,
                "completed_requests": 0,
                "sent_requests": 0
            },
            "metrics": {
                "tcp_syn_retransmit": 0
            }
        },
        "clients": {}
    }

    for client in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        client_results["clients"][client] = {
            "results": {
                "bw": {"result": [], "str": []},
                "rps": {"result": [], "str": []},
                "lat_avg": {"result": [], "str": []},
                "lat_stdv": {"result": [], "str": []},
                "lat_max": {"result": [], "str": []},
                "sock_err_connect": {"result": [], "str": []},
                "sock_err_read": {"result": [], "str": []},
                "sock_err_write": {"result": [], "str": []},
                "sock_err_timeout": {"result": [], "str": []},
                "completed_requests": {"result": [], "str": []},
                "sent_requests": {"result": [], "str": []}
            },
            "metrics": {
                "tcp_syn_retransmit_before": 0,
                "tcp_syn_retransmit_after": 0
            }
        }

    total_results = {
        "test_details": {
            "nginx_server": "",
            "nginx_workers": 0,
            "num_of_client_machines": "",
            "client_machines": "",
            "total_amount_of_connections": 0,
            "file": "",
            "duration": 0,
        },
        "results": {
            "server_cpu_utilization": 0,
            "connections": 0,
            "vma_irqs": 0,
            "throughput": 0,
            "requests": 0,
            "avg_latency": 0,
            "max_latency": 0,
            "sent_requests": 0,
            "completed_requests": 0,
            "socket_connect_errors": 0,
            "socket_read_errors": 0,
            "socket_write_errors": 0,
            "socket_timeout_errors": 0,
            "tcp_syn_retrans": 0,

        }
    }


def collect_metrics_before_test(options):
    """Metric collection before the test steps."""
    # Get number of connections from Nginx before the test:
    get_server_connection_cmd = "curl -s {server_url}/stub_status | tail -2 | head -1".format(
        server_url=server_url)
    output = run_remote_cmd_get_output(cmd=get_server_connection_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])
    server_results["connections_num_before"] = int(output.replace("\n", "").split()[1])

    # Run CPU utilization sampling on server:
    cpustat_period = options.duration - 20
    cpu_util_cmd = "nohup {_bin} -s -w 10 -i {duration} -d -o {log}".format(
        _bin=config[Keys.SERVER][Keys.CPUSTAT_BIN], duration=cpustat_period, log=cpustat_log_file)
    run_remote_cmd_on_backround(cmd=cpu_util_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])

    # Get number of VMA IRQs statistics before the test:
    get_vma_irqs_cmd = "cat /proc/interrupts | grep \"{interface}-0\"".format(
        interface=config[Keys.SERVER][Keys.INTERFACE])
    output = run_remote_cmd_get_output(cmd=get_vma_irqs_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])
    server_results["num_of_vma_irqs_before"] = int(output.split()[1])

    ### Get client metrics before the test ###

    for client in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        # Get SYN TCP retransmit statistics before the test:
        get_tcp_syn_retransmit_cmd = "netstat -s | grep TCPSynRetrans"
        output = run_remote_cmd_get_output(cmd=get_tcp_syn_retransmit_cmd, host=client)
        if output.replace(" ", "") is "":
            output = 0
        else:
            output = output.split()[1]
        client_results["clients"][client]["metrics"]["tcp_syn_retransmit_before"] = int(output)


def collect_metrics_after_test(options):
    """Metric collection after the test steps."""
    # Get CPU utilization sampling from server log:
    get_cpu_usage_cmd = "grep -Po '^Average: total=\K[0-9.]+' {log}".format(log=cpustat_log_file)
    output = run_remote_cmd_get_output(cmd=get_cpu_usage_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])
    if output.replace(" ", "") is not "":
        server_results["cpu_utilization"] = float(output)

    # Get number of connections from Nginx after the test:
    get_server_connection_cmd = \
        "curl -s {server_url}/stub_status | tail -2 | head -1".format(server_url=server_url)
    output = run_remote_cmd_get_output(
        cmd=get_server_connection_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER], timeout=command_timeout)
    if output.replace(" ", "") is not "":
        server_results["connections_num_after"] = int(output.replace("\n", "").split()[1])

    # Get total number of connections during the test:
    server_results["connections_num_total"] = server_results["connections_num_after"] - \
        server_results["connections_num_before"]

    # Get number of VMA IRQs statistics after the test:
    get_vma_irqs_cmd = "cat /proc/interrupts | grep \"{interface}-0\"".format(
        interface=config[Keys.SERVER][Keys.INTERFACE])
    output = run_remote_cmd_get_output(cmd=get_vma_irqs_cmd, host=config[Keys.SERVER][Keys.NGINX_SERVER])
    server_results["num_of_vma_irqs_after"] = int(output.split()[1])

    # Get total number of connections during the test:
    server_results["num_of_vma_irqs_total"] = server_results["num_of_vma_irqs_after"] - \
        server_results["num_of_vma_irqs_before"]

    ### Get client metrics after the test ###

    for client in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        # Get SYN TCP retransmit statistics after the test:
        get_tcp_syn_retransmit_cmd = "netstat -s | grep TCPSynRetrans"
        output = run_remote_cmd_get_output(cmd=get_tcp_syn_retransmit_cmd, host=client)
        if output.replace(" ", "") is "":
            output = 0
        else:
            output = output.split()[1]
        client_results["clients"][client]["metrics"]["tcp_syn_retransmit_after"] = int(output)
        tcp_syn_retransmit_total = client_results["clients"][client]["metrics"]["tcp_syn_retransmit_after"] - \
            client_results["clients"][client]["metrics"]["tcp_syn_retransmit_before"]

        # Get total number of SYN TCP retransmit statistics during the test:
        client_results["total"]["metrics"]["tcp_syn_retransmit"] += tcp_syn_retransmit_total


def run_the_test(options):
    """Run the test on remote setups."""
    wrk_command_format = ("taskset -c {core} {_bin} -t 1 --latency -c {connections} -d {duration}s "
                          "--timeout {socket_timeout}s {url} >> {wrk_log_dir}/wrk_{host}_{_id} & ")
    # Build client commands:
    client_commands = dict()
    client_id = 1
    for client_name in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        # Build current client command:
        client = client_details[client_name]
        cmd = ""
        core = 0
        for wrk_index in range(1, client["num_of_clients"] + 1):
            url = "{server_url}/{file}".format(server_url=server_url, file=options.server_file)
            cmd += wrk_command_format.format(
                core=core, _bin=config[Keys.CLIENT][Keys.WRK_BIN], connections=client["num_of_connections"],
                duration=options.duration, socket_timeout=wrk_socket_timeout,
                url=url, wrk_log_dir=wrk_log_dir, host=client_name, _id=client_id)
            client_id += 1
            core += 1
        client_commands[client_name] = "{cmd}".format(cmd=cmd)

    # Run the different client servers:
    for client_name in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        run_remote_cmd_on_backround(cmd=client_commands[client_name], host=client_name)

    time.sleep(options.duration)

    wrk_status_cmd = "pgrep wrk | wc -l"
    kill_counter = 1
    while True:
        done = True
        for client_name in config[Keys.CLIENT][Keys.WRK_SERVERS]:
            output = run_remote_cmd_get_output(cmd=wrk_status_cmd, host=client_name)
            num_of_wrks = int(output)
            if num_of_wrks != 0:
                done = False
        if done is True:
            break
        time.sleep(1)
        kill_counter -= 1
        if kill_counter == 0:
            break

    if kill_counter == 0:
        for client_name in config[Keys.CLIENT][Keys.WRK_SERVERS]:
            run_remote_cmd(cmd="pkill -2 wrk", host=client_name)
        time.sleep(1)


def get_bw_result(line):
    """Return calculated BW result."""
    bw_str = line.split()[1]
    if "GB" in bw_str:
        result = bw_str[:-2]
        result_units = " [GB]"
        multiplier = 1000000000
    elif "MB" in bw_str:
        result = bw_str[:-2]
        result_units = " [MB]"
        multiplier = 1000000
    elif "KB" in bw_str:
        result = bw_str[:-2]
        result_units = " [KB]"
        multiplier = 1000
    elif "B" in bw_str:
        result = bw_str[:-1]
        result_units = " [B]"
        multiplier = 1
    bw_result_str = "{result:,} {units}".format(result=float(result), units=result_units)
    bw_result_bps = float(result) * 8 * multiplier

    return (bw_result_str, bw_result_bps)


def get_rps_result(line):
    """Return calculated RPS result."""
    rps_str = line.split()[1]
    result_units = "[RPS]"
    rps_result = float(rps_str)
    rps_result_str = "{result:,} {units}".format(result=rps_result, units=result_units)

    return (rps_result_str, rps_result)


def get_latency_result(line):
    """Return calculated latency result."""
    def convert_to_ms(lat_str):
        lat_result = 0
        if "us" in lat_str:
            lat_result = float(lat_str[:-2]) / 1000
        elif "ms" in lat_str:
            lat_result = float(lat_str[:-2]) * 1
        elif "s" in lat_str:
            lat_result = float(lat_str[:-1]) * 1000
        elif "m" in lat_str:
            lat_result = float(lat_str[:-1]) * 60 * 1000

        result_units = "[ms]"
        lat_result_str = "{result:,} {units}".format(result=lat_result, units=result_units)

        return lat_result_str, lat_result

    lat_avg_result_str, lat_avg_result = convert_to_ms(line.split()[1])
    lat_stdv_result_str, lat_stdv_result = convert_to_ms(line.split()[2])
    lat_max_result_str, lat_max_result = convert_to_ms(line.split()[3])

    return (lat_avg_result_str, lat_avg_result,
            lat_stdv_result_str, lat_stdv_result,
            lat_max_result_str, lat_max_result)


def get_sock_err_result_helper(line, error_index):
    """Return socket error result helper function."""
    sock_err_str = line.split()[error_index].replace(",", "")
    if sock_err_str.replace(" ", "") is "":
        sock_err_str = str(0)
    result_units = ""
    sock_err_result = int(sock_err_str)
    sock_err_result_str = "{result:,} {units}".format(result=sock_err_result, units=result_units)

    return (sock_err_result_str, sock_err_result)


def get_completed_requests_result(line):
    """Return the requests completed successfully result."""
    completed_requests_str = line.split()[0]
    if completed_requests_str.replace(" ", "") is "":
        completed_requests_str = str(0)
    result_units = ""
    completed_requests_result = int(completed_requests_str)
    completed_requests_result_str = "{result:,} {units}".format(result=completed_requests_result, units=result_units)

    return (completed_requests_result_str, completed_requests_result)


def get_sent_requests_result(line):
    """Return the total requests sent result."""
    sent_requests_str = line.split()[3]
    if sent_requests_str.replace(" ", "") is "":
        sent_requests_str = str(0)
    result_units = ""
    sent_requests_result = int(sent_requests_str)
    sent_requests_result_str = "{result:,} {units}".format(result=sent_requests_result, units=result_units)

    return (sent_requests_result_str, sent_requests_result)


def calculate_results(options):
    """Calculate test result and print them."""
    # Get log files from remote hosts:
    host_logs = list()
    cmd_pids = list()
    for client_name in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        get_logs_list_cmd = "ls {dir_}/* | sort -V".format(dir_=wrk_log_dir)
        logs_list = run_remote_cmd_get_output(cmd=get_logs_list_cmd, host=client_name).split("\n")

        for file in logs_list:
            if file.replace(" ", "") is "":
                continue

            get_log_file_cmd = "scp {user}@{client}:{file} {all_wrk_logs_dir}".format(
                user=config[Keys.GENERAL][Keys.USER], client=client_name, file=file, all_wrk_logs_dir=all_wrk_logs_dir)
            pid = run_cmd_on_background(cmd=get_log_file_cmd, stdout=open(os.devnull, 'w'))
            cmd_pids.append(pid)
            worker_id = os.path.basename(file)
            local_file = "{all_wrk_logs_dir}/{worker_id}".format(all_wrk_logs_dir=all_wrk_logs_dir, worker_id=worker_id)
            host_logs.append(local_file)

    time.sleep(1)
    for pid in cmd_pids:
        get_output_from_pipe(pid)

    # Calculate the results:
    total_bw_gbps = 0
    total_rps = 0

    for log_file in host_logs:
        client_name = log_file.split('_')[-2]
        cur_rst = client_results["clients"][client_name]["results"]
        if os.path.isfile(log_file) is False:
            get_log_file_cmd = "scp {user}@{client}:{folder}/{file} {all_wrk_logs_dir}".format(
                user=config[Keys.GENERAL][Keys.USER], client=client_name,
                folder=wrk_log_dir, file=log_file.split('/')[-1],
                all_wrk_logs_dir=all_wrk_logs_dir)
            run_cmd_and_wait(cmd=get_log_file_cmd, stdout=open(os.devnull, 'w'))
        with open(log_file, 'r') as wrk_output_file:
            bw_result_bps = rps_result = sent_requests_result = 0
            lat_avg_result = lat_stdv_result = lat_max_result = 0
            sock_err_connect_result = sock_err_read_result = sock_err_write_result = sock_err_timeout_result = 0
            bw_result_str = rps_result_str = sent_requests_str = ""
            sock_err_connect_str = sock_err_read_str = sock_err_write_str = sock_err_timeout_str = ""
            lat_avg_result_str = lat_stdv_result_str = lat_max_result_str = ""
            for line in wrk_output_file:
                if "Transfer/sec" in line:
                    (bw_result_str, bw_result_bps) = get_bw_result(line)
                elif "Requests/sec" in line:
                    (rps_result_str, rps_result) = get_rps_result(line)
                elif "Latency" in line and "Distribution" not in line:
                    (lat_avg_result_str, lat_avg_result,
                        lat_stdv_result_str, lat_stdv_result,
                        lat_max_result_str, lat_max_result) = get_latency_result(line)
                elif "Socket errors" in line:
                    (sock_err_connect_str, sock_err_connect_result) = get_sock_err_result_helper(line, 3)
                    (sock_err_read_str, sock_err_read_result) = get_sock_err_result_helper(line, 5)
                    (sock_err_write_str, sock_err_write_result) = get_sock_err_result_helper(line, 7)
                    (sock_err_timeout_str, sock_err_timeout_result) = get_sock_err_result_helper(line, 9)
                elif "requests in" in line:
                    (completed_requests_str, completed_requests_result) = get_completed_requests_result(line)
                elif "Total requests sent" in line:
                    (sent_requests_str, sent_requests_result) = get_sent_requests_result(line)

        cur_rst["bw"]["result"].append(bw_result_bps)
        cur_rst["bw"]["str"].append(bw_result_str)
        cur_rst["rps"]["result"].append(rps_result)
        cur_rst["rps"]["str"].append(rps_result_str)
        cur_rst["lat_avg"]["result"].append(lat_avg_result)
        cur_rst["lat_avg"]["str"].append(lat_avg_result_str)
        cur_rst["lat_stdv"]["result"].append(lat_stdv_result)
        cur_rst["lat_stdv"]["str"].append(lat_stdv_result_str)
        cur_rst["lat_max"]["result"].append(lat_max_result)
        cur_rst["lat_max"]["str"].append(lat_max_result_str)
        cur_rst["sock_err_connect"]["result"].append(sock_err_connect_result)
        cur_rst["sock_err_connect"]["str"].append(sock_err_connect_str)
        cur_rst["sock_err_read"]["result"].append(sock_err_read_result)
        cur_rst["sock_err_read"]["str"].append(sock_err_read_str)
        cur_rst["sock_err_write"]["result"].append(sock_err_write_result)
        cur_rst["sock_err_write"]["str"].append(sock_err_write_str)
        cur_rst["sock_err_timeout"]["result"].append(sock_err_timeout_result)
        cur_rst["sock_err_timeout"]["str"].append(sock_err_timeout_str)
        cur_rst["completed_requests"]["result"].append(completed_requests_result)
        cur_rst["completed_requests"]["str"].append(completed_requests_str)
        cur_rst["sent_requests"]["result"].append(sent_requests_result)
        cur_rst["sent_requests"]["str"].append(sent_requests_str)
        client_results["total"]["results"]["rps"] += round(rps_result, 2)
        client_results["total"]["results"]["bw_gbps"] += round(bw_result_bps / 1000000000, 2)

    all_clients_lat_avg_list = list()
    all_clients_lat_max_list = list()
    all_clients_sock_err_connect_list = list()
    all_clients_sock_err_read_list = list()
    all_clients_sock_err_write_list = list()
    all_clients_sock_err_timeout_list = list()
    all_clients_completed_requests_list = list()
    all_clients_sent_requests_list = list()
    for client, value in client_results["clients"].items():
        result = value["results"]
        all_clients_lat_avg_list += result["lat_avg"]["result"]
        all_clients_lat_max_list += result["lat_max"]["result"]
        all_clients_sock_err_connect_list += result["sock_err_connect"]["result"]
        all_clients_sock_err_read_list += result["sock_err_read"]["result"]
        all_clients_sock_err_write_list += result["sock_err_write"]["result"]
        all_clients_sock_err_timeout_list += result["sock_err_timeout"]["result"]
        all_clients_completed_requests_list += result["completed_requests"]["result"]
        all_clients_sent_requests_list += result["sent_requests"]["result"]

    client_results["total"]["results"]["lat_avg"] = sum(all_clients_lat_avg_list) / len(all_clients_lat_avg_list)
    client_results["total"]["results"]["lat_max"] = max(all_clients_lat_max_list)
    client_results["total"]["results"]["sock_err_connect"] = sum(all_clients_sock_err_connect_list)
    client_results["total"]["results"]["sock_err_read"] = sum(all_clients_sock_err_read_list)
    client_results["total"]["results"]["sock_err_write"] = sum(all_clients_sock_err_write_list)
    client_results["total"]["results"]["sock_err_timeout"] = sum(all_clients_sock_err_timeout_list)
    client_results["total"]["results"]["completed_requests"] = sum(all_clients_completed_requests_list)
    client_results["total"]["results"]["sent_requests"] = sum(all_clients_sent_requests_list)


def print_results(options):
    """Print results summary."""
    get_workers_cmd = "cat {config_file} | grep worker_processes | head -n 1".format(
        config_file=config[Keys.SERVER][Keys.NGINX_CONF])
    output = run_cmd_get_output(get_workers_cmd)
    num_of_nginx_workers = output.split()[1].replace(";", "")
    log("{:*^80}\n".format(" Test Parameters "))
    log("--- Nginx server: {server}".format(server=config[Keys.SERVER][Keys.NGINX_SERVER]))
    log("--- Number of workers: {workers}".format(workers=num_of_nginx_workers))
    log("--- Number of client machines: {clients}".format(clients=len(config[Keys.CLIENT][Keys.WRK_SERVERS])))
    log("--- Client machines: {clients_list}".format(clients_list=str(config[Keys.CLIENT][Keys.WRK_SERVERS])))
    log("--- Total amount of connections: {connections}".format(connections=options.connections))
    log("--- File: {file}".format(file=options.server_file))
    log("--- Duration: {duration} seconds".format(duration=options.duration))

    worker_result_format = (
        "Client {id_:<2} --> BW: {bw:<12} | RPS: {rps:<12} | LAT AVG: {lat_avg:<12} |"
        " LAT STDV: {lat_stdv:<12} | LAT MAX: {lat_max:<12} |"
        " Sent requests: {sent_requests:<5} | Completed requests: {completed_requests:<5} |"
        " Connect ERR: {sock_err_connect:<5} |"
        " Read ERR: {sock_err_read:<5} |"
        " Write ERR: {sock_err_write:<5} |"
        " Timeout ERR: {sock_err_timeout:<5} |")
    id_counter = 1
    log("\n{:*^80}\n".format(" Clients Results Summary "))

    for client in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        result = client_results["clients"][client]["results"]
        log("------------- Host: {client}\n".format(client=client))
        for wrk_index in range(client_details[client]["num_of_clients"]):
            result_line = worker_result_format.format(
                id_=id_counter,
                bw=result["bw"]["str"][wrk_index],
                rps=result["rps"]["str"][wrk_index],
                lat_avg=result["lat_avg"]["str"][wrk_index],
                lat_stdv=result["lat_stdv"]["str"][wrk_index],
                lat_max=result["lat_max"]["str"][wrk_index],
                sock_err_connect=result["sock_err_connect"]["str"][wrk_index],
                sock_err_read=result["sock_err_read"]["str"][wrk_index],
                sock_err_write=result["sock_err_write"]["str"][wrk_index],
                sock_err_timeout=result["sock_err_timeout"]["str"][wrk_index],
                completed_requests=result["completed_requests"]["str"][wrk_index],
                sent_requests=result["sent_requests"]["str"][wrk_index])
            log(result_line)
            id_counter += 1
        log("\n")

    log("{:*^80}\n".format(" Total results summary "))
    log("{:=^50}".format(" Server Results "))
    log("------- CPU utilization:        {cpu_util} [%]".format(
        cpu_util=server_results["cpu_utilization"]))
    log("------- Connections:            {connections:,}".format(
        connections=server_results["connections_num_total"]))
    log("------- VMA IRQs:               {irqs:,}".format(
        irqs=server_results["num_of_vma_irqs_total"]))

    log("{:=^50}\n".format(""))

    log("{:=^50}".format(" Client Results "))
    log("------- Throughput:             {bw:} [Gbps]".format(
        bw=client_results["total"]["results"]["bw_gbps"]))
    log("------- Requests:               {rps:,} [RPS]".format(
        rps=client_results["total"]["results"]["rps"]))
    log("------- Avg latency:            {lat_avg:,.2f} [ms]".format(
        lat_avg=client_results["total"]["results"]["lat_avg"]))
    log("------- Max latency:            {lat_max:,.2f} [ms]".format(
        lat_max=client_results["total"]["results"]["lat_max"]))
    log("------- Sent requests:          {sent_requests:,}".format(
        sent_requests=client_results["total"]["results"]["sent_requests"]))
    log("------- Completed requests:     {completed_requests:,}".format(
        completed_requests=client_results["total"]["results"]["completed_requests"]))
    log("------- Socket connect error:   {sock_err_connect:,}".format(
        sock_err_connect=client_results["total"]["results"]["sock_err_connect"]))
    log("------- Socket read error:      {sock_err_read:,}".format(
        sock_err_read=client_results["total"]["results"]["sock_err_read"]))
    log("------- Socket write error:     {sock_err_write:,}".format(
        sock_err_write=client_results["total"]["results"]["sock_err_write"]))
    log("------- Socket timeout error:   {sock_err_timeout:,}".format(
        sock_err_timeout=client_results["total"]["results"]["sock_err_timeout"]))
    log("------- TCPSynRetrans:          {retrans:,}".format(
        retrans=client_results["total"]["metrics"]["tcp_syn_retransmit"]))
    log("{:=^50}".format(""))

    total_results["test_details"]["nginx_server"] = config[Keys.SERVER][Keys.NGINX_SERVER]
    total_results["test_details"]["nginx_workers"] = num_of_nginx_workers
    total_results["test_details"]["num_of_client_machines"] = len(config[Keys.CLIENT][Keys.WRK_SERVERS])
    total_results["test_details"]["client_machines"] = str(config[Keys.CLIENT][Keys.WRK_SERVERS])
    total_results["test_details"]["total_amount_of_connections"] = options.connections
    total_results["test_details"]["file"] = options.server_file
    total_results["test_details"]["duration"] = options.duration
    total_results["results"]["server_cpu_utilization"] = server_results["cpu_utilization"]
    total_results["results"]["connections"] = server_results["connections_num_total"]
    total_results["results"]["vma_irqs"] = server_results["num_of_vma_irqs_total"]
    total_results["results"]["throughput"] = client_results["total"]["results"]["bw_gbps"]
    total_results["results"]["requests"] = client_results["total"]["results"]["rps"]
    total_results["results"]["avg_latency"] = client_results["total"]["results"]["lat_avg"]
    total_results["results"]["max_latency"] = client_results["total"]["results"]["lat_max"]
    total_results["results"]["sent_requests"] = client_results["total"]["results"]["sent_requests"]
    total_results["results"]["completed_requests"] = client_results["total"]["results"]["completed_requests"]
    total_results["results"]["socket_connect_errors"] = client_results["total"]["results"]["sock_err_connect"]
    total_results["results"]["socket_read_errors"] = client_results["total"]["results"]["sock_err_read"]
    total_results["results"]["socket_write_errors"] = client_results["total"]["results"]["sock_err_write"]
    total_results["results"]["socket_timeout_errors"] = client_results["total"]["results"]["sock_err_timeout"]
    total_results["results"]["tcp_syn_retrans"] = client_results["total"]["metrics"]["tcp_syn_retransmit"]

    with open(server_results_log_file, 'w') as file:
        json.dump(obj=server_results, fp=file)

    with open(client_results_log_file, 'w') as file:
        json.dump(obj=client_results, fp=file)

    with open(total_results_summary_log_file, 'w') as file:
        json.dump(obj=total_results, fp=file)


def build_client_details(options):
    """Build clients details structure."""
    global client_details

    connections_per_client_machines = options.connections / len(config[Keys.CLIENT][Keys.WRK_SERVERS])
    for client in config[Keys.CLIENT][Keys.WRK_SERVERS]:
        client_details[client] = dict()
        num_of_clients = run_remote_cmd_get_output(cmd="nproc --all", host=client)
        wrk_connections = math.floor(connections_per_client_machines / int(num_of_clients))
        client_details[client]["num_of_connections"] = int(wrk_connections)
        client_details[client]["num_of_clients"] = int(num_of_clients)


def parse_list_callback(option, opt, value, parser):
    """Parse list from input."""
    setattr(parser.values, option.dest, value.split(','))


def add_options(parser):
    """Add options to the parser."""
    parser.add_option('-f', '--file', dest='server_file', type='string',
                      help="File to get from server", metavar='<ARG>')
    parser.add_option('-c', '--connections', dest='connections', type='int',
                      help="The total number of connections to open", metavar='<ARG>')
    parser.add_option('-d', '--duration', dest='duration', type='int',
                      help="The duration in seconds of each test case", metavar='<ARG>')


def set_custom_variables(options):
    """Set custom variables for the script options."""
    pass


def main():
    """Run entry point of the script."""
    signal.signal(signal.SIGINT, signal_handler)

    usage = "usage: %prog options\n"
    parser = OptionParser(usage=usage)
    add_options(parser)
    (options, args) = parser.parse_args()
    set_custom_variables(options)

    build_client_details(options)
    build_result_structures()

    print "> Running cleanup..."
    run_cleanup()

    print "> Running metrics collection before the test..."
    collect_metrics_before_test(options)

    print "> Running clients..."
    run_the_test(options)

    print "> Running metrics collection after the test..."
    collect_metrics_after_test(options)

    print "> Running results calculation..."
    calculate_results(options)
    print_results(options)


if __name__ == "__main__":
    main()
