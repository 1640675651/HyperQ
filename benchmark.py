# benchmark using the hypervisor backend

# checklist before run:
# 1. small only or small+med
# 2. barrier
# 3. scheduling switches (time, intra, noise)
# 4. dynamic (qasm3-runner, this option is no longer available in the new IBM API)
# 5. access token
# 6. backend choice (brisbane, kyoto, etc.)
# 7. intra vm scheduling
# 8. calibration data output path

from HypervisorBackend import *
from vm_executable import *
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, RuntimeJobFailureError
from qiskit_ibm_runtime import SamplerV2 as Sampler

from qasmbench import QASMBenchmark
from qiskit_aer import AerSimulator
from qiskit import transpile

import time
import sys

from getdata.get_calibration import score_all

class Tee:
    def __init__(self, *streams):
        self.streams = streams

    def write(self, message):
        for stream in self.streams:
            stream.write(message)

    def flush(self):  # Needed for compatibility with `sys.stdout`
        for stream in self.streams:
            stream.flush()

# we exclude circuits that has classical bit control which cause unknown error
# some tests do not measure at the end of execution, we also exclude them.
exclude_tests = {'ipea_n2', 'inverseqft_n4', 'vqe_uccsd_n4', 'pea_n5', 'qec_sm_n5', 'shor_n5', 'vqe_uccsd_n6', 'hhl_n7', 'sat_n7', 'vqe_uccsd_n8', 'qpe_n9', 'adder_n10', 'hhl_n10', 'cc_n12', 'hhl_n14', 'factor247_n15', 'bwt_n21', 'vqe_n24'}


workload_type = ''
output_path = ''
workload_id = ''

if len(sys.argv) != 4:
    print("usage: benchmark.py small/all output_path workload_id")
    exit()
else:
    if sys.argv[1] != 'small' and sys.argv[1] != 'all':
        print("usage: benchmark.py small/all output_path workload_id")
        exit()
    workload_type = sys.argv[1]
    output_path = sys.argv[2]
    workload_id = sys.argv[3]

    if output_path[-1] != '/' or output_path[-1] != '\\':
        output_path += '/'

# only test small for fidelity, 29 types of tests in total, each appears 5 times
if workload_type == 'small':
    #job_queue = [25, 12, 20, 16, 17, 6, 26, 8, 4, 14, 11, 5, 27, 24, 28, 23, 9, 4, 8, 6, 7, 15, 1, 10, 4, 14, 23, 12, 5, 14, 27, 11, 7, 7, 7, 18, 12, 27, 14, 1, 19, 13, 24, 13, 15, 22, 20, 3, 26, 11, 4, 20, 20, 25, 1, 9, 25, 2, 16, 5, 10, 8, 3, 0, 9, 14, 6, 3, 19, 3, 0, 26, 8, 27, 2, 10, 21, 3, 8, 5, 18, 22, 18, 24, 19, 0, 17, 21, 25, 22, 6, 0, 18, 5, 23, 15, 12, 23, 24, 28, 0, 28, 16, 12, 25, 17, 26, 4, 22, 10, 18, 9, 17, 1, 13, 13, 13, 15, 20, 27, 24, 16, 26, 2, 19, 21, 28, 11, 19, 2, 15, 23, 16, 1, 9, 21, 21, 6, 11, 7, 22, 2, 28, 17, 10]
    job_queue = [13, 24, 13, 26, 20, 20, 25, 1, 9, 25, 2, 16, 5, 10, 8, 3, 0, 9, 14, 6, 3, 19, 3, 0, 26, 8, 27, 2, 10, 21, 3, 8, 5, 18, 22, 18, 24, 19, 0, 17, 21, 25, 22, 6, 0, 18, 5, 23, 15, 12, 23, 24, 28, 0, 28, 16, 12, 25, 17, 26, 4, 22, 10, 18, 9, 17, 1, 13, 13, 13, 15, 20, 27, 24, 16, 26, 2, 19, 21, 28, 11, 19, 2, 15, 23, 16, 1, 9, 21, 21, 6, 11, 7, 22, 2, 28, 17, 10]
else:
# test a mix of small and medium for throughput. 29 + 20 = 49 tests, each appears 4 times
    job_queue = [25, 45, 0, 30, 7, 8, 4, 14, 10, 2, 33, 5, 20, 19, 7, 6, 34, 43, 24, 46, 12, 25, 30, 15, 21, 5, 30, 21, 19, 39, 26, 26, 18, 32, 44, 9, 28, 10, 31, 22, 17, 42, 3, 3, 12, 37, 37, 9, 11, 5, 6, 48, 38, 8, 15, 22, 0, 32, 41, 48, 23, 25, 40, 29, 42, 22, 41, 12, 33, 4, 20, 19, 20, 2, 35, 33, 21, 13, 0, 29, 47, 24, 35, 24, 31, 5, 25, 35, 18, 43, 41, 34, 11, 4, 2, 11, 1, 31, 46, 1, 47, 30, 41, 32, 10, 31, 12, 42, 16, 2, 15, 29, 11, 37, 42, 27, 36, 16, 48, 17, 1, 40, 36, 6, 47, 38, 26, 23, 3, 44, 26, 36, 44, 36, 40, 39, 37, 19, 20, 45, 16, 46, 13, 23, 17, 35, 8, 23, 34, 24, 21, 48, 27, 34, 10, 39, 40, 0, 7, 33, 28, 16, 32, 18, 17, 38, 18, 39, 47, 27, 8, 27, 6, 14, 45, 28, 4, 9, 46, 29, 28, 13, 45, 13, 43, 7, 9, 15, 43, 14, 1, 22, 44, 14, 3, 38]

# get real backend
service = QiskitRuntimeService(channel="ibm_quantum", token="Your access token")

real_backend = service.backend('ibm_brisbane')
#real_backend = service.least_busy(simulator=False)
#print('get real backend successfully')

# create fake (simulator) backend or use real backend directly
#backend = AerSimulator.from_backend(real_backend)
backend = real_backend

# create virtual backend
basis_gates = real_backend.basis_gates #['ecr', 'id', 'rz', 'sx', 'x']
hc = [(2, -2), (-2, 0), (6, -1), (-1, 4)]
vc = [(4, -3), (-3, -2), (-2, -1), (-1, 0)]
shared_up = {-3: -1}
shared_down = {-1: -2}
vm_coupling_map = [[1, 0], [0, 1], [1, 2], [2, 1], [1, 3], [3, 1], [3, 5], [5, 3], [4, 5], [5, 4], [5, 6], [6, 5]]
allowed_dimensions = [(1, 1), (1, 2), (2, 1), (1, 3), (3, 1), (2, 2), (2, 3), (3, 2), (3, 3)]

# vm qubit mappings
vms = [[[3, 4, 5, 15, 21, 22, 23], [7, 8, 9, 16, 25, 26, 27], [11, 12, 13, 17, 29, 30, 31]], 
       [[40, 41, 42, 53, 59, 60, 61], [44, 45, 46, 54, 63, 64, 65], [48, 49, 50, 55, 67, 68, 69]], 
       [[78, 79, 80, 91, 97, 98, 99], [82, 83, 84, 92, 101, 102, 103], [86, 87, 88, 93, 105, 106, 107]]]

hc_backend = [[[6, 24], [10, 28]], 
              [[43, 62], [47, 66]],
              [[81, 100], [85, 104]]]

vc_backend = [[[20, 33, 39], [24, 34, 43], [28, 35, 47]],
              [[58, 71, 77], [62, 72, 81], [66, 73, 85]]]

# create hypervisor backend
hypervisor = HypervisorBackend(backend, vms, hc_backend, vc_backend)

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

exec_list = []
for i, circ in enumerate(circ_list):
    evm = elastic_vm(circ.num_qubits, basis_gates, hc, vc, shared_up, shared_down, vm_coupling_map, allowed_dimensions)
    #print('transpiling', circ_name_list[i])
    exe = vm_executable(circ, evm, True)
    exec_list.append(exe)

exec_queue = list(exec_list[i] for i in job_queue)
exec_queue_names = list(circ_name_list[i] for i in job_queue)

def count_to_prob(counts: dict, shots: int):
    for k in counts:
        counts[k] /= shots

real_job_queue = []
tot_par = 0
tot_depth = 0
job_cnt = 0
cal_file = open(output_path + 'calib' + workload_id + '.txt', 'w')
log_file = open(output_path + 'workload' + workload_id + '.txt', 'a')
sys.stdout = Tee(sys.stdout, log_file)


while len(exec_queue):
    selection = hypervisor.schedule(exec_queue, time_sched = False, intra_vm_sched = True, noise_aware = False) 
    print('selection:', selection)
    # for j in selection:
    #     print(exec_queue_names[j[0]], end=' ')
    # print()
    names = []
    for i in selection:
       names.append(tuple(exec_queue_names[i[0][j]] for j in range(len(i[0]))))
    print(names)

    if len(real_job_queue) == 3:
        try:
            res = real_job_queue[0].result() # use result to block
        except RuntimeJobFailureError:
            print('failed job:', real_job_queue[0].job_id())
        real_job_queue.pop(0)
        # write calibration data when a job finishes
        cal_file.write(str(score_all(hypervisor, vm_coupling_map)) + '\n')

    #for real run
    job = hypervisor.run(exec_queue, selection=selection, dynamic=True)
    real_job_queue.append(job)

    print(job.job_id(), 'combined', sum(len(s[0]) for s in selection))

    #delete_indexes = sorted((i[0] for i in selection), reverse=True)
    delete_indexes = sorted((j for i in selection for j in i[0]), reverse=True)
    for i in delete_indexes:
        #exec_queue.pop(i)
        exec_queue_names.pop(i)
        job_queue.pop(i)

    print('remaining job queue:')
    print(job_queue)
    print()
    #break

# wait all jobs to finish
while len(real_job_queue):
    try:
        res = real_job_queue[0].result() # use result to block
    except RuntimeJobFailureError:
        print('failed job:', real_job_queue[0].job_id())
    real_job_queue.pop(0)
    # write calibration data when a job finishes
    cal_file.write(str(score_all(hypervisor, vm_coupling_map)) + '\n')
    
cal_file.close()
# print('combined job cnt =', job_cnt)
# print('average estimated qubit-level parallization =',tot_par/job_cnt)
# print('tot depth =', tot_depth)