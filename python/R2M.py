#!/usr/bin/env python2
#####
#
# Reftek 2 MSEED script to convert Raw Reftek and manage Gaps
#
# Developed by Bruno Collaco <bruno@iag.usp.br>
#
# This tool uses the program 'rt2mseed' from Reftek
#
# It can be downloaded here:
# https://seiscode.iris.washington.edu/projects/dataselect/files
#
#
# Centro de Sismologia da USP @ 2018
#
#####

import sys
from os import walk, sep, system, makedirs, getcwd, remove
from os.path import basename, isdir
from optparse import OptionParser
from shutil import rmtree



'''

RT -> MSEED Conversion
Need Reftek rt2mseed @2005

'''

def toMSEED(path, net, sta, seedCode, naming):

    for root, dirs, files in walk(path):
        for file in files:
            rtFile = root+sep+file
            #
            ## Check if file is reftek raw
            try:
                len(rtFile.split("_")[1])
            except:
                print rtFile, "is not a reftek file, skipping"
                continue
            #
            ## Do not convert stream 0
            stream = rtFile.split("/")[len(rtFile.split("/"))-2]

            mseedPath = "/".join((getcwd(), net+'.'+sta+".MSEED"))

            if (stream != '1'):
                continue

            try:
                makedirs(mseedPath)
            except:
                pass

            #
            ## Convert File:
            print "processing", rtFile
            #system("rt2mseed %s -P%s 2> /dev/null" % (rtFile,mseedPath))
            system("rt2mseed %s -P%s" % (rtFile,mseedPath))

    if not isdir(mseedPath):
        print "stream 1 not found, terminating."
        exit()

    for root, dirs, files in walk(mseedPath):
        for file in files:

            msfile = root+sep+file

            #
            ## Channel Orientation:
            cha_suffix = msfile[-5]

            if cha_suffix == "1" :
                cha = seedCode+'H'+'Z'

            if cha_suffix == "2" :
                if naming:
                    cha = seedCode+'H'+'1'
                else:
                    cha = seedCode+'H'+'N'

            if cha_suffix == "3" :
                if naming:
                    cha = seedCode+'H'+'2'
                else:
                    cha = seedCode+'H'+'E'

            #
            ## Date
            year = basename(msfile)[0:4]
            juli = basename(msfile)[4:7]
            hour = basename(msfile)[8:10]

            new_msfile = ".".join((net,sta,'',cha,"D",str(year),str(juli),str(hour)))

            new_msfile = root+sep+new_msfile

            system("msmod --net %s --sta %s --chan %s -o %s %s" % (net,sta,cha,new_msfile,msfile))

            # try:
            #     st = read(msfile)
            # except:
            #     print "cannot read %s" % msfile
            #     continue
            #
            # #
            # ## MSEED Headers
            # st[0].stats.network = net
            # st[0].stats.station = sta
            # loc = st[0].stats.location
            #
            # #
            # ## Channel Orientation:
            # cha_suffix = str(st[0].stats.channel[-1])
            #
            # if cha_suffix == "1" :
            #     cha = seedCode+'H'+'Z'
            #
            # if cha_suffix == "2" :
            #     if naming:
            #         cha = seedCode+'H'+'1'
            #     else:
            #         cha = seedCode+'H'+'N'
            #
            # if cha_suffix == "3" :
            #     if naming:
            #         cha = seedCode+'H'+'2'
            #     else:
            #         cha = seedCode+'H'+'E'
            #
            # st[0].stats.channel = cha
            #
            # #
            # ## Date
            # year = st[0].stats.starttime.year
            # juli = "%03d" % st[0].stats.starttime.julday
            # hour = "%02d" % st[0].stats.starttime.hour
            #
            #
            # new_msfile = ".".join((net,sta,loc,cha,"D",str(year),str(juli),str(hour)))
            #
            # st.sort()
            # st.write(root+sep+new_msfile,"MSEED",reclen=512)

            remove(msfile)
            print new_msfile, "created."


    return None

'''
SC3 SCART
'''
def runScart(msPath,sdsPath):

    print "now, running scart ..."

    for root, dirs, files in walk(msPath):
        for file in files:
            msFile = root+sep+file
            system("seiscomp exec scart --sort -I file://%s %s" % (msFile,sdsPath))

    rmtree(msPath)
    print "... done!"

    return None

'''
DataSelect
'''
def runDataselect(sdsPath):

    print "now, running datadelect to sort files ..."

    for root, dirs, files in walk(sdsPath):
        for file in files:
            sdsFile = root+sep+file
            system("dataselect -Pr -rep -mod -nb %s" % sdsFile)

    print "... done!"

    return None


'''
Command Line Parser
'''
def make_cmdline_parser():
    #
    ## Create the parser
    parser = OptionParser(usage="%prog [options] <files>", version="1.0", add_help_option = True)

    parser.add_option("-p", "--path", dest="rtpath", help="Path where are Reftek files to convert", default=None)
    parser.add_option("-s", "--stream", dest="stream", help="SEED stream code as NET.STATION, e.g. BL.ESAR", default=None)
    parser.add_option("-i", "--seedcode", dest="seedcode", help="SEED Channel Prefix, eg 'E' for Short Period Instrument 100Hz. Default is H", default="H")
    # parser.add_option("-r", "--rate", dest="rate", help="Station Sampling Rate, e.g. 100 for 100Hz", default=None)
    parser.add_option("", "--not-oriented", action="store_true", dest="cha_naming", help="Channel naming, use this option to use [Z,1,2] instead of [Z,N,E]", default=False)
    parser.add_option("", "--scart", action="store_true", dest="scart", help="Run SeisComP3 Scart to create SDS locally", default=False)


    return parser



if __name__ == "__main__":
    parser = make_cmdline_parser()
    (options, args) = parser.parse_args()

    rtpath = options.rtpath
    if rtpath == None:
        print >>sys.stderr,"Nothing to do, please specify the path to search for Reftek Files."
        sys.exit(1)

    stream = options.stream
    if stream == None:
        print >>sys.stderr,"Please specify SEED Code for station, eg. BL.ESAR"
        sys.exit(1)

    # rate = int(options.rate)
    # if rate == None:
    #     print >>sys.stderr,"Please specify Station Sampling Rate, eg. 100"
    #     sys.exit(1)

    net,sta  = stream.split(".")
    seedCode = options.seedcode
    scart    = options.scart
    naming   = options.cha_naming

    e = toMSEED(rtpath, net, sta, seedCode, naming)

    if scart:
        _msPath  = "/".join((getcwd(),net+'.'+sta+".MSEED"))
        _sdsName = ".".join(('SDS',basename(stream)))
        _sdsPath = "/".join((getcwd(),_sdsName))
        runScart(_msPath,_sdsPath)
        runDataselect(_sdsPath)


    sys.exit(0)
