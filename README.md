File Descriptions

Core Libraries:

    HypervisorBackend.py

    vm_executable.py

    CombinerJob.py

Benchmark Scripts:

    benchmark_ideal.py: Get the ideal state distribution with a noiseless simulator

    benchmark_baseline.py: Run benchmark with IBM Qiskit default setting (no multiprogramming)

    benchmark.py: Run benchmark with HyperQ, can specify 1. time scheduling 2. intra-vm scheduling 3. noise-aware scheduling

    benchmark_poisson.py: Same as above but for the poisson benchmark

Data Retrieval and Analysis Scripts:

    getdata/get_result_baseline.py: Get the measured results of a baseline benchmark from IBM

    getdata/get_result.py: Get the measured results of a HyperQ benchmark from IBM

    getdata/get_job_time.py: Get the run time of each job (for both baseline and HyperQ)

    getdata/throughput_utilization.py: Get the throughput/utilization and their improvement over baseline

    getdata/throughput_utilization_poisson.py: Same as above but for the poisson benchmark

    analysis/fidelity

    analysis/latency

Prerequisites:

    1. Install Qiskit and activate venv: https://docs.quantum.ibm.com/guides/install-qiskit

    2. Install qiskit_aer simulator: pip install qiskit_aer

    3. Clone qasmbench from github: https://github.com/pnnl/QASMBench to the same directory as this repo (not inside of this repo). At this moment, QASMBench has a file name inconsistency, which can cause error. Rename QASMBench/medium/gcm_n13/gcm_h6.qasm to gcm_n13.qasm

    4. Register IBM Quantum account: https://quantum.ibm.com/ and get access token.

Benchmark preperation:

    1. Get ideal result (statevector)
    python benchmark_ideal.py
    May need to manually correct some state vectors. You can directly use result_ideal.txt.

    2. Run baseline benchmark
    We need "small" and "all" benchmark for comparison with HyperQ. To save IBM token usage, we don't need to run both "small" and "all" benchmark since "small" is included in "all". In practice, we can:
    
    python benchmark_baseline.py small ./benchmark_result/baseline/small 1
    python benchmark_baseline.py med ./benchmark_result/baseline/med 1

    Then concatenate them to "all":

    cat benchmark_result/baseline/small/workload1.txt benchmark_result/baseline/med/workload1.txt > benchmark_result/baseline/all/workload1.txt

    3. Get baseline benchmark result
    python getdata/get_result_baseline.py benchmark_result/baseline/small/workload1.txt > benchmark_result/baseline/small/result1.txt

    4. Calculate baseline fidelity
    python fidelity/fidelity.py ./benchmark_result/baseline/small/result1.txt > ./benchmark_result/baseline/small/l1_1.txt

HyperQ all-at-once benchmark workflow:

    1. Run HyperQ benchmark
    
    python benchmark.py small/all output_path workload_id
    
    E.g. python benchmark.py small benchmark_result/small/all_at_once/spaceonly 1

    This writes the workload file and calibration data to output_path. You can use the benchmark_result directory structure as a reference to keep track of different benchmark

    To test different scheduling strategies, tune the knobs for scheduling at the line "selection = hypervisor.schedule(exec_queue, time_sched = False, intra_vm_sched = True, noise_aware = False)". The options stands for time scheduling, intra vm scheduling (fractional qVM), and noise aware scheduling. 
    
    In the results of the paper, HyperQ = (False, True, False)
    
    HyperQ space+time = (True, True, False)
    
    HyperQ noise aware = (False, False, True).

    2. Get throughput and utilization
    python getdata/throughput_utilization.py benchmark_result/baseline/all/workload1.txt benchmark_result/(category)/workload.txt small/all

    E.g. python getdata/throughput_utilization.py benchmark_result/baseline/all/workload1.txt benchmark_result/small/all_at_once/spaceonly/workload1.txt small

    3. (small only) Get measurement result
    python getdata/get_result.py ./benchmark_result/(category)/workload1.txt > ./benchmark_result/(category)/result1.txt

    E.g. python getdata/get_result.py ./benchmark_result/small/all_at_once/spaceonly/workload1.txt > ./benchmark_result/small/all_at_once/spaceonly/result1.txt

    4. (small only) Calculate fidelity
    python fidelity/fidelity.py ./benchmark_result/(category)/result.txt > ./benchmark_result/(category)/l1_1.txt

    E.g. python fidelity/fidelity.py ./benchmark_result/small/all_at_once/spaceonly/result1.txt > ./benchmark_result/small/all_at_once/spaceonly/l1_1.txt

    5. (small only) Print fidelity comparison report. The report contains datapoints (workload_id, l1 error). First line for baseline and second line for HyperQ.
    python fidelity/fidelity_compare.py ./benchmark_result/baseline/small/l1_1.txt ./benchmark_result/(category)/l1_1.txt > ./benchmark_result/(category)/l1_compare_1.txt

    E.g. python fidelity/fidelity_compare.py ./benchmark_result/baseline/small/l1_1.txt ./benchmark_result/small/all_at_once/spaceonly/l1_1.txt > ./benchmark_result/small/all_at_once/spaceonly/l1_compare_1.txt


HyperQ poisson benchmark workflow:

    1. Run HyperQ benchmark
    python benchmark_poisson.py small/all output_path workload_id

    E.g. python benchmark_poisson.py small ./benchmark_result/small/poisson/spaceonly 1

    2. Get throughput and utilization
    python getdata/throughput_utilization_poisson.py ./benchmark_result/baseline/all/workload1.txt benchmark_result/(category)/workload.txt small/all

    E.g. python getdata/throughput_utilization_poisson.py ./benchmark_result/baseline/all/workload1.txt benchmark_result/small/poisson/spaceonly/workload1.txt small

    3. (small only) Get measurement result
    python getdata/get_result_poisson.py ./benchmark_result/(category)/workload1.txt > ./benchmark_result/(category)/result1.txt

    E.g. python getdata/get_result_poisson.py ./benchmark_result/small/poisson/spaceonly/workload1.txt > ./benchmark_result/small/poisson/spaceonly/result1.txt

    Fidelity analysis steps are the same as all-at-once benchmark.

Note: At the time when the paper was written, we used IBM qiskit provider's backend.run() API with dynamic=True option. Now this API is deprecated and we changed our code to use the Sampler API. With this new API, HyperQ cannot reach ideal speedup or encounters error with time scheduling. We believe there are some instruction-level scheduling that we don't have control.
