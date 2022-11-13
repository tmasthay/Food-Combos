import numpy as np
from subprocess import check_output as co
import sys

def get_arg(field, deflt, eval_func, deflt_eval=True):
    cmd_args = ' '.join(sys.argv)
    res = cmd_args.split('%s='%field)
    if( deflt_eval ):
        return eval_func(deflt) if len(res) == 1 else eval_func(res[1].split(' ')[0])
    else:
        return deflt if len(res) == 1 else eval_func(res[1])

def get_random_combos(combo_file, num_combos):
    l = np.array(open(combo_file, 'r').read().split('\n'))
    return np.random.choice(l, num_combos)

def get_full_random_combos(directory, num_combos):
    s = co('find %s -name "*.txt"'%directory, shell=True).decode('utf-8').split('\n')
    while( '' in s ):
        s = s[:-1]
    all_combos = []
    for ss in s:
        curr = open(ss, 'r').read().split('\n')
        for c in curr:
            if( c != '' ):
                all_combos.append(c)
    all_combos = np.ndarray.flatten(np.array(all_combos))
    return np.random.choice(all_combos, num_combos)
