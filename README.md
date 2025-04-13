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

    2. Clone qasmbench from github: https://github.com/pnnl/QASMBench to the same directory as this repo

Benchmark preperation:

    1. Get ideal result (statevector)
    python benchmark_ideal.py > result_ideal.txt. May need to manually correct some state vectors. You can directly use benchmark_result_osdi25/result_ideal.txt.

    2. Run baseline benchmark
    python benchmark_baseline.py small > ./benchmark_result/baseline/workload.txt

    3. Get baseline benchmark result
    python getdata/get_result_baseline.py benchmark_result/baseline/workload.txt > benchmark_result/baseline/result.txt

    4. Calculate baseline fidelity
    python fidelity/fidelity.py ./benchmark_result/baseline/result.txt > ./benchmark_result/baseline/l1.txt

HyperQ all-at-once benchmark workflow:

    1. Run HyperQ benchmark
    see checklist in benchmark.py before running.
    
    python benchmark.py small/all output_path workload_id
    
    This writes the workload file and calibration data to output_path.

    2. Get throughput and utilization
    python getdata/throughput_utilization.py benchmark_result/baseline/workload.txt benchmark_result/(category)/workload.txt small/all

    3. (small only) Get measurement result
    python getdata/get_result.py ./benchmark_result/(category)/workload.txt > ./benchmark_result/(category)/result.txt

    4. (small only) Calculate fidelity
    python fidelity/fidelity.py ./benchmark_result/(category)/result.txt > ./benchmark_result/(category)/l1.txt

    5. (small only) Print fidelity comparison report
    python fidelity/fidelity_compare.py ./benchmark_result/baseline/l1.txt ./benchmark_result/(category)/l1.txt > ./benchmark_result/(category)/l1_compare.txt

HyperQ poisson benchmark workflow:

    1. Run HyperQ benchmark
    python benchmark_poisson.py small/all output_path workload_id

    2. Get throughput and utilization
    python getdata/throughput_utilization_poisson.py benchmark_result/baseline/workload.txt benchmark_result/(category)/workload.txt small/all

    3. (small only) Get measurement result
    python getdata/get_result_poisson.py ./benchmark_result/(category)/workload.txt > ./benchmark_result/(category)/result.txt

    Same for remaining steps.


