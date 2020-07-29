# Copyright 2020 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import subprocess
import csv
import pandas as pd

parser = argparse.ArgumentParser(
        description="update configuration of design(s) per given PDK")


parser.add_argument('--benchmark', '-b', action='store', required=True,
                help="The csv file from which to extract the benchmark results")

parser.add_argument('--regression_results', '-r', action='store', required=True,
                help="The csv file to be tested")

parser.add_argument('--output_report', '-o', action='store', required=True,
                help="The file to print the final report in")


args = parser.parse_args()
benchmark_file = args.benchmark
regression_results_file = args.regression_results
output_report_file = args.output_report

benchmark =dict()
regression_results =dict()

output_report_list = []

testFail = False

configuration_mismatches = []
critical_mismatches = []

missing_configs = []


base_configs = ['CLOCK_PERIOD', 'SYNTH_STRATEGY', 'SYNTH_MAX_FANOUT','FP_CORE_UTIL', 'FP_ASPECT_RATIO',
                'FP_PDN_VPITCH', 'FP_PDN_HPITCH', 'PL_TARGET_DENSITY', 'GLB_RT_ADJUSTMENT', 'PDK_VARIANT', 'CELL_PAD', 'ROUTING_STRATEGY']

critical_statistics = ['cell_count', 'tritonRoute_violations', 'Short_violations','MetSpc_violations','OffGrid_violations','MinHole_violations','Other_violations' , 'Magic_violations', 'antenna_violations' ,'wire_length', 'vias']

note_worthy_statistics = ['runtime','DIEAREA_mm^2','CellPer_mm^2' ,'OpenDP_Util', 'wns', 'HPWL', 'wires_count','wire_bits','public_wires_count', 'public_wire_bits','memories_count','memory_bits', 'processes_count' ,'cells_pre_abc', 'AND','DFF','NAND', 'NOR' ,'OR', 'XOR', 'XNOR', 'MUX','inputs', 'outputs', 'level','EndCaps', 'TapCells', 'Diodes', 'Total_Physical_Cells',]

def findIdx(header, label):
    for idx in range(len(header)):
        if label == header[idx]:
            return idx
    else:
        return -1

def parseCSV(csv_file):
    map_out = dict()
    csvOpener = open(csv_file, 'r')
    csvData = csvOpener.read().split("\n")
    headerInfo = csvData[0].split(",")
    designNameIdx = findIdx(headerInfo, "design")
    
    remover = 0
    size = len(base_configs)
    while remover < size:
        if base_configs[remover] not in headerInfo:
            missing_configs.append("\nThis configuration "+base_configs[remover]+" doesn't exist in the sheets.")
            base_configs.pop(remover)
            remover -= 1
            size -= 1
        remover += 1

    if designNameIdx == -1:
        print("invalid report. No design names.")
    for i in range(1, len(csvData)):
        if len(csvData[i]):
            entry = csvData[i].split(",")
            designName=entry[designNameIdx]
            for idx in range(len(headerInfo)):
                if idx != designNameIdx:
                    if designName not in map_out.keys():
                        map_out[designName] = dict()
                    map_out[designName][headerInfo[idx]] = entry[idx]
    return map_out

def configurationMismatch(benchmark, regression_results):
    for design in benchmark.keys():
        output_report_list.append("\nComparing Configurations for: "+ design+"\n")
        configuration_mismatches.append("\nComparing Configurations for: "+ design+"\n")
        if design not in regression_results:
            output_report_list.append("\tDesign "+ design+" Not Found in the provided regression sheet\n")
            configuration_mismatches.append("\tDesign "+ design+" Not Found in the provided regression sheet\n")
            continue

        for config in base_configs:
            if benchmark[design][config] == regression_results[design][config]:
                output_report_list.append("\tConfiguration "+ config+" MATCH\n")
                output_report_list.append("\t\tConfiguration "+ config+" value: "+ benchmark[design][config] +"\n")       
            else:
                configuration_mismatches.append("\tConfiguration "+ config+" MISMATCH\n")
                output_report_list.append("\tConfiguration "+ config+" MISMATCH\n")
                configuration_mismatches.append("\t\tDesign "+ design + " Configuration "+ config+" BENCHMARK value: "+ benchmark[design][config] +"\n")
                output_report_list.append("\t\tDesign "+ design + " Configuration "+ config+" BENCHMARK value: "+ benchmark[design][config] +"\n")
                configuration_mismatches.append("\t\tDesign "+ design + " Configuration "+ config+" USER value: "+ regression_results[design][config] +"\n")
                output_report_list.append("\t\tDesign "+ design + " Configuration "+ config+" USER value: "+ regression_results[design][config] +"\n")

def criticalMistmatch(benchmark, regression_results):
    global testFail
    for design in benchmark.keys():
        output_report_list.append("\nComparing Critical Statistics for: "+ design+"\n")
        critical_mismatches.append("\nComparing Critical Statistics for: "+ design+"\n")
        if design not in regression_results:
            testFail = True
            output_report_list.append("\tDesign "+ design+" Not Found in the provided regression sheet\n")
            critical_mismatches.append("\tDesign "+ design+" Not Found in the provided regression sheet\n")
            continue

        for stat in critical_statistics:
            if benchmark[design][stat] >= regression_results[design][stat] or benchmark[design][stat] == "-1":
                output_report_list.append("\tStatistic "+ stat+" MATCH\n")
                output_report_list.append("\t\tStatistic "+ stat+" value: "+ benchmark[design][stat] +"\n")       
            else:
                testFail = True
                critical_mismatches.append("\tStatistic "+ stat+" MISMATCH\n")
                output_report_list.append("\tStatistic "+ stat+" MISMATCH\n")
                critical_mismatches.append("\t\tDesign "+ design + " Statistic "+ stat+" BENCHMARK value: "+ benchmark[design][stat] +"\n")
                output_report_list.append("\t\tDesign "+ design + " Statistic "+ stat+" BENCHMARK value: "+ benchmark[design][stat] +"\n")
                critical_mismatches.append("\t\tDesign "+ design + " Statistic "+ stat+" USER value: "+ regression_results[design][stat] +"\n")
                output_report_list.append("\t\tDesign "+ design + " Statistic "+ stat+" USER value: "+ regression_results[design][stat] +"\n")

def noteWorthyMismatch(benchmark, regression_results):
    for design in benchmark.keys():
        output_report_list.append("\nComparing Note Worthy Statistics for: "+ design+"\n")
        if design not in regression_results:
            output_report_list.append("\tDesign "+ design+" Not Found in the provided regression sheet\n")
            continue

        for stat in note_worthy_statistics:
            if benchmark[design][stat] >= regression_results[design][stat] or benchmark[design][stat] == "-1":
                output_report_list.append("\tStatistic "+ stat+" MATCH\n")
                output_report_list.append("\t\tStatistic "+ stat+" value: "+ benchmark[design][stat] +"\n")       
            else:
                output_report_list.append("\tStatistic "+ stat+" MISMATCH\n")
                output_report_list.append("\t\tDesign "+ design + " Statistic "+ stat+" BENCHMARK value: "+ benchmark[design][stat] +"\n")
                output_report_list.append("\t\tDesign "+ design + " Statistic "+ stat+" USER value: "+ regression_results[design][stat] +"\n")


benchmark = parseCSV(benchmark_file)
regression_results = parseCSV(regression_results_file)

configurationMismatch(benchmark,regression_results)
criticalMistmatch(benchmark,regression_results)
noteWorthyMismatch(benchmark, regression_results)

report = ""
if testFail:
    report = "TEST FAILED\n"
else:
    report = "TEST PASSED\n"

if len(missing_configs):
    report += "\nThese configuration are missing:\n"
    report += "".join(missing_configs)

if testFail:
    report += "\n\nCritical Mismatches These are the reason why the test failed:\n\n"
    report += "".join(critical_mismatches)

if testFail:
    report += "\n\nConfiguration Mismatches. These are expected to cause differences between the results:\n\n"
    report += "".join(configuration_mismatches)
    
report += "\nThis is the full generated report:\n"
report += "".join(output_report_list)



outputReportOpener = open(output_report_file, 'w')
outputReportOpener.write(report)
outputReportOpener.close()