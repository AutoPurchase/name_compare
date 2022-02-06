import divide_to_words
from modificated_difflib import SequenceMatcher

def calc_distance(var1, var2):
    return 0

if __name__ == '__main__':
    vnames = ['print_gui_data', 'print_data_gui', 'gui_print_data', 'gui_data_print', 'data_print_gui', 'data_gui_print']
    vnames = ['print_gui_data', 'print_data_gui']

    for i in range(len(vnames)):
        for j in range(i + 1):
            s = SequenceMatcher(lambda x: x == "_", vnames[j], vnames[i])
            for block in s.get_matching_blocks()[:-1]:
                print(f'a="{vnames[j]}", b="{vnames[i]}":', "a[%d] and b[%d] match for %d elements" % block)

            print('\n', end='')