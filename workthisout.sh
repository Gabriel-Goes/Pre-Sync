#!/bin/bash
## Código desenvolvido por M. Bianchi <m.bianchi@iag.usp.br
## Revisado por Gabriel Góes Rocha de Lima <gabrielgoes@usp.br>
##

target=/SDS
luke=0
bf=$(basename $(pwd))
log=${bf}.log
stop=1

[ ! -d "sds" ] && echo "No sds folder found" && exit

while [ $# -ge 1 ]
do
	case $1 in
	--nostop)
		stop=0
		;;
	--luke)
		[ ! -f "$log" ] && echo "Dont be dumb - check the force first !" && exit
		luke=1
		;;
	*)
		echo "Bad option: $1"
		echo "Options are: --luke, --no-frozen"
		exit
		;;
	esac
	shift
done

# source  /opt/miniconda2/bin/activate

cat <<EOF

  ** Watch Out **

Date is $(date)
Merging to: $target
Running with luke: $luke

EOF

if [ $stop -eq 1 ]; then
  read -p "GO (s/n)?" ans
  [ "$ans" != "s" ] && echo "Bailling out !" && exit
fi

if [ -f "$log" -a $luke -eq 0 ]; then
 read -p "Log file exists, continue (s/n)?" ans
 [ "$ans" != "s" ] && exit
fi

if [ $luke -eq 1 ]; then
(
 echo ""
 echo " This is a real merge "
 echo ""
 python ~suporte/bin/sdsmerge.py -m ARCHIVE -v -s sds/ -d $target 2>&1
 exit
) | tee -a $log

else

(
 echo ""
 echo "*** Step (1) ***"
 echo "File size is:  $(du -ms sds/)"
 echo "File count is: $(find sds -type f | wc -l)"
 [ $stop -eq 1 ] && read -p "Continuar (s/n)" ans || ans="s"
 [ "$ans" != "s" ] && echo "Stopping on request!" && exit

 echo ""
 echo "*** Step (2) ***"
 echo "Listing network / station / channels on tree:"
 find sds/ -type f -exec msi {} \; | awk -F"," '{print $1}' | sort -u
 find sds/ -type f | awk -F"/" '{print $NF}' | awk -F"." '{print $1,$2}' | sort -u
 [ $stop -eq 1 ] && read -p "Continuar (s/n)" ans || ans="s"
 [ "$ans" != "s" ] && echo "Stopping on request!" && exit

 echo ""
 echo "*** Step (3) ***"
 echo "Listing days availability:"
 for d in $(find sds/ -mindepth 4 -type d | awk -F"/" '{print $5$2,$0}' |\
   sort -r | awk '{print $2}'); do (echo -n "$d "; cd $d && ls -1 |\
   sort | awk -F"." '{if (NR==1) start=$6"/"$7; end=$6"/"$7} END {print start, end}'); done
 [ $stop -eq 1 ] && read -p "Continuar (s/n)" ans || ans="s"
 [ "$ans" != "s" ] && echo "Stopping on request!" && exit


 echo ""
 echo "*** Step (4) ***"
 echo "Checking for internal gaps"
 for d in $(find sds/ -mindepth 4 -type d)
 do
 echo "Channel -> $(basename $d)"
 (cd $d && msi -T -tg  *) | awk '{print "  ",$0}'
 done
 [ $stop -eq 1 ] && read -p "Continuar (s/n)" ans || ans="s"
 [ "$ans" != "s" ] && echo "Stopping on request!" && exit

 echo ""
 echo "*** Step (5) ***"
 echo "Checking for overlapping files"
 n=0
 for f in $(find sds/ -type f)
 do
   p=$(echo "$(basename $f)" | awk -F"." -v target="$target" '{printf "%s/%d/%s/%s/%s.%c/%s\n",target,$6,$1,$2,$4,$5,$0}')
   [ ! -f "$p" ] && continue
   diff -q $f $p
   n=$(( n + 1 ))
 done
 [ $n -gt 0 ] && echo -e "\n$n files overlaps\n" || echo "No overlapps!"
 [ $stop -eq 1 ] && read -p "Continuar (s/n)" ans || ans="s"
 [ "$ans" != "s" ] && echo "Stopping on request!" && exit


 #echo ""
 #echo "*** Step (6) Doing msmod ***"
 #for folder in $(find sds/ -mindepth 4 -type d)
 #do
 #  (
 #    cd $folder
 #    msmod --quality M -i *.??? 2>&1 | awk '{print " "$0}'
 #  )
 #done
 #[ $stop -eq 1 ] && read -p "Continuar (s/n)" ans || ans="s"
 #[ "$ans" != "s" ] && echo "Stopping on request!" && exit

 echo ""
 echo "*** Dry Run ***"
 python ~suporte/bin/sdsmerge.py -m ARCHIVE -v -s sds/ -d $target -n 2>&1
 echo ""

 #echo ""
 #echo "CHECK FDSN"
 #echo ""
 #bash ../checkfdsn.sh $log
) | tee -a $log

fi
