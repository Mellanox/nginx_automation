#!/bin/python

import os
import json

from common import *

output_file = "{res_dir}/{run_type}_nginx_automation_parsed_results.csv"
unified_output_file = "{res_dir}/unified_nginx_automation_parsed_results.csv".format(
    res_dir=config[Keys.GENERAL][Keys.RES_DIR])
csv_header = "Workers,File,Connections,Throughput[Gbps],Requests[RPS],Concurrent Connections,CPU[%],CPU/Gbps[%],CPU/RPS[%]\n"
csv_line = "{workers},{file_size},{connections},{throughput},{requests},{concurrent_connections},{cpu},{cpu_gbps},{cpu_rps}\n"


def parse_directory(run_type):
    """Parse VMA/kernel directory."""
    top_dir = "{res_dir}/{run_type}".format(res_dir=config[Keys.GENERAL][Keys.RES_DIR], run_type=run_type)
    workers_dir_format = "{top_dir}/{workers_dir}"
    connections_dir_format = "{workers_dir}/{connections_dir}"
    logs_dir_format = "{connections_dir}/{files_dir}"
    results = list()

    for workers_dir in os.listdir(top_dir):
        workers_dir = workers_dir_format.format(top_dir=top_dir, workers_dir=workers_dir)
        for connections_dir in os.listdir(workers_dir):
            connections_dir = connections_dir_format.format(workers_dir=workers_dir, connections_dir=connections_dir)
            for files_dir in os.listdir(connections_dir):
                logs_dir = logs_dir_format.format(connections_dir=connections_dir, files_dir=files_dir)
                result_json = "{logs_dir}/nginx_automation_logs/total_results_summary_log_file.json".format(
                    logs_dir=logs_dir)
                with open(result_json, 'r') as file:
                    result = json.load(file)
                    results.append(result)

    return results


def convert_results_to_csv(run_type, results):
    """Convert results objects list to CSV file."""
    output_csv_file = output_file.format(res_dir=config[Keys.GENERAL][Keys.RES_DIR], run_type=run_type)
    if os.path.exists(output_csv_file) is True:
        os.remove(output_csv_file)

    with open(output_csv_file, 'w') as file:
        file.write(csv_header)
        for result in results:
            line = csv_line.format(
                workers=result["test_details"]["nginx_workers"],
                file_size=result["test_details"]["file"][:-4],
                connections=result["test_details"]["total_amount_of_connections"],
                throughput=result["results"]["throughput"],
                requests=result["results"]["requests"],
                concurrent_connections=result["results"]["connections"],
                cpu=result["results"]["server_cpu_utilization"],
                cpu_gbps=float("{:.4f}".format(
                    result["results"]["server_cpu_utilization"] / result["results"]["throughput"])),
                cpu_rps=float("{:.4f}".format(
                    result["results"]["server_cpu_utilization"] / result["results"]["requests"]))
            )
            file.write(line)


def unify_to_one_csv(run_types):
    """Unify CSV files to one file."""
    unified_file_list = list()
    table_column_width = "," * 8
    for run_type in run_types:
        csv_file = output_file.format(res_dir=config[Keys.GENERAL][Keys.RES_DIR], run_type=run_type)
        current_file_list = list()
        current_file_list.append(run_type + table_column_width)
        with open(csv_file, 'r') as file:
            for line in file:
                current_file_list.append(line.replace("\n", ""))
        unified_file_list.append(current_file_list)

    csv_table_size = len(unified_file_list[0])
    csv_line_format = "{line},,"
    with open(unified_output_file, 'w') as file:
        file.write("\n\n")
        for line in range(0, csv_table_size):
            for table in unified_file_list:
                csv_line = csv_line_format.format(line=table[line])
                file.write(csv_line)
            file.write("\n")


def main():
    """Run main entry point of the script."""
    for run_type in config[Keys.TEST_PARAMS][Keys.RUN_TYPES]:
        results = parse_directory(run_type)
        convert_results_to_csv(run_type=run_type, results=results)
    unify_to_one_csv(run_types=config[Keys.TEST_PARAMS][Keys.RUN_TYPES])


if __name__ == "__main__":
    main()
