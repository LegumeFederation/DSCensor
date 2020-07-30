#!/usr/bin/env python

import os
import sys
import re
import argparse
import json
import datetime
import textwrap
import logging
from jinja2 import Environment, FileSystemLoader


msg_format = '%(asctime)s|%(name)s|[%(levelname)s]: %(message)s'
logging.basicConfig(format=msg_format, datefmt='%m-%d %H:%M',
                    level=logging.DEBUG)
log_handler = logging.StreamHandler()
formatter = logging.Formatter(msg_format)
log_handler.setFormatter(formatter)
logger = logging.getLogger('DSCensor_test')
logger.addHandler(log_handler)


def render_igv(data):
   run_dir = os.path.dirname(os.path.realpath(__file__))
   env = Environment(loader=FileSystemLoader(run_dir), lstrip_blocks=True, trim_blocks=True)
   template = env.get_template('templates/igv_view.jinja')
   return template.render(data=data)


if __name__ == '__main__':
    data = '''{
  "data": {
    "fasta": [
       {
        "filename": "medtr.A17_HM341.v4.0.genome.fa",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/assembly/medtr.A17_HM341.v4.0.genome.fa"
      }
    ],
    "gff": [
      {
        "filename": "medtr.A17_HM341.v4.0.gff3",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/annotation/medtr.A17_HM341.v4.0.gff3"
      }
    ],
    "gwas": [
      {
        "filename": "height_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/height_results.gwas"
      },
      {
        "filename": "noda_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/noda_results.gwas"
      },
      {
        "filename": "trichomes_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/trichomes_results.gwas"
      },
      {
        "filename": "totalnod_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/totalnod_results.gwas"
      },
      {
        "filename": "floweringdate_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/floweringdate_results.gwas"
      },
      {
        "filename": "occupancyB_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/occupancyB_results.gwas"
      },
      {
        "filename": "occupancyA_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/occupancyA_results.gwas"
      },
      {
        "filename": "nodb_results.gwas",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/nodb_results.gwas"
      }
    ],
    "phenotype": [
      {
        "filename": "GH2_combined.csv",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/GWAS/GH2_combined.csv"
      }
    ],
    "vcf": [
      {
        "filename": "filtered-set-2014Apr12.vcf.gz",
        "url": "/iplant/home/shared/Legume_Federation_prerelease/Medicago_truncatula/genome.A17_HM341.v4.0/diversity/filtered-set-2014Apr12.vcf.gz"
      }
    ]
  },
  "selection": "medtr.A17_HM341.v4.0.genome.fa"
}
'''
    data = json.loads(data)
    template = render_igv(data)
    print(template)
