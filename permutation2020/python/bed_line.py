"""Parses an individual line in a BED file."""
from collections import namedtuple
import logging

# Initialize a global named tuple to make handling BED lines less awkward
BED_HEADER = ('chrom', 'chromStart', 'chromEnd', 'name',
              'score', 'strand', 'thickStart', 'thickEnd',
              'itemRgb', 'blockCount', 'blockSizes', 'blockStarts')
BedTuple = namedtuple('BedTuple', BED_HEADER)

# initialize module logger
logger = logging.getLogger(__name__)  # module logger

class BedLine(object):
    """The BedLine class parses a single line in a BED file.

    A BED file line is parsed into object attributes within the constructor.
    Genomic positions can also be queried against the BedLine object to retreive
    a relative position along the CDS.

    Example
    -------

        >>> bline_str = "chr3	41240941	41281939	CTNNB1	0	+	41265559	41280833	0	16	220,61,228,254,239,202,145,104,339,159,120,151,122,61,221,630,	0,24570,25075,25503,25883,26209,27757,33890,34078,34688,36273,36898,37137,38565,39683,40368,"
        >>> bed = BedLine(bline_str)
        >>> bed.chrom
        'chr3'
        >>> bed.strand
        '+'
        >>> bed.query_position('+', 'chr3', 41265559)
        0

    """

    def __init__(self, line):
        # make input a list of strings
        if type(line) is str:
            line = line.split('\t')
        elif type(line) is list:
            pass
        else:
            raise ValueError('Expected either a string or a list of strings')

        # bed tuple maintains the orginal data from the bed line
        tmp = dict(zip(BedTuple._fields, line))
        self.bed_tuple = BedTuple(**tmp)

        # convenience attributes
        self.gene_name = self.bed_tuple.name
        self.chrom = self.bed_tuple.chrom
        self.chrom_start = int(self.bed_tuple.chromStart)
        self.strand = self.bed_tuple.strand

        # set exons
        self._init_exons()

    def _filter_utr(self, ex):
        """Filter out UTR regions from the exon list (ie retain only coding regions).

        Coding regions are defined by the thickStart and thickEnd attributes.

        Parameters
        ----------
        ex : list of tuples
            list of exon positions, [(ex1_start, ex1_end), ...]

        Returns
        -------
        filtered_exons : list of tuples
            exons with UTR regions "chopped" out
        """
        # define coding region
        coding_start = int(self.bed_tuple.thickStart)
        coding_end = int(self.bed_tuple.thickEnd)
        if (coding_end - coding_start) < 3:
            # coding regions should have at least one codon, otherwise the
            # region is invalid and does not indicate an actually coding region
            logger.debug('{0} has an invalid coding region specified by thickStart '
                         'and thickEnd (only {1} bps long). This gene is possibly either '
                         'a non-coding transcript or a pseudo gene.'.format(self.gene_name,
                                                                             coding_end-coding_start))
            return []

        filtered_exons = []
        for exon in ex:
            if exon[0] > coding_end and exon[1] > coding_end:
                # exon has no coding region
                pass
            elif exon[0] < coding_start and exon[1] < coding_start:
                # exon has no coding region
                pass
            elif exon[0] <= coding_start and exon[1] >= coding_end:
                # coding region entirely contained within one exon
                filtered_exons.append((coding_start, coding_end))
            elif exon[0] <= coding_start and exon[1] < coding_end:
                # only beginning of exon contains UTR
                filtered_exons.append((coding_start, exon[1]))
            elif exon[0] > coding_start and exon[1] >= coding_end:
                # only end part of exon contains UTR
                filtered_exons.append((exon[0], coding_end))
            elif exon[0] > coding_start and exon[1] < coding_end:
                # entire exon is coding
                filtered_exons.append(exon)
            else:
                # exon is only a UTR
                pass
        return filtered_exons

    def _init_exons(self):
        """Sets a list of position intervals for each exon.

        Only coding regions as defined by thickStart and thickEnd are kept.
        Exons are stored in the self.exons attribute.
        """
        exon_starts = [self.chrom_start + int(s)
                       for s in self.bed_tuple.blockStarts.strip(',').split(',')]
        exon_sizes = map(int, self.bed_tuple.blockSizes.strip(',').split(','))

        # get chromosome intervals
        exons = [(exon_starts[i], exon_starts[i] + exon_sizes[i])
                 for i in range(len(exon_starts))]
        no_utr_exons = self._filter_utr(exons)
        self.exons = no_utr_exons
        self.exon_lens = [e[1] - e[0] for e in self.exons]
        self.num_exons = len(self.exons)
        self.cds_len = sum(self.exon_lens)
        self.five_ss_len = 2*(self.num_exons-1)

    def get_exons(self):
        """Returns the list of exons that have UTR regions filtered out."""
        return self.exons

    def get_num_exons(self):
        """Returns the number of exons (not including UTR exons)."""
        return self.num_exons

    def query_position(self, strand, chr, genome_coord):
        """Provides the relative position on the coding sequence for a given
        genomic position.

        Parameters
        ----------
        chr : str
            chromosome, provided to check validity of query
        genome_coord : int
            0-based position for mutation, actually used to get relative coding pos

        Returns
        -------
        pos : int or None
            position of mutation in coding sequence, returns None if mutation
            does not match region found in self.exons
        """
        # first check if valid
        pos = None  # initialize to invalid pos
        if chr != self.chrom:
            logger.debug('Wrong chromosome queried. You provided {0} but gene is '
                         'on {1}.'.format(chr, self.chrom))
            return pos

        # return position if contained within coding region or splice site
        for i, (estart, eend) in enumerate(self.exons):
            # in coding region
            if estart <= genome_coord < eend:
                prev_lens = sum(self.exon_lens[:i])  # previous exon lengths
                pos = prev_lens + (genome_coord - estart)
                return pos
            # in splice site
            elif (eend <= genome_coord < eend + 2) and i != self.num_exons-1:
                if strand == '+':
                    pos = self.cds_len + 2*i + (genome_coord - eend)
                elif strand == '-':
                    pos = self.cds_len + self.five_ss_len + 2*(self.num_exons-(i+2)) + (genome_coord - eend)
            # in splice site
            elif (estart - 2 <= genome_coord < estart) and i != 0:
                if strand == '-':
                    pos = self.cds_len + 2*(self.num_exons-(i+2)) + (genome_coord - (estart - 2))
                elif strand == '+':
                    pos = self.cds_len + self.five_ss_len + 2*(i-1) + (genome_coord - (estart - 2))

        return pos