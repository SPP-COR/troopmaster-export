#!/usr/bin/env python3
import csv
import logging
import parse
#logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)


def unfold_opens(infile='../JoeColin.txt',outfile='../JoeColin2.txt'):
 with open(infile) as infp:
  with open(outfile,'w') as outfp:
   open_active = False
   open_line = ""
   for line in infp:
       if open_active:
           open_line = open_line + line
           outfp.writeline(line)
           open_active=False
       elif line.startswith("Open Reqts: ") and line.endswith(","):
           open_active=True
           open_line = line
       else:
           outfp.write(line)
    
if __name__=='__main__':
    unfold_opens()