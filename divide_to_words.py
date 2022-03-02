import re
from itertools import chain


class Variable:
    NUMBERS_SEPARATE_WORD = 0
    NUMBERS_IGNORE = 1
    NUMBERS_LEAVE = 1

    def __init__(self, name='', literal=False, case_sensitivity=False, word_separator='_',
                 separate_by_big_letters=True, numbers_behavior=NUMBERS_SEPARATE_WORD):
        self.case_sensitivity = case_sensitivity
        self.word_separator = word_separator
        self.separate_by_big_letters = separate_by_big_letters
        self.numbers_behavior = numbers_behavior
        self.name = name
        self.literal = literal
        self.words = self.divide()

    def set_name(self, name, literal=False):
        self.name = name
        self.literal = literal
        self.words = self.divide()

    def set_case_sensitivity(self, case_sensitivity):
        self.case_sensitivity = case_sensitivity

    def set_word_separator(self, word_separator):
        self.word_separator = word_separator

    def set_literal(self, literal):
        self.literal = literal


    def divide(self):
        if self.literal:
            return [self.name]

        name = re.sub(f'[^0-9A-Za-z{self.word_separator}]', self.word_separator, self.name)

        if self.separate_by_big_letters:
            name = re.sub('(.)([A-Z][a-z]+)', fr'\1{self.word_separator}\2', name)
            name = re.sub('([a-z0-9])([A-Z])', fr'\1{self.word_separator}\2', name)

            if self.numbers_behavior == Variable.NUMBERS_SEPARATE_WORD:
                name = re.sub('([A-Za-z])([0-9])', fr'\1{self.word_separator}\2', name)
                name = re.sub('([0-9])([a-z])', fr'\1{self.word_separator}\2', name)
            elif self.numbers_behavior == Variable.NUMBERS_IGNORE:
                name = re.sub('[0-9]', '', name)

        if not self.case_sensitivity:
            name = name.lower()

        return list(filter(None, name.split(self.word_separator)))

    def get_words(self, name=None):
        if name is not None:
            self.set_name(name)

        return self.words

    def get_normalized_name(self, name=None, literal=False, word_separator=''):
        if name is not None:
            self.set_name(name, literal)

        return word_separator.join(self.words)

    def get_words_len(self):
        return [len(w) for w in self.words]

    # def get_var_len(self):
    #     return len(self.name)

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
