from qasmbench import QASMBenchmark
from qiskit_aer import AerSimulator, StatevectorSimulator
from qiskit import transpile

# path to the root directory of QASMBench
path = "../QASMBench"

# selected category for QASMBench
category = "small" 

exclude_tests = {'ipea_n2', 'inverseqft_n4', 'vqe_uccsd_n4', 'pea_n5', 'qec_sm_n5', 'shor_n5', 'vqe_uccsd_n6', 'hhl_n7', 'sat_n7', 'vqe_uccsd_n8', 'qpe_n9', 'adder_n10', 'hhl_n10', 'cc_n12', 'hhl_n14', 'factor247_n15', 'bwt_n21', 'vqe_n24'}

# whether to remove the final measurement in the circuit
remove_final_measurements = True

# whether use qiskit.transpile() to transpile the circuits (note: must provide qiskit backend)
do_transpile = False

# arguments for qiskit.transpile(). backend should be provide at least
transpile_args = {}

bm = QASMBenchmark(path, category, remove_final_measurements=remove_final_measurements, do_transpile=do_transpile, **transpile_args)

simulator = AerSimulator(method='statevector')
#simulator = StatevectorSimulator()
#Aer.get_backend('statevector_simulator')

circ_name_list = list(i for i in bm.circ_name_list if i not in exclude_tests)
circ_list = list(bm.get(i) for i in circ_name_list)

print("There are", len(circ_list), "circuits in the small category:")
print(circ_name_list)
print()

# different types of simulations:
# 1. get the final probability distribution
# remove all measurements in the end, use save_statevector and shot=1

# What happens if some qubits are measured and some are not?
# num_clbits depends on measurements
# If clbits = 0, it outputs the probability of each possible final state
# Otherwise only clbits are in the result, like a shot in method 2.

# can use statevector to retrive the final state even if clbit exists

# 2. use multiple shots like a real machine (sampling)

# We use method 1 to get the statevector. 
for i in range(len(circ_list)):
    test_circ = transpile(circ_list[i], simulator)
    test_circ.save_statevector()
    result = simulator.run(test_circ, shots=1).result()
    counts = result.get_counts()
    print(circ_name_list[i])
    print(counts)

    #statevector = result.get_statevector(test_circ)
    #print(statevector.probabilities_dict())