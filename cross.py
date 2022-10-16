import sys
import itertools
from subprocess import check_output as co
from update import write_and_close, go

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
        return eval_func(deflt) if len(res) == 1 else eval_func(res[1].split(' ')[0])
    else:
        return deflt if len(res) == 1 else eval_func(res[1])

def create_product(ext, input_files, out_file,
    empty, cartesian=False, nspaces=5):

    if( len(input_files) == 0 ):
        raise Exception('No input files!')
    
    if( empty ):
        l = [open(e, 'r').read().split('\n') \
            for e in input_files]
    else:
        l = [remove_all(open(e, 'r').read() \
            .split('\n'), '') \
            for e in input_files]
   
    if( cartesian ): 
        u = '\n'.join([','.join(e) \
            for e in itertools.product(*l)])
    else:
        lengths = [len(e) for e in l]
        max_length = max(lengths)
        spaces = ''.join(nspaces * [' '])
        u = ''
        for i in range(max_length):
            curr_line = ''
            for e in l:
                if( i < len(e) ):
                    curr_line = '%s%s'%(curr_line,
                       e[i])
                curr_line = curr_line + spaces
            u += curr_line + '\n'
    write_and_close(out_file, u)

if( __name__ == "__main__" ):
    ext_default = 'txt'
    out_default = 'out.%s'%ext_default
    empty_default = False
    input_default = '[]'
    cartesian_default = False
    update_default = False
    print('Usage: python cross.py ext= %s'%(
        'out_file= empty= input_files= %s'%(
        'cartesian= update=')))
    print('Unspecified parameters default to %s'%(
        'to the following: input_files is %s'%(
        'mandatory, else the program will quit.')))
    print('ext=%s'%ext_default)
    print('out_file=%s'%out_default)
    print('empty=%s'%str(empty_default))
    print('input_default=%s'%(input_default))
    print('cartesian_default=%s'%str(
        cartesian_default))
    print('update_default=%s'%(str(
       update_default)))
    
    ext = get_arg('ext', ext_default, str)
    input_files = get_arg('input_files', 
        input_default, 
        eval)
    out_file = get_arg('out_file', 
        out_default, 
        str)
    empty = get_arg('empty', empty_default,
        lambda x : str(x).lower()[0] == 't')
    cartesian = get_arg('cartesian', 
        cartesian_default,
        lambda x : str(x).lower()[0] == 't')
    update_data = get_arg('update',
        update_default,
        lambda x: str(x).lower()[0] == 't')
        
    if( ext not in out_file ):
        out_file = '%s.%s'%(out_file,ext)

    print('REFETCHING DATABASE')
    if( update_data ):
        go(True)
    print('DONE REFETCHING')

    print('BEGINNING PRODUCT QUERY')
    create_product(ext, input_files, out_file, 
        empty, cartesian)
    print('SUCCESS: output in "%s"'%(out_file))
