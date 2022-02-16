import re
from itertools import chain


class Variable:
    def __init__(self, name):
        self.name = name
        self.words = self.divide()

    def divide(self):
        # name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', self.name)
        # name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

        name = re.sub('[^0-9A-Za-z_]', '_', self.name)
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        # name = re.sub('([A-Z]{2})([0-9]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()

        return list(filter(None, name.split('_')))

    def get_words(self):
        return self.words

    def get_var_len(self):
        return len(self.name)

    def get_num_of_words(self):
        return len(self.words)

    def get_words_ratio(self):
        return self.get_num_of_words() / self.get_var_len()


if __name__ == '__main__':
    words_data = []
    for vname in ['printGuiData', 'PrintGuiData', 'PrintGUIData', 'print_gui_data', 'print___gui_data', 'Print_gui_Data23', 'Print23guiData',
                  'Print_23GuiData', 'printGUI23Data', 'printGui23Data', 'printGUI2_3Data', 'printGUI_data', 'Print_GUI_data', '_Print_GUI_data__']:
        words_data.append(Variable(vname))

    for wd in words_data:
        print(f'"{wd.name}": \t\t{wd.words}. \t\tRatio: {wd.get_words_ratio()}')
