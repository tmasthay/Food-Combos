# Food-Combos
Small script that generates lists of food combinations by scraping Wikipedia articles. 

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

From there, just run ```python gui.py``` and the gui should open up. 

NOTE: if you just want to see the whole list, set the number of samples to a very large number, and it should work out since the sampling algorithm is without replacement. 
