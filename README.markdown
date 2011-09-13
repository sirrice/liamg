Tool to download your gmail headers, store them in a sqlite database.  Includes
a tool that plots a histogram of the number of emails exchanged with friends.

Python Modules
--------
 
This requires the following modules:

 - dateutil
 - psycopg2 (http://initd.org/psycopg/download/)
 - pyparsing

For the other packages, they are included in `modules/`.  
For example, you can install dateutil using the following

    cd `modules`
    tar -xf python-dateutil-1.5.tar.gz
    cd python-dateutil-1.5
    sudo python setup.py install

This should install it in `$PYTHONHOME/site-packages/`
To check that it works do

    python
    >>> import dateutil    

Databases
-------

Inboxdr uses PostgreSQL


Getting started
------------

Create the database and user

    createdb liamg
    createuser liamg

Create your private settings file

    cd liamgweb
    cp private_settings.py.tmpl private_settings.py

Edit your private settings to use the correct database backend.  Do not add or commit
`private_settings.py`!  This is customized for your own deployment.

Download your entire inbox's message headers and enter your username and password.

    python getdata.py 2> err

If you only want a subset, open `getdata.py` and edit `label_string` 
and `search_string` in `download_headers`



Things to checkout
-----------------

D3 declarative visualizations

    http://mbostock.github.com/d3/


TODOs
--------------

Eugene

 * Create message download pipeline
 * Separate header download and message contents download
 * Modularize latencies calculation
 * Integrate latencies calculation into message download pipeline

Lydia 

 * Deploy onto AWS

Chris

 * Get SQL queries working (done for the Rec'd messages)
 * Integrate backend scripts with front end for the Sent messages

Melinda / Allin

 * Frontend?

Ravi

 * Scripts/Backend

author: sirrice