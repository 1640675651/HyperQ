from math import log
from collections import defaultdict
import sys

def kl(ideal: dict, real: dict):
    ret = 0
    for k, v in ideal.items():
        if k not in real:
            return None # cannot divide by 0
        ret += v*log(v/real[k])
    return ret

def l1(ideal: dict, real: dict):
    ret = 0
    for k, v in ideal.items():
        if k in real:
            ret += abs(v - real[k])
        else:
            ret += v
    for k, v in real.items():
        # avoid re-adding the same state
        if k in ideal:
            continue
        ret += v
    return ret

result_ideal_file = open('result_ideal.txt', 'r')

if len(sys.argv) < 2:
    print('need result file')
    exit()
result_real_filename = sys.argv[1]
result_real_file = open(result_real_filename, 'r')

# read gold result from ideal simulator
result_ideal = {}
name_line = True
circ_name = ''
for line in result_ideal_file.readlines():
    if(name_line):
        circ_name = line.strip()
    else:
        result_ideal[circ_name] = eval(line) # read a dict
    name_line = not name_line

# read result to be compared
# maintain the same order as in result file
tot_l1 = 0
job_cnt = 0

name_line = True
for line in result_real_file.readlines():
    if(name_line):
        circ_name = line.strip()
        print(circ_name)
    else:
        result_real = eval(line) # eval(line.split(',', 1)[1].strip(')\n')) # not reading a defaultdict anymore
        cur_l1 = l1(result_ideal[circ_name], result_real)
        print(cur_l1)
        tot_l1 += cur_l1
        job_cnt += 1
        
    name_line = not name_line

#print('avg l1:', tot_l1/job_cnt)