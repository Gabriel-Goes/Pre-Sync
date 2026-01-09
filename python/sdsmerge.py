#!/us/bin/env python

###
#
# SDS merge scripts with checks
# replace old syncnrt + syncflash
#
# Initiated by Marcelo Bianchi <m.bianchi@iag.usp.br>
#              Bruno Colaco    <bruno@iag.usp.br>
#
# IAG/IEE/USP @ 2015
#######

###
# Program description:
#
# Merge the contents from one SDS to another. It has
# two operation modes:
#
# When mode == NRT it delete source files and only 
#              sync files older than a day
#
# When mode == ARCHIVE it syncs all files in source 
#              SDS and do not delete files from source
#              unless -f flag is given. In this case it
#              deletes files from source SDS
#
# On both cases using -n options runs the code in dry-run mode
# that does not touch source or destination files, but only 
# simulate
#
#######

import datetime
import sys
import mseedlite
from os import walk, sep, path, makedirs as mkdir, remove
from optparse import OptionParser
from shutil import copyfile as cp
from obspy.core import UTCDateTime, read, stream
from genericpath import isdir
import signal

try:
    from iaghacks import Postman
    haspostman = True
except:
    haspostman = False

VERSION = "0.1"
FORCESTOP = False

class Logs(object):
    DEBUG = 0
    INFO  = 1
    WARN  = 2
    ERROR = 3

    def __init__(self, level, destination = sys.stderr):
        self.level = level
        self.destination = destination

    def setdestination(self, destination):
        self.destination = destination

    def error(self, message):
        if self.level > Logs.ERROR: return
        print >>self.destination,"\nERROR::",message
        return

    def warn(self, message):
        if self.level > Logs.WARN: return
        print >>self.destination,"WARN::",message
        return

    def info(self, message):
        if self.level > Logs.INFO: return
        print >>self.destination,"INFO::",message
        return

    def debug(self, message):
        if self.level > Logs.DEBUG: return
        print >>self.destination,"DEBUG::",message
        return

class CheckStatus():
    ALLOK = 1
    FORCESORT = 2
    NOSYC = 99

class Mode():
    NRT = 1
    ARCHIVE = 2

def signal_handler(signal, frame):
    global FORCESTOP

    logerror('*** Wait, preparing to stop ***')
    FORCESTOP = True
    return

def get_filelist(sourcefolder, mode):
    fileList=[]
    
    if mode == Mode.NRT:
        now = datetime.datetime.now().date()
        time2cut = datetime.datetime.strptime(str(now)+"-00-00", "%Y-%m-%d-%H-%M") - datetime.timedelta(days=1)
    
        for root, dirs, files in walk(sourcefolder):
            for msFile in files:
                mtime = datetime.datetime.fromtimestamp(path.getmtime(root+sep+msFile))
                if mtime < time2cut :
                    fileList.append(root+sep+msFile)
    elif mode == Mode.ARCHIVE:
        for root, dirs, files in walk(sourcefolder):
            for msFile in files:
                fileList.append(root+sep+msFile)
    else:
        logerror("Invalid mode of operation")

    return sorted(fileList)

def check_file(sourcefolder, currentfile):
    filename = path.basename(currentfile)
    status = CheckStatus.ALLOK

    # Check filename
    #
    if filename.count(".") != 6:
        logerror("%s: Invalid SDS filename." % filename)
        status = max(status, CheckStatus.NOSYC)

        return status

    try:
        (network, station, location, channel, stream, year, jday) = filename.split(".")
    except ValueError:
        status = max(status, CheckStatus.NOSYC)
        return status

    year = int(year)
    jday = int(jday)

    if network == "":
        status = max(status, CheckStatus.NOSYC)
        logerror("%s: Invalid network." % filename)

    if station == "":
        status = max(status, CheckStatus.NOSYC)
        logerror("%s: Invalid station." % filename)

    if channel == "":
        status = max(status, CheckStatus.NOSYC)
        logerror("%s: Invalid channel." % filename)

    if stream == "" or stream not in [ "D", "L" ]:
        status = max(status, CheckStatus.NOSYC)
        logerror("%s: Invalid stream, not supported." % filename)

    flcheck = path.join(sourcefolder, str(year), network, station,"%s.%s" % (channel, stream), "%s.%s.%s.%s.%s.%04d.%03d" % (network, station, location, channel, stream, year, jday))

    if currentfile != flcheck:
        status = max(status, CheckStatus.NOSYC)
        logerror("%s: Reconstructed path %s != %s ." % (filename, flcheck, currentfile))

    if path.getsize(currentfile) == 0:
        status = max(status, CheckStatus.NOSYC)
        logerror("%s: File has 0 size" % filename)

        return status

    # Headers match name
    #
    infile = file(path.join(currentfile))
    records = mseedlite.Input(infile)

    morning = datetime.datetime.now().strptime("%s-%sT%s:%s:%s" % (year, jday, 0,0,0),"%Y-%jT%H:%M:%S")
    evening = morning + datetime.timedelta(days = 1)

    lastrecord = None

    wnet = False
    wsta = False
    wloc = False
    wcha = False
    worder = False 
    wlast = False
    wlastover = False

    for record in records:
        # Check Codes
        #
        if network  != record.net and not wnet:
            status = max(status, CheckStatus.NOSYC)
            logerror("%s: Invalid header network code." % filename)
            wnet = True

        if station  != record.sta and not wsta:
            status = max(status, CheckStatus.NOSYC)
            logerror("%s: Invalid header station code." % filename)
            wsta = True

        if location != record.loc and not wloc:
            status = max(status, CheckStatus.NOSYC)
            logerror("%s: Invalid header location code." % filename)
            wloc = True

        if channel  != record.cha and not wcha:
            status = max(status, CheckStatus.NOSYC)
            logerror("%s: Invalid header channel code." % filename)
            wcha = True

        # Fits day
        #
        if record.begin_time < morning or record.begin_time > evening and not worder:
            status = max(status, CheckStatus.NOSYC)
            logerror("%s: Record does not fit day." % filename)
            worder = True

        # Ordered
        #
        _dt2 = datetime.timedelta(0, 1.0 / record.fsamp / 4.0)
        if lastrecord:
            if (record.begin_time + _dt2) < lastrecord.begin_time and not wlast:
                status = max(status, CheckStatus.FORCESORT)
                logwarning("%s: Records out of order." % filename)
                wlast = True
            elif (record.begin_time + _dt2) < lastrecord.end_time and not wlastover:
                logwarning("%s: Possible Overlapping records." % filename)
                wlastover = True

        lastrecord = record
    infile.close()

    return status

def ensure_folder(folder):
    
    # Check if a folder exists. If not, make it.
    #
    if not isdir(folder):
        try:
            mkdir(folder, 0755)
        except:
           
            pass

def cansimplemerge(stream):
    sps = None
    for t in stream:
        if sps is None:
            sps = t.stats.sampling_rate
        if t.stats.sampling_rate != sps:
            return False
    return True

def multimerge(st):
    #
    # Split streams by sps !
    #
    streams = { }
    while st:
        trone = st.pop()
        sps = trone.stats.sampling_rate
        try:
            ts = streams[sps]
        except KeyError:
            ts = stream.Stream()
            streams[sps] = ts
        ts.append(trone)
    
    merged = stream.Stream()
    for t in streams.keys():
        streams[t].merge(method=-1, misalignment_threshold = 0.25)
        merged += streams[t]
        del streams[t]
    
    return merged

def execute_merge(currentfile, destinationfolder, mode, forcekeep, forcedelete, forcesort, dryrun):
    
    # Build SDS path
    #
    (net, sta, loc, cha, stream, year, jday) = path.basename(currentfile).split('.')

    sdsPath = path.join(destinationfolder, year, net, sta, "%s.%s" % (cha, stream))
    sdsFile = path.join(sdsPath, path.basename(currentfile))

    merged = False
    copied = False
    removed = False

    # Check if destination exists. If not, make it
    # 
    if not dryrun: ensure_folder(sdsPath)

    # Check if file exists in destination. If affirmative, merge them
    #
    if path.isfile(sdsFile) or forcesort:
        try:
            st = read(currentfile)
            print >>sys.stderr,currentfile
            if path.isfile(sdsFile) and path.getsize(sdsFile) > 0:
                st += read(sdsFile)
            if cansimplemerge(st):
                st.merge(method=-1)
            else:
                logwarning("Cannot execute a simple merge, doing a multi merge on file %s !" % currentfile)
                st = multimerge(st)
            st.sort(['starttime'])

            if not dryrun: st.write(sdsFile, "MSEED")
            merged = True
        except Exception as e:
            logerror("Failed to execute merge %s to %s\n (%s)" % (currentfile, path.dirname(sdsFile), str(e)))
            return (merged, copied, removed)

    else:
        # Copy currentFile into destination
        #
        try:
            if not dryrun: cp(currentfile, sdsFile)
            copied = True
        except Exception as e:
            logerror("Failed to execute cp %s to %s\n (%s)" % (currentfile, path.dirname(sdsFile), str(e)))
            return (merged, copied, removed)

    # Remove origin file if asked to
    #
    if (mode == Mode.NRT and not forcekeep) or (mode == Mode.ARCHIVE and forcedelete):
        try:
            if not dryrun: remove(currentfile)
            removed = True
        except Exception as e:
            logerror("Failed to execute rm %s\n (%s)" % (currentfile, str(e)))
            return (merged, copied, removed)

    return (merged, copied, removed)

def make_cmdline_parser():
    # Create the parser
    #
    parser = OptionParser(usage="%prog [options] <-m mode> <-s source> <-d destination>", version=VERSION, add_help_option = True)

    parser.add_option("-m","--mode", type="string", dest="mode",
                      help="Mode of operation: NRT or ARCHIVE", default=None)

    parser.add_option("-v","--verbose", action="store_true", dest="verbose",
                      help="verbose, report each file.", default=False)

    parser.add_option("-f","--force-delete", action="store_true", dest="forcedelete",
                      help="Force delete, i.e. move from source SDS files instead of moving/merge when operating in ARCHIVE mode.", default=False)

    parser.add_option("-k","--force-keep", action="store_true", dest="forcekeep",
                      help="Force keep, i.e. copy from source SDS files instead of moving/merge when operating in NRT mode.", default=False)

    parser.add_option("-n", "--dry-run", action="store_true", dest="dryrun",
                      help="Run in Dry mode, i.e. just simulate sincronization performing basic checks", default=False)

    parser.add_option("-s","--source", type="string", dest="source",
                      help="Source SDS to copy files from. In NRT mode those files will be deleted.", default=None)

    parser.add_option("-d","--destination", type="string", dest="destination",
                      help="Destination SDS, use an empty folder for coping from source SDS, duplicating the SDS while performing the checks.", default=None)

    if haspostman:
        parser.add_option("-l","--mail-to", type="string", dest="mailusers",
                          help="Send log as mail to users (separated by comma) using IAG Postman.", default=None)

    return parser

if __name__ == "__main__":

    # Parse command line
    #
    stop = False
    parser = make_cmdline_parser()
    (options, args) = parser.parse_args()

    # Setup logs
    #
    logger = Logs( (Logs.WARN if not options.verbose else Logs.INFO), sys.stderr);
    
    logerror   = logger.error
    logwarning = logger.warn
    loginfo    = logger.info
    logdebug   = logger.debug

    if not options.source:
        logerror("Source SDS was not informed.")
        stop = True

    if options.source and not path.isdir(options.source):
        logerror("Source folder, %s, is not a folder." % options.source)
        stop = True

    if not options.destination:
        logerror("Destination SDS was not informed.")
        stop = True

    if options.destination and not path.isdir(options.destination):
        logerror("Destination folder, %s, is not a folder." % options.destination)
        stop = True

    if not options.mode:
        logerror("Operation mode was not supplied.")
        stop = True

    if options.mode:
        if hasattr(Mode, options.mode):
            options.mode = getattr(Mode, options.mode)
        else:
            logerror("Invalid operation mode: '%s'" % options.mode)
            stop = True

    if options.forcekeep and options.mode == Mode.ARCHIVE:
        logerror("Cannot force keep on ARCHIVE mode (is already the default mode).")
        stop = True

    if options.forcedelete and options.mode == Mode.NRT:
        logerror("Cannot force delete on NRT mode (is already the default mode).")
        stop = True

    if not options.source or not options.destination or not options.mode:
        logerror("Missing basic options, source, destination and mode are needed.")
        stop = True

    if args:
        logerror("Invalid options: %s" % args)
        stop = True

    if stop:
        sys.exit(1) 

    if haspostman and options.mailusers:
        logger.setdestination(Postman.getnewmessagebody())

    # Get filelist to sync
    #
    files = get_filelist(options.source, options.mode)

    # Catch signal
    signal.signal(signal.SIGINT, signal_handler)

    # Main loop
    #
    nmerged  = 0
    ncopied  = 0
    nremoved = 0
    nerror   = 0

    ntotal = len(files)
    ncurrent = 0
    for current in files:
        try:
            if FORCESTOP:
                break

            # Check the file
            #
            status = check_file(options.source, current)

            # Check for errors
            #
            if status == CheckStatus.NOSYC: 
                logwarning("File, %s, failed checking, will not synchronize" % current)
                nerror += 1
                continue

            # Synchronize
            #
            (merged, copied, removed) = execute_merge(current, options.destination, options.mode, options.forcekeep, options.forcedelete, status == CheckStatus.FORCESORT, options.dryrun)

            loginfo( "[%05d/%05d] %s %s%s%s" % (ncurrent + nerror, ntotal, path.basename(current), "M" if merged else "-",  "C" if copied else "-",  "R" if removed else "-", ) )

            ncurrent += 1
            if merged: nmerged+=1
            if copied: ncopied+=1
            if removed: nremoved+=1

        except Exception as e:
            logerror("Uncatch exception: %s" % str(e))
            continue

    if FORCESTOP:
        logwarning("Not all files were processed")

    if options.dryrun:
        logwarning("This was a dry RUN")

    logwarning("Copied: %d Merged: %d Removed: %d Errors: %d" % (ncopied, nmerged, nremoved, nerror))

    if haspostman and options.mailusers:
        Postman.send(options.mailusers, "SdsMerge run on %s " % (str(UTCDateTime())))
