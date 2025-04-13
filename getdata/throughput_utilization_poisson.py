# launch this file from the root directory of the repo
# input files: baseline workload, qvm workload
import sys
sys.path.append('.')
from qiskit_ibm_runtime import QiskitRuntimeService
from qasmbench import QASMBenchmark
from utils import read_workload, read_workload_poisson
from CombinerJob import CombinerJob

workload_type = ''

if len(sys.argv) != 4:
    print('usage: throughput_utilzation.py baseline_workload qvm_workload small/all')
    exit()
if sys.argv[3] != 'small' and sys.argv[3] != 'all':
    print('usage: throughput_utilzation.py baseline_workload qvm_workload small/all')
    exit()

baseline_workload_filename = sys.argv[1]
qvm_workload_filename = sys.argv[2]
workload_type = sys.argv[3]

def read_workload_baseline(filename, encoding = 'utf-8') -> {'name': 'jobid'}:
    ret = {}
    f = open(filename, 'r', encoding=encoding)
    for line in f.readlines():
        jobid, name = line.strip().split()
        ret[name] = jobid
    return ret

service1 = QiskitRuntimeService(channel="ibm_quantum", token="Your access token for baseline workload")

service2 = QiskitRuntimeService(channel="ibm_quantum", token="Your access token for qvm workload")

# small
if workload_type == 'small':
    job_queue = [25, 12, 20, 16, 17, 6, 26, 8, 4, 14, 11, 5, 27, 24, 28, 23, 9, 4, 8, 6, 7, 15, 1, 10, 4, 14, 23, 12, 5, 14, 27, 11, 7, 7, 7, 18, 12, 27, 14, 1, 19, 13, 24, 13, 15, 22, 20, 3, 26, 11, 4, 20, 20, 25, 1, 9, 25, 2, 16, 5, 10, 8, 3, 0, 9, 14, 6, 3, 19, 3, 0, 26, 8, 27, 2, 10, 21, 3, 8, 5, 18, 22, 18, 24, 19, 0, 17, 21, 25, 22, 6, 0, 18, 5, 23, 15, 12, 23, 24, 28, 0, 28, 16, 12, 25, 17, 26, 4, 22, 10, 18, 9, 17, 1, 13, 13, 13, 15, 20, 27, 24, 16, 26, 2, 19, 21, 28, 11, 19, 2, 15, 23, 16, 1, 9, 21, 21, 6, 11, 7, 22, 2, 28, 17, 10]
else:
    job_queue = [25, 45, 0, 30, 7, 8, 4, 14, 10, 2, 33, 5, 20, 19, 7, 6, 34, 43, 24, 46, 12, 25, 30, 15, 21, 5, 30, 21, 19, 39, 26, 26, 18, 32, 44, 9, 28, 10, 31, 22, 17, 42, 3, 3, 12, 37, 37, 9, 11, 5, 6, 48, 38, 8, 15, 22, 0, 32, 41, 48, 23, 25, 40, 29, 42, 22, 41, 12, 33, 4, 20, 19, 20, 2, 35, 33, 21, 13, 0, 29, 47, 24, 35, 24, 31, 5, 25, 35, 18, 43, 41, 34, 11, 4, 2, 11, 1, 31, 46, 1, 47, 30, 41, 32, 10, 31, 12, 42, 16, 2, 15, 29, 11, 37, 42, 27, 36, 16, 48, 17, 1, 40, 36, 6, 47, 38, 26, 23, 3, 44, 26, 36, 44, 36, 40, 39, 37, 19, 20, 45, 16, 46, 13, 23, 17, 35, 8, 23, 34, 24, 21, 48, 27, 34, 10, 39, 40, 0, 7, 33, 28, 16, 32, 18, 17, 38, 18, 39, 47, 27, 8, 27, 6, 14, 45, 28, 4, 9, 46, 29, 28, 13, 45, 13, 43, 7, 9, 15, 43, 14, 1, 22, 44, 14, 3, 38]

exclude_tests = {'ipea_n2', 'inverseqft_n4', 'vqe_uccsd_n4', 'pea_n5', 'qec_sm_n5', 'shor_n5', 'vqe_uccsd_n6', 'hhl_n7', 'sat_n7', 'vqe_uccsd_n8', 'qpe_n9', 'adder_n10', 'hhl_n10', 'cc_n12', 'hhl_n14', 'factor247_n15', 'bwt_n21', 'vqe_n24'}

# get QASMbenchmark object
path = "../QASMBench"
remove_final_measurements = False # do not remove the final measurement for real benchmark
do_transpile = False
transpile_args = {}
bm_small = QASMBenchmark(path, 'small', remove_final_measurements=remove_final_measurements, do_transpile=do_transpile, **transpile_args)
bm_medium = QASMBenchmark(path, 'medium', remove_final_measurements=remove_final_measurements, do_transpile=do_transpile, **transpile_args)

# use the .get method instead of .circ_name to avoid getting the large unusable circuits to save time
circ_name_list_small = list(i for i in bm_small.circ_name_list if i not in exclude_tests)
circ_list_small = list(bm_small.get(i) for i in circ_name_list_small)

if workload_type == 'small':
    circ_name_list = circ_name_list_small
    circ_list = circ_list_small

else:
    circ_name_list_medium = list(i for i in bm_medium.circ_name_list if i not in exclude_tests)
    circ_list_medium = list(bm_medium.get(i) for i in circ_name_list_medium)

    circ_name_list = circ_name_list_small + circ_name_list_medium
    circ_list = circ_list_small + circ_list_medium

baseline_name_to_index = dict((circ_name_list[i], i) for i in range(len(circ_name_list)))

# get baseline jobs
# first get a list of all types baseline jobs
# then construct baseline_jobs using this local list to reduce number of requests
baseline_name_to_id = read_workload_baseline(baseline_workload_filename)
baseline_jobs_list = list(service1.job(baseline_name_to_id[i]) for i in circ_name_list)
baseline_jobs = list(baseline_jobs_list[i] for i in job_queue)
qvm_jobs = []

# get qvm jobs
workload = read_workload_poisson(qvm_workload_filename, encoding='utf-8')
#workload = read_workload_poisson(qvm_workload_filename, 5, encoding='utf-8')
qvm_jobs = list(service2.job(i[0]) for i in workload)

# qvm vs baseline comparison
# throughput
single_thread_time = sum(i.result().metadata['execution']['execution_spans'].duration for i in baseline_jobs)
print('single thread time =', single_thread_time)

qvm_time = sum(i.result().metadata['execution']['execution_spans'].duration for i in qvm_jobs)
print('qvm time =', qvm_time)

print('speedup = ', single_thread_time/qvm_time)

# utilization
# define utilization: active qubit second / total qubit second
# We cannot precisely measure the active time of each qubit, so we assume that in an individual job, all used qubits are active for all the time.
# In a combine job, we can use the run time of an individual job as an approximation of active time of the qubits used by that job.
TOT_QUBIT = 127

baseline_utilization = list(circ_list[i].num_qubits/TOT_QUBIT for i in range(len(circ_list)))
baseline_utilization_avg = sum(baseline_utilization)/len(baseline_utilization)

qvm_utilization = []
for i in range(len(workload)):
    #names = workload[i][1]

    # for workload with internal scheduling
    names = [name for qvm in workload[i][1] for name in qvm]

    # sum of qubit * time of each sub-job
    u = sum(circ_list[baseline_name_to_index[name]].num_qubits * baseline_jobs_list[baseline_name_to_index[name]].result().metadata['execution']['execution_spans'].duration for name in names)
    # divided by total qubit * total time
    qvm_utilization.append(u/(TOT_QUBIT*qvm_jobs[i].result().metadata['execution']['execution_spans'].duration))
qvm_utilization_avg = sum(qvm_utilization)/len(qvm_utilization)

print('baseline average utilization =', baseline_utilization_avg)
print('qvm average utilization =', qvm_utilization_avg)
print('utilization improvement =', qvm_utilization_avg / baseline_utilization_avg)