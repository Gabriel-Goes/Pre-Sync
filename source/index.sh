#!/bin/bash 

####
#
# Indexing script to be executed regularly.
# Depends on: awk, diff, find, mysql and mysqlimport
#
# Command line option is only:
#   --luke to remove dead database entries, entries that has no file associated.
#
# Bianchi jan/2015
#
##### Oo............................................

export MYUSER="root"                 # SQL user for connection
export MYPASS="root"                 # SQL user password
export MYDB="IPTINDEX"               # SQL Database
export MYHOST="localhost"            # SQL host machine
export TABLE="globalsds"             # SQL table to store information (1 per SDS)

export SDS="/SDS/"               # Base SDS folder
export EXTRASDS=$(cd $SDS && ls -1d  20*/* 2>/dev/null) # Internal SDS folder to scan
export TEMPDIR="/tmp"


[ ! -d "${TEMPDIR}" ] && mkdir -p ${TEMPDIR}

export currentlist=$(mktemp -p ${TEMPDIR})  # Support file for current SDS filelist
export sqllist=$(mktemp -p ${TEMPDIR})      # Support file for SQL filelist

[ -z "${MYPASS}" -o -z "${MYUSER}" -o -z "${MYDB}" -o -z "${MYHOST}" ] && echo "FIX ME, need DB parameters." && exit

function createtable() {
	cat << EOF | mysql --protocol TCP --host ${MYHOST} -u${MYUSER} -p${MYPASS} ${MYDB}
DROP TABLE IF EXISTS ${TABLE};
CREATE  TABLE ${TABLE} (
  filename VARCHAR(128) NOT NULL,
  mtime INT NOT NULL,
  stream CHAR(15) NOT NULL,
  start REAL NOT NULL,
  end REAL NOT NULL,
  dt REAL NOT NULL,
  INDEX stindex (stream),
  INDEX fname (filename)
)
EOF
}

function buildlocallist() {
	echo -n "Init local index ($(date)) ..."
	(for pat in $EXTRASDS
	do
		find $SDS"/"$pat -type f -wholename '*/*.D/*.*.*.*.D.????.???' -printf "%f\t%T@\n" | awk -F"\t" '{printf "%s\t%d\n",$1,int($2)}'
	done ) | sort > $currentlist
	echo " $(cat $currentlist | wc -l) entries ($(date))."
	return 0
}

function builddblist() {
	echo -n "Init  SQL  index ($(date)) ..."
	mysql -q --protocol TCP --host ${MYHOST} -s -N -r --user=${MYUSER} --password=${MYPASS} ${MYDB} -e 'SELECT filename, mtime FROM '${TABLE}';' 2> /dev/null | awk '{printf "%s\t%d\n",$1,int($2)}' | sort -S768M --parallel=3 -u > $sqllist
	echo " $(cat $sqllist | wc -l) entries ($(date))."
	return 0
}

function index() {
	basefilename=$1
	filename=$SDS/$(echo $1 | awk -F"." '{printf "%04d/%s/%s/%s.%s/%s",$6,$1,$2,$4,"D",$0}')
	if [ ! -f "$filename" ]; then
		echo "cannot be found in folder $filename." >&2
		return 1
	fi
	mtime=$(find $filename -printf "%T@" |awk '{print int($1)}')

	/home/suporte/bin/msi -tf 2 -T $filename |\
	 awk -v filename="$basefilename" -v mtime="$mtime" '{
	if (NF != 5) next;
	parts[0]=1;
	split($1,parts,"_");n=parts[1];s=parts[2];l=parts[3];c=parts[4];
	ts=$2;te=$3;
	dt=$4;
	printf "%s\t%d\t%s.%s.%s.%s\t%f\t%f\t%f\n",filename,mtime,n,s,l,c,ts,te,dt;
}'
	return 0
}

function cleanup() {
	toremove=$(mktemp -p ${TEMPDIR})
	doit="$1"

	did=0
	echo -n "Clean-up SQL  ... "

	diff  --suppress-common-lines $currentlist $sqllist | awk '$1 == ">" {print $2}' > $toremove
	if [ $(cat $toremove | wc -l) -gt 0 ]; then
		did=1
		echo ""
		echo "   * * * WARNING * * * "
		echo ""
		echo "Files in DB but not in filesystem:"
		cat $toremove | awk '{print " "$0}'

		if [ "$doit" == "--luke" ]; then
			cat $toremove | awk '{ printf "DELETE FROM '${TABLE}' WHERE filename = \"%s\";\n",$1}' | mysql --protocol TCP --host ${MYHOST} -u${MYUSER} -p${MYPASS} ${MYDB}
		fi

	fi

	[ $did -eq 0 ] && echo "done."
	rm -f $toremove
	return 0
}

function addnew() {
	importfile=${TEMPDIR}/${TABLE}.txt
	toadd=$(mktemp -p ${TEMPDIR})
	did=0
	chunks=1000

	diff  --suppress-common-lines $currentlist $sqllist | awk '$1 == "<" {print $2}' > $toadd

	rm -f ${TEMPDIR}/chunks_*
	split -l ${chunks} -a 5 $toadd ${TEMPDIR}/chunks_

	if [ $(cat $toadd | wc -l) -eq 0 ]; then
		rm -f $toadd
		return 1
	fi

	for chunk in ${TEMPDIR}/chunks_*
	do
		echo ""
		echo -n "Processing chunk ... $(basename $chunk)"
		did=0
		cat $chunk > $toadd
		if [ $(cat $toadd | wc -l) -ge 1 ]; then
			did=1
			echo ""
			echo "Indexing new files: "
			total=$(cat $toadd | wc -l)
			i=1
			[ -f $importfile ] && rm -f $importfile
			touch $importfile
			cat $toadd | while read filename
			do
				printf "  [%05d/%05d] %-28s\n" $i $total $filename
				index $filename >> $importfile
				i=$(( i + 1 ))
			done

			if [ $(cat $importfile | wc -l) -gt 0 ]; then
				echo ""
				echo ""
				echo "Cleanning: $(cat $toadd | wc -l ) file entries."
				cat $toadd | awk '{printf "DELETE FROM '${TABLE}' WHERE filename=\"%s\";\n",$1}' | mysql --protocol TCP --host ${MYHOST}  -u${MYUSER} -p${MYPASS} ${MYDB}
				[ $(cat $importfile | wc -l) -gt 0 ] && echo "Importing into DB:" && mysqlimport --protocol TCP  --host ${MYHOST}  --replace  -u${MYUSER} -p${MYPASS} --local -v ${MYDB} $importfile | awk '{print " ",$0}'
				echo ""
			fi
			rm -f $importfile
		fi
		[ $did -eq 0 ] && echo "done."
	done
	rm -f $toadd ${TEMPDIR}/chunks_*

	return 0
}

#createtable
#exit

# Build the local list
buildlocallist

# Build the DB list
builddblist

# Add new / update files and make a new list if needed
addnew && builddblist

# Search for missing files
cleanup $1

# Finish
rm -f "$currentlist" "$sqllist"
