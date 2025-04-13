# not really running the benchmark, just using running time of each job to simulate the poisson process
from HypervisorBackend import *
from vm_executable import *
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, RuntimeJobFailureError

from qasmbench import QASMBenchmark
from qiskit_aer import AerSimulator
from qiskit import transpile

import time
import random
import sys

from utils import read_runtime_list

if len(sys.argv) != 3:
    print("usage: benchmark_poisson_baseline.py small/all baseline_job_time")
    exit()
workload_type = sys.argv[1]

# we exclude circuits that has classical bit control which cause unknown error
# some tests do not measure at the end of execution, we also exclude them.
exclude_tests = {'ipea_n2', 'inverseqft_n4', 'vqe_uccsd_n4', 'pea_n5', 'qec_sm_n5', 'shor_n5', 'vqe_uccsd_n6', 'hhl_n7', 'sat_n7', 'vqe_uccsd_n8', 'qpe_n9', 'adder_n10', 'hhl_n10', 'cc_n12', 'hhl_n14', 'factor247_n15', 'bwt_n21', 'vqe_n24'}

# only test small for fidelity, 29 types of tests in total, each appears 5 times
if workload_type == 'small':
    job_queue = [25, 12, 20, 16, 17, 6, 26, 8, 4, 14, 11, 5, 27, 24, 28, 23, 9, 4, 8, 6, 7, 15, 1, 10, 4, 14, 23, 12, 5, 14, 27, 11, 7, 7, 7, 18, 12, 27, 14, 1, 19, 13, 24, 13, 15, 22, 20, 3, 26, 11, 4, 20, 20, 25, 1, 9, 25, 2, 16, 5, 10, 8, 3, 0, 9, 14, 6, 3, 19, 3, 0, 26, 8, 27, 2, 10, 21, 3, 8, 5, 18, 22, 18, 24, 19, 0, 17, 21, 25, 22, 6, 0, 18, 5, 23, 15, 12, 23, 24, 28, 0, 28, 16, 12, 25, 17, 26, 4, 22, 10, 18, 9, 17, 1, 13, 13, 13, 15, 20, 27, 24, 16, 26, 2, 19, 21, 28, 11, 19, 2, 15, 23, 16, 1, 9, 21, 21, 6, 11, 7, 22, 2, 28, 17, 10]
else:
# test a mix of small and medium for throughput. 29 + 20 = 49 tests, each appears 4 times
    job_queue = [25, 45, 0, 30, 7, 8, 4, 14, 10, 2, 33, 5, 20, 19, 7, 6, 34, 43, 24, 46, 12, 25, 30, 15, 21, 5, 30, 21, 19, 39, 26, 26, 18, 32, 44, 9, 28, 10, 31, 22, 17, 42, 3, 3, 12, 37, 37, 9, 11, 5, 6, 48, 38, 8, 15, 22, 0, 32, 41, 48, 23, 25, 40, 29, 42, 22, 41, 12, 33, 4, 20, 19, 20, 2, 35, 33, 21, 13, 0, 29, 47, 24, 35, 24, 31, 5, 25, 35, 18, 43, 41, 34, 11, 4, 2, 11, 1, 31, 46, 1, 47, 30, 41, 32, 10, 31, 12, 42, 16, 2, 15, 29, 11, 37, 42, 27, 36, 16, 48, 17, 1, 40, 36, 6, 47, 38, 26, 23, 3, 44, 26, 36, 44, 36, 40, 39, 37, 19, 20, 45, 16, 46, 13, 23, 17, 35, 8, 23, 34, 24, 21, 48, 27, 34, 10, 39, 40, 0, 7, 33, 28, 16, 32, 18, 17, 38, 18, 39, 47, 27, 8, 27, 6, 14, 45, 28, 4, 9, 46, 29, 28, 13, 45, 13, 43, 7, 9, 15, 43, 14, 1, 22, 44, 14, 3, 38]

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

circ_name_list_medium = list(i for i in bm_medium.circ_name_list if i not in exclude_tests)
circ_list_medium = list(bm_medium.get(i) for i in circ_name_list_medium)

circ_name_list = circ_name_list_small + circ_name_list_medium
circ_list = circ_list_small + circ_list_medium

job_queue_names = list(circ_name_list[i] for i in job_queue)

baseline_runtime = read_runtime_list(sys.argv[2])

# poisson process simulation
MAX_QUEUE_SIZE = 99999
AVG_INTERVAL = 1

t = 0
arrived_jobs = 0
finished_jobs = 0
tot_job_cnt = len(job_queue)
job_arrival_time = []
job_finish_time = []
poisson_job_queue = []
while finished_jobs < tot_job_cnt:
    if len(poisson_job_queue):
        # run and get running time
        job_time = baseline_runtime[poisson_job_queue[0]]
        print('job', finished_jobs, 'takes', job_time)
        finished_jobs += 1
        
        # record job finish time
        job_finish_time.append(t + job_time)

        # pop finished job
        poisson_job_queue.pop(0)

        # simulate job arrivals while the last job was running
        t1 = t
        while t1 < t + job_time and len(poisson_job_queue) < MAX_QUEUE_SIZE and arrived_jobs < tot_job_cnt:
            interval = random.expovariate(AVG_INTERVAL)
            t1 += interval
            if t1 < t + job_time:
                print('job', arrived_jobs, 'arrives at time', t1)
                poisson_job_queue.append(job_queue[arrived_jobs])
                job_arrival_time.append(t1)
                arrived_jobs += 1

        t += job_time
    else: # if queue is empty, let the next job enqueue
        interval = random.expovariate(AVG_INTERVAL)
        t += interval
        print('job', arrived_jobs, 'arrives at time', t)
        poisson_job_queue.append(job_queue[arrived_jobs])
        job_arrival_time.append(t)
        arrived_jobs += 1

#print(job_arrival_time)
#print(job_finish_time)
wait_time = list(j-i for (i, j) in zip(job_arrival_time, job_finish_time))
print(wait_time)
print('average wait time', sum(wait_time)/tot_job_cnt)        
print('total time', t)
