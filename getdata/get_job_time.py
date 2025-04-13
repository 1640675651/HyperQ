# launch this file from the root directory of the repo
import sys
sys.path.append('.')
from qiskit_ibm_runtime import QiskitRuntimeService
from utils import read_workload, read_workload_poisson

def remove_key_space(counts: dict) -> dict:
    new_dict = {}
    for k, v in counts.items():
        newk = k.replace(' ','')
        new_dict[newk] = v
    return new_dict

def count_to_prob(counts: dict, shots: int):
    for k in counts:
        counts[k] /= shots

def read_workload_baseline_tuple(filename, encoding = 'utf-8'):
    ret = []
    f = open(filename, 'r', encoding=encoding)
    for line in f.readlines():
        jobid, name = line.strip().split()
        ret.append((jobid, name))
    return ret

service = QiskitRuntimeService(channel="ibm_quantum", token="Your access token")

if len(sys.argv) < 2:
    print('need workload file name')
    exit()
workload_filename = sys.argv[1]
# baseline
workload = read_workload_baseline_tuple(workload_filename)

# all-at-once
# workload = read_workload(workload_filename, 5, encoding='utf-8')

# poisson
# workload = read_workload_poisson(workload_filename)

jobs = list(service.job(i[0]) for i in workload)

for i in range(len(jobs)):
    metadata = jobs[i].result().metadata
    execution = metadata['execution']['execution_spans']
    print(workload[i][0], execution.duration)