#! /usr/bin/env python2.7 -3
__doc__ = '''
extract.py

This script implements the "transposon phylogeny extraction scheme".
As input, it takes the result of a blast search for one or several
transposons against a single fly genome, and it writes for each one
a fasta file suitable for multiple alignment. The currently supported
format for input is tab-delimited or comma-separated values (e.g. by
using -outfmt 6 or -outfmt 10 with blastn or blast_formatter) contained
in any number of files. The files must each have a header that labels
the data, which must include the following fields (in any order,
uppercase or lowercase):

[FIELDS_GO_HERE]

A companion utility is available that links this utility directly to
BLAST, without any need for your interaction: see blastextract.py in
this file.
'''

defaults = { 'max_overlap' : (int,1), 'min_distance' : (int,5000),
             'min_length' : (int,-1), 'evalue_threshold': (float,0.0) }

def maybeint(x): return x if x is None else int(x)

import classify, argparse, sys, fasta, itertools as it, os
__doc__ = __doc__.replace('[FIELDS_GO_HERE]', ', '.join(classify.allflds))

def makeparser(parser=None):
  if parser is None:
    parser = argparse.ArgumentParser(description=__doc__,
                         formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-o','--out',default='-',help='''\
      Output file name. Use '-' to output to stdout; this is the default.
      NOTE: If the input contains more than one transposon, their output
      will be written to separate files (e.g., 'penelope.fna') and this
      argument will be ignored.''')
    parser.add_argument('file',help='''\
      Input file name; should be a csv file whose lines correspond to BLAST
      hits, and including the fields QSTART, QEND, SSTART, SEND, and EVALUE.
      Use '-' to read the file from stdin. This argument is required.''')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-a','--append',dest='mode',action='store_const',
      help='''Triggers append mode: if the output file already exists, data is
      appended to it.''',const='a')
    group.add_argument('-w','--overwrite',action='store_const',help='''
      Triggers overwrite mode: if the output file already exists, the program
      replaces it. This is the default behavior.''',const='w',dest='mode')
    parser.set_defaults(mode='w')
  parser.add_argument('-d','--min-distance',help='''
        Minimum distance between islands - in other words, if two fragments
        are any closer than this in their subject ordinates, they will be
        part of the same island. Defaults to {}. The
        larger this value, the more the effects of this program: if set to
        0, for instance, the only islands will be nests and every fragment
        will go on a separate line.'''.format(defaults['min_distance']))
  parser.add_argument('-e','--evalue-threshold', help='''\
        Maximum evalue; hits with a higher evalue will be ignored. If
        omitted, no threshold will be enforced. In practice, this option
        and --min-length may have redundant effects, and this one is
        probably more biologically meaningful.''')
  parser.add_argument('-l','--min-length',help='''
        Minimum length; hits in a nest that are shorter will be excluded.
        If omitted, no minimum will be enforced. In either case, no minimum
        will apply for hits outside of nests. Note: given the right argument
        for --evalue-threshold, this argument may be redundant.''')
  parser.add_argument('-p','--max-overlap',help='''\
        Overlap threshold between blast hits (in the subject sequence) -
        i.e. if two hits have an overlap by at least this many base pairs,
        they are part of a nest. If this option is omitted, any overlap
        whatever will trigger a nest relationship, while specifying a
        higher number allows insignificant overlaps to be ignored.''')
  return parser

if __name__=='__main__' and not sys.flags.interactive:
    parser = makeparser()
    args = parser.parse_args()
    if 0 in (args.max_overlap,args.min_distance,args.min_length):
        parser.print_usage()
        sys.exit(parser.prog+': error: 0 not a valid arg')
    for k,(T,v) in defaults.iteritems():
        given = getattr(args,k)
        try: setattr(args,k,v if given is None else T(given))
        except ValueError:
            parser.print_usage()
            sys.exit('{}: error: bad type for --{} (got {})'.format(
                                   parser.prog,k.replace('_','-'),given))
    with fasta.fasta(args.out,args.mode) as out:
        classify.full_transposon_treatment(
             seq = classify.hitsfromcsv(args.file),
             overlap = args.max_overlap,
             gap = args.min_distance,
             minlength = args.min_length,
             evalue = args.evalue_threshold,
             fastaout = out
        )
