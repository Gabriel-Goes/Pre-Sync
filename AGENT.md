# Agent
This agent can read the log files from the last execution so can help debug;

./Pre-Sync/PARFILES/*
./Pre-Sync/LOGS/SYNC_20260109_180702.xtrace
./Pre-Sync/LOGS/test.log
./BC9_20251211/rt2ms.msg
./BC9_20251211/parfile.txt

this files can help debug
SYNC_YYYYMMDD_HHMMSS.xtrace is the debug file, and need more attention to;
use the most recent file, always, the last file will be the last executed process;

the script
./Pre-Sync/SYNC.sh is the main script; the one that has been executed;
./LOGS/test.log is the log outputed when the mains script breaks without finishing;
./LOGS/SYNC_YYYYMMDD_HHMMSS.xtrace is the debug log when ./SYNC.sh is executed with -d flag;
