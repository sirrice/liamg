Tool to download your gmail headers, store them in a sqlite database.  Includes
a tool that plots a histogram of the number of emails exchanged with friends.

Requires
--------
 
This requires the following modules:

 - matplotlib
 - dateutil
 - numpy

You can install numpy and matplotlib on ubuntu using 

    sudo apt-get install python-numpy
    sudo apt-get install python-matplotlib

Otherwise, you can download and install numpy from 

    http://new.scipy.org/download.html

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


Getting started
------------

Run the following script, follow the instructions and copy down the token
and secret.

	sh gen_tokens.sh <username@gmail.com>

Add tokens into settings.py

    token = '<your token>' 
    secret = '<your secret>'
    gmailaddr = '<yourname@gmail.com>'

Download your entire inbox's message headers

    python getdata.py 2> err

If you only want a subset, open `getdata.py` and edit `label_string` and `search_string` in `download_headers`

Once your headers are downloaded, you can visualize your correspondence

    python histogram.py
    
    enter part of a friend's name and I'll plot a histogram of your email to him/her
    enter a blank line to exit
    name: <type in a part of your friend's name.  case insensitive>


author: sirrice