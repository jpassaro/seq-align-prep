from nameholder import nameholder
try: from cStringIO import StringIO
except ImportError: from StringIO import StringIO
import collections as _coll, contextlib as _cont, itertools as _it
import operator as _op, re as _re, sys as _sys
from future_builtins import map

class Error(Exception): pass
class FastaParseError(Error): 
    def __init__(self,msg,line,lineno,file):
      arg = 'Bad fasta file {f!r} at line {no:d}: {msg}. Problem line:\n{line}'
      arg = arg.format(f=file,no=lineno,msg=msg,line=line)
      super(FastaParseError,self).__init__(arg)
class FastaAttrError(Error): pass

_consts = ['RAW','BASIC','FULL']
exec('[%s] = range(%d)'%(','.join(_consts),len(_consts)))

_locpattern,_id = _re.compile(r'([^:.]+):(\d+)..(\d+)'),lambda x: x
class locus:
    def __init__(self,src,start=None,end=None):
      msg = 'locus must be initialized by a string of the form ' + \
            '<id>:<start>..<end> or by a tuple (id,start,end). (%s)'
      if isinstance(src,locus):
           self.id,self.start,self.end = src.id,src.start,src.end ; return
      if not isinstance(src,basestring):
          raise TypeError(msg%('got %r as first argument'%src))
      if start is not None or end is not None:
          if not all(isinstance(x,int) for x in (start,end)):
              raise TypeError(msg%('bad start (%r) or end (%r)'%(start,end)))
          self.id,self.start,self.end = src,start,end ; return
      match = _locpattern.match(src)
      if match is None: raise Error(msg%('bad string %r'%src))
      self.id = match.group(1)
      self.start,self.end = int(match.group(2)),int(match.group(3))
    def __str__(self): return '{0.id}:{0.start}..{0.end}'.format(self)
    def __repr__(self): return 'locus({})'.format(self)
_prop_pattern = _re.compile(r'([^=;]+)=([^=;]+);$')
_convs = dict(loc=locus,length=int)
class seq_entry(nameholder):
    def __init__(self,src,parse_fully=False):
        super(seq_entry,self).__init__(_conversions=_convs)
        err = 'seq_entry must be initialized with mapping type, sequence of' +\
              ' key-value pairs, or fasta-style string'
        if isinstance(src,_coll.Mapping):
           if not ('NAME' in src and 'SEQ' in src): raise Error(
               'sequence entry must have at least NAME and SEQ fields defined')
           self.update(((k,src[k]) for k in src.fields())
                       if hasattr(src,'fields') else src)
           return
        elif not isinstance(src,basestring):
            if not hasattr(src,'__iter__'):
                raise Error(err+' (got %r)'%type(src))
            src = list(src)
            if not all(isinstance(x,tuple) and len(x)==2 and
                       isinstance(x[0],basestring) for x in src): raise Error(
                   err + '; not all sequence items are proper pairs')
            self.update(src)
            return
        lines = src.split('\n')
        title = lines.pop(0)
        assert(title.startswith('>'))
        title = title[1:]
        if not parse_fully:
          self.update([('NAME',title),('SEQ',''.join(lines))])
          return
        props = title.split()
        name = props.pop(0)
        mlist = list(map(_prop_pattern.match,props))
        if None in mlist: raise FastaAttrError(props[mlist.index(None)])
        self['NAME'] = name
        self.update((m.group(1),m.group(2)) for m in mlist)
        self['SEQ'] = ''.join(lines)
        self._str = {}
    def copy(self):  return seq_entry(self)
    def writeto(self,f,parse=BASIC,endline='\n',line_width=80):
        f.write('>'+self.NAME)
        if parse==FULL: f.write(' '+' '.join('{}={};'.format(k.lower(),self[k])
                for k in self.fields() if k != 'NAME' and 'SEQ' not in k))
        f.write(endline)
        if not self.SEQ: return
        for n,c in enumerate(self.SEQ,1):
            f.write(c + (endline if n%line_width==0 else ''))
        if n%line_width!=0: f.write(endline)
    def tostring(parse=BASIC,endline='\n',line_width=80):
        if parse not in self._str:
            with _cont.closing(StringIO()) as f:
                self.writeto(f,parse,endline,line_width)
                self._str[parse] = f.getvalue()
        return self._str[parse]
    def __repr__(self): return "seq_entry(name={0.NAME},seq={1})".format(
                 self , self.SEQ if len(self.SEQ)<20 else self.SEQ[:15]+'...')
def _myopen_r(fname): return _sys.stdin if fname=='-' else open(fname,'rU')
def _myopen_a(fname): return _sys.stdout if fname=='-' else open(fname,'a')
def _myopen_w(fname): return _sys.stdout if fname=='-' else open(fname,'w')
_funcs = _coll.OrderedDict().fromkeys('rwasf') # to list elts in correct order
_funcs.update(r=_myopen_r, w=_myopen_w, a=_myopen_a, f=_id,
              s=(lambda x: (StringIO(x) if x else StringIO())))
_names = _coll.OrderedDict((s,_id) for s in 'rwa')
_names['s'],_names['f'] = lambda x: '<string obj>',_op.attrgetter('name')

class fasta:
    def _err(self,msg): raise FastaParseError(msg=msg,line=self._line,
                                   file=self._name,lineno=self._lineno)
    def __init__(self,src=None,mode=None,parse=BASIC,line_width=80):
        if parse not in (RAW,BASIC,FULL): raise Error(
          '"parse" arg must be RAW, BASIC or FULL (got {!r})'.format(parse))
        if mode is None:
           if src is None: mode = 's'
           elif any(hasattr(src,x) for x in ('write','read')): mode = 'f'
           elif isinstance(src,basestring): mode = 'r'
           else: raise TypeError(
                   'requires a filename or file object (got {!r})'.format(src))
        if mode[0] not in _funcs: raise Error("'mode' arg must begin with " +
            ', '.join(map(repr,_funcs)) + ' (got %r)'%mode)
        self._f,self._mode,self._parse = _funcs[mode[0]](src),mode,parse
        self._line,self._name,self._lineno = None,_names[mode[0]](src),0
        self._line_width = line_width
    def _getline(self):
        self._line = next(self._f,'')
        self._lineno += bool(self._line)
    def readentry(self):
        if self._line is None: self._getline()
        if not self._line: return None
        if not self._line.startswith('>'):
            self._err('expect first line of fasta sequence to begin with ">"')
        with _cont.closing(StringIO()) as buf:
            buf.write(self._line)
            self._getline()
            while self._line and not self._line.startswith('>'):
                if ' ' in self._line: self._err('non-title line has space')
                buf.write(self._line)
                self._getline()
            try: return seq_entry(buf.getvalue(),parse_fully=self._parse==FULL)
            except FastaAttrError as e: self._err(
              'expect all attributes in title line to have form "key=value;".')
    def next(self): 
        val = self.readentry()
        if val is None: raise StopIteration
        return val

    def __iter__(self): return self
    def readentries(self): return list(self)
    def flush(self): return self._f.flush()
    def close(self): return self._f.close()
    def __enter__(self): return self
    def __exit__(self,type,value,traceback): return self.close()
    def __repr__(self): return \
     "<{2} fasta file {0._name!r}, mode {0._mode!r} at {1:#x}>".format(
         self,id(self),'closed' if self._f.closed else 'open')

    def writeentry(self,entry,**kwds):
        for kwd in ('parse','line_width'):
           if kwds.get(kwd) is None: kwds[kwd] = getattr(self,'_'+kwd)
        if kwds['parse'] == RAW: self._f.write(entry)
        elif kwds['parse'] in (BASIC,FULL):
            if not isinstance(entry,seq_entry): raise TypeError(
                  'can only write items of seq_entry type (got %r)'%entry)
            entry.writeto(self._f,**kwds)
        else: raise ValueError('"parse" arg must be RAW, BASIC or FULL ' +
                          '(got {!r})'.format(kwds['parse']))
    def writeentries(self,entries,parse=None):
        for e in entries: self.writeentry(e,parse=parse)

def quick_entry(name,seq,parse_fully=False):
    return fasta.seq_entry(dict(NAME=name,SEQ=seq),parse_fully)
