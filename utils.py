def max_in_dict(d: dict) -> (['keys'], 'value'):
    maxv = 0
    keys = []
    for k, v in d.items():
        if v > maxv:
            keys = [k]
            maxv = v
        elif v == maxv:
            keys.append(k)
    return (keys, maxv)

def sort_dict_by_value(d: dict) -> [('key', 'value')]:
    return sorted(d.items(), key=lambda item: item[1])

def empty_2d_list(n: int) -> [list]:
    ret = []
    for i in range(n):
        ret.append([])
    return ret


def empty_3d_list(n: int, m: int) -> [[list]]:
    ret = []
    for i in range(n):
        ret.append(empty_2d_list(m))
    return ret

def read_workload(filename, infocnt: int, encoding = 'utf-8') -> [('id', ('circ name'), 'selection')]:
    f = open(filename, 'r', encoding = encoding)
    linecnt = 0
    ret = []
    cur_comb = None
    cur_id = ''
    selection = None
    for line in f.readlines():
        if linecnt == 0:
            selection = eval(line.strip('selection:').strip())
        if linecnt == 1:
            #cur_comb = tuple(line.strip().split())
            # for workload with internal scheduling
            cur_comb = eval(line)
        elif linecnt == 2:
            cur_id = line.split()[0]
            ret.append((cur_id, cur_comb, selection))
        elif linecnt == infocnt: # 4 if remaining job queue is in the file, otherwise 3
            linecnt = 0
            continue
        linecnt += 1
    return ret

def read_workload_poisson(filename, encoding = 'utf-8') -> [('id', ('circ name'), 'selection')]:
    f = open(filename, 'r', encoding = encoding)
    linecnt = -1
    ret = []
    cur_comb = None
    cur_id = ''
    selection = None
    for line in f.readlines():
        if 'selection' in line:
            linecnt = 0
            selection = eval(line.split(':')[1].strip())
        elif linecnt == 1:
            cur_comb = eval(line)
        elif linecnt == 2:
            cur_id = line.split()[2]
            ret.append((cur_id, cur_comb, selection))
        linecnt += 1
    return ret

def read_workload_baseline(filename, encoding = 'utf-8') -> {'name': 'jobid'}:
    ret = {}
    f = open(filename, 'r', encoding=encoding)
    for line in f.readlines():
        jobid, name = line.strip().split()
        ret[name] = jobid
    return ret

def read_workload_baseline_tuple(filename, encoding = 'utf-8') -> [('jobid', 'name')]:
    ret = []
    f = open(filename, 'r', encoding=encoding)
    for line in f.readlines():
        jobid, name = line.strip().split()
        ret.append((jobid, name))
    return ret

def remove_key_space(counts: dict) -> dict:
    new_dict = {}
    for k, v in counts.items():
        newk = k.replace(' ','')
        new_dict[newk] = v
    return new_dict


def count_to_prob(counts: dict, shots: int):
    for k in counts:
        counts[k] /= shots

def read_runtime(filename: str, encoding = 'utf-8') -> dict:
    f = open(filename, 'r', encoding = encoding)
    res = {}
    for line in f.readlines():
        if line == '\n':
            break
        job_id, runtime = line.strip().split()
        res[job_id] = float(runtime)
    f.close()
    return res

def read_runtime_list(filename: str, encoding = 'utf-8') -> list:
    f = open(filename, 'r', encoding = encoding)
    res = []
    for line in f.readlines():
        if line == '\n':
            break
        job_id, runtime = line.strip().split()
        res.append(float(runtime))
    f.close()
    return res