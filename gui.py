from tkinter import *
from tkinter import ttk
from subprocess import check_output as co
import re
import os
from helper import get_random_combos, get_full_random_combos

def extract(cmd):
    return co(cmd, shell=True).decode('utf-8').split('\n')[:-1]

files = extract('find Final -name "results.txt"')
files_string = '\n'.join(files)

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

box1_text = StringVar()
combobox = ttk.Combobox(top, values=indented_files, state='readonly', textvariable=box1_text)
combobox.pack(fill='x')

box2_text = StringVar()
combobox = ttk.Combobox(top, values=indented_files, state='readonly', textvariable=box2_text)
combobox.pack(fill='x')

list_length_input = Entry(top, width = 20)
list_length_input.pack()

output_box = Text(top, height = 10, width = 100)
output_box.pack()

def button_call_back():
    first_search = '.*%s.*'%(box1_text.get()).replace(indent_char,'')
    second_search = '.*%s.*'%(box2_text.get()).replace(indent_char,'')
    first = re.findall(first_search, files_string)
    second = re.findall(second_search, files_string)
    if( len(first) != 1 or len(second) != 1 ):
        u = ''
        if( len(first) != 1 ):
            u += 'Field "%s" may not correspond to a file...check again\n'%box1_text.get().replace(indent_char,'')
        else:
            u += first[0] + '\n'
        if( len(second) != 1 ):
            u += 'Field "%s" may not correspond to a file...check again\n'%box2_text.get().replace(indent_char,'')
        else:
            u += second[0] + '\n'
        output_box.delete('1.0',END)
        output_box.insert(END, u)
        return -1
    else:
        first = first[0]
        second = second[0]
        query_dir = 'Queries'
        target_file = '%s/%s/%s-%s.txt'%(os.getcwd(), query_dir,
            first_search.replace('.','').replace('*',''), 
            second_search.replace('.', '').replace('*',''))
        if( not os.path.exists(target_file) ):
            cmd = 'python cross.py out_file=%s input_files='%target_file
            cmd += "'"
            cmd += '["%s","%s"]'%(first, second)
            cmd += "' cartesian=True"
            print('Executing "%s"'%(cmd))
            os.system(cmd)
        try:
            num_combos = int(list_length_input.get())
            res = '\n'.join(get_random_combos(target_file, num_combos))
            output_box.delete('1.0',END)
            output_box.insert(END, res)
        except:
            output_box.delete('1.0', END)
            output_box.insert(END, 'Invalid combo #="%s"'%list_length_input.get())

        return 0

btn = Button(top, text='Run Selected Combo', command=button_call_back)
btn.pack()

def full_call_back():
    try:
            num_combos = int(list_length_input.get())
            res = '\n'.join(get_full_random_combos('Queries', num_combos))
            output_box.delete('1.0',END)
            output_box.insert(END, res)
    except:
            output_box.delete('1.0', END)
            output_box.insert(END, 'Invalid input for number of combos: "%s"'%list_length_input.get())

btn2 = Button(top, text='Run Full Query History', command=full_call_back)
btn2.pack()

top.geometry('1024x1024')
top.mainloop()
