import os
import fnmatch
import yaml
from mh.core import DotDict

d = DotDict()

# Walk through the directory tree
for dirpath, dirnames, filenames in os.walk('.'):
    for filename in fnmatch.filter(filenames, 'results.txt'):
        new_key = dirpath.replace('./Final/', '').replace('/', '.')
        with open(os.path.join(dirpath, filename)) as f:
            s = f.read().strip()
            while '\n\n' in s:
                s = s.replace('\n\n', '\n')
            tokens = s.split('\n')
            try: 
                d[new_key] = tokens
            except Exception as e:
                print(f"Failed to add {new_key=}, {tokens=} {e=}")

u = d.simple_dict()

yaml.dump(u, open('data.yaml', 'w'))