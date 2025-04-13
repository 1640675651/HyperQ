from CombinerJob import CombinerJob
from qiskit.providers.fake_provider import GenericBackendV2
from qiskit.providers import BackendV2
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister, transpile
from vm_executable import *
from qiskit_ibm_runtime import SamplerV2 as Sampler

# for the last translation pass
from qiskit.transpiler import PassManager
from qiskit.transpiler.passes import GateDirection
from qiskit.circuit.library import *
from qiskit.converters import circuit_to_dag
from qiskit.transpiler import TransformationPass
import numpy as np
import random

# Need to adjust ecr gate directions. GateDirection uses sdg, s, and h gates, need to translate to basis gates.
# https://quantumcomputing.stackexchange.com/questions/22149/replace-gate-with-known-identity-in-quantum-circuit
class GateDirectionTranslator(TransformationPass):
    def run(self, dag):
        """Run the pass."""

        # iterate over all operations
        for node in dag.op_nodes():
            if node.op.name == 'sdg':
                replacement = QuantumCircuit(1)
                replacement.rz(-np.pi/2, 0)
                dag.substitute_node_with_dag(node, circuit_to_dag(replacement))
            
            if node.op.name == 's':
                replacement = QuantumCircuit(1)
                replacement.rz(np.pi/2, 0)
                dag.substitute_node_with_dag(node, circuit_to_dag(replacement))
                
            if node.op.name == 'h':
                replacement = QuantumCircuit(1)
                replacement.rz(np.pi/2, 0)
                replacement.sx(0)
                replacement.rz(np.pi/2, 0)
                dag.substitute_node_with_dag(node, circuit_to_dag(replacement))

        return dag

class HypervisorBackend(BackendV2):

    def __init__(self, backend, vms, hc, vc, **fields):
        super().__init__(**fields)
        self.backend = backend
        self.sampler = Sampler(mode=backend)
        self.vms = vms
        self.hc = hc
        self.vc = vc
        self.translate = PassManager([GateDirection(backend.coupling_map, backend.target), GateDirectionTranslator()])

    @property
    def target(self):
        return self.backend.target

    @property
    def max_circuits(self):
        return self.backend.max_circuits

    # it deletes chosen executables from the executables list. Is it a proper way?
    def run(self, executables, selection = None, time_sched = False, intra_vm_sched = False, noise_aware = False, **kwargs) -> CombinerJob:
        QVM_INTERNAL_MAX_PARTITIONS = 2
        # add selection to parameter if want to override selection
        if selection == None:
            selection = self.schedule(executables, time_sched, intra_vm_sched, noise_aware)
        mappings = []
        clbit_cnt = []
        compiled_circuits = []
        for i, r, c, n, m, v in selection:
            mappings.append(self.get_mapping(r, c, n, m))
            # for internal scheduling
            if(len(i) > 1):
                internal_circuit = self.combine_internal(list(executables[j] for j in i), [[0, 1, 2], [4, 5, 6]])
                #internal_circuit = transpile(internal_circuit, executables[i[0]].vbl[v][0])
                compiled_circuits.append(internal_circuit)
                for j in i:    
                    clbit_cnt.append(executables[j].clbits)
            else:
                compiled_circuits.append(executables[i[0]].qc[v])
                clbit_cnt.append(executables[i[0]].clbits)

        # first combine then adjust ecr gate direction for the whole circuit
        combined_circ = self.combine(compiled_circuits, mappings, self.backend.num_qubits, 'vm')
        direction_corrected_circ = self.translate.run(combined_circ)

        # delete chosen executables from executables list. Loop backwards to keep the index
        # delete_indexes = sorted((i[0] for i in selection), reverse=True)
        delete_indexes = sorted((j for i in selection for j in i[0]), reverse=True)
        for i in delete_indexes:
            executables.pop(i)

        # print(direction_corrected_circ)
        return CombinerJob(self.sampler.run([direction_corrected_circ]), mappings, clbit_cnt, backend=self)
    
    # do not actually submit job to backend, just for latency test
    def dryrun(self, executables, selection = None, time_sched = False, intra_vm_sched = False, noise_aware = False, **kwargs):
        QVM_INTERNAL_MAX_PARTITIONS = 2
        if selection == None:
            selection = self.schedule(executables, time_sched, intra_vm_sched, noise_aware)
        mappings = []
        clbit_cnt = []
        compiled_circuits = []
        for i, r, c, n, m, v in selection:
            mappings.append(self.get_mapping(r, c, n, m))
            # for internal scheduling, need to recompile source circuits
            if(len(i) > 1):
                internal_circuit = self.combine_internal(list(executables[j] for j in i), [[0, 1, 2], [4, 5, 6]])
                #internal_circuit = transpile(internal_circuit, executables[i[0]].vbl[v][0])
                compiled_circuits.append(internal_circuit)
                for j in i:    
                    clbit_cnt.append(executables[j].clbits)
            else:
                compiled_circuits.append(executables[i[0]].qc[v])
                clbit_cnt.append(executables[i[0]].clbits)

        # first combine then adjust ecr gate direction for the whole circuit
        combined_circ = self.combine(compiled_circuits, mappings, self.backend.num_qubits, 'vm')
        direction_corrected_circ = self.translate.run(combined_circ)

        # delete chosen executables from executables list. Loop backwards to keep the index
        # comment out if doing schedule time test because timeit repeats this function
        # delete_indexes = sorted((j for i in selection for j in i[0]), reverse=True)
        # for i in delete_indexes:
        #     executables.pop(i)
        
        return direction_corrected_circ

    # return qubit mapping of the specified region
    def get_mapping(self, r, c, n, m): # ith qubit in vm is mapped to ret[i]th qubit in the backend
        ret = []
        hc_set = set()
        # add vm regions
        for i in range(r, r+n, 1):
            for j in range(c, c+m, 1):
                ret += self.vms[i][j]
            
        # add horizontal connections
        for i in range(r, r+n, 1):
            for j in range(c, c+m-1, 1):
                ret += self.hc[i][j]
                hc_set = hc_set.union(set(self.hc[i][j]))

        # add vertical connections
        for i in range(r, r+n-1, 1):
            for j in range(c, c+m, 1):
                for k in self.vc[i][j]:
                    if k not in hc_set:
                        ret.append(k)
        return ret

    def get_qvm_ranking(self):
        def score(qubits: list, tgt_cm, backend) -> float:
            link_err = []
            readout_err = []
            for q1, q2 in tgt_cm:
                if (q1, q2) not in backend.coupling_map: # handle single-way ecr
                    continue
                link_err.append(backend.properties().gate_error('ecr', (q1, q2))) # use backend.properties(refresh=True) if calibration data changes
            for q in qubits:
                readout_err.append(backend.properties().readout_error(q))
            return np.mean(link_err)

        scores = []
        for i in range(3):
            for j in range(3):
                mapping = self.get_mapping(i, j, 1, 1)
                vm_coupling_map = [[1, 0], [0, 1], [1, 2], [2, 1], [1, 3], [3, 1], [3, 5], [5, 3], [4, 5], [5, 4], [5, 6], [6, 5]]
                cm = [(mapping[q1], mapping[q2]) for q1, q2 in vm_coupling_map]
                scores.append((score(mapping, cm, self.backend), i*3+j))

        scores.sort() # lower error -> higher rank
        #print(scores)
        ranking = [0]*9
        for rank, (score, index) in enumerate(scores):
            ranking[rank] = index
        return ranking

    # try to select a maximum number of executables to run
    # return which executables get run and their position
    # no side effect
    def schedule(self, executables, time_sched = False, intra_vm_sched = False, noise_aware = False):        
        # check if all the qvms at (i, j, n, m) are unused
        def fit1(i, j, n, m, region_status) -> bool:
            for a in range(n):
                for b in range(m):
                    if region_status[i+a][j+b] >= 1:
                        return False
            return True

        # noise aware placement
        def fit(region_status, exe, bad_qvm_mark):
            if is_sensitive(exe):
                for v in range(exe.versions):
                    n, m = exe.dimensions[v][0], exe.dimensions[v][1]
                    for i in range(3-n+1):
                        for j in range(3-m+1):
                            # ensure all qvms used are good
                            if fit1(i, j, n, m, region_status) and fit_bad_cnt(i, j, n, m, bad_qvm_mark) == 0:
                                return i, j, v
                return None, None, None
            else:
                max_bad_qvm_used = -1
                ret_i, ret_j, ret_v = None, None, None
                for v in range(exe.versions):
                    n, m = exe.dimensions[v][0], exe.dimensions[v][1]
                    for i in range(3-n+1):
                        for j in range(3-m+1):
                            # use the maximum number of bad qvms
                            bad_qvm_used = fit_bad_cnt(i, j, n, m, bad_qvm_mark)
                            if fit1(i, j, n, m, region_status) and bad_qvm_used > max_bad_qvm_used:
                                max_bad_qvm_used = bad_qvm_used
                                ret_i, ret_j, ret_v = i, j, v
                                # return if all qvms used are bad
                                if max_bad_qvm_used == n*m:
                                    return ret_i, ret_j, ret_v
                                
                return ret_i, ret_j, ret_v

        # return the number of bad qvm used if putting the current workload at (i, j)
        def fit_bad_cnt(i, j, n, m, bad_qvm_mark) -> int:
            ret = 0
            for a in range(n):
                for b in range(m):
                    ret += bad_qvm_mark[i+a][j+b]
            return ret

        # the function does not have any side effect
        # greedy, check all possible position and use the first one that does not max depth
        # I misused the word "height" here, it should actually be "depth"
        def timefit(n, m, region_status, region_height, circ_depth, cur_volume, cur_max_height, max_reuse):
            for i in range(3-n+1):
                for j in range(3-m+1):
                    if max_reuse_check(i, j, n, m, region_status, max_reuse) == False:
                        continue
                    region_max_height = max_pool(i, j, n, m, region_height)
                    if region_max_height + circ_depth < cur_max_height:
                        return i, j
            return None, None

        def max_reuse_check(i, j, n, m, region_status, max_reuse) -> bool:
            for a in range(n):
                for b in range(m):
                    if region_status[i+a][j+b] >= max_reuse:
                        return False
            return True

        # update region_status(how many time reused and region_height)
        def update_region_status(i, j, n, m, region_status, region_height, circ_depth, cur_max_height):
            pooled_height = max_pool(i, j, n, m, region_height)
            #print('before:', region_height)
            for a in range(n):
                for b in range(m):
                    region_status[i+a][j+b] += 1
                    region_height[i+a][j+b] = pooled_height + circ_depth
            #print('after:', region_height)
            if cur_max_height < pooled_height + circ_depth:
                print('exceeding max height') # should never get printed
            return max(cur_max_height, pooled_height + circ_depth)
                
        # define how many times a region can be reused when doing time scheduling
        # 1 = no time scheduling
        MAX_REUSE = 2

        def mark_bad_qvm(n):
            mark = [[0]*3, [0]*3, [0]*3]
            ranking = self.get_qvm_ranking()
            #print('ranking:', ranking)
            for i in range(1, n+1, 1):
                qvm_index = ranking[-i]
                r, c = qvm_index//3, qvm_index%3
                mark[r][c] = 1
                #print('marking qvm', qvm_index)
            #print(mark)
            return mark

        def is_sensitive(exe) -> bool:
            if noise_aware == False:
                return True
            # if a circuit has more than 340 gates, we say it's noise insensitive (always noisy)
            # We treat the executable as sensitive if any of its version is sensitive.
            sensitivity_threshold = 340
            for qc in exe.qc:
                op_cnt = sum(qc.count_ops().values())
                if op_cnt < sensitivity_threshold:
                    return True
            return False

        # 1st pass: space scheduling
        # TODO: do not hardcode the dimensions
        region_status = [[0]*3, [0]*3, [0]*3] # how many times each region has been used
        region_height = [[0]*3, [0]*3, [0]*3] # circuit depth on each region
        remaining_region = len(self.vms) * len(self.vms[0])
        selection = []
        selected = set() # which executables have been selected

        # if not using noise aware scheduling, we set all workloads sensitive and all qvms are good.
        # This will be equivalent to greedy scheduling.
        bad_qvm_mark = [[0]*3, [0]*3, [0]*3]
        # noise aware scheduling
        if noise_aware == True:
            good_qvm_cnt = 6
            bad_qvm_cnt = 3
            bad_qvm_mark = mark_bad_qvm(bad_qvm_cnt)

        for i in range(len(executables)):
            if remaining_region == 0:
                break
            if remaining_region < executables[i].dimensions[0][0] * executables[i].dimensions[0][1]:
                continue
            r, c, v = fit(region_status, executables[i], bad_qvm_mark)
            if r != None:
                # ([executable indexes], starting row, starting col, height, width, version)
                n, m = executables[i].dimensions[v][0], executables[i].dimensions[v][1]
                selection.append(([i], r, c, n, m, v))
                selected.add(i)
                
                for a in range(n):
                    for b in range(m):
                        region_status[r+a][c+b] = 1
                        region_height[r+a][c+b] += executables[i].qc[v].depth()

                remaining_region -= n*m


        # 2nd pass: intra vm scheduling
        if intra_vm_sched:
            self.intra_schedule(executables, selection, selected, region_height, time_sched = False)

        #print(region_height)
        #print(selected)

        # return here if skip time scheduling
        # noise aware will override time_sched
        if noise_aware or not time_sched:
            return selection
        #print('before time scheduling')
        #print(region_height)
        
        max_height = max(max(i) for i in region_height)
        min_height = min(min(i) for i in region_height)
        if max_height - min_height < 50:
            return selection

        # 3rd pass: time scheduling. If some circuits are very short and some are very long, short ones have to wait for long ones and qubit time are wasted.
        # Imagine we have a 3*3 ground and we are putting lego blocks onto it. The blocks can have m*n base and arbitrary height.
        # Total volume is 3*3*max height. Utilized volume is the volume of all lego blocks. We want to maximize utilized volume/total volume.
        
        # need to maintain useful volume and max height.
        util_volume = sum(sum(i) for i in region_height)
        
        #cur_util = util_volume / (9 * max_height)
        #print('estimated util before time scheduling =', util_volume / (9 * max_height))

        # calculate the total number that basic qvm can be reused
        # for later loop exit condition
        remaining_reuse = 0
        for i in range(len(region_height)):
            for j in range(len(region_height[i])):
                if region_height[i][j] < max_height:
                    remaining_reuse += MAX_REUSE - region_status[i][j]
                else:
                    region_status[i][j] = MAX_REUSE
                    
        # separate the selection of space scheduling and time scheduling
        # to simplify the intra_schedule function
        selection2 = []
        for i in range(len(executables)):
            if i in selected:
                continue
            # find a version that can be scheduled without increasing the total height
            for j in range(executables[i].versions):
                qc, n, m = executables[i].qc[j], executables[i].dimensions[j][0], executables[i].dimensions[j][1]
                r, c = timefit(n, m, region_status, region_height, qc.depth()+50, util_volume, max_height, MAX_REUSE) # the function should not edit any data structure
                if r != None:
                    update_params = (r, c, n, m, region_status, region_height, qc.depth()+50, max_height)
                    selection2.append(([i], r, c, n, m, j))
                    selected.add(i)
                    new_max_height = update_region_status(*update_params)
                    assert(new_max_height == max_height)
                    remaining_reuse -= n*m
                    break
            if remaining_reuse == 0:
                break
        
        # print('after time scheduling')
        # print(region_height)

        # 4th pass: intra vm scheduling
        if intra_vm_sched:
            self.intra_schedule(executables, selection2, selected, region_height, time_sched = False)

        #print('estimated util after time scheduling =', util_volume / (9 * max_height))
        return selection+selection2
    
    # intra vm scheduling
    # updates the selection, selected, and region_height argument
    # should I separate internal and external time_sched?
    # for noise-aware scheduling: currently only workloads with qubit count <= 3 will use internal scheduling.
    # These workloads are noise sensitive, so the chosen qvms must be good.
    # So for our benchmark we can just do nothing on noise-aware intra-vm scheduling.
    def intra_schedule(self, executables, selection: list, selected: {int}, region_height, time_sched = False):
        # define at most what percentage of qubits can be used when doing internal space scheduling
        QVM_MAX_ALLOWED_PERCENTAGE = 1
        # define at most how many circuits can be squeezed into a (scaled) qvm when doing internal space scheduling
        QVM_INTERNAL_MAX_PARTITIONS = 2
        # define how many times a partition can be reused for internal time scheduling
        QVM_INTERNAL_PARTITION_MAX_REUSE = 2

        def timefit_internal(qvm_status, circ_depth, max_reuse):
            for i, qvm in enumerate(qvm_status):
                max_depth = max(part[0] for part in qvm)
                for j, part in enumerate(qvm):
                    # the cicruit fits into the partition and does not increase max depth
                    if part[0] + circ_depth <= max_depth and part[1] < max_reuse:
                        return i, j
            return None, None

        def all_part_usedup(qvm, qvm_status, max_reuse) -> bool:
            for part in qvm_status[qvm]:
                if part[1] < max_reuse:
                    return False
            return True
        
        remaining_reusable_qvm = 0
        remaining_partition_cnt = []
        qvm_status = [] # in the format [[[depth, reuse count]]], record the info of sub-circuits
        max_height = max(max(i) for i in region_height)

        # calculate the remaining partition count of each (scaled) qvm
        for i in selection:
            exe_index = i[0][0] # only one circuit per qvm before space scheduling
            exe_ver = i[5]
            exe = executables[exe_index]
            # intra scheduling allowed
            if exe.half_qc != None:
                remaining_partition_cnt.append(1)
                qvm_status.append([[exe.half_qc.depth(), 1]])
                remaining_reusable_qvm += 1
            else:
                remaining_partition_cnt.append(0)
                qvm_status.append([[exe.qc[exe_ver].depth(), 1]])


        for i, exe in enumerate(executables):
            if i in selected or exe.half_qc == None:
                continue
            # find a already allocated qvm to see if there are remaining partitions and the current circuit fits
            for j in range(len(selection)):
                if remaining_partition_cnt[j] > 0:
                    selection[j][0].append(i)
                    selected.add(i)
                    remaining_partition_cnt[j] -= 1
                    remaining_reusable_qvm -= 1
                    # update external region depth
                    y, x = selection[j][1], selection[j][2]
                    region_height[y][x] = max(region_height[y][x], exe.half_qc.depth())
                    # update internal partition status
                    qvm_status[j].append([exe.half_qc.depth(), 1])
                    break

            if remaining_reusable_qvm == 0:
                break

        # intra vm time scheduling
        if not time_sched:
            return

        # calculate the total number of (scaled) qvms that can be reused
        # for later loop exit condition
        remaining_reusable_qvm = 0
        for i in range(len(selection)):
            # only 1 circuit in qvm, not doing time scheduling
            if len(selection[i][0]) == 1:
                continue
            
            # there is enough time difference
            max_height = max(part[0] for part in qvm_status[i])
            min_height = min(part[0] for part in qvm_status[i])
            if max_height - min_height > 50:
                remaining_reusable_qvm += 1
            
            # if a partition is already the longest, mark it as already maximally reused, so it won't be further reused
            for part in qvm_status[i]:
                if part[0] == max_height:
                    part[1] = QVM_INTERNAL_PARTITION_MAX_REUSE

        for i, exe in enumerate(executables):
            if i in selected or exe.half_qc == None:
                continue
            circ_depth = exe.half_qc.depth()
            qvm, part = timefit_internal(qvm_status, circ_depth, QVM_INTERNAL_PARTITION_MAX_REUSE)
            if qvm != None:
                #old_max_height = max(part[0] for part in qvm_status[qvm])
                qvm_status[qvm][part][0] += circ_depth
                qvm_status[qvm][part][1] += 1
                selection[qvm][0].append(i)
                selected.add(i)

                # update exit condition
                max_height = max(part[0] for part in qvm_status[qvm])
                min_height = min(part[0] for part in qvm_status[qvm])
                #assert(max_height == old_max_height)
                if max_height - min_height <= 50 or all_part_usedup(qvm, qvm_status, QVM_INTERNAL_PARTITION_MAX_REUSE):
                    remaining_reusable_qvm -= 1
                if remaining_reusable_qvm == 0:
                    break

    # add time scheduling, if some qubit is used, add reset operation
    # one classical register per vm
    def combine(self, vcs, mappings, num_qubits, clreg_prefix: str) -> QuantumCircuit:
        assert(len(vcs) == len(mappings))
        combined_qc_param = [QuantumRegister(num_qubits, 'q')]
        qubit_used = [False]*num_qubits

        # add classical registers
        creg_list = []
        for i, vc in enumerate(vcs):
            for creg in vc.cregs: # .cregs is not in qiskit documentation. not sure if it is proper to use.
                # add vm{num}_ prefix
                #creg_list.append(ClassicalRegister(creg.size, f'vm{i}_'+creg.name))
                creg_list.append(ClassicalRegister(creg.size, clreg_prefix+f'{i}_'+creg.name))
        combined_qc_param += creg_list

        res = QuantumCircuit(*combined_qc_param)
        clbit_offset = 0
        for i in range(len(vcs)):
            reuse = False
            # if the qubit is time-shared, need to reset it
            for j in mappings[i]:
                if qubit_used[j] == True:
                    reuse = True
                    res.reset(j)
            if reuse:
                res.barrier(mappings[i])

            # maybe first barrier then reset?
            # for j in mappings[i]:
            #     if qubit_used[j] == True:
            #         reuse = True
            #         break
            # if reuse:
            #     res.barrier(mappings[i])
            #     for j in mappings[i]:
            #         if qubit_used[j] == True:
            #             res.reset(j)

            res.compose(vcs[i], qubits = mappings[i], clbits = list(i for i in range(clbit_offset, clbit_offset+vcs[i].num_clbits)), inplace = True)
            # mark the region as used
            for j in mappings[i]:
                qubit_used[j] = True
            clbit_offset += vcs[i].num_clbits

        return res

    # combine to a large classical register
    def combine1(self, vcs, mappings, num_qubits) -> QuantumCircuit:
        assert(len(vcs) == len(mappings))
        tot_clbit = sum(vc.num_clbits for vc in vcs)
        res = QuantumCircuit(num_qubits, tot_clbit) # need to make combined circuit and the backend have the same size, since we use identical mapping
        qubit_used = [False]*num_qubits

        clbit_offset = 0
        for i in range(len(vcs)):
            reuse = False
            # if the qubit is time-shared, need to reset it
            for j in mappings[i]:
                if qubit_used[j] == True:
                    reuse = True
                    res.reset(j)
            # add barrier
            if reuse:
                res.barrier(mappings[i])

            # compose
            res.compose(vcs[i], qubits = mappings[i], clbits = list(i for i in range(clbit_offset, clbit_offset+vcs[i].num_clbits)), inplace = True)
            clbit_offset += vcs[i].num_clbits

            # mark the region as used
            for j in mappings[i]:
                qubit_used[j] = True
            
        return res

    # for internal scheduling
    # just 2 3-qubit line shaped partitions for now
    def combine_internal(self, exes, partition_mapping) -> QuantumCircuit:
        vcs = list(exe.half_qc for exe in exes)

        partition_table = [] # format [partition info] partition info: [[circuit numbers], depth]
        for i, vc in enumerate(vcs):
            depth = vc.depth()
            if len(partition_table) < len(partition_mapping):
                partition_table.append([[i], depth])
            else:
                # find the partition with minimum depth and fits the circuit
                target_part = 0
                min_depth = partition_table[0][1]
                for j, part in enumerate(partition_table):
                    if part[1] < min_depth:
                        target_part = j
                        min_depth = part[1]
                partition_table[target_part][0].append(i)
                partition_table[target_part][1] += depth
        
        mappings = [None]*len(exes)
        for i, part in enumerate(partition_table):
            for circ_num in part[0]:
                mappings[circ_num] = partition_mapping[i]

        # only doing internal scheduling for basic 7-qubit qvm
        return self.combine(vcs, mappings, 7, 'circ')


    @classmethod
    def _default_options(cls):
        return None

# below are user-side functions

def vmbackend(num_qubits, basis_gates, coupling_map):
    return GenericBackendV2(num_qubits, basis_gates = basis_gates, coupling_map = coupling_map)

'''
elastic_vm: get a combination of multiple vm regions to satisfy the number of qubits. Return a list of backend objects with their dimensions.
The region is defined as n*m vms. This limits the shapes of the combined vm so we only need to transpile to 1 or 2 (reversing n and m) combined vms.
We use the heuristics that vm_graph is like a grid. We observe such property on IBM and rigetti machines.
But in the worst case, the vm_graph can be arbitrary and all links can be different. Then it's more difficult to handle...

Assumptions: 
All single vms have the same shape. 
All horizontal edges have the same shape.
All vertical edges have the same shape.
vm_graph is a grid.

@ num_qubits: number of qubits of the input circuit
@ basis_gates
@ vm_graph (deleted): specify how vm regions are connected. Vertices represent vms and edges represent the connection of vms.
The edges should not conflict with each other. For instance, we have vms 0,1,2,3. Edge (0, 1) can overlap with edge (0, 2)
since they both use vm 0, but edge (0, 1) should not overlap with edge (2, 3) because we may want to combine (0, 1) and (2, 3) into separate vms.
@ hc: coupling map of horizontal connection, negative qubit number suggests extra qubit not in any vm region,
positive qubit number refers to the same qubit number in vm
@ vc: coupling map of vertical connection
@ shared_up & shared_down: a vertical connection may share qubits with the horizontal connection on the topleft or bottomleft of it.
q and shared_up[q] should refer to the same physical qubit.
@ vm_coupling_map: coupling map of a single vm. 
@ allowed_dimensions: a list of allowed n*m values. In our IBM_brisbane case, we allow 1*1, 1*2, 2*1, 2*2, 2*3, 3*2, 3*3. 
To ensure better connectivity (avoiding long chains of vms),  we constrain |n-m|<=1 so removed 1*3 and 3*1. 
Notice, 2*1 is different from 1*2 because horizontal and vertical connections can be different.
'''

def elastic_vm(num_qubits: int, basis_gates, hc, vc, shared_up: dict, shared_down: dict,
                vm_coupling_map, allowed_dimensions):
    allowed_dimensions.sort(key=lambda d: d[0]*d[1]) # sort by vm count
    single_vm_size = max(max(i) for i in vm_coupling_map)+1
    hc_num_qubit = -min(min(i) for i in hc)
    vc_num_qubit = -min(min(i) for i in vc)
    hv_shared_num_qubit = len(shared_up) + len(shared_down)
    ret = []
    for n, m in allowed_dimensions:
        # horizontal connections: n rows, m-1 connections per row
        # vertical connections: n-1 rows, m connections per row
        # need to minus shared qubits of hc and vc
        elastic_vm_size = n*m*single_vm_size + n*(m-1)*hc_num_qubit + (n-1)*m*vc_num_qubit - (n-1)*(m-1)*hv_shared_num_qubit 
        if elastic_vm_size >= num_qubits:
            #print(n, m)
            combined_coupling_map = combine_coupling_map(vm_coupling_map, hc, vc, shared_up, shared_down, n, m)
            #print(combined_coupling_map)
            combined_vm = GenericBackendV2(elastic_vm_size, basis_gates = basis_gates, coupling_map = combined_coupling_map, control_flow = True)
            ret.append((combined_vm, n, m))

            # see if swapping m and n is allowed and fit
            rotated_vm_size = n*m*single_vm_size + m*(n-1)*hc_num_qubit + (m-1)*n*vc_num_qubit - (n-1)*(m-1)*hv_shared_num_qubit
            if n != m and (m, n) in allowed_dimensions and rotated_vm_size >= num_qubits:
                #print(m, n)
                combined_coupling_map = combine_coupling_map(vm_coupling_map, hc, vc, shared_up, shared_down, m, n)
                #print(combined_coupling_map)
                combined_vm = GenericBackendV2(rotated_vm_size, basis_gates = basis_gates, coupling_map = combined_coupling_map, control_flow = True)
                ret.append((combined_vm, m, n))
            break
    return ret

'''
combine_coupling_map: combine basic qvm, horizontal connections, and vertical connections to the coupling map of a scaled qvm
qubit order: basic qvm, horizontal connections, vertical connections
@ shared_up/shared down: a vertical connection may have overlapping qubits with horizontal connections on its top or bottom.
There are r*(c-1) horizontal connections and (r-1)*c vertical connections.
Assuming vertical connections at (n, m) can only overlap with horizontal connections at (n, m-1) and (n+1, m-1)
they are dictionaries in format {qubit in vc : qubit in hc}
'''

def combine_coupling_map(vm_coupling_map, hc, vc, shared_up: dict, shared_down: dict, n, m):
    single_vm_size = max(max(i) for i in vm_coupling_map)+1
    hc_num_qubit = -min(min(i) for i in hc)
    vc_num_qubit = -min(min(i) for i in vc)

    # change the order of vc to make lower numbered qubits in vc still have lower number in the final coupling map
    # no matter what the given order of vc
    vc.sort(key = lambda d: min(d))
    for i in range(len(vc)):
        if vc[i][0] < 0 and vc[i][1] < 0 and vc[i][0] > vc[i][1]:
            vc[i] = (vc[i][1], vc[i][0])

    ret = []
    edge_set = set()
    offset = 0

    # give all qubits new numbers and add edges in single vm to the combined vm
    for i in range(n):
        for j in range(m):
            # add all edges in one vm region
            for k in vm_coupling_map:
                edge = (k[0] + offset, k[1] + offset)
                ret.append(edge)
                edge_set.add(edge)
            offset += single_vm_size
    

    # add horizontal connections
    # we need to make the edge (l, r) directed. 
    # If l is in some vm region (l>=0), it's the vm on the left (lower qubit number).
    # If r is in some vm region (r>=0), it's the vm on the right (higher qubit number).
    # If l, r < 0, the direction does not matter.
    for i in range(n):
        for j in range(m-1):
            vm_offset_l = (i*m+j)*single_vm_size 
            vm_offset_r = vm_offset_l + single_vm_size
            #edge = None
            for l, r in hc:
                # if l < 0 and r > 0: # <0 means it's a node in connection, which does not belong to any single vm
                #     edge = (l+hc_num_qubit+offset, r+offset_r)
                # else if l > 0 and r < 0:
                #     edge = (l+offset_l, r+hc_num_qubit+offset)
                # else if l < 0 and r < 0: # both vertices are in connection
                #     edge = (l+hc_num_qubit+offset, r+hc_num_qubit+offset)
                # else: # l,r >= 0, both vertices are in vm region
                #     edge = (l+offset_l, r+offset_r)

                # can simplify the above logic, check l and r separately, calculate the qubit number
                if l < 0:
                    l = l+hc_num_qubit+offset
                else:
                    l = l+vm_offset_l
                if r < 0:
                    r = r+hc_num_qubit+offset
                else:
                    r = r+vm_offset_r

                ret.append((l, r))
                ret.append((r, l))
                edge_set.add((l, r))
                edge_set.add((r, l))
            offset += hc_num_qubit

    # add vertical connections
    for i in range(n-1):
        for j in range(m):
            vm_offset_u = (i*m+j)*single_vm_size 
            vm_offset_d = vm_offset_u + m*single_vm_size
            unshared_bit = {} # map from negative value to final qubit number
            for u, d in vc:
                # check if u and d are shared with horizontal connections
                # avoid adding one qubit multiple times
                if u < 0:
                    u = check_shared(u, i, j, n, m, shared_up, shared_down, single_vm_size, hc_num_qubit)
                    if u < 0: # not shared
                        if u in unshared_bit:
                            u = unshared_bit[u]
                        else:
                            unshared_bit[u] = offset
                            u = offset
                            offset += 1
                else:
                    u = u+vm_offset_u

                if d < 0:
                    d = check_shared(d, i, j, n, m, shared_up, shared_down, single_vm_size, hc_num_qubit)
                    if d < 0: # not shared
                        if d in unshared_bit:
                            d = unshared_bit[d]
                        else:
                            unshared_bit[d] = offset
                            d = offset
                            offset += 1
                else:
                    d = d+vm_offset_d

                if (u, d) not in edge_set:
                    edge_set.add((u, d))
                    edge_set.add((d, u))
                    ret.append((u, d))
                    ret.append((d, u))

    return ret

# horizontal connection qubit offset
def hc_offset(single_vm_size: int, n: int, m: int, r: int, c: int, hc_num_qubit: int) -> int:
    # n rows, m columns, m-1 horizontal connections per row
    return n*m*single_vm_size + (r*(m-1)+c)*hc_num_qubit

def check_shared(q: int, i: int, j: int, n: int, m: int, shared_up, shared_down, single_vm_size, hc_num_qubit) -> int:
    if j-1 >= 0: # the first vertical connection on each row won't share qubits with any horizontal connections
        hc_up_offset = hc_offset(single_vm_size, n, m, i, j-1, hc_num_qubit)
        hc_down_offset = hc_offset(single_vm_size, n, m, i+1, j-1, hc_num_qubit)
        if q in shared_up:
            return shared_up[q] + hc_num_qubit + hc_up_offset
        elif q in shared_down:
            return shared_down[q] + hc_num_qubit + hc_down_offset

    return q # return the original negative q if not shared
    
def max_pool(i, j, n, m, region_height) -> float:
    res = 0
    for a in range(n):
        for b in range(m):
            res = max(res, region_height[i+a][j+b])
    return res