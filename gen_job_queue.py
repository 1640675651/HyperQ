import random

test_types = 49
test_repeat = 4

job_queue = []
for i in range(test_types):
    job_queue += [i] * test_repeat

random.shuffle(job_queue)
print(job_queue)
print(len(job_queue))