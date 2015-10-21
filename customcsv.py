#! /usr/bin/env python2.7
import csv as _csv, os.path as _path, sys as _sys, os as _os, utils
from nameholder import nameholder
[PROMPT,FORCE,DONT_OVER,DONT_ALL] = range(4)
[GETALL,IGNORE,DELETE] = range(3)

class Error(Exception):
    """Special exception class thrown by functions in this module."""
    def __init__(self,*args): Exception.__init__(self,*args)
    def __hash__(self): return hash(tuple(self.items()))
_dialects = { '.csv': 'excel', '.txt': 'excel-tab' }

def parseHeaderedCSV(fname,header=None,intflds=[],fltflds=[],
                     txtflds=[],delim=None,**kwds):
    '''Converts a csv file, with a header line, to a sequence of
    nameholder objects, with keys corresponding to the fields in the
    header line. This is a generator function (i.e. returns an iterator).
    
    *intflds*, *fltflds*, and *txtflds*, if specified, are sequences of
    strings which are required to appear as field names (i.e. as fields
    of the header). A key's presence in *fltflds* signal that its value
    should be converted to a float; similarly, the value for a key in 
    *intfields* will be converted to a long.
    
    Additional keywords may be specified. If KEY=CONV is included among
    the arguments, then the converter function CONV will be applied to
    records in the field KEY; additionally, similarly to txtfields and
    others, the function will fail if a user-specified key is not found
    in the header line. User-specified conversions take precedence over
    float conversions, which in turn take precedence over long
    conversions.
    
    *header*, if specified, should be a sequence of labels corresponding
    to the columns of the file. If omitted, this function assumes the
    first line of the file is a header line; otherwise, that line is taken
    to be data.
    '''
    def check(header):
        head = header
        header = map(str.upper,header)
        missingfields = [nm for nm in conversions if nm not in header]
        if missingfields: raise Error(('Required fields ({}) not found in ' +
                      'file {!r}; detected fields {} instead.').format(
                          ', '.join(missingfields), fname, ', '.join(head)))
        return header
    def yieldable(tup,lineno,f):
        if len(tup) != len(header): raise Error( 
            'line %d in file %s does not match header:'%(lineno,f.name) +
            delim.join(header) + '\n' + delim.join(tup))
        try: r = nameholder(zip(header,tup),_conversions=conversions)
        except ValueError: raise Error('Conversion error at line %d'%lineno + 
           ', file %r' % f.name)
        r.close() ; return r
    conversions = dict((x,str) for x in txtflds)
    conversions.update((x,int) for x in intflds)
    conversions.update((x,float) for x in fltflds)
    conversions.update(kwds) # user-defined types / conversion functions
    if header is not None: header = check(header)
    with utils.quickopen(fname,'r') as f:
        try: s = next(f).rstrip()
        except StopIteration: return # indicates file was empty
        if delim is None:
           for delim in ',\t':
               s_s = s.split(delim)
               if len(s_s) > 1: break
           else: raise Error('First line of file %r improperly '%fname +
            'improperly formatted: must be comma-separated or tab-delimited\n'+
            'problem line: %r'%s)
        else:
            s_s = s.split(delim)
            names = {'\t':'tabs', ',':'commas'}
            if len(s_s)==1: raise Error('First line of file %r' %fname +
             'improperly formatted: expected fields delimited by ' +
             names.get(delim,delim) + '\nproblem line: %r'%s)
        if header is None: header = check(s_s)
        else: yield yieldable(s_s,1,f)
        for line,rec in enumerate(f,2):
            yield yieldable(rec.rstrip().split(delim),line,f)

def writetocsv(seq,outname,overwrite):
    '''Takes a sequence of nameholder records and writes them to the specified
    output file. The 'overwrite' parameter specifies how to handle a filename
    that already exists; also, if overwrite is equal to DONT_ALL, function
    returns immediately.

    Return value: 1 if a file was written, 0 if not.'''

    if overwrite==DONT_ALL or not seq: return 0
    fields = seq[0].fields() ; S = set(fields)
    assert(all(set(s.fields()) == S for s in seq[1:]))
    if _path.exists(outname):
        if not _path.isfile(outname):
            print >>_sys.stderr, _sys.argv[0]+': warning: file ',
            print >>_sys.stderr, outname, 'exists, caused a problem. skipping.'
        if overwrite==DONT_OVER or (overwrite==PROMPT and \
          raw_input('\nOverwrite file {!r}? (y/n) '.format(outname)) in 'nN'):
             return 0
    dirname = _path.dirname(outname)
    if not _path.exists(dirname): _os.mkdir(dirname)
    with open(outname,'ab') as out:
        wr = _csv.DictWriter(out,fields,extrasaction='ignore')
        wr.writeheader()
        wr.writerows(seq)
    return 1

