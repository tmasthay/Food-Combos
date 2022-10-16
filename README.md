# Food-Combos
Small script that scrapes Wiki pages to find a bunch of different dishes.

# installation
html2text should be the only dependency and can be installed by pip or conda. Just perform one of the following commands
```
conda install html2text
```
or
```
pip install html2text
```
The only other packages used are ```re```, ```os```, and ```subprocess```, which I believe are standard with a Python installation. 
However, if not, perform a similar command to the above if Python cannot find one or more of those modules.
# update.py
This script updates the database of data.

# cross.py
This script lets you write combinations of different files to help come up with fusion food ideas. 
**This program is the main driver.** To generate the database, simply set the "update" flag in command line to true.

# get_started.sh
This script gets you started generating the database and doing a few search queries. ```cross.py``` has six command line arguments, of which the only 
mandatory one is ```input_files```. ```get_started.sh``` is just two lines; the first makes the database and explicitly uses all command line arguments for illustration purposes; the second line shows how you will likely want to use most of the time, with most options defaulted, outside of input and output file names.

To get started, just perform the following from command line!

```
chmod +x get_started.sh
./get_started.sh
```

Below is a description of the command line arguments for ```cross.py```.

```
ext -- desired file extension for your output file -- defaults to ".txt"
input_files -- the files you which to mix together -- MANDATORY
out_file -- path you wish to place output file, will generate path if folders not created yet -- defaults to "out.txt"
empty -- when True, this will add the empty string to your lists, i.e., if you mix three files, it will do all order-2 mixes also -- defaults to False
cartesian -- when True, will explicitly list all possible combos of your two files, else will just list them in column format -- defaults to False
update -- when True, this will run update.py to add to the database, else will just do parsing -- defaults to False
```

**SOME IMPORTANT NOTES BELOW**

**(1) If input_files is empty, the program will intentionally crash, so it is MANDATORY.** 

**(2) When creating your command line arguments, the program parses Python strings, so make sure to take into account bash string parsing with ' and " characters!**

**(3) database generation takes ~15 minutes, but after that queries are essentially instantaneous.**

**(4) In general, don't try to read through all the output; it is just there to expose you to new dishes and to get your mind thinking in ways you might not normally as far as food combinations!**
