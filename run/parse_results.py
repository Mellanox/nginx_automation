#!/bin/python

import os
import json

results_dir = "/auto/mtrswgwork/simonra/temp/nginx_automation_results"
output_file = "{results_dir}/{run_type}_nginx_automation_parsed_results.csv"
unified_output_file = "{results_dir}/unified_nginx_automation_parsed_results.csv".format(results_dir=results_dir)
csv_header = "File,Connections,Throughput[Gbps],Requests[RPS],Concurrent Connections,CPU[%],CPU/Gbps[%],CPU/RPS[%]\n"
csv_line = "{file_size},{connections},{throughput},{requests},{concurrent_connections},{cpu},{cpu_gbps},{cpu_rps}\n"


def parse_directory(run_type):
    """Parse VMA/kernel directory."""
    top_dir = "{results_dir}/{run_type}".format(results_dir=results_dir, run_type=run_type)
    connections_dir_format = "{top_dir}/{connections_dir}"
    logs_dir_format = "{connections_dir}/{files_dir}"
    results = list()
    for connections_dir in os.listdir(top_dir):
        connections_dir = connections_dir_format.format(top_dir=top_dir, connections_dir=connections_dir)
        for files_dir in os.listdir(connections_dir):
            logs_dir = logs_dir_format.format(connections_dir=connections_dir, files_dir=files_dir)
            result_json = "{logs_dir}/nginx_automation_client_logs/total_results_summary_log_file.json".format(
                logs_dir=logs_dir)
            with open(result_json, 'r') as file:
                result = json.load(file)
                results.append(result)

    return results


def convert_results_to_csv(run_type, results):
    """Convert results objects list to CSV file."""
    output_csv_file = output_file.format(results_dir=results_dir, run_type=run_type)
    if os.path.exists(output_csv_file) is True:
        os.remove(output_csv_file)

    with open(output_csv_file, 'w') as file:
        file.write(csv_header)
        for result in results:
            line = csv_line.format(
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
    for run_type in run_types:
        csv_file = output_file.format(results_dir=results_dir, run_type=run_type)
        current_file_list = list()
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
    """ Run main entry point of the script."""
    run_types = os.listdir(results_dir)
    for run_type in run_types:
        results = parse_directory(run_type)
        convert_results_to_csv(run_type=run_type, results=results)
    unify_to_one_csv(run_types=run_types)


if __name__ == "__main__":
    main()
