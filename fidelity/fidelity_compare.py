from math import log
from collections import defaultdict
import sys

if len(sys.argv) < 3:
    print('need baseline l1 file and test l1 file')
    exit()
baseline_filename = sys.argv[1]
test_filename = sys.argv[2]
baseline_file = open(baseline_filename, 'r')
test_file = open(test_filename, 'r')

# read baseline result
test_names = []
result_baseline = []
name_line = True
circ_name = ''
for line in baseline_file.readlines():
    if(name_line):
        circ_name = line.strip()
        test_names.append(circ_name)
    else:
        if line.startswith('None'):
            result_baseline.append(None)
        else:
            result_baseline.append(float(line.strip()))
    name_line = not name_line


# read test result
result_real = defaultdict(list) # real result contain a list of kl value per type of circuit
name_line = True
for line in test_file.readlines():
    if(name_line):
        circ_name = line.strip()
    else:
        if not line.startswith('None'):
            result_real[circ_name].append(float(line.strip())) 
    name_line = not name_line

# calculate average
def avg(l: list) -> float:
    if len(l) == 0:
        return None
    return sum(l)/len(l)

for k, v in result_real.items():
    result_real[k] = avg(v)

baseline_kl_sum = 0
vm_kl_sum = 0
valid_tests = 0
# print comparison report
# for i in range(len(test_names)):
#     if type(result_baseline[i]) == float and type(result_real[test_names[i]]) == float:
#         baseline_kl_sum += result_baseline[i]
#         vm_kl_sum += result_real[test_names[i]]
#         valid_tests += 1
#     print(test_names[i])
#     print('baseline =', result_baseline[i], 'test =', result_real[test_names[i]])
#     if result_baseline[i] != None:
#         print('test/baseline =', result_real[test_names[i]]/result_baseline[i])
#         print('test-baseline =', result_real[test_names[i]]-result_baseline[i])
#     print()
# end report


# print in latex figure format
for i in range(len(test_names)):
    if type(result_baseline[i]) == float and type(result_real[test_names[i]]) == float:
        baseline_kl_sum += result_baseline[i]
        vm_kl_sum += result_real[test_names[i]]
        valid_tests += 1
        print('(' + str(i+1) + ', {:.3f})'.format(result_baseline[i]), end = ' ')

print()

for i in range(len(test_names)):
    if type(result_baseline[i]) == float and type(result_real[test_names[i]]) == float: #and (i!=13 and i != 24 and i != 27):
        print('(' + str(i+1) + ', {:.3f})'.format(result_real[test_names[i]]), end = ' ')
print()
# end latex

print('average')
print('baseline =', baseline_kl_sum/valid_tests, 'test =', vm_kl_sum/valid_tests)