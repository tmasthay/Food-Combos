# Food-Combos
Small script that generates lists of food combinations by scraping Wikipedia articles. 

# installation
html2text should be the only dependency and can be installed by pip or conda. Just perform one of the following commands
```
git clone X
cd Food-Combos
pip install -r requirements.txt
```

To setup the database of foods, run the following. This might take a few minutes (it's fetching HTML pages from wikipedia), but only ever needs to be run once.

```
python update.py fetch=True
python update_yaml.py
```

From there just run

```
python nextGen.py
```
