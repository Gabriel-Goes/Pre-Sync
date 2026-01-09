#!/home/suporte/seiscomp/bin/seiscomp-python
#
import os
from seiscomp import mseedlite, logs
import sys
import datetime
import subprocess
import re

from optparse import OptionParser


VERSION = "2014.098"
LOG_FILE = sys.stderr

def warn(message):
    print message


class MSFile(object):

    def __init__(self, directory, filename, logfile = None, verbose = False):
        self._verbose = verbose
        self._testboard = {}
        self._validSDSpath = True
        ## Attach the log file
        self._log = logfile if type(logfile) == file else sys.stderr
        ## Save the file path
        self.directory = directory
        self.filename = filename
        ## Parse
        try:
            print >>self._log,"%s:" % (self.filename)
            (self.net, self.sta, self.loc, self.cha, self.mstype, self.year, self.jday) = self.filename.split('.')
            self.year=int(self.year)
            self.jday=int(self.jday)
            self.s = datetime.datetime.now().strptime("%s-%sT%s:%s:%s" % (self.year, self.jday, 0,0,0),"%Y-%jT%H:%M:%S")
            self.e = self.s + datetime.timedelta(1)
        except ValueError:
            print >>self._log,"Error parsing %s on %s" % (self.filename, self.directory)
            print >>self._log," Filename is not of SDS type NN.STA.LOC.CHA.TYP.YEAR.JDAY"
            self._validSDSpath = False
        except Exception as e:
            print >>self._log,"Error parsing %s on %s" % (self.filename, self.directory)
            print >>self._log," %s" % str(e)
            self._validSDSpath = False

        ## Run
        try:
            ## Run the check sequence
            self.check()
        except Exception as e:
            print >>self._log,"Error checking %s on %s" % (self.filename, self.directory)
            print >>self._log," %s" % str(e)

    def _checkStartTime(self, rec):
        if not self._validSDSpath: return False
        if rec.begin_time >= self.s and rec.begin_time < self.e:
            return
        raise Exception(" checkStartTime:: Record start time does not fit day.")

    def _checkCodes(self, record):
        if not self._validSDSpath: return False
        _raise = False
        if record.net != self.net:
            _raise = True
        if record.sta != self.sta:
            _raise = True
        if record.loc != self.loc:
            _raise = True
        if record.cha != self.cha:
            _raise = True
        if _raise:
            raise Exception(
                " checkCodes:: (%s.%s.%s.%s does not match current file.)"
                % (record.net, record.sta, record.loc, record.cha))

    def _checkSequence(self, previousrecord, record):
        _raise = False
        _message = []

        if not previousrecord:
            return

        _dt2 = datetime.timedelta(0, (1.0 / record.fsamp) / 2.0)

        ##
        # On comments P = Previous C = Current
        ##
        if ( record.begin_time + _dt2 ) < previousrecord.begin_time:
            if ( record.end_time + _dt2 ) < previousrecord.begin_time:
                _raise = True
                #print record.begin_time, record.end_time, previousrecord.begin_time, previousrecord.end_time
                _message.append("goes back (whole record) [C--C P--P]")
            elif ( record.end_time + _dt2 ) < previousrecord.end_time:
                _raise = True
                _message.append( "goes back (partial overlap start) [C-P-C-P]")
            else:
                _raise = True
                _message.append( "goes back (total overlap) [C-P--P-C]")
        elif ( record.begin_time + _dt2 ) < previousrecord.end_time:
            if ( record.end_time + _dt2 ) < previousrecord.end_time:
                _raise = True
                _message.append("goes back (complete inside) [P-C--C-P]")
            else:
                _raise = True
                _message.append("goes back (partial overlap end) [P-C-P-C]")
        else:
            return 0

        if _raise:
            raise Exception(" checkSequence:: " + ",".join(_message))

    def _checkDuplicate(self, record, reclist):
        date = str(record.begin_time)
        if date in reclist:
            raise Exception(" checkDuplicate:: Duplicate %s" % date)
        reclist.append(date)

    def tests(self):
        return self._testboard.keys()

    def testSucceed(self, testName = None):
        '''
        Returns True when a test succeed, otherwise false
        Raises Exception when a test is not found
        '''
        if testName in self._testboard:
            return self._testboard[testName]
        raise Exception("Test %s is not available" % testName)

    def check(self):
        infile = file(os.path.join(self.directory,self.filename))
        records = mseedlite.Input(infile)
        errors = []
        previousrecord = None
#         reclist = []
        i = 0

        self._testboard['checkCodes'] = True
        self._testboard['checkSequence'] = True
        self._testboard['checkStartTime'] = True
        self._testboard['checkDuplicate'] = True
        for record in records:
            i += 1
            ## Check Codes
            try:
                self._checkCodes(record)
            except Exception as e:
                self._testboard['checkCodes'] = False
                if str(e) not in errors:
                    if self._verbose:
                        errors.append(str(i) + " " + str(e))
                    else:
                        errors.append(str(e))
#             ## Check Duplicates
#             try:
#                 self._checkDuplicate(record, reclist)
#             except Exception,e:
#                 self._testboard['checkDuplicate'] = False
#                 if str(e) not in errors:
#                     if self._verbose:
#                         errors.append(str(i) + " " + str(e))
#                     else:
#                         errors.append(str(e))
            ## Check Sequence
            try:
                self._checkSequence(previousrecord, record)
            except Exception,e:
                self._testboard['checkSequence'] = False
                if str(e) not in errors:
                    if self._verbose:
                        errors.append(str(i) + " " + str(e))
                    else:
                        errors.append(str(e))
            ## Check Start time
            try:
                self._checkStartTime(record)
            except Exception as e:
                self._testboard['checkStartTime'] = False
                if str(e) not in errors:
                    if self._verbose:
                        errors.append(str(i) + " " + str(e))
                    else:
                        errors.append(str(e))

            ## Save current record on pipe
            previousrecord = record

        # Close file
        infile.close()

        # Present erros
        if len(errors):
            for line in errors:
                print >>self._log," %s" %line
        self._log.flush()

class SDS (object):

    def __init__ (self, path = None, log = sys.stderr, y1 = 1980, y2 = 2500, patterns = None, verbose = False):
        self.path = path
        self._runScart = False
        self._checkMS = False
        self._fixSort = False
        self._verbose = verbose
        self._logfile = log
        self.y1 = int(y1)
        self.y2 = int(y2)
        self.patterns = patterns

    def enableScart(self, destinationSDS):
        if self._fixSort:
            raise Exception("Cannot clone while fixing sorting issues.")

        if not os.path.isdir(destinationSDS):
            os.mkdir(destinationSDS)
        else:
            warn("Supplied SDS folder already exists ... will not merge !")
            sys.exit()
        self._scartSDS = destinationSDS
        self._runScart = True

    def enablecheckMS(self):
        self._checkMS = True

    def enableFixSort(self):
        if self._runScart:
            raise Exception("Cannot fix sorting issues while clonning.")
        if not self._checkMS:
            warn("Enabling checks since you required to sort files.")
            self._checkMS = True
        self._fixSort = True

    def _scart(self, infile):
        cmd = "cat %s | scart %s" % (infile, self._scartSDS)
        os.system(cmd)

    def _sort(self, infile):
        subprocess.call(["dataselect","-Pr","-rep","-mod", "-nb",infile], stdout=self._logfile, stderr=self._logfile)

    def runone(self, fileitem):
        print >>self._logfile,"Starting ONE Job @ %s" % str(datetime.datetime.now())
        self._logfile.flush()
        if self._runScart:
            raise Exception("Cannot run scart with one file !")

        filename = os.path.basename(fileitem)
        root = os.path.dirname(fileitem)

        if self._checkMS:
            ms = MSFile(directory=root, filename=filename, logfile=self._logfile, verbose=self._verbose)

            ## Fix Sorting issues
            if self._fixSort and 'checkSequence' in ms.tests() and not ms.testSucceed('checkSequence'):
                self._sort(os.path.join(root, filename))
            del ms

        pass


    def run(self):
        if self.path is None or not os.path.isdir(self.path):
            raise Exception("Folder '%s' is invalid" % self.path)

        if self._runScart is False and self._checkMS is False:
            raise Exception("Nothing to do, clone and check is disabled")

        print >>self._logfile,"Starting Job @ %s" % str(datetime.datetime.now())
        self._logfile.flush()
        for year in range(self.y1, self.y2 + 1):
            print >>self._logfile,"Starting Year %04d @ %s" % (year, str(datetime.datetime.now()))
            tree=os.walk(os.path.join(self.path,str(year)))
            for root, _, files in tree:
                files.sort()
                for eachfile in files:

                    ## If a pattern is given, then check if file name matches the given pattern and also the year
                    if (self.patterns) and "".join(eachfile.split(".")[5]) == str(year):
                        match = False
                        for pattern in self.patterns :
                            if re.match(pattern, ".".join(eachfile.split(".")[0:4])):
                                match = True
                        if not match:
                            continue

                    print >>sys.stderr, os.path.join(root,eachfile)

                    ## Run Checks
                    if self._checkMS:
                        ms = MSFile(directory=root, filename=eachfile, logfile=self._logfile, verbose=self._verbose)

                        ## Fix Sorting issues
                        if self._fixSort and 'checkSequence' in ms.tests() and not ms.testSucceed('checkSequence'):
                            self._sort(os.path.join(root,eachfile))
                        del ms

                    ## Run Scart clonning
                    if self._runScart:
                        self._scart(os.path.join(root,eachfile))

        print >>self._logfile,"Job Done @ %s" % str(datetime.datetime.now())
        self._logfile.flush()

def _error(message):
    print >>LOG_FILE," ",message

def parsepat(pattern):
    if pattern.count(".") == 0:
        pattern += ".*.*.*"
    elif  pattern.count(".") == 1:
        pattern += ".*.*"
    elif  pattern.count(".") == 2:
        pattern += ".*"
    elif pattern.count(".") == 3:
        pass
    else:
        raise Exception("Pattern is invalid")

    return pattern.replace(".","[.]").replace("*",".*").replace("?",".")

if __name__ == '__main__':
    parser = OptionParser(usage="%prog [options] -s|--source-sds <Source SDS folder>",version="%prog v" + VERSION)

    parser.add_option("-l","--log-file", type="string", dest="log_file",
                      help="Filename to contain the log resulted from the checks (defaults STDERR", default=None)

    parser.add_option("","--one-file", type="string", dest="one_file",
                      help="Indicate one mini-seed file for checking.", default=None)

    parser.add_option("-s","--source-sds", type="string", dest="source_sds",
                      help="Folder containing the original SDS structure.", default=None)

    parser.add_option("-d","--destination-sds", type="string", dest="destination_sds",
                      help="Non-existing folder that will contain the cloned/cleanned destination SDS (set this option to enable the clonning).", default=None)

    parser.add_option("","--start-year", type="string", dest="start_year",
                      help="Start Year to run in the form y1[:y2] (Defaults to 1980)", default=None)

    thisyear = datetime.datetime.now().year
    parser.add_option("","--end-year", type="string", dest="end_year",
                      help="End Year to run in the form y1[:y2] (Defaults to  %d)" % thisyear, default=None)

    parser.add_option("-n", "--no-check", action="store_false", dest="check",
                      help="Disable checking the input files", default=True)

    parser.add_option("", "--sort", action="store_true", dest="sort",
                      help="Enable file sorting inplace, will use the dataselect tool from IRIS (options -Pr/-rep).", default=False)

    parser.add_option("-p","--pattern", type="string", dest="patternList",
                      help="Pattern to search and fix files", default=None)

    parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                      help="Be verbose in check reports.", default=False)

    ## Parse CMD LINE
    (options, args) = parser.parse_args()

    ## Attach error log to catch failures from mseedlite
    logs.error = _error
    if options.log_file:
        LOG_FILE = file(options.log_file, "a")

    ## Check if a pattern was given and parse it
    patternList = options.patternList
    if patternList:
        patterns = []
        if patternList.find(",") != -1:
            patternList = patternList.split(",")

        else:
            patternList = [patternList]

        for pattern in patternList :
            pattern = parsepat(pattern)
            patterns.append(pattern)
    else:
        patterns = None

    y1 = 1980
    y2 = thisyear

    ## Parse the years
    try:
        if options.start_year:
            y1 = int(options.start_year)
    except:
        _error("Invalid start year, %s" % options.start_year)
        sys.exit()

    try:
        if options.end_year:
            y2 = int(options.end_year)
    except:
        _error("Invalid end year, %s" % options.end_year)
        sys.exit()

    if y1 > y2:
        _error("Year %d <= %d, aborting." % (y1,y2))
        sys.exit()

    if not options.source_sds and not options.one_file:
        _error("Option -s/--source-sds")
        _error(" or ")
        _error("Option --one-file are mandatory.")
        sys.exit()

    if options.one_file:
        if not options.check:
            _error("Option -n/--no-check is invalid with --one-file.")
            sys.exit()
        if options.destination_sds:
            _error("Option -d/--destination-sds cannot be used with --one-file.")
            sys.exit()
        if options.source_sds:
            _error("Options --one-file and --source-sds are independent, cannot be used together.")
            sys.exit()



    ## Prepare the SDS walk class
    sds = SDS(options.source_sds, LOG_FILE, y1, y2, patterns, options.verbose)

    ## Enable the clone
    if options.destination_sds:
        sds.enableScart(options.destination_sds)

    ## Enable the check while processing
    if options.check:
        sds.enablecheckMS()

    if options.sort:
        sds.enableFixSort()

    ## Run
    try:
        if options.one_file:
            sds.runone(options.one_file)
        else:
            sds.run()
    except Exception as e:
        _error("Could not start job, %s" % str(e))

    ## Close the log file
    LOG_FILE.close()
