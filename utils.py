'''utils.py

A few randomly useful functions and classes, that are broadly enough used
that they belong in a shared module.
'''

import os as _os, collections as _coll, sys as _sys, functools as _func, signal

def quickopen(f_obj='-',mode='r',bufsize=-1):
    '''Flexibly returns a file object. Can take:
    * integers:     interpreted as file-descriptors -> os.fdopen(f_obj,mode,-1)
    * strings:      interpreted as file names       -> open(f_obj,mode)
                    except for '-'                  -> stdin or stdout
    * file objects: returned without change         -> f_obj
    '''
    if mode[0] not in 'rwa':
        raise ValueError('mode must begin with rwa (got %r)'%mode)
    if f_obj is '-': return _sys.stdin if mode[0] is 'r' else _sys.stdout
    if hasattr(f_obj,'read' if mode[0] is 'r' else 'write'): return f_obj
    if isinstance(f_obj,basestring): return open(f_obj,mode,bufsize)
    if isinstance(f_obj,int): return _os.fdopen(f_obj,mode,bufsize)
    raise ValueError(('Could not find appropriate action for mode=%r, '%mode)+
                     'f_obj=%r'%f_obj)

def groupby(seq,key=None):
    '''Returns a dict, whose keys are the return values of key (default:
    the identity function) and whose values are lists, in order, of the
    items from seq matching to that key.
    '''
    d = _coll.defaultdict(list)
    if key is None: key = lambda x: x
    for x in seq: d[key(x)].append(x)
    return dict(d)

def bifilter(seq,key=None):
    '''Returns (T,F), two subsequences (in list form) of seq such that
    key(x) is true for all items in T and false for all items in F.
    Expects that seq not be an infinite sequence.
    '''
    _key = bool if key is None else lambda x: bool(key(x))
    d = groupby(seq,key=_key)
    return d.get(True,[]),d.get(False,[])

def equiv_classes(seq,rel):
    '''Partitions seq according to the equivalence relation rel. Expects the
    following: if rel(x,y) then rel(y,x), and if furthermore rel(y,z), then
    rel(x,z) (i.e. rel is symmetric and transitive).
    '''
    parts = []
    for x in seq:
        try: next(L for L in parts if rel(L[0],x)).append(x)
        except StopIteration: parts.append([x])
    return parts 

def components(iterable,rel):
    '''Performs a breadth-first search of *iterable*, using the graph
    structure implied by *rel*, and returns an iterator over the
    connected components.
    
    More simply put: returns an iterator over lists, which partition the
    original iterable (preserving order), and are maximal with respect to
    the following property (in graph-theory language, "connectedness"):
    
    * for all x,y in L, there's a sequence x=z0,z1,z2, ... ,zn=y such that
      rel(z0,z1), rel(z1,z2), ... are all true.
    
    Expects rel to be reflexive -- rel(x,x) is never false -- and symmetric
    -- if rel(x,y) then rel(y,x). If rel happens to be transitive as well,
    this may be slower than necessary: see equiv_classes().
    '''
    seq,parts = list(iterable),[]
    while seq:
        part,toadd = [],[seq.pop(0)]
        while toadd:
            part.extend(toadd)
            toadd,seq = bifilter(seq,key=lambda x: any(rel(x,y) for y in part))
        yield part

def popmax(seq,key=None):
    '''Removes the largest element of the given list, and returns it.'''
    if not seq: raise ValueError('cannot pop from an empty sequence')
    if key is None: key = lambda x: x
    vi,vk = _func.reduce(lambda v,u: (u if u[1]>v[1] else v),
                   enumerate(map(key,seq)))
    return seq.pop(vi)

def popmin(seq,key=None):
    '''Removes the largest element of the given list, and returns it.'''
    if not seq: raise ValueError('cannot pop from an empty sequence')
    if key is None: key = lambda x: x
    vi,vk = _func.reduce(lambda v,u: (u if u[1]<v[1] else v),
                   enumerate(map(key,seq)))
    return seq.pop(vi)

def restoresigpipe(): signal.signal(signal.SIGPIPE, signal.SIG_DFL)
