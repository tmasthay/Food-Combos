from tkinter import *
from subprocess import check_output as co

def extract(cmd):
    return co(cmd, shell=True).decode('utf-8').split('\n')[:-1]

files = extract('find Final -name "results.txt"')

categories = [e.split('/')[1:] for e in files]

top = Tk()

Lb1 = Listbox(top)
for (i,f) in enumerate(categories):
    Lb1.insert(i+1, f)

Lb1.pack()

top.geometry('1024x1024')
top.mainloop()
