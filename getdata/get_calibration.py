import sys
sys.path.append('.')
from HypervisorBackend import *
from vm_executable import *
from qiskit import QuantumCircuit, transpile
from qiskit_ibm_runtime import QiskitRuntimeService, RuntimeJobFailureError

from qasmbench import QASMBenchmark
from qiskit_aer import AerSimulator
from qiskit import transpile

import time

from numpy import mean, var

def score(qubits: list, tgt_cm: "coupling map", backend, properties):
    link_err = []
    readout_err = []
    for q1, q2 in tgt_cm:
        if (q1, q2) not in backend.coupling_map: # handle single-way ecr
            continue
        link_err.append(properties.gate_error('ecr', (q1, q2)))
    for q in qubits:
        readout_err.append(properties.readout_error(q))

    return mean(link_err), max(link_err), min(link_err), var(link_err), mean(readout_err), max(readout_err), min(readout_err), var(readout_err) 

def score_qvm(hypervisor, r, c, vm_coupling_map, properties):
    mapping = hypervisor.get_mapping(r, c, 1, 1)
    vm_region = [mapping[k] for k in range(7)]
    cm = [(mapping[q1], mapping[q2]) for q1, q2 in vm_coupling_map]
    return score(mapping, cm, hypervisor.backend, properties)

def score_all(hypervisor, vm_coupling_map):
    scores = []
    properties = hypervisor.backend.properties(refresh=True)
    for i in range(3):
        for j in range(3):
            scores.append(score_qvm(hypervisor, i, j, vm_coupling_map, properties))
    return scores

if __name__ == '__main__':
    service = QiskitRuntimeService(channel="ibm_quantum", token="Your access token")
    real_backend = service.backend('ibm_brisbane')
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

    scores = score_all(hypervisor, vm_coupling_map)
    print('link_err_avg link_err_max link_err_min link_err_var readout_err_avg readout_err_max readout_err_min readout_err_var')
    for i in range(3):
        for j in range(3):
            print(scores[i*3+j][0])