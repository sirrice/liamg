#!/bin/bash

if [ $# -lt 1 ]
then
    echo "./gen_tokens.sh [your gmail account ex: sirrice@gmail.com]"
    exit
fi


python xoauth.py --gen_oauth_token --user=$1

echo "copy the token and secret value into settings.py"