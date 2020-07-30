#!/usr/bin/env python

import os, sys
import string
import subprocess
import logging
import argparse
import simplejson as json
import re
import datetime
import gzip
from neo4j.v1 import GraphDatabase, basic_auth
import summary_tools.FastaMetrics as fmetrics
import summary_tools.FeatureCounts as fcounts
from summary_tools.fstools import create_directories, check_file, return_json
from glob import glob

parser = argparse.ArgumentParser(description='''

    Neo4j Loader and Object Creator for Summary Portal Testing

''', formatter_class=argparse.RawTextHelpFormatter)
#Parser
parser.add_argument('--fileobject', metavar = '<object.json>',
help='''Object to load.  JSON Format required!\n\n
Populate config files using --new_config\n\n''')
parser.add_argument('--production', action='store_true',
help='''Swaps driver to a wright facing connection.''')
parser.add_argument('--fofn', metavar = '<objects.txt>',
help='''File of object files to load.  Please provide full paths\n\n''')
parser.add_argument('--new_config', action='store_true',
help='''For minimum requirements please see "PUT MY REPO DOC.MD URL HERE."''')
parser.add_argument('--generate_counts', action='store_true',
help='''Set to generate counts data for object.''')
parser.add_argument('--infile', metavar='<my_file.<fasta|gff>>',
help='''File to generate counts data for.''')
parser.add_argument('--filename',
help='''Name of file object.''')
parser.add_argument('--filetype',
help='''File type of file object.''')
parser.add_argument('--canonical_type',
help='''Canonical type of file object.''')
parser.add_argument('--url',
help='''URL of file object.''')
parser.add_argument('--genus',
help='''Genus of object.''')
parser.add_argument('--species',
help='''Species of file object.''')
parser.add_argument('--infraspecies',
help='''Infraspecies of file object.''')
parser.add_argument('--origin', metavar='<file_origin>', default='UKNOWN',
help='''Origin of file object, ex:LIS, PB, Cyverse, w/e...''')
parser.add_argument('--derived_from', metavar = '<name1 ... nameN>', nargs='+',
help='''Object names this file was derived from.''')


parser._optionals.title = "Program Options"
args = parser.parse_args()
#Logging
msg_format = '%(asctime)s|%(name)s|[%(levelname)s]: %(message)s'
logging.basicConfig(format=msg_format, datefmt='%m-%d %H:%M',
                    level=logging.DEBUG)
log_handler = logging.StreamHandler()
formatter = logging.Formatter(msg_format)
log_handler.setFormatter(formatter)
logger = logging.getLogger('censor_graph_loader')
logger.addHandler(log_handler)

fmetrics = fmetrics.FastaMetrics(logger)
fcounts = fcounts.FeatureCounts(logger)

DATA_OBJECT = {'filename' : '',
               'filetype' : '',
               'url' : '',
               'counts' : '',
               'genus' : '',
               'species' : '',
               'origin' : '',
               'infraspecies' : '',
               'derived_from' : []}

REPORT_STATS = {'N50', 'allbases', 'gapbases', 'gaps', 'contigs', 'scaffolds',
                'records'}


def connect_neo4j():
    host = '//0.0.0.0'
    port = 7687
    auth = 'neo4j'
    pswd = 'neo4j'
    bolt = 'bolt:{}:{}'.format(host, port)
    driver = GraphDatabase.driver(bolt, auth=basic_auth(auth, pswd))
    logger.info('connection succeeded, driver:{}'.format(driver))
    return driver


def connect_neo4j_wright():
    '''Connection object for wright to upload production data after testing'''
    host = '//wright'
    port = 7687
    auth = 'censor'
    pswd = 'CensorMe123'
    bolt = 'bolt:{}:{}'.format(host, port)
    driver = GraphDatabase.driver(bolt, auth=basic_auth(auth, pswd))
    logger.info('connection succeeded, driver:{}'.format(driver))
    return driver


def log_me(level, msg, log):
    if not log:
        print('No Logger object\n')
        sys.exit(1)
    stream = getattr(log, level.lower())
    stream(msg)


def fasta_metrics(fasta):
    logger.info('Generating FASTA metrics for {}...'.format(fasta))
    fmetrics.generate_metrics(fasta)
    return fmetrics.metrics


def gff_features(gff):
    logger.info('Counting GFF features for {}...'.format(gff))
    fcounts.count_gff_features(gff)
    return fcounts.gff_counts


def generate_new_config():
    if (not (args.filename and args.filetype and args.url
                           and args.genus and args.species and args.canonical_type)): # Required
        msg = ('--filename, --filetype, --genus, --species, --canonical_type and --url ' +
               'required for new config object')
        log_me('error', msg, logger)
        sys.exit(1)
    fname = args.filename
    ftype = args.filetype.lower() # set lower for ez standard
    canonical_type = args.canonical_type
    genus = args.genus.lower()
    species = args.species.lower()
    infraspecies = args.infraspecies
    url = args.url
    origin = args.origin
    der_from = args.derived_from # object names this object is derived from
    new_config = DATA_OBJECT # set to global object
    new_config['counts'] = None
    if args.generate_counts: # if counts wanted
        f_in = args.infile
        if not check_file(f_in):
            msg = 'Could not find {}!'.format(f_in)
            log_me('error', msg, logger)
            sys.exit(1)
        if ftype == 'gff' or ftype == 'gff3':
            ftype = 'gff'
            new_config['counts'] = gff_features(f_in) # get counts gff
        elif ftype == 'fasta' or ftype == 'fa' or ftype == 'fna':
            ftype = 'fasta'
            new_config['counts'] = fasta_metrics(f_in) # get counts fasta
        elif ftype == 'mrk':
            ftype = 'mrk'
            new_config['counts'] = gff_features(f_in) # get counts for markers
        
    object_out = './{}_node.json'.format(fname)
    msg = 'creating new config {}'.format(object_out)
    log_me('info', msg, logger)
    new_config['filename'] = fname  # populate object
    new_config['filetype'] = ftype
    new_config['canonical_type'] = canonical_type
    new_config['url'] = url
    new_config['genus'] = genus
    new_config['species'] = species
    new_config['infraspecies'] = infraspecies
    new_config['origin'] = origin
    new_config['derived_from'] = der_from
    new_config['child_of'] = der_from
    fout = open(object_out, 'w')
    fout.write(json.dumps(new_config)) # write object
    msg = 'Finished.  Run --object or --fofn to load.'
    log_me('info', msg, logger)


def load_config_object(obj, driver):
    msg = 'Adding new file object {}'.format(obj['filename'])
    statement = ('MERGE (a:{}:{}:{}:{}:{}'.format(obj['filetype'], obj['genus'],
                          obj['species'], obj['origin'], obj['canonical_type'])+
                 ' {name:{filename}, genus:{genus}, species:{species}' + 
                 ', url:{url}, filetype:{filetype}, origin:{origin}' +
                 ', canonical_type:{canonical_type}')
#    if obj.get('counts', None):
#        statement += ', counts:{path}'
#        if obj['filetype'] == 'fasta' or obj['filetype'] == 'assembly':
#            obj['sequences'] = obj['counts'].get('records', 0)
#            obj['contigs'] = obj['counts'].get('contigs', 0)
#            obj['scaffolds'] = obj['counts'].get('scaffolds', 0)
#            obj['N50'] = obj['counts'].get('N50', 0)
#            obj['totalbases'] = obj['counts'].get('allbases', 0)
#            obj['gapbases'] = obj['counts'].get('gapbases', 0)
#            statement += (' {sequences:{sequences}, contigs:{contigs}' +
#                          ', scaffolds:{scaffolds}, N50:{N50}' + 
#                          ', totalbases:{totalbases}, gapbases{gapbases}}')
#        elif obj['filetype'] == 'gff' or obj['filetype'] == 'annotation':
    if obj.get('infraspecies', ''):
        statement += ', infraspecies:{infraspecies}'
    for f in obj.get('counts', {}):
        if obj['filetype'] == 'fasta' and not f in REPORT_STATS:
            continue
        obj[f] = obj['counts'][f]
        statement += ', {0}:{{{0}}}'.format(f)
    for f in obj.get('busco', {}):
        obj[f] = obj['busco'][f]
        statement += ', {0}:{{{0}}}'.format(f)
    statement += '}) RETURN a.name, labels(a)'
    with driver.session() as session:
        for r in session.run(statement, obj):
            name = r['a.name']
            print(name)
        if obj.get('derived_from'):
            for d in obj['derived_from']:
                params = {'derived_from' : d, 'filename' : obj['filename']}
                statement = ('MATCH (a), (b)' +
                             " WHERE a.name = '{}' and b.name = '{}'".format(
                                                              d,
                                                              obj['filename']) +
                             ' MERGE (b)-[r:DERIVED_FROM]->(a)' + 
                             ' RETURN type(r)')
                for r in session.run(statement):
                    print(r)
        if obj.get('child_of'):
            for c in obj['child_of']:
                params = {'child_of': c, 'filename': obj['filename']}
                statement = ('MATCH (a), (b)' +
                             " WHERE a.name = '{}' and b.name = '{}'".format(
                                                              c,
                                                              obj['filename']) +
                             ' MERGE (b)-[r:CHILD_OF]->(a)' + 
                             ' RETURN type(r)')
                for r in session.run(statement):
                    print(r)

    return True


if __name__ == '__main__':
    if not (args.fofn or args.fileobject or args.new_config):
        msg = 'config object or new_config argument must be provided\n'
        log_me('error', msg, logger)
        sys.exit(1)
    if args.new_config:
       generate_new_config() # generate new config object, see method
       sys.exit(0)
    driver = False
    if args.production:
        driver = connect_neo4j_wright()
    else:
        driver = connect_neo4j()
    config_obj = return_json(args.fileobject) # get json object from config
    config_obj['path'] = os.path.abspath(args.fileobject)
    if not config_obj.get('counts', []):
        config_obj['counts'] = [] # set to allow for empty iterator
    if not load_config_object(config_obj, driver): # load config object
        msg = 'Loading Failed for {}!  See Log\n'.format(args.fileobject)
        log_me('error', msg, logger)
