# launch this file from the root directory of the repo
# only get result for small benchmarks
import sys
sys.path.append('.')
from qiskit_ibm_runtime import QiskitRuntimeService
from qasmbench import QASMBenchmark

def read_workload_baseline(filename, encoding = 'utf-8'):
    ret = []
    f = open(filename, 'r', encoding=encoding)
    for line in f.readlines():
        jobid, name = line.strip().split()
        ret.append((jobid, name))
    return ret

def remove_key_space(counts: dict) -> dict:
    new_dict = {}
    for k, v in counts.items():
        newk = k.replace(' ','')
        new_dict[newk] = v
    return new_dict

def count_to_prob(counts: dict, shots: int):
    for k in counts:
        counts[k] /= shots

if len(sys.argv) != 2:
    print('usage: get_result_baseline.py workload_file')
workload_path = sys.argv[1]

service = QiskitRuntimeService(channel="ibm_quantum", token="Your access token")

baseline_id_name = read_workload_baseline(workload_path)
baseline_jobs_list = list(service.job(i[0]) for i in baseline_id_name)

#print baseline results
for i in range(len(baseline_jobs_list)):
    print(baseline_id_name[i][1])
    # qaoa_n3, bell_n4, bb84_n8 have spaces in their result
    # need to remove them
    result = baseline_jobs_list[i].result()
    counts = result[0].join_data().get_counts() if len(result[0].data) > 1 else list(result[0].data.values())[0].get_counts()

    count_to_prob(counts, 4096)
    print(counts)

