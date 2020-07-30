#!/usr/bin/env python

import os
import sys
import gzip


def clean_ids(my_id):
    '''Removes transcript part of <geneid>.<transcript> if exists'''
    new_id = '.'.join(my_id.split('.')[:-1])
    return new_id


def un_yukify(my_id):
    '''Removes upstream DS information from fully qualified gene names

       ex: glyma.Wm82.gnm1.ann1.Glyma16g30815

       becomes: Glyma16g30815
    '''
    new_id = '.'.join(my_id.split('.')[4:])
    return new_id


def parse_pansets(dataset):
    '''Parses hsh.tsv.gz file for gene assignment'''
    genes = {}
    with gzip.open(dataset, mode="rt") as fopen:
        for line in fopen:
            line = line.rstrip()
            if line.startswith('#') or not line:
                continue
            (panset, transcript) = line.split('\t')
            gene = clean_ids(transcript)
            short_name = un_yukify(gene)
            if not gene in genes:
                genes[gene] = []
            if not short_name in genes:
                genes[short_name] = []
            if panset not in genes[gene]:
                genes[gene].append(panset)
            if panset not in genes[short_name]:
                genes[short_name].append(panset)
    return genes


def parse_clusters(dataset):
    '''Parses clust.tsv.gz file for pan set assignment'''
    pansets = {}
    with gzip.open(dataset, mode="rt") as fopen:
        for line in fopen:
            line = line.rstrip()
            if line.startswith('#') or not line:
                continue
            panset = line.split('\t')[0]
            pansets[panset] = [ clean_ids(t) for t in line.split('\t')[1:]]
    return pansets


def main():
    '''Main runtime for import

       Needs to be expanded to db access to scale
    '''
    my_datasets = ['glysp.mixed.pan2.TV81']
    dataset_dir = './panparser'
    datasets = {}
    for d in my_datasets:
        my_hsh = f'{os.path.abspath(dataset_dir)}/{d}.hsh.tsv.gz'
        my_clust = f'{os.path.abspath(dataset_dir)}/{d}.clust.tsv.gz'
        pansets = parse_pansets(my_hsh)  # get pansets from files
        clusters = parse_clusters(my_clust)  # get clusters from files
        datasets[d] = {'pansets': pansets, 'clusters': clusters}
    return datasets


if __name__ == '__main__':
    main()

