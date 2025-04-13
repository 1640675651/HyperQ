# Run 1 circuit at a time as baseline
# checklist before running:
# 1. small only or small+med
# 2. which quantum computer we are using
# 3. which access token we are using
from HypervisorBackend import *
from vm_executable import *
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, RuntimeJobFailureError
from qiskit_ibm_runtime import SamplerV2 as Sampler

from qasmbench import QASMBenchmark
from qiskit_aer import AerSimulator
from qiskit import transpile

from getdata.get_calibration import score_all

import sys

class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for stream in self.streams:
            stream.write(message)

    def flush(self):  # Needed for compatibility with `sys.stdout`
        for stream in self.streams:
            stream.flush()

exclude_tests = {'ipea_n2', 'inverseqft_n4', 'vqe_uccsd_n4', 'pea_n5', 'qec_sm_n5', 'shor_n5', 'vqe_uccsd_n6', 'hhl_n7', 'sat_n7', 'vqe_uccsd_n8', 'qpe_n9', 'adder_n10', 'hhl_n10', 'hhl_n14', 'factor247_n15', 'bwt_n21', 'vqe_n24'}

workload_type = ''
output_path = ''
workload_id = ''

if len(sys.argv) != 4:
    print("usage: benchmark_baseline.py small/med/all output_path workload_id")
    exit()
else:
    if sys.argv[1] != 'small' and sys.argv[1] != 'med' and sys.argv[1] != 'all':
        print("usage: benchmark_baseline.py small/med/all output_path workload_id")
        exit()
    workload_type = sys.argv[1]
    output_path = sys.argv[2]
    workload_id = sys.argv[3]

    if output_path[-1] != '/' or output_path[-1] != '\\':
        output_path += '/'

cal_file = open(output_path + 'calib' + workload_id + '.txt', 'w')
log_file = open(output_path + 'workload' + workload_id + '.txt', 'a')
sys.stdout = Tee(sys.stdout, log_file)

# get real backend
service = QiskitRuntimeService(channel="ibm_quantum", token="Your access token")

real_backend = service.backend('ibm_brisbane')
real_sampler = Sampler(mode=real_backend)

# create fake (simulator) backend or use real backend directly
#backend = AerSimulator.from_backend(real_backend)
backend = real_backend

vm_coupling_map = [[1, 0], [0, 1], [1, 2], [2, 1], [1, 3], [3, 1], [3, 5], [5, 3], [4, 5], [5, 4], [5, 6], [6, 5]]

vms = [[[3, 4, 5, 15, 21, 22, 23], [7, 8, 9, 16, 25, 26, 27], [11, 12, 13, 17, 29, 30, 31]], 
       [[40, 41, 42, 53, 59, 60, 61], [44, 45, 46, 54, 63, 64, 65], [48, 49, 50, 55, 67, 68, 69]], 
       [[78, 79, 80, 91, 97, 98, 99], [82, 83, 84, 92, 101, 102, 103], [86, 87, 88, 93, 105, 106, 107]]]

hc_backend = [[[6, 24], [10, 28]], 
              [[43, 62], [47, 66]],
              [[81, 100], [85, 104]]]

vc_backend = [[[20, 33, 39], [24, 34, 43], [28, 35, 47]],
              [[58, 71, 77], [62, 72, 81], [66, 73, 85]]]

hypervisor = HypervisorBackend(real_backend, vms, hc_backend, vc_backend)

# get QASMbenchmark object
path = "../QASMBench"
#num_qubits_list = list(range(1, 8))
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

if workload_type == 'small':
    circ_name_list = circ_name_list_small
    circ_list = circ_list_small
elif workload_type == 'med':
    circ_name_list = circ_name_list_medium
    circ_list = circ_list_medium
elif workload_type == 'all':
    circ_name_list = circ_name_list_small + circ_name_list_medium
    circ_list = circ_list_small + circ_list_medium


def count_to_prob(counts: dict, shots: int):
    for k in counts:
        counts[k] /= shots

# There are spaces between results of different classical registers
def remove_key_space(counts: dict) -> dict:
    new_dict = {}
    for k, v in counts.items():
        newk = k.replace(' ','')
        new_dict[newk] = v
    return new_dict


# for simulator, get result immediately
'''
for i in range(len(circ_list)):
    if circ_name_list[i] in exclude_tests:
        continue
    circ_transpiled = transpile(circ_list[i], backend)
    job = backend.run(circ_transpiled)
    #print(job.job_id())
    counts = job.result().get_counts()

    print(circ_name_list[i])
    count_to_prob(counts, 1024)
    print(counts)
    #print(remove_key_space(counts))
'''

# for real machine, just submit jobs, get results later

real_job_queue = []
# add automatic job queue maintainance
for i in range(len(circ_list)):
    if circ_name_list[i] in exclude_tests:
        continue
    circ_transpiled = transpile(circ_list[i], backend)
    if len(real_job_queue) == 3: # IBM Quantum allows at most 3 jobs in the queue
        try:
            res = real_job_queue[0].result() # use result to block
        except RuntimeJobFailureError:
            print('failed job:', real_job_queue[0].job_id())
        real_job_queue.pop(0)
        cal_file.write(str(score_all(hypervisor, vm_coupling_map)) + '\n')

    job = real_sampler.run([circ_transpiled])
    print(job.job_id(), circ_name_list[i])
    real_job_queue.append(job)

while len(real_job_queue):
    try:
        res = real_job_queue[0].result() # use result to block
    except RuntimeJobFailureError:
        print('failed job:', real_job_queue[0].job_id())
    real_job_queue.pop(0)
    # write calibration data when a job finishes
    cal_file.write(str(score_all(hypervisor, vm_coupling_map)) + '\n')
    
cal_file.close()