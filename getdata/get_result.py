# launch this file from the root directory of the repo
import sys
sys.path.append('.')
from qiskit_ibm_runtime import QiskitRuntimeService
from qasmbench import QASMBenchmark
from utils import read_workload
from CombinerJob import CombinerJob

def remove_key_space(counts: dict) -> dict:
    new_dict = {}
    for k, v in counts.items():
        newk = k.replace(' ','')
        new_dict[newk] = v
    return new_dict

def count_to_prob(counts: dict, shots: int):
    for k in counts:
        counts[k] /= shots

# hz2915@columbia
service = QiskitRuntimeService(channel="ibm_quantum", token="Your access token")

# get QASMbenchmark object
path = "../QASMBench"
category = "small" 
remove_final_measurements = False # do not remove the final measurement for real benchmark
do_transpile = False
transpile_args = {}
bm = QASMBenchmark(path, category, remove_final_measurements=remove_final_measurements, do_transpile=do_transpile, **transpile_args)

qvm_jobs = []

# get qvm jobs
if len(sys.argv) < 2:
    print('need workload file name')
    exit()
workload_filename = sys.argv[1]
workload = read_workload(workload_filename, 5, encoding='utf-8')
qvm_jobs = list(service.job(i[0]) for i in workload)

# print qvm results
# maintain the same order as in workload file
for i in range(len(workload)):
    # works = workload[i][1]
    # for workload with internal scheduling
    works = [name for qvm in workload[i][1] for name in qvm]
    clbits = list(bm.get(i).num_clbits for i in works)
    job = CombinerJob(qvm_jobs[i], None, clbits, None)
    counts_individual = job.result()
    for j in range(len(works)):
        print(works[j])
        count_to_prob(counts_individual[j], 4096)
        print(dict.__repr__(counts_individual[j]))
