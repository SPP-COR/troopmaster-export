#!/usr/bin/env python3
import os, re
from parse import *
import csv
import logging
#logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

#filepath = 'IndividualHistoryReport-103144_c.txt'
filepath = '../JoeColin.txt'
# filepath = 'ColinT_IHR.txt'
filepathout = 'SB_IndividualHistoryReport.csv'


with open(filepath) as fp:
 with open(filepathout,'w') as csvfile:
   fields = ['BSA Member ID','First Name', 'Middle Name', 'Last Name', 
             'Advancement Type', 'Advancement', 'Version','Date Complete', 
             'Approved', 'Awarded']
   csvwriter = csv.DictWriter(csvfile, fieldnames=fields)
   csvwriter.writeheader()
   troopdata = dict()

   num_scouts=0
   num_processed=0
   num_partial_rank=0
   num_partial_mb=0
   scoutdata = dict()
   phase = "name"
   for cnt, line in enumerate(fp):
       #print("Processing {}: {}".format(cnt, line))
       if line.startswith("Name:"):
          num_scouts +=1
          scoutdata = dict()
          phase = "bsaid"
          p = parse("Name: {}, {} Email:{}", line)
          if p is None:
            logging.error("Coulnd't find name for line %s - using 'Joe Scout'",
                           line.replace('\n',''))
            scoutdata['First Name'] = 'Joe'
            scoutdata['Middle Name'] = ""
            scoutdata['Last Name'] = 'Scout'
          else:
            scoutdata['First Name'] = p[1]
            scoutdata['Middle Name'] = ""
            scoutdata['Last Name'] = p[0]
          logging.debug("Scout Data: %s",scoutdata)

       if line.startswith("Position:"):
          p = parse("Position: {} BSA ID: {}",line)
          if p is None:
             logging.error("No BSA ID for %s %s in line '%s', using 123",
                           scoutdata['First Name'] ,
                           scoutdata['Last Name'],
                           line.replace('\n',''))
             scoutdata['BSA Member ID'] = 123
          else:
             scoutdata['BSA Member ID'] = p[1]
             phase = "partialrank"
          logging.debug("Scout Data: %s",scoutdata)
          num_processed += 1

       if "partialrank" in phase and line.startswith("Scout"):
         scoutdata['Advancement Type'] = 'Scout Rank Requirement'
         scoutdata['Version'] = 2016
         logging.info("current rank: scout")

       if line.startswith("Tenderfoot"):
         scoutdata['Advancement Type'] = 'Tenderfoot Rank Requirement'
         scoutdata['Version'] = 2016
         logging.info("current rank: tf")

       if line.startswith("Second Class"):
         scoutdata['Advancement Type'] = 'Second Class Rank Requirement'
         scoutdata['Version'] = 2016
         logging.info("current rank: sc")

       if line.startswith("First Class"):
         scoutdata['Advancement Type'] = 'First Class Rank Requirement'
         scoutdata['Version'] = 2016
         logging.info("current rank: fc")

       # if we hit 'Star' we're done with partial rank stuff
       if line.startswith("Star"):
         logging.info("saw star, no more partial rank stuff..")
         phase = "partialmb" 
         
       # if we've seen a rank, and are starting w a number, this is a partial rank requirement
       # or a date header...
       if "partialrank" in phase and line[0].isdigit():
          #p = parse("{2}/{2}/{2}",line)
          #if p is not None:
          #  continue

          # handle left column (or only column)
          p = parse("{:.2}. {} {:.2}/{:.2}/{:.2} {}",line)
          if p is not None:
            (req1, dd1, mm1, yy1, col2) = (p[0],p[2],p[3],p[4],p[5])
          else:
            logging.warning("couldn't parse double-col line, try single '%s'",line)
            p = parse("{:.2}. {} {:.2}/{:.2}/{:.2}",line)
            if p is not None:
              (req1, dd1, mm1, yy1) = (p[0],p[2],p[3],p[4])
            else:
              logging.warning("couldn't parse line?! '%s'",line)

          if "__" not in mm1:
              logging.info("Found partial (left column) for %s: %s %s on date %s/%s/%s",
                  scoutdata['First Name'], 
                  scoutdata['Advancement Type'], 
                  req1, dd1, mm1, yy1)
              scoutdata['Date Complete'] = str(dd1)+"/"+str(mm1)+"/"+str(dd1)
              scoutdata['Approved'] = "1"
              scoutdata['Awarded'] = ""
              scoutdata['Advancement'] = req1
              num_partial_rank += 1
              csvwriter.writerow(scoutdata)

          # handle right column (if exists)
          p = parse("{:.2}. {} {:.2}/{:.2}/{:.2}",col2)
          if p is not None:
            (req2, dd2, mm2, yy2) = (p[0],p[2],p[3],p[4])
            if "__" not in mm2:
              logging.info("Found partial (right column) for %s: %s %s on date %s/%s/%s",
                  scoutdata['First Name'], 
                  scoutdata['Advancement Type'], 
                  req2, dd2, mm2, yy2)
              scoutdata['Date Complete'] = str(dd2)+"/"+str(mm2)+"/"+str(dd2)
              scoutdata['Approved'] = "1"
              scoutdata['Awarded'] = ""
              scoutdata['Advancement'] = req2
              num_partial_rank += 1
              csvwriter.writerow(scoutdata)

       if "partialmb" in phase and line.startswith("Partial Merit Badges"):
         phase = "findpmb"
         continue

       if "findpmb" in phase:
         p = parse("{} ({}) : {}", line.replace("*",""))
         if p is not None:
           mb = p[0]
           scoutdata['Advancement Type'] = 'Merit Badge Requirement'
           version = p[1]
           scoutdata['Version'] = p[1]
           logging.info("Found %s (%s) for %s",
               mb,
               scoutdata['Version'],
               scoutdata['First Name'])
           num_partial_mb += 1
           phase = "findopen"

       if "findopen" in phase:
         p = parse("Open Reqts: {}",line)
         if p is not None:
           openreqts = p[0]                  # a string "1abc, 2a, 3, ..."
           myre = re.compile(r'\w+')
           or_list = myre.findall(openreqts) # a list of ['1abc','2a','3',...]
           sb_or_list = [] # list of open requirements in sb format
                           # 1 2a 2b 2c 9b[1] 9b[2] 
           for openr in or_list:
             myre = re.compile(r'\w')
             char_list = myre.findall(openr)
             # 1
             if len(char_list)==1 and char_list[0].isdigit():
               sb_or_list.append(char_list)
             # 2a or 2ab or 2abcdf
             if (char_list[0].isdigit() and char_list[1:].isalpha()):
                for l in char_list[1:]:
                  sb_or_list.append(char_list[0]+l)
             #  6b5
             if len(char_list)==3 and char_list[0].isdigit() \
                                  and char_list[1].isalpha() \
                                  and char_list[2].isdigit():
               sb_or_list.append(char_list)
           logging.info("sb_or_lst=%s",sb_or_list)




   logging.info("%d Scouts found",num_scouts)
   logging.info("%d Scouts properly processed",num_processed)
   logging.info("%d Partial TTFC Rank Requirements", num_partial_rank)
   logging.info("%d Partial MB Requirements", num_partial_mb)