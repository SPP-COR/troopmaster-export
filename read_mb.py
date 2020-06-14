#!/usr/bin/env python3
import csv
import logging
#logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

#filepath = '../all_mb_reqmts.csv'
filepath = '../some_mb_reqmts.csv'

mb_dBase = dict()
with open(filepath) as fp:
   reader = csv.reader(fp)
   for row in reader:
       print("Processing ", row)
       mb = row[0].strip()
       req = row[1]
       yy = row[2]
       if mb not in mb_dBase.keys():
           mb_dBase[mb] = dict()
       if yy not in mb_dBase[mb].keys():
           mb_dBase[mb][yy] = []
       mb_dBase[mb][yy].append(req)

print(mb_dBase)
