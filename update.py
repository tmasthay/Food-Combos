from html2text import html2text as htt
from subprocess import check_output as co
import re
import os

def reg_clean(lp, rp, lb, rb, bar):
    def helper(x, inv=False):
        if( inv ):
            return x.replace(lp, '(') \
               .replace(rp, ')') \
                .replace(lb, '[') \
                .replace(rb, ']') \
                .replace(bar, '|')
        else:
            return x.replace('(', lp) \
                .replace(')',rp) \
                .replace('[', lb) \
                .replace(']', rb) \
                .replace('|', bar)
    return helper

def write_and_close(dest, src):
    if( dest[0] != '/' ):
        dest = '%s/%s'%(os.getcwd(), dest)
    dest = dest.replace("'",'') \
        .replace('(', '') \
        .replace(')', '') \
        .replace('&', '') \
        .replace('\\','')

    subs = dest.split("/")[1:-1]
    curr = ''
    for s in subs:
        curr = '%s/%s'%(curr, s)
        if( not os.path.exists(curr) ):
            os.system('mkdir %s'%curr)
            print('Made directory "%s"'%(curr)) 
    f = open(dest, 'w')
    f.write(src)
    f.close()

def invert_dict(d):
    u = dict()
    for (k,v) in d.items():
        if( k != 'order' ):
            u[v] = k
    return u

def valid_parser(d):
    return eval(' and '.join([str(e in d['order']) \
        for e in set(d.keys()).difference(['order'])]))
        
def split_all(splitters, s):
    regex = '(' + '|'.join([re.sub('(\[|\]|\(|\))', r'\\\1',
        e.replace('|','\|')) for e in splitters]) + ')'
    exception_regex = '\n[ ]*\* .*\w+.*/wiki/.* ".*".*'
    exception_case = re.findall(exception_regex, '\n'.join(splitters))
    thres = .8
     
    if( (1.0 * len(exception_case)) / (1.0 * max(1,len(splitters))) > thres ):
        if( splitters[0][0:5] == '\n    ' ):
            res = re.split(exception_regex.replace('[ ]*','    '), s)
            found_fields = exception_case
            print('EXCEPTION LENGTHS=(%d,%d)'%(len(res), len(found_fields)))
        else:
            res = re.split(exception_regex.replace('[ ]*','  '), s)
            found_fields = exception_case
            print('EXCEPTION LENGTHS=(%d,%d)'%(len(res), len(found_fields)))
    else:
        res = re.split(r'%s'%regex, s)
        found_fields = [e for e in res if e in splitters]
        [res.remove(e) for e in found_fields]
    return res[1:], found_fields

def eat_layer(regex, 
    the_text, 
    cdir, 
    f=(lambda x : x)):
  
    if( type(regex) == str ):
        fields = [e if type(e) != tuple else e[0] \
            for e in re.findall(regex, the_text)]
        subtexts, fields = split_all(fields, the_text)
        fields = [f(e) for e in fields]
        next_dir = []
        for (i,e) in enumerate(fields):
            next_dir.append('%s/%s'%(cdir, e))
            write_and_close('%s/%s_total.txt'%(next_dir[-1], e), subtexts[i])
        print('EXITING BASE: "%s"'%regex)
        return subtexts, fields, next_dir
    else:
        sbt, flds, ndir = eat_layer(regex[0], the_text, cdir, f[0])
        sbt_total = [sbt]
        flds_total = [flds]
        ndir_total = [ndir]
        if( len(regex) == 1 ):
            return sbt_total, flds_total, ndir_total
        for (i,e) in enumerate(sbt):
            t1,t2,t3 = eat_layer(regex[1:], e, ndir[i], f[1:])
            sbt_total.append([t1])
            flds_total.append([t2])
            ndir_total.append([t3])
        return sbt, flds, ndir

def initialize_html():
    wiki_food_portal = 'https://en.wikipedia.org/wiki/Portal:Food'
    s = co("curl -s '%s'"%wiki_food_portal, shell=True) \
       .decode('utf-8')
    cleaned = htt(s)
    write_and_close('Final/wiki_portal_raw_html.txt', s)
    write_and_close('Final/wiki_portal_cleaned.txt', cleaned)
    return cleaned

def setup_regex_tree():
    regex = []
    regex_cleaner = []

    regex.append(2 * [r'(\[v\]\(/wiki/Template:(Cuisines|Meals_navbox) %s'%(
        '"Template:(Cuisines|Meals navbox)"\))')])
    regex_cleaner.append(
        2 * [lambda x : x.split(':')[1].split(' ')[0].split('_')[0]])

    regex.append(r'\w+\|')
    regex_cleaner.append(lambda x : \
        x.replace('|','').split('[')[-1].split(']')[0])

    regex.append('\\n  \* \[.*\].*/wiki/.* ".*".*')
    regex_cleaner.append(lambda x : \
        x.replace('\n','') \
            .split('/wiki/')[1] \
            .split(' ')[0])

    return regex, regex_cleaner

def get_sites():
    cleaned = initialize_html()
    regex, regex_cleaner = setup_regex_tree()

    sbt, flds, ndir = eat_layer(regex, cleaned, 'Final', regex_cleaner)

def fetch_pages():
    get_sites()
    files = co('find Final -type d', shell=True) \
        .decode('utf-8') \
        .split('\n')[:-1]
    num_files = len(files)
    num_performed = 0
    num_failed = 0
    for f in files:
        num_performed += 1
        parts = f.split('/')
        cdir = parts[:-1]
        page = 'https://en.wikipedia.org/wiki/%s'%parts[-1]
        if( os.path.exists('%s/WebContentsClean_%s.txt'%(f, parts[-1])) ):
            print('Skipping %d of %d'%(num_performed, num_files))
            continue
        try:
            contents = co('curl -s %s'%page, shell=True).decode('utf-8')
        except CalledProcessError:
            num_failed += 1
            print('Failure %d of %d, page "%s"'%(num_failed, num_performed))
            continue
        out_file = open('%s/WebContentsRaw_%s.txt'%(f, parts[-1]), 'w')
        out_clean_file = open('%s/WebContentClean_%s.txt'%(f,parts[-1]), 'w')
        out_file.write(contents)
        out_clean_file.write(htt(contents))
        out_file.close()
        out_clean_file.close()
        print('Processed %d of %d'%(num_performed, num_files))
    print('Total failed: %d of %d'%(num_failed, num_files))

def process_pages(max_dishes):
    res = co('find Final -type d -name "List*"', shell=True) \
        .decode('utf-8') \
        .split('\n')[:-1]
    regex = '\* \[.*\].*/wiki/.* ".*".*'
    for curr in res:
        lcl = curr.split('/')
        cdir = '%s/%s'%(os.getcwd(), curr)
        clean_page = '%s/WebContentClean_%s.txt'%(cdir, lcl[-1])
        try:
            s = open(clean_page, 'r').read()
        except:
            print('Skipping %s, %s'%(curr, clean_page))
            continue
        curr_res = re.findall(regex, s)
        out_file = open('%s/results.txt'%cdir, 'w')
        fnl_res = [e.split('/wiki/')[-1].split(' ')[0] for e in curr_res]
        fnl_res = [e for e in fnl_res if 'cuisine' not in e.lower()]
        out_file.write('\n'.join(fnl_res))
        out_file.close()
        print('%s: %d'%(curr, len(curr_res)))

def go():
    max_dishes = 100
    #fetch_pages()
    process_pages(max_dishes)

if( __name__ == "__main__" ):
    go()  
