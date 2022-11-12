from tkinter import *
from tkinter import ttk
from subprocess import check_output as co

def extract(cmd):
    return co(cmd, shell=True).decode('utf-8').split('\n')[:-1]

def button_call_back():
    print('You clicked the button')

files = extract('find Final -name "results.txt"')

paths = [e.split("/")[:-1] for e in files]
indent_no = 4
indent_char = '-'
indented_files = []
for p in paths:
    for (i, pp) in enumerate(p):
        curr = i*indent_no*indent_char + pp
        if( i == len(pp) - 1 or (curr not in indented_files) ):
            indented_files.append(curr)
        
top = Tk()

combobox = ttk.Combobox(top, values=indented_files, state='readonly')
combobox.pack(fill='x')

combobox = ttk.Combobox(top, values=indented_files, state='readonly')
combobox.pack(fill='x')

btn = Button(top, text='Run', command=button_call_back)
btn.pack()

top.geometry('1024x1024')
top.mainloop()
