import os
import fnmatch
import yaml
import copy

def like_dict(obj) -> bool:
    required_methods = ['keys', 'items', 'get']
    return all(hasattr(obj, method) for method in required_methods)


def like_list(obj) -> bool:
    required_methods = [
        '__getitem__',
        '__setitem__',
        '__len__',
        'append',
        'extend',
        'pop',
    ]
    return all(hasattr(obj, method) for method in required_methods)


def gen_items(obj):
    if like_dict(obj):
        return obj.items()
    elif like_list(obj):
        return enumerate(obj)
    else:
        raise ValueError(f'Object {obj} is neither a list nor a dictionary')
    
class DotDict:
    def __init__(self, d=None, self_ref_resolve=False, deep=False):
        if d is None:
            d = {}
        if deep:
            D = copy.deepcopy(d)
        else:
            D = d
        if type(d) is DotDict:
            self.__dict__.update(d.__dict__)
        else:
            for k, v in D.items():
                if type(v) is dict:
                    D[k] = DotDict(v, self_ref_resolve=False)
                elif type(v) is list:
                    D[k] = [
                        (
                            DotDict(e, self_ref_resolve=False)
                            if type(e) is dict
                            else e
                        )
                        for e in v
                    ]
            self.__dict__.update(D)
        if self_ref_resolve:
            self.self_ref_resolve()

    def set(self, k, v):
        self.deep_set(k, v)

    def get(self, k, default_val=None):
        try:
            return self.deep_get(k)
        except KeyError:
            return default_val

    def simple_dict(self):
        u = {}
        for k, v in self.items():
            if isinstance(v, DotDict):
                u[k] = v.simple_dict()
            elif isinstance(v, list):
                u[k] = [e.simple_dict() if isinstance(e, DotDict) else e for e in v]
            else:
                u[k] = v
        return u

    def __setitem__(self, k, v):
        self.deep_set(k, v)

    def __getitem__(self, k):
        return self.deep_get(k)

    def __setattr__(self, k, v):
        if isinstance(v, dict):
            v = DotDict(v)
        self.__dict__[k] = v

    def __iter__(self):
        return iter(self.__dict__)

    def __delitem__(self, k):
        del self.__dict__[k]

    def getd(self, k, v):
        return self.__dict__.get(k, v)

    def setdefault(self, k, v):
        self.__dict__.setdefault(k, v)

    def keys(self):
        return self.__dict__.keys()

    def items(self):
        return self.__dict__.items()

    def values(self):
        return self.__dict__.values()

    def update(self, d):
        self.__dict__.update(DotDict(d).dict())

    def str(self):
        # return str(self.__dict__)
        return self.pretty_str()
        # return str(self.dict())

    def dict(self):
        tmp = {}
        for k, v in self.items():
            if isinstance(v, DotDict):
                tmp[k] = v.dict()
            elif like_list(v):
                tmp[k] = [e.dict() if isinstance(e, DotDict) else e for e in v]
            else:
                tmp[k] = v
        return tmp

    def __str__(self):
        return self.str()

    def __repr__(self):
        return self.str()

    def deep_get(self, k):
        d = self.__dict__
        if type(k) != str:
            return d[k]
        keys = k.split('.')
        for key in keys:
            d = d[key]
        return d

    def deep_set(self, k, v):
        d = self.__dict__
        if type(k) != str:
            return d[k]
        keys = k.split('.')
        for key in keys[:-1]:
            try:
                d = d[key]
            except KeyError:
                d[key] = DotDict({})
                d = d[key]
        d[keys[-1]] = v

    def has_self_ref(self, *, self_key='self'):
        d = self.__dict__
        q = [d]
        while q:
            d = q.pop()
            if like_dict(d):
                for k, v in d.items():
                    if like_dict(v) or like_list(v):
                        q.append(v)
                    elif isinstance(v, str):
                        if self_key in v or 'eval(' in v:
                            return True
            elif like_list(d):
                for e in d:
                    if like_dict(e) or like_list(e):
                        q.append(e)
                    elif isinstance(e, str):
                        if self_key in e or 'eval(' in e:
                            return True
        return False

    def pretty_str(self, max_length=160):
        return dict_dump(self, max_length=max_length)

    def self_ref_resolve(
        self, *, self_key='self', max_passes=5, gbl=None, lcl=None, relax=False
    ):
        lcl = lcl or {}
        gbl = gbl or {}
        lcl.update(locals())
        gbl.update(globals())
        passes = 0
        while passes < max_passes and self.has_self_ref(self_key=self_key):
            d = self.__dict__
            q = [d]
            while q:
                d = q.pop()
                for k, v in gen_items(d):
                    if isinstance(v, DotDict) or like_list(v):
                        q.append(v)
                    elif isinstance(v, dict):
                        d[k] = DotDict(v)
                        q.append(d[k])
                    elif isinstance(v, str):
                        try:
                            if 'eval(' in v:
                                d[k] = eval(
                                    v[5:-1].replace(self_key, 'self'), gbl, lcl
                                )
                            elif v.startswith(f'{self_key}.'):
                                d[k] = eval(
                                    v.replace(self_key, 'self'), gbl, lcl
                                )

                        except AttributeError:
                            msg = (
                                f"Could not resolve self reference for {k}={v}"
                                f"\ngiven below\n\n{self}"
                            )
                            if not relax:
                                raise AttributeError(msg)
                            else:
                                UserWarning(msg)
                        except TypeError as e:
                            msg = str(e)
                            final_msg = (
                                f'Error evaluating {v} of type {type(v)}\n{msg}'
                            )
                            raise RuntimeError(final_msg)

            passes += 1

        if passes == max_passes:
            msg = f"Max passes ({max_passes}) reached. self_ref_resolve failed."
            if not relax:
                raise ValueError(msg)
            else:
                further_msg = (
                    '. Continuing...set relax=False to raise error if '
                    ' this behavior is unexpected.'
                )
                UserWarning(f'{msg}...{further_msg}')
        return self

    def filter(self, exclude=None, include=None, relax=False):
        keys = set(self.keys())
        exclude = set() if exclude is None else set(exclude)
        include = keys if include is None else set(include)
        if not relax:
            if not include.issubset(keys):
                raise ValueError(
                    f"include={include} contains keys not in d={keys}"
                )
            if not exclude.issubset(keys):
                raise ValueError(
                    f"exclude={exclude} contains keys not in d={keys}...use"
                    " relax=True to ignore this error"
                )
            return DotDict({k: self[k] for k in include.difference(exclude)})
        else:
            include = include.intersection(keys)
            exclude = exclude.intersection(include)
            return DotDict(
                {k: self.get(k, None) for k in include.difference(exclude)}
            )


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