#!/usr/bin/env python

import os, sys
import re
import argparse
import json
import datetime
import textwrap
import logging
#from server.summary_tools import fstools
from neo4j.v1 import GraphDatabase, basic_auth
#import simplejson as json
from jinja2 import Environment, FileSystemLoader
from shutil import copyfile
#from dscensor import app


msg_format = '%(asctime)s|%(name)s|[%(levelname)s]: %(message)s'
logging.basicConfig(format=msg_format, datefmt='%m-%d %H:%M',
                    level=logging.DEBUG)
log_handler = logging.StreamHandler()
formatter = logging.Formatter(msg_format)
log_handler.setFormatter(formatter)
logger = logging.getLogger('DSCensor_test')
logger.addHandler(log_handler)

def connect_neo4j():
    host = os.environ['HOST']
    port = os.environ['PORT']
    auth = os.environ['AUTH']
    pswd = os.environ['PSWD']
    bolt = 'bolt:{}:{}'.format(host, port)
    driver = GraphDatabase.driver(bolt, auth=basic_auth(auth, pswd))
    logger.info('connection succeeded, driver:{}'.format(driver))
    return driver


def format_data(r, header):
    label = r['name']
    org_species = r['species']
    org_genus = r['genus']
    origin = r['origin']
    url = r.get('url')
    org_infra = r.get('infraspecies', 'N/A')
    org_cname = r.get('common_name', 'N/A')
    linkout = r.get('linkout_example', False)
    if not linkout:
        linkout = 'N/A'
        if (label == 'medtr.A17_HM341.v4.0.gff3.gz' or label == 'medtr.A17_HM341.v4.0.genome.fa.gz'): # REMOVE LATER
            linkout = 1
    else:
        linkout = '<button class=popupLinks>{}</button>'.format(linkout)
    data = {'label' : label, 'origin' : origin, 'linkout_example' : linkout,
             'org_infra' : org_infra, 'org_genus' : org_genus,
             'org_species' : org_species, 'org_cname' : org_cname,
             'url' : url}
    if not (r.get('gene', None) or r.get('N50', None)):
        logger.warning('gene or N50 required to render {}... continuing'.format(
                                                                        label))
#        return False
    for f in r:
        k = f.lower()
#        print f  #fill more of these in later
        if k == 'gene':
            data['genes'] = int(r[f])
            header['Genes'] = 1
        elif k == 'mrna':
            data['mrnas'] = int(r[f])
            header['mRNAs'] = 1
        elif k == 'five_prime_utr':
            data['5p_utrs'] = int(r[f])
            header["5' UTR"] = 1
        elif k == 'three_prime_utr':
            data['3p_utrs'] = int(r[f])
            header["3' UTR"] = 1
        elif k == 'cds':
            data['cds'] = int(r[f])
            header['CDS'] = 1
        elif k == 'exon':
            data['exons'] = int(r[f])
            header['Exons'] = 1
        elif k == 'scaffolds':
            data['scaffolds'] = int(r[f])
            header['Scaffolds'] = 1
        elif k == 'contigs':
            data['contigs'] = int(r[f])
            header['Contigs'] = 1
        elif k == 'n50':
            data['N50'] = int(r[f])
            header['N50'] = 1
        elif k == 'allbases':
            data['allbases'] = int(r[f])
            header["Bases"] = 1
        elif k == 'gaps':
            data['gaps'] = int(r[f])
            header["Gaps"] = 1
        elif k == 'gapbases':
            data['gapbases'] = int(r[f])
            header["Gap Bases"] = 1
        elif k == 'records':
            data['records'] = int(r[f])
            header["Fasta Records"] = 1
        elif k == 'complete_buscos':
            data['complete_buscos'] = int(r[f])
            header["% Complete BUSCOs"] = 1
        elif k == 'fragmented_buscos':
            data['fragmented_buscos'] = int(r[f])
            header["% Fragmented BUSCOs"] = 1
        elif k == 'missing_buscos':
            data['missing_buscos'] = int(r[f])
            header["% Missing BUSCOs"] = 1
    return data


def dscensor_neo4j_test(ftype):
    run_dir = os.path.dirname(os.path.realpath(__file__))
    #domain = app.domain
    domain = 'http://dev.lis.ncgr.org:50020'  # should import from app
    key_lookup = {'Genes' : 'genes', 'mRNAs' : 'mrnas', 'Exons' : 'exons',
                  'CDS' : 'cds', "3' UTR" : '3p_utrs', "5' UTR" : '5p_utrs',
                  'Scaffolds' : 'scaffolds', 'Contigs' : 'contigs',
                  'N50' : 'N50', 'Bases' : 'allbases', 
                  '% Complete BUSCOs': 'complete_buscos', 'Gaps' : 'gaps',
                  '% Frgamented BUSCOs': 'fragmented_buscos', 
                  '% Missing BUSCOs': 'missing_buscos',
                  'Gap Bases' : 'gapbases', 'Fasta Records' : 'records'}
    header_lookup = {'Unique Label' : 'label', 'Origin' : 'origin',
                     'Genus' : 'org_genus', 'Species' : 'org_species',
                     'infraspecies' : 'org_infra', 'Common Name' : 'org_cname',
                     'Linkout Example' : 'linkout_example', 'Genes' : 'genes',
                     'mRNAs' : 'mrnas', 'Exons' : 'exons', 'CDS' : 'cds', 
                     "3' UTR" : '3p_utrs', "5' UTR" : '5p_utrs',
                     'Scaffolds' : 'scaffolds', 'Contigs' : 'contigs',
                     'N50' : 'N50', 'Bases' : 'allbases', 'Gaps' : 'gaps',
                     'Gap Bases' : 'gapbases', 'Fasta Records' : 'records',
                     '% Complete BUSCOs': 'complete_buscos',
                     '% Frgamented BUSCOs': 'fragmented_buscos',
                     '% Missing BUSCOs': 'missing_buscos',}
    header_order = ['Unique Label', 'Origin', 'Genus', 'Species', 
                    'infraspecies', 'Common Name', 'Linkout Example',
                    'Genes', 'mRNAs', 'Exons', 'CDS', "3' UTR", "5' UTR",
                    '% Complete BUSCOs', '% Frgamented BUSCOs', '% Missing BUSCOs',
                    'Fasta Records', 'Contigs', 'Scaffolds', 'N50', 'Bases', 
                    'Gaps', 'Gap Bases']
    header_includes = {'Unique Label' : 1, 'Origin' : 1,
                        'Genus' : 1, 'Species' : 1, 'infraspecies' : 1,
                        'Common Name' : 1, 'Linkout Example' : 1}
    data = {
#            'header' : ['Unique Label', 'Origin',
#                        'Genus', 'Species', 'infraspecies',
#                        'Common Name',
#                        'Chromosomes', 'Super Contigs',
#                        'Linkage Groups', 'Genetic Markers', 'QTLs',
#                        'Syntenic Regions', 'Consensus Regions', 'Primers',
#                        'Genes', 'mRNAs', 'Exons', 'Polypeptides', 'CDS',
#                        "3' UTR", "5' UTR",
#                        'Polypeptide Domains', 'HMM Matches', 'Protein Matches'
#                       ],
            'ftype' : ftype,
            'header' : [],
#                        'Unique Label', 'Origin',
#                        'Genus', 'Species', 'infraspecies',
#                        'Common Name', 'Linkout Example',
#                        'Genes', 'mRNAs', 'Exons', 'CDS',
#                        "3' UTR", "5' UTR"
#                       ],
            'counts' : {},
            'partition' : {'name' : 'Origin', 'children' : []},
            'table_data' : [],
            'json_data' : '',
            'json_header' : '',
            'json_table_data' : '',
            'json_partition_data' : '',
            'hist_append' : '''<div class="container" style="position:relative;left:-50px;padding-top:10px;padding-bottom:10px;overflow: auto"> <b>Stack:</b>''',
            'scat_append_x' : '''<div class="container" style="position:relative;left:-50px;padding-top:10px;padding-bottom:10px"> <b>XAXIS:</b>''',
            'scat_append_y' : '''<div class="container" style="position:relative;left:-50px;padding-bottom:10px"> <b>YAXIS:</b>''',
            'scat_append' : ''
           }
    origins = {}
    check_me = {}
    genus = {}
    counts = data['counts']
    driver = connect_neo4j()
    statement = ''
    switch = 1
    print(ftype)
    for f in ftype.split(':'):
        print(f)
        if f == 'gff' or f == 'gene_models_main':
            switch = 1
            data['ftype'] = 'gff'
        elif f == 'fasta' or f == 'genome_main':
            switch = 1
            data['ftype'] = 'fasta'
        elif f == 'gwas':
            switch = 1
            data['ftype'] = 'gwas'
    if not switch:
        return False
    statement = 'match (a:{}) return a'.format(ftype)
    c = 0
    with driver.session() as session:
        for r in session.run(statement):
            data_obj = format_data(r[0], header_includes)
            if not data_obj:
                continue
            label = data_obj['label']
            origin = data_obj['origin']
            org_genus = data_obj['org_genus']
            linkout = ''
            if data_obj['linkout_example'] != 'N/A':
                c += 1
                value = 'popuptext{}'.format(c)
#                igv = '{}/visualize-igv/{}'.format(domain, label)
                igv = '/visualize-igv/{}'.format(label)
                if label == 'medtr.A17_HM341.v4.0.gff3.gz' or label == 'medtr.A17_HM341.v4.0.genome.fa.gz': #remove this when i link actual file objects to nodes                   
                    example = 'medtr.Medtr2g020630'#data_obj['linkout_example']
                    linkout = ("<div class='popup'><button value='" + value + 
                               "' class='popupLinkout'>" + example + 
                               "</button><span class='popupText' " + 
                               "id='" + value + "'>test</span></div>")  
                    data_obj['linkout_example'] = linkout
            if data_obj['url']:
#                igv = '{}/visualize-igv/{}'.format(domain, label)
                igv = '/visualize-igv/{}'.format(label)
                linkout += ("<a target='_blank' href='" + igv  + "'>" + 
                            "<button value='test_igv'>IGV</button></a>")
            if linkout:
                data_obj['linkout_example'] = linkout
            counts[label] = data_obj
            if origin not in origins:
                origins[origin] = []
                check_me[origin] = {}
            if org_genus not in genus:
                genus[org_genus] = []
            if org_genus not in check_me[origin]:
                check_me[origin][org_genus] = 1
                origins[origin].append(org_genus)
            genus[org_genus].append(data_obj)
    for h in header_order:
        if header_includes.get(h, None):
            data['header'].append(h)
    partition = data['partition']['children']
    count = 0
    for o in origins:
     #   print len(origins[o])
        partition.append({'name' : o, 
                          'children' : []})
        p_g = partition[count]['children']
        for g in origins[o]:
      #      print len(genus[g])
            p_g.append({'name' : g,
                        'color' : '{} 0'.format(g),
                        'children' : []})
            p_o = p_g[-1]['children']
            for c in genus[g]:
                if c['origin'] != o:
                    continue
                org_genus = c['org_genus']
                org_species = c['org_species']
                label = c['label']
                cstring = '{} {}'.format(org_genus, org_species)
                children = []
                for h in data['header'][7:]:
                    if not c.get(header_lookup[h]):
                        c[header_lookup[h]] = 0
                    children.append({'name' : h, 'count' : 1, 
                                     'number' : c[header_lookup[h]]})
                p_o.append(
                       {'name' : label,
                        'color' : cstring,
                        'children' : children
                       }
                )
        count += 1
    ordered = []
    for d in counts:
        o = counts[d]
        datum = [o[header_lookup[h]] for h in data['header']]
        data['table_data'].append(datum)
        ordered.append(o)
    header = [{'title' : h} for h in data['header']]
    json_header = json.dumps(header)
    json_data = json.dumps(ordered)
    json_table_data = json.dumps(data['table_data'])
    json_partition_data = json.dumps(data['partition'])
#    print json_header
#    print json_data
#    print json_table_data
    data['json_header'] = json_header
    count = 1
    for h in header[7:]:
        name = h['title']
        value = key_lookup.get(name)
        name = name.replace("'", '&#39;')
        data['hist_append'] += ('''<label class="checkbox-inline">''' + 
             '''<input type="checkbox" value="''' + value + '"')
        if value == 'genes' or value == 'records':
             data['hist_append'] += ''' class="customhistogram-1" checked>''' + name + '''</label>'''
        else:
             data['hist_append'] += ''' class="customhistogram-1">''' + name + '''</label>'''
        data['scat_append_x'] += ('''<label class="checkbox-inline">''' +
             '''<input type="checkbox" value="''' + value + '"')
        if value == 'exons' or value == 'records':
             data['scat_append_x'] += ''' class="customscatter-1x" checked>''' + name + '''</label>'''
        else:
             data['scat_append_x'] += ''' class="customscatter-1x">''' + name + '''</label>'''
        data['scat_append_y'] += ('''<label class="checkbox-inline">''' +
             '''<input type="checkbox" value="''' + value + '"')
        if value == 'genes' or value == 'N50':
             data['scat_append_y'] += ''' class="customscatter-1y" checked>''' + name + '''</label>'''
        else:
             data['scat_append_y'] += ''' class="customscatter-1y">''' + name + '''</label>'''
    data['hist_append'] += '''<button id="filterhistogram-1" style="inline:block;position:relative;left:10px" class="customhistogram1">Render</button></div><li class="list-group-item"><div class=container style="overflow:auto"><span id="customHistogram-1"></span></div></li>'''
    data['scat_append_x'] += '''</div>'''
    data['scat_append_y'] += '''</div>'''
    data['scat_append'] = (data['scat_append_x'] + data['scat_append_y'] +
                           '''<div class="container" style="position:relative;left:-50px;padding-bottom:10px"><button id="filterscatter-1" style="inline:block;position:relative;left:10px" class="customscatter1">Render</button></div></div><li class="list-group-item"><soan id="customScatter-1"></span></li>''')
#    print data['scat_append']
#    print data['hist_append']
    data['busco_append'] = '''<li class="list-group-item"><div class=container style="overflow:auto"><span id="buscoHistogram-1"></span></div></li>'''
    data['json_data'] = json_data
    data['json_table_data'] = json_table_data
    data['json_partition_data'] = json_partition_data
    env = Environment(loader=FileSystemLoader(run_dir), lstrip_blocks=True, trim_blocks=True)
    template = env.get_template('templates/js.jinja')
    #print data
    #print json_header
    #print data['results'][0]['data'][0]
    return template.render(data=data)
    #print template.render(data=data)


if __name__ == '__main__':
    template = dscensor_neo4j_test('fasta')
    print(template)

