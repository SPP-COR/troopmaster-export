#!/usr/bin/env python3
import os, re
from parse import *
import csv
import logging
import read_mb

#logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)

filepath = '../IndividualHistoryReport-103144_c.txt'
#filepath = '../JoeColin.txt'
# filepath = 'ColinT_IHR.txt'
filepathout = 'SB_IndividualHistoryReport.csv'


# unwrap multiple-row "Open Reqts: lines"
if not os.path.exists(filepath+'2'):
  import unfold_openreq
  unfold_openreq.unfold_opens(filepath,filepath+'2')

# read in dbase of mb requirements, from scoutbook
mbdBase = read_mb.read_mb_dbase('all_mb_reqmts.csv')

with open(filepath+'2') as fp:
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
         logging.debug("current rank: scout")

       if line.startswith("Tenderfoot"):
         scoutdata['Advancement Type'] = 'Tenderfoot Rank Requirement'
         scoutdata['Version'] = 2016
         logging.debug("current rank: tf")

       if line.startswith("Second Class"):
         scoutdata['Advancement Type'] = 'Second Class Rank Requirement'
         scoutdata['Version'] = 2016
         logging.debug("current rank: sc")

       if line.startswith("First Class"):
         scoutdata['Advancement Type'] = 'First Class Rank Requirement'
         scoutdata['Version'] = 2016
         logging.debug("current rank: fc")

       # if we hit 'Star' we're done with partial rank stuff
       if line.startswith("Star"):
         logging.debug("saw star, no more partial rank stuff..")
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
            logging.debug("couldn't parse double-col line, try single '%s'",line)
            p = parse("{:.2}. {} {:.2}/{:.2}/{:.2}",line)
            if p is not None:
              (req1, dd1, mm1, yy1) = (p[0],p[2],p[3],p[4])
            else:
              logging.warning("couldn't parse line?! '%s'",line)

          if "__" not in mm1:
              logging.debug("Found partial (left column) for %s: %s %s on date %s/%s/%s",
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
              logging.debug("Found partial (right column) for %s: %s %s on date %s/%s/%s",
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
         p = parse("{} ({}) : {} Start Date: {}/{}/{} {}", line.replace("*",""))
         if p is not None:
           scoutdata['Advancement Type'] = 'Merit Badge Requirement'
           mb = p[0]
           logging.debug("Found partial mb - %s for %s %s",
               mb,
               scoutdata['First Name'],
               scoutdata['Last Name'])
           num_partial_mb += 1

           # count down till you find a set of valid requirements
           years = mbdBase[mb]
           started = "20"+p[5]
           mbyear = started
           while mbyear not in years.keys():
             mbyear = str(int(mbyear)-1)
           scoutdata['Version'] = mbyear
           phase = "findopen"

           # neither TM nor SB line up with usscouts.org history of Camping?
           #if ("Camping" in mb and "2015" in scoutdata['Version']):
           #  scoutdata['Version'] = "2012"
           # TM got fishing wrong
           #if ("Fishing" in mb and "2014" in scoutdata['Version']):
           #  scoutdata['Version'] = "2013"
           #if ("Fishing" in mb and "2014" in scoutdata['Version']):
           #  scoutdata['Version'] = "2013"


       if "findopen" in phase:
         p = parse("Open Reqts: {}",line)
         if p is not None:
           openreqts = p[0]                  # a string "1abc, 2a, 3, ..."
           #myre = re.compile(r'\S+')
           #or_list = myre.findall(openreqts.replace(',','')) # a list of ['1abc','2a','3',...]
           or_list = openreqts.split(',')
           sb_or_list = [] # list of open requirements in sb format
                           # 1 2a 2b 2c 6b1 9b[1] 9b[2] 
                           # Family Life has 6b1 but Archery has 2d[2]
           for openr in or_list:
             openr = openr.strip() # remove any whitespace

             if len(openr)==0:
               continue

             myre = re.compile(r'\w')
             char_list = myre.findall(openr.strip())
             decoded = False
             # 1
             if len(char_list)==1 and char_list[0].isdigit():
               sb_or_list.append(char_list[0])
               decoded = True

             # 14
             if len(char_list)==2 and char_list[0].isdigit() and char_list[1].isdigit():
               sb_or_list.append(char_list[0]+char_list[1])
               decoded = True

             # 2a or 2ab or 2abcdf
             if (char_list[0].isdigit() and openr[1:].isalpha()):
                for l in char_list[1:]:
                  sb_or_list.append(char_list[0]+l)
                  decoded = True

             # 11a or 11ab or 11bcdf
             if (openr[0:2].isdigit() and openr[2:].isalpha()):
                for l in char_list[2:]:
                  sb_or_list.append(openr[0:2]+l)
                  decoded = True

             #  6b5 in TM, would be 6b[5] in SB
             if len(char_list)==3 and char_list[0].isdigit() \
                                  and char_list[1].isalpha() \
                                  and char_list[2].isdigit():
               sb_or_list.append(char_list[0]+char_list[1]+"["+char_list[2]+"]")
               decoded = True

             # Rest, pass as-is
             #  6b[5] in TM, is also 6b[5] in SB
             #  "5f[1]d Opt A" (Archery)
             #  "5d3 avian" (Animal Science)
             #  "5a Grp 1" (Athletics)
             if not decoded:
              # bug in TM output report
              if "Camping" in mb and "9b[6]c" in openr:
                sb_or_list.append("9c")
              else:
                sb_or_list.append(openr)

           logging.debug("Open Requirements: %s",sb_or_list)
           # Check against dbase, alert us to any mismatches
           # Looks like TM is using some shorthand - 1f insead of 1f[1] 1f[2] etc....
           for req in sb_or_list:
              if req not in mbdBase[mb][scoutdata['Version']]:
               logging.error("Sorry, open requirement %s for mb %s (%s) not found, full list is %s",
                              req, mb, scoutdata['Version'], mbdBase[mb][scoutdata['Version']])
           logging.debug("Verified all open requirements for badge %s (%s)", mb, scoutdata['Version'])

           # Grab full copy of that year's version of that mb
           for req in mbdBase[mb][scoutdata['Version']]:
             if req not in sb_or_list:
               #logging.info('Found completed requirement: %s (%s): %s',
               #  mb, scoutdata['Version'], req)
               scoutdata['Advancement'] = mb + " #" + req
               csvwriter.writerow(scoutdata)
               
           phase = "findpmb" # look for another partial merit badge




   logging.info("%d Scouts found",num_scouts)
   logging.info("%d Scouts properly processed",num_processed)
   logging.info("%d Partial TTFC Rank Requirements", num_partial_rank)
   logging.info("%d Partial MB Requirements", num_partial_mb)