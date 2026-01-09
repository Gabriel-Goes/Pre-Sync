import MySQLdb
import sys
import datetime
import calendar
from optparse import OptionParser

_D = "IPTINDEX"
_P = "root"
_U = "root"
_H = "localhost"

class segment(object):
	def __init__(self, s, e, dt):
		self.s    = s
		self.e    = e
		self.dt   = dt
		self.pall = None
		self.__as_date = False
		self.format = None
	
	def __sub__(self, other):
		return datetime.timedelta(0,self.s - other.e,0)

	def invertsense(self):
		if self.pall is None:
			return None
		
		cur = self
		ns = segment(cur.e, cur.pall.s, cur.pall.dt)
		tip = ns
		cur = cur.pall

		while cur is not None and cur.pall is not None:
			ns = ns.extend(cur.e, cur.pall.s, cur.pall.dt)
			cur = cur.pall

		return tip

	def extend(self, s, e, dt):
		if (self.dt != dt):
			self.pall = segment(s,e, dt)
			return self.pall

		if (s-self.e) >= 1.5/self.dt:
			self.pall = segment(s,e, dt)
			return self.pall

# 		if (s-self.e) <= 0.5/self.dt:
# 			print "Warning: 1 sample overlaps."

		self.e = e

		return self

	def printDates(self, true_or_false = None, julian = False):
		if true_or_false is None:
			return self.__as_date
		
		self.__as_date = bool(true_or_false)
		
		if self.__as_date:
			if julian:
				self.__format = "%Y-%jT%H:%M:%S.%f"
			else:
				self.__format = "%Y-%m-%dT%H:%M:%S.%f"
		else:
			self.__format = None
		
		return

	def overlap(self, other):
		if other.e < self.s: return (None, None)
		if other.s > self.e: return (None, None)
		return (max(other.s, self.s),min(other.e, self.e))

	def match(self, other):
		tip = None
		ns  = None
		cur = self
		while cur:
			if cur.s > other.e:
				break
			
			if cur.e < other.s:
				cur = cur.pall
				continue
			
			(s, e) = cur.overlap(other)

			if s == None or s == None:
				continue

			if ns is None:
				ns = segment(s, e, cur.dt)
				tip = ns
			else:
				ns = ns.extend(s, e, cur.dt)

			cur = cur.pall
		return tip

	def mergeGaps(self, max_gap_size = 0.0):
		z = self

		while z:
			if z.pall is None:
				z = z.pall
				continue
			
			df = (z.pall - z).total_seconds()
			if df <= max_gap_size:
				z.e = z.pall.e
				z.pall = z.pall.pall
				continue
			
			z = z.pall
		
		return self

	def cut(self, t1, t2, copy = False):
		tip = self.__copy__() if copy else self
		
		# Parse t1 & t2
		t1 = calendar.timegm(t1.timetuple()) if t1 is not None else t1
		t2 = calendar.timegm(t2.timetuple()) if t2 is not None else t2

		if t1 is not None:
			if t2 is not None and tip.s > t2: return None
			while tip.e < t1:
				tip = tip.pall
				if tip is None:
					return tip
			if t2 is not None and tip.s > t2:
				return None
			if tip.s < t1:
				tip.s = t1
		
		if t2 is not None:
			if tip.e > t2:
				tip.e = t2
				tip.pall = None
				return tip
			curr = tip
			while curr.e < t2:
				if curr.pall is not None and curr.pall.s > t2:
					break
				curr = curr.pall
				if curr is None: return tip
			curr.pall = None
			if curr.e > t2:
				curr.e = t2

		return tip

	def totalDataLength(self):
		tip = self
		
		df = 0.
		while tip:
			df += (tip.e - tip.s)
			tip = tip.pall
		
		return datetime.timedelta(seconds = df)

	def totalLength(self):
		tip = self
		
		s = tip.s
		e = None
		while 1:
			if tip.pall is None: break
			tip = tip.pall
		e = tip.e
		
		return datetime.timedelta(seconds = (e-s))

	def totalGaps(self):
		tip = self
		
		df = 0.
		while tip:
			if tip.pall is not None:
				df += (tip.pall - tip).total_seconds()
			tip = tip.pall

		return datetime.timedelta(seconds = df)

	def __copy__(self):
		tip = self
		
		tipdc = segment(self.s, self.e, self.dt)
		dc = tipdc
		
		while tip:
			dc.pall = None if tip.pall is None else segment(tip.pall.s, tip.pall.e, tip.pall.dt)
			dc = dc.pall
			tip = tip.pall
		
		return tipdc

	def __str__(self):
		s  = self.s
		e  = self.e
		dt = self.dt
		df = (self.pall - self).total_seconds() if self.pall else None
		
		if self.__as_date:
			s = datetime.datetime.utcfromtimestamp(s).strftime(self.__format)
			e = datetime.datetime.utcfromtimestamp(e).strftime(self.__format)
			df =  self.pall - self if self.pall else None
		
		return "%s %s %s %s" % (s, e, dt, df)

def parseDate(value):
	if value == "": return None
	if value == None: return None
	
	value = value.replace("_","-")
	y,m,d = value.split("-")

	return datetime.datetime(int(y),int(m),int(d))
	
def loadChannels(table, pattern = '*', H = _H, U = _U, P = _P, D = _D):
	db = MySQLdb.connect(host = H, user = U, passwd = P, db = D)

	pattern = pattern.replace("*","%%")
	cursor = db.cursor()
	cursor.execute("SELECT DISTINCT stream from %s where stream LIKE '%s'" % (table,pattern))
	stream = []
	while True:
		try:
			ss = cursor.fetchone()
			stream.append(ss[0])
		except TypeError:
			break
	return stream

def loadStream(stream, table, first = None, last = None, H = _H, U = _U, P = _P, D = _D):
	db = MySQLdb.connect(host = H, user = U, passwd = P, db = D)

	cursor = db.cursor()
	SQL = "SELECT start, end, dt from %s where stream = '%s'" % (table, stream)
	if first is not None:
		SQL += ' and end > %s' % calendar.timegm(first.timetuple())
	if last is not None:
		SQL += ' and start < %s' % calendar.timegm(last.timetuple())
	SQL +=  " ORDER BY start"
	cursor.execute(SQL)

	tip = None
	cur = None
	while True:
		try:
			s,e,dt = cursor.fetchone()
		except TypeError:
			break

		if tip is None:
			tip = segment(s,e,dt)
			cur = tip
			continue

		cur = cur.extend(s,e,dt)
	cursor.close()
	
	return tip

def dump_segments(z, options, where = sys.stdout):
	if z is None:
		return
	
	z.printDates(options.asdate, options.asjulian)
	print >>where," ",z

	z = z.pall
	while z:
		z.printDates(options.asdate, options.asjulian)
		print >>where," ",z
		z = z.pall

def dump_segments_start_end(z, options, where = sys.stdout):
	_format = "%Y-%jT%H:%M:%S.%f" if options.asjulian else "%Y-%m-%dT%H:%M:%S.%f"
	first = z
	zold = z
	while z:
		zold = z
		z = z.pall
	last = zold

	start = first.s
	end   = last.e

	if options.asdate:
		start = datetime.datetime.utcfromtimestamp(start).strftime(_format)
		end = datetime.datetime.utcfromtimestamp(end).strftime(_format)

	print >>where, " ", start, end

def dump_gmt_segments(z, options, where = sys.stdout):
	def tostring(v, ref, fmt):
		if ref is not None:
			return str(v - ref)
		return datetime.datetime.utcfromtimestamp(v).strftime(fmt)
	
	def m(v, t):
		v = datetime.datetime.utcfromtimestamp(v)
		if t == "O": return v.month
		if t == "Y": return v.year
		if t[0] == "C": return (1 if t.find(",") == -1 else t.split(",")[1])
		if t == "S":
			v = m.seq
			m.seq += 1
			return v
		raise Exception("Wow")
	m.seq = 0
	
	if z is None: return
	
	_format = "%Y-%jT%H:%M:%S.%f" if options.asjulian else "%Y-%m-%dT%H:%M:%S.%f"
	
	reference = None
	if options.gmtref:
		reference = parseDate(options.gmtref)
		reference = calendar.timegm(reference.timetuple())

	print >>where,">"
	mm = m(z.s, options.gmtyaxis)
	print >>where, tostring(z.s, reference, _format), mm
	print >>where, tostring(z.e, reference, _format), mm

	z = z.pall
	while z:
		print >>where,">"
		mm = m(z.s, options.gmtyaxis)
		print >>where, tostring(z.s, reference, _format), mm
		print >>where, tostring(z.e, reference, _format), mm
		z = z.pall

def make_cmdline_parser():
	# Create the parser
	#
	parser = OptionParser(usage="%prog [options] <-s stream> <-m mode> <-f> <-w>", add_help_option = True)
	
	parser.add_option("-s", "--stream", type="string", dest="stream", help="Define specific stream as NET.STA.LOC.CHA, or use wildcards, eg. *CHA*", default=None)
	
	parser.add_option("-q", "--quick", action="store_true", dest="quick", help="Show just a quick simple overview of the timespans")
	
	parser.add_option("-m", "--mode", type="string", dest="mode", help="Mode of operation: GAPS or DATA", default='DATA')
	
	parser.add_option("-f", "--match", type="string", dest="match", help="Table that will be searched for gap filling data, normally 'SDS'", default=False)
	
	parser.add_option("-t", "--table", type="string", dest="table", help="Table that will be searched for gaps, normally 'global'", default='globalsds')
	
	parser.add_option("-w", "--write", action="store", dest="save", help="Save a report (txt file) to disk", default=False)
	
	parser.add_option("-d", "--dates", action="store_true", dest="asdate", help="Show segments as dates?", default=False)
	
	parser.add_option("-g", "--merge-gaps", type="float", dest="merge", help="Merge gaps smaller than given size", default=False)

	parser.add_option("-j", "--as-julian-dates", action="store_true", dest="asjulian", help="Use julian days", default=False)

	parser.add_option("-i", "--interval", type="string", dest="daterange", help="Range for cutting dates", default=None)

	parser.add_option("", "--dump-channels", action="store_true", dest="streamsonly", help="Show a list of streams in database", default=False)

	##
	# Gmt output options
	##
	parser.add_option("", "--gmt", action="store_true", dest="asgmt", help="Print a format gmt file", default=False)

	parser.add_option("", "--gmtref", type="string", dest="gmtref", help="Gmt reference", default=None)
	
	parser.add_option("", "--gmtyaxis", type="string", dest="gmtyaxis", help="Y-axis value for the GMT output", default="C")

	return parser

if __name__ == "__main__":
	m = dump_segments
	
	date_start = None
	date_end   = None
	
	#
	## Parse command line
	parser = make_cmdline_parser()
	(options, args) = parser.parse_args()
	
	if options.mode not in ('GAPS', 'DATA'):
		print 'Please select a valid operation mode: GAPS or DATA.'
		exit(-1)
	
	if options.table not in ('globalsds'):
		print 'Table should be one of: globalsds.'
		exit(-1)

	if options.merge is not False and options.merge <= 0.0:
		print 'Cannot merge gaps with size <= 0.0'
		exit(-1)
	
	if options.stream:
		st = options.stream
	else:
		st = '*'
	
	if options.asjulian:
		options.asdate = True
	
	if options.gmtyaxis and options.gmtyaxis[0] not in ["S", "C", "O", "Y"]:
		print 'Invalid option for gmt Y axis'
		exit (-1)
	
	if options.quick:
		m = dump_segments_start_end
	
	if options.asgmt:
		m = dump_gmt_segments
	
	if options.daterange:
		try:
			a,b = options.daterange.split(":")
			try:
				date_start = parseDate(a)
			except Exception,e:
				print e, " on:",a
				raise e

			try:
				date_end = parseDate(b)
			except Exception,e:
				print e, " on:",b
				raise e
		except:
			print "Need a date range like 2016-01-01:2017-01-01 any of dates can also be empty"
			exit(-1)
	
	g = loadChannels(options.table, st)
	
	out = sys.stdout
	if options.save:
		out = open(options.save, "w")
	
	if options.streamsonly:
		
		#if options.table == 'frozen':
		#	g.extend(loadChannels('sds', st))
		#else:
		#	g.extend(loadChannels('frozen', st))
		
		for s in set(g):
			print >>out,s
		out.close()
		exit(0)
	
	#
	## Load Segments from FROZEN or SDS given a pattern
	#
	for s in set(g):
		if not options.asgmt:
			print >>out, s, "%s=" % (options.table)
		streams = loadStream(s, options.table)
		streams = streams.cut(date_start, date_end)
		if streams == None:
			print "  -- no data found in interval --"
			continue
		
		if options.merge:
			streams.mergeGaps(options.merge)
		
		if not options.match:
			if options.mode == 'GAPS':
				streams = streams.invertsense()
				if streams == None:
					print " -- no gaps found in interval -- "
					continue
			m(streams, options, out)
			tg = streams.totalGaps()
		
			if not options.asgmt:
				print "  --Total %s in Serie=%s" % ("Gaps" if options.mode == 'DATA' else "Data", tg)
		#
		## Perform the matching of the SDS to the inverted FROZEN
		#
		else:
			streamsmatch = loadStream(s, options.match)
			if (streams != None) and (streamsmatch != None):
				print "Processing:"
				streams = streams.invertsense()
				f = streams
				while f:
					gaps = streamsmatch.match(f)
					if gaps:
						f.printDates(options.dates)
						print >>out,"%s=" % (options.table),f
						m(gaps, options, out)
					f = f.pall
				print ""
			else:
				print "Cannot process, one of the SDSs has no entries."
	out.close()

