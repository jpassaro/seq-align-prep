# seq-align-prep
A tool for preparing bioinformatic input for a multiple-sequence alignment.

## Purpose

In brief, it is written for somebody looking to run a multiple-alignment
of different instances of a transposon in a genome. It uses BLAST+ to
identify said instances, it assembles them into "connected" sections within
the genome, and it presents them in a sort of pre-aligned version to make
the multi-aligner's job easier.

## Acknowledgments

This code was written for Professor Justin Blumenstiel's lab at the University
of Kansas; it was designed with his constant input. The work was funded, to the
best of my recollection, by an NSF grant. My gratitude to Prof.  Blumenstiel,
the NSF, and the University of Kansas for the opportunity to work on this.

## Terms

This code is released under the terms of the GNU Public License version 2. See
LICENSE for specific terms.

## References

* Blumenstiel Lab: http://eeb.ku.edu/justin-blumenstiel
* BLAST+: https://blast.ncbi.nlm.nih.gov/Blast.cgi?PAGE_TYPE=BlastDocs&DOC_TYPE=Download
