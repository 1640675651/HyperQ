from qiskit import transpile
from qiskit.providers.fake_provider import GenericBackendV2
'''
@ qc: "source circuit" (uncompiled circuit)
@ virtual_backend_list: a list of vm configurations, which can be generated by function elastic_vm
@ allow_intra_sched: whether the user permits this program to share a qvm with others,
currently only program less than 3 qubits is allowed
'''

HALF_VM_SIZE = 3
half_vm_coupling_map = [[0, 1], [1, 0], [1, 2], [2, 1]]

def half_vm(basis_gates: [str], coupling_map):
    return GenericBackendV2(HALF_VM_SIZE, basis_gates = basis_gates, coupling_map = coupling_map, control_flow = True)

class vm_executable:
    def __init__(self, qc, virtual_backend_list: [('Backend', 'row', 'col')], allow_intra_sched):
        # for intra-vm scheduling, we may need the uncompiled circuit
        self.source_qc = qc
        self.allow_intra_sched = allow_intra_sched
        self.half_qc = None
        self.basis_gates = virtual_backend_list[0][0]._basis_gates
        if allow_intra_sched and qc.num_qubits <= HALF_VM_SIZE:
            self.half_qc = transpile(qc, half_vm(self.basis_gates, half_vm_coupling_map))
        
        self.qc = []
        self.dimensions = []
        self.vbl = virtual_backend_list
        for vb in virtual_backend_list: # at most 2 versions
            self.qc.append(transpile(qc, vb[0]))
            self.dimensions.append((vb[1], vb[2]))
        self.versions = len(virtual_backend_list)
        self.clbits = qc.num_clbits
        
