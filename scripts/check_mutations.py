#!/usr/bin/env python
"""This scripts checks whether mutations are specified correctly.

Specifically, this script tests mutations to check whether they are
reported as being on the positive strand or on the coding strand.
"""
# fix problems with pythons terrible import system
import os
import sys
file_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(os.path.join(file_dir, '../src/python'))

# actually important imports
import utils
import pysam
import pandas as pd
import argparse
import logging
import datetime

logger = logging.getLogger(__name__)  # module logger

def start_logging(log_file='', log_level='INFO'):
    """Start logging information into the log directory.

    If os.devnull is specified as the log_file then the log file will
    not actually be written to a file.
    """

    if not log_file:
        # create log directory if it doesn't exist
        file_dir = os.path.dirname(os.path.realpath(__file__))
        log_dir = os.path.join(file_dir, '../log/')
        if not os.path.isdir(log_dir):
            os.mkdir(log_dir)

        # path to new log file
        log_file = log_dir + 'log.run.' + str(datetime.datetime.now()).replace(':', '.') + '.txt'

    # logger options
    lvl = logging.DEBUG if log_level.upper() == 'DEBUG' else logging.INFO
    myformat = '%(asctime)s - %(name)s - %(levelname)s \n>>>  %(message)s'

    # create logger
    if not log_file == 'stdout':
        # normal logging to a regular file
        logging.basicConfig(level=lvl,
                            format=myformat,
                            filename=log_file,
                            filemode='w')
    else:
        # logging to stdout
        root = logging.getLogger()
        root.setLevel(lvl)
        stdout_stream = logging.StreamHandler(sys.stdout)
        stdout_stream.setLevel(lvl)
        formatter = logging.Formatter(myformat)
        stdout_stream.setFormatter(formatter)
        root.addHandler(stdout_stream)
        root.propagate = True


def parse_arguments():
    info = 'Extracts gene sequences from a genomic FASTA file'
    parser = argparse.ArgumentParser(description=info)

    # logging arguments
    parser.add_argument('-ll', '--log-level',
                        type=str,
                        action='store',
                        default='',
                        help='Write a log file (--log-level=DEBUG for debug mode, '
                        '--log-level=INFO for info mode)')
    parser.add_argument('-l', '--log',
                        type=str,
                        action='store',
                        default='stdout',
                        help='Path to log file. (Default: stdout)')

    # program arguments
    help_str = 'Human genome FASTA file'
    parser.add_argument('-f', '--fasta',
                        type=str, required=True,
                        help=help_str)
    help_str = 'Text file specifying mutations in the format required for permutation test'
    parser.add_argument('-m', '--mutations',
                        type=str, required=True,
                        help=help_str)
    args = parser.parse_args()

    # handle logging
    if args.log_level or args.log:
        if args.log:
            log_file = args.log
        else:
            log_file = ''  # auto-name the log file
    else:
        log_file = os.devnull
    log_level = args.log_level
    start_logging(log_file=log_file,
                  log_level=log_level)  # start logging

    return vars(args)


def detect_coordinates(mut_df, genome_fa):
    # detect problems with using 0-based coordinates
    zero_len_count = 0
    num_snv = 0
    matching_ref = [0, 0]
    matching_pair = [0, 0]
    for ix, row in mut_df.iterrows():
        if (row['End_Position'] - row['Start_Position']) == 0:
            zero_len_count += 1
        no_shift_seq = genome_fa.fetch(reference=row['Chromosome'],
                                       start=row['Start_Position'],
                                       end=row['End_Position'])
        minus_1_seq = genome_fa.fetch(reference=row['Chromosome'],
                                      start=row['Start_Position']-1,
                                      end=row['End_Position'])
        seqs = [minus_1_seq, no_shift_seq]

        if len(row['Reference_Allele']) == 1 and row['Reference_Allele'] != '-':
            num_snv += 1

        for i in range(len(seqs)):
            if seqs[i].upper() == row['Reference_Allele'].upper() and len(row['Reference_Allele']) == 1:
                matching_ref[i] += 1
            elif seqs[i].upper() == utils.rev_comp(row['Reference_Allele']).upper() and len(row['Reference_Allele']) == 0:
                matching_pair[i] += 1

    # return coordinate type
    num_mut = len(mut_df)
    zero_len_pct = zero_len_count / float(num_mut)
    matching_pair_pct = map(lambda x: x / float(num_snv), matching_pair)
    matching_pct = map(lambda x: x / float(num_snv), matching_ref)
    logger.info('{0} of {1} tested mutations had zero length'.format(zero_len_pct, num_mut))
    logger.info('{0} of {1} did match the + strand reference genome'.format(matching_pct, num_snv))
    logger.info('{0} of {1} did match the - strand reference genome'.format(matching_pair_pct, num_snv))
    if zero_len_pct > .3:
        logger.info('1-based coordinate system likely used.')
        if matching_pair_pct[1] > .25:
            logger.info('Mutations likely reported on the genes\'s coding strand')
            return 1, 'coding'
        else:
            logger.info('Mutations likely reported on the genes\'s + strand')
            return 1, '+'
    elif (matching_ref[0] + matching_pair[0]) > (matching_ref[1] + matching_pair[1]):
        logger.info('0-based coordinate system likely used.')
        if matching_pair_pct[1] > .25:
            logger.info('Mutations likely reported on the genes\'s coding strand')
            return 0, 'coding'
        else:
            logger.info('Mutations likely reported on the genes\'s + strand')
            return 0, '+'
    else:
        logger.info('1-based coordinate system likely used.')
        if matching_pair_pct[1] > .25:
            logger.info('Mutations likely reported on the genes\'s coding strand')
            return 1, 'coding'
        else:
            logger.info('Mutations likely reported on the genes\'s + strand')
            return 1, '+'


def main(opts):
    # read in mutations
    mut_df = pd.read_csv(opts['mutations'], sep='\t')

    # read genome fasta file
    genome_fa = pysam.Fastafile(opts['fasta'])

    coord_base, coord_strand = detect_coordinates(mut_df, genome_fa)
    logger.info('RESULT: {0}-based coordinates, positions reported on {1} strand'.format(coord_base, coord_strand))

    genome_fa.close()


if __name__ == "__main__":
    opts = parse_arguments()
    main(opts)