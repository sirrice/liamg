#!/bin/bash

if [ $# -lt 1 ]
then
    echo "./analyzedb.sh [your database name]"
    exit
fi

sqlite3 $1 < "../analysis/analyze.sql"
echo "database set up with analysis tables"