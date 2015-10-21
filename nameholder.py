_id = lambda x: x
import collections as _coll
class nameholder(_coll.OrderedDict):
    '''Class that extends dict, with property that __getattr__ is an
    alias for __getitem__. Thus, if nh associates the value 42 to the
    key 'spam', then nh.spam==42 is true. Also requires that all keys
    be strings, and does not distinguish caps.
    
    Also has functionality for interacting with csv module: keys
    inserted after the close() method has been invoked are considered
    'ignorable', and this module's interfaces to the csv module will
    generally not print them.
    '''
    def __init__(self,it=None,_conversions=None,**kwds):
        """Same as dict constructor."""
        super(nameholder,self).__init__()
        self._convs = _coll.defaultdict(lambda: _id)
        if _conversions is not None:
          try: self._convs.update((k.upper(),v) for k,v in _conversions.items())
          except AttributeError: raise TypeError(
           'conversions argument must be a mapping from strings to functions.')
        self._open,self._ignore = True,set()
        self.update(it or [],**kwds)
        if isinstance(it,nameholder):
            self._ignore,self._open = it._ignore,it._open
    def open(self): self._open = True
    def close(self): self._open = False
    @property
    def isopen(self): return self._open
    def __getattr__(self,name):
        """Causes self.attr to be the same as self["attr"]"""
        try:
           if name.isupper(): return self[name]
           else: return self.__getattribute__(name)
        except KeyError: raise AttributeError('attribute %r not found'%name)
    def __setitem__(self,key,value):
        key = key.upper()
        if self._open: self._ignore.discard(key)
        elif key not in self.iterkeys(): self._ignore.add(key)
        super(nameholder,self).__setitem__(key,self._convs[key](value))
    def __getitem__(self,key):
        return super(nameholder,self).__getitem__(key.upper())
    def __delitem__(self,key):
        self._ignore.discard(key); super(nameholder,self).__delitem__(key)
    def __contains__(self,key):
        return super(nameholder,self).__contains__(key.upper())
    def update(self,it=[],**kwds):
        for k,v in list(getattr(it,'items',lambda: it)()) + kwds.items():
            self[k] = v
    def copy(self): return nameholder(self)
    def hide(self,key): 
        key = key.upper()
        if key not in self: raise KeyError('key %r not in dict'%key)
        self._ignore.add(key)
    def show(self,key):
        key = key.upper()
        if key not in self: raise KeyError('key %r not in dict'%key)
        self._ignore.discard(key)
    def fields(self):
        return [f for f in self.iterkeys() if f not in self._ignore]
    def __repr__(self): return "nameholder({})".format(','.join(
                           '{}={!r}'.format(k,v) for k,v in self.iteritems()))

