#! /usr/bin/env python2.7
'''blastextract.py

A script that automates the pipeline between blastn and extract.py. In the
future, this script may automate the role of mafft or some other multiple
alignment program; for now, you must manually run the multiple aligner of your
choice (we recommend ginsi, which ships with mafft) on the output of this
program. This program requires a working installation of BLAST+; see the
accompanying file BLASTHELP for more information on this.

EDIT (Oct 2015):
The "accompanying" file BLASTHELP has been lost, and in the intervening four
years, the author has forgotten what little he knew in the first place. The
curious hacker may consult the BLAST+ home page, whose URL is given below. Note
that this project was developed in summer 2011, so it may rely upon an older
version of BLAST+.

BLAST+ url:
https://blast.ncbi.nlm.nih.gov/Blast.cgi?PAGE_TYPE=BlastDocs&DOC_TYPE=Download
'''

import glob, os, sys, os.path as path, subprocess as proc, argparse as arg
import textwrap, itertools as it, signal
import fasta, classify, extract, utils

def main(args):
    return args.func(args,args.blargs) # args.func can be blast_func,
                                       # extract_func, or ext_from_archive_func

def functionmaker(f):
    def new_f(args,blargs):
        tups = tuple(map(tuple,f(args,blargs)))
        if args.dry_run:
            print pipestr(tups,stdout=args.out,append=args.mode=='a')
            return 0
        with utils.quickopen(args.out,args.mode) as out:
            process = pipe_together(tups,stdout=out,shell=False,bufsize=-1)
            return process.wait()
    return new_f

@functionmaker
def blast_func(args,blargs):
    if args.archive and args.mode=='a': 
        raise CmdLineError('Cannot append to an archive.')
    yield blast_cmd_tup(query=args.query,subject=args.subject,db=args.db,
                        archive=args.archive,*blargs)
    if not args.archive:  yield sed_cmd_tup()

@functionmaker
def extract_func(args,blargs):
    if '-' is args.query:
       raise CmdLineError('Cannot use stdin for query')
    yield blast_cmd_tup(query=args.query,db=args.db,subject=args.subject,
                        archive=False,*blargs)
    yield sed_cmd_tup()
    yield te_extraction_tup(args)
    yield ('cat',args.query,'-')

@functionmaker
def ext_from_archive_func(args,blargs):
    if blargs:
       raise CmdLineError('option {0[0]} not understood'.format(blargs))
    if args.query=='-':
       raise CmdLineError('Cannot use stdin for query')
    yield ('blast_formatter','-outfmt',_std_outfmt,'-archive',args.archive)
    yield sed_cmd_tup()
    yield te_extraction_tup(args)
    if args.query is not None: yield ('cat',args.query,'-')

# should subclass all error classes for here.
class LocalError(Exception):
     errcode = 1

# for errors of command line.
class CmdLineError(LocalError):
     errcode = 2

# when files are not found
class FileNotFoundError(LocalError):
     errcode = 3

_std_outfmt = '10 ' + ' '.join(classify.allflds).lower()
def blast_cmd_tup(query=None,db=None,subject=None,archive=None,*args):
    for x in ('-html','-outfmt'):
       if x in args: 
         raise CmdLineError('cannot request {} with this tool. '.format(x) +
                            'If you need it, use blastn instead.')
    for x in ('-help','-query','-subject','-db'):
        if x in args: 
          raise CmdLineError('{0} option invalid; use -{0} instead'.format(x))
    yield 'blastn'
    yield '-query' ; yield  '-' if query is None else query
    if db is None:
        yield '-subject' ; yield subject
    else:
        yield '-db' ; yield db
    yield '-outfmt' ; yield  '11' if archive else _std_outfmt
    for x in args: yield x

def sed_cmd_tup(input=None):
    yield 'sed' ; yield '1i\\\n{}\n'.format(','.join(classify.allflds))
    if input is not None: yield input
    
def te_extraction_tup(args,input=None):
    if extract.__file__.endswith('.pyc'): yield extract.__file__[:-1]
    else: yield extract.__file__
    for x in ('out','min_distance','min_length','max_overlap',
              'evalue_threshold'):
        val = getattr(args,x)
        if val is not None:
           yield '--{}={}'.format(x.replace('_','-'),val)
    yield '-' if input is None else input

def pipestr(tups,stdout=None,stdin=None,append=False):
    def stringify(s):
        if any(c in s for c in '\n$!\\` "\t'): 
           return "'{}'".format(s.replace("'",r"\'"))
        if any(c in s for c in " \t'"): return '"{}"'.format(s)
        return s
    def maketup(t):
        st = ''
        for w in t:
            newst = st + (st and ' ') + w
            if len(newst) >= 67:
                yield st or newst
                newst = w if st else ''
            st = newst            
        if st: yield st
    tups = [map(stringify,t) for t in tups]
    lines = [' \\\n        '.join(maketup(t)) for t in tups]
    cmdstr = ' | \\\n  '.join(lines)
    if stdin not in (None,'-'): cmdstr += ' < ' + stdin
    if stdout not in (None,'-'): cmdstr += (' >> ' if append else ' > ')+stdout
    return cmdstr

def pipe_together(argtuples,stdout=None,stdin=None,**kwds):
    if not argtuples: raise TypeError('must have at least one tuple for pipe')
    streams = [stdin]
    for n,tup in enumerate(argtuples):
        nosigpipe = tup[0].startswith('python') or tup[0].endswith('.py')
        p = proc.Popen(tup,
                       stdin=streams[-1],
                       stdout=stdout if n+1==len(argtuples) else proc.PIPE,
                       preexec_fn=None if nosigpipe else utils.restoresigpipe,
                       **kwds)
        streams.append(p.stdout)
    return p

# action that checks whether the argument is a valid file
class FileCheckAction(arg.Action):
   def __call__(self,parser,namespace,values,option_string=None):
      if values is not None and values is not '-' and not path.isfile(values):
         raise FileNotFoundError('%r is not a valid file name' % values)
      setattr(namespace,self.dest,values)

def make_parser():
    def doeachparser(parser):
        parser.add_argument('-o','--out',default='-',help='''
          File to which to write output. To write to standard output, give 
          - as the argument to --output; this behavior is the default.''')
        parser.add_argument('-a','--append',action='store_const',const='a',
           dest='mode',default='w',help='''
           If --append is specified, output is added to the output file, as
           opposed to the default behavior of overwriting it.''') 
        parser.add_argument('--dry-run',action='store_true', help='''
               If specified, %(prog)s will print a shell-able version of the
               commands it executes, and then exit. May help users learn to
               use the underlying tools directly.''')
 
    def doblastparser(parser):
        subj = parser.add_mutually_exclusive_group(required=True)
        subj.add_argument('--db',help='''\
          A database containing subject sequences (usually a genome
          sequence) for the blast search. The argument may be a path to
          an existing database (e.g. --db=path/to/dvir); if it is not
          (e.g. --db=dvir), BLAST+ assumes it is a database name and
          tries to figure out where it is, using the $BLASTDB environment
          variable.  This may cause cryptic errors; see the accompanying
          file BLASTDB for some troubleshooting information.''')
        subj.add_argument('-s','--subject',action=FileCheckAction,help='''\
          The subject sequences for the blast search; usually a genome.''')
        parser.add_argument('-q','--query',action=FileCheckAction,help='''\
          The query sequence(s) for the blast search; should be a single
          transposon sequence.''')
        parser.add_argument('blargs',nargs='*',help='''Any unrecognized
            arguments (i.e., those not mentioned elsewhere) are passed
            directly to blastn, allowing the use of options like -penalty or
            -ungapped (type blastn -help for a full list). Note that to avoid
            ambiguity (e.g. %(prog)s may confuse blastn's "-penalty" with
            extract.py's option -p), you should put -- before your blastn args,
            e.g. %(prog)s --db dvir -- -penalty 4''')

    parser = arg.ArgumentParser(formatter_class=arg.RawDescriptionHelpFormatter,
                 description=__doc__ + '''
       
       Type %(prog)s CMD -h to see help for a particular command.''')
    subparsers = parser.add_subparsers()

    blast = subparsers.add_parser('blast',
       description='''Do only a blast search, and postpone the extraction step.
          Output will be a CSV file with a header, or a BLAST archive if the
          --archive option is given. You may give other blast parameters if
          you wish (type blastn -help at the terminal for a full list), as any
          options not recognized by %(prog)s will be given unchanged to
          blastn.''')
    doblastparser(blast)
    blast.add_argument('--archive',action='store_true',help='''
       By default, this command writes as its output a CSV file, treatable
       by extract.py directly. If this option is set, output is instead
       written in a special archive format known as ASN.1, which can be
       inspected separately from the present process using blast_formatter.''')
    doeachparser(blast)
    blast.set_defaults(func=blast_func)

    ext_from_archive = subparsers.add_parser('ar-extract',
       fromfile_prefix_chars='@',
       description='''This command retrieves a blast search from an archive
         file -- i.e. one produced by '%(prog)s blast --archive' or by 
         'blastn -outfmt 11' -- and performs extraction on the results.''')
    doeachparser(ext_from_archive)
    ext_from_archive.add_argument('archive',action=FileCheckAction,
         help="The archive file. Use - to retrieve from stdin.")
    ext_from_archive.add_argument('-q','--query',action=FileCheckAction,
      help='''The query file from which the BLAST search was made. If
         given, this file is prepended to the extraction results, which is
         usually desirable.''')
    extract.makeparser(ext_from_archive)
    ext_from_archive.set_defaults(func=ext_from_archive_func)
    ext_from_archive.set_defaults(blargs=())

    extract_p = subparsers.add_parser('extract',
       fromfile_prefix_chars='@',
       description='''This command pastes together the blast search and the
          transposon extraction. As with '%(prog)s blast', unknown options
          will be passed to blastn, allowing you to give custom parameters
          to your blast search.''')
    doblastparser(extract_p) ; doeachparser(extract_p)
    extract.makeparser(extract_p)
    extract_p.set_defaults(func=extract_func)
    
    return parser

if __name__ == '__main__':
    parser = make_parser()
    try: val = main(parser.parse_args())
    except LocalError as e:
        if not isinstance(e,FileNotFoundError): parser.print_usage(sys.stderr)
        print >>sys.stderr, parser.prog,': error: ', e
        sys.exit(e.errcode)
    else: sys.exit(val)
