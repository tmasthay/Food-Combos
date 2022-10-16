import sys
import itertools
from subprocess import check_output as co

def remove_all(the_list, elem):
    try:
        while( True ):
            the_list.remove(elem)
    except:
        pass
    return the_list

def get_arg(field, deflt, eval_func, deflt_eval=True):
    cmd_args = ' '.join(sys.argv)
    res = cmd_args.split('%s='%field)
    if( deflt_eval ):
        return eval_func(deflt) if len(res) == 1 else eval_func(res[1])
    else:
        return deflt if len(res) == 1 else eval_func(res[1])

ext = get_arg('ext', 'txt', str)
out_file = get_arg('out_file', 'out.%s'%ext, str)
empty = get_arg('empty', True, lambda x : str(x).lower()[0] == 't')

all_files = co('ls *.%s'%ext, shell=True).decode('utf-8').split('\n')
remove_all(all_files, '')
remove_all(all_files, out_file)

input_files = get_arg('input_files', all_files, eval, False)

if( empty ):
    l = [open(e, 'r').read().split('\n') for e in input_files]
else:
    l = [remove_all(open(e, 'r').read().split('\n'), '') \
        for e in input_files]

u = [e for e in itertools.product(*l)]
f = open(out_file, 'w')

[f.write(','.join(uu) + '\n') for uu in u]

f.close()
