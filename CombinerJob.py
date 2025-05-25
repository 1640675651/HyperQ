from qiskit.providers import JobV1
from collections import defaultdict
class CombinerJob(JobV1):
    def __init__(self, job: JobV1, circuit_map: [list], clbits: [list], backend, **fields):
        self.job = job
        self.circuit_map = circuit_map
        self.clbits = clbits
        self._backend = backend
        super().__init__(backend, '', **fields)

    def result(self) -> [dict]:

        # Why sometimes there are spaces in the result?
        result = self.job.result()
        counts = result[0].join_data().get_counts() if len(result[0].data) > 1 else list(result[0].data.values())[0].get_counts()
        clbits = self.clbits

        circ_cnt = len(clbits)
        counts_individual = []
        for i in range(circ_cnt):
            counts_individual.append(defaultdict(int))

        for k, v in counts.items():
            offset = 1
            # remove spaces
            k = k.replace(' ', '')
            for i in range(circ_cnt-1, -1, -1): # correction: reverse order
            #for i in range(circ_cnt):
                ki = k[offset:offset+clbits[i]]
                counts_individual[i][ki] += v
                offset += clbits[i]
                
        return counts_individual

    def job_id(self):
        return self.job.job_id()

    def status(self):
        return self.job.status()

    def submit(self):
        self.job.submit()

    def time_taken(self):
        return self.job.result().time_taken