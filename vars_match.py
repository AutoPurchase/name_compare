import sys
from os.path import abspath, dirname, join
import re
from modificated_difflib import SequenceMatcher
import editdistance as ed
from strsimpy.damerau import Damerau
# from divide_to_words import Variable
import pandas as pd
from itertools import chain

SYNONYMS_PLURAL_PATH = abspath(join(dirname(__file__), r'synonyms_and_plural.csv'))


def get_synonyms_plural_df():
    synonyms_and_plural_df = pd.read_csv(SYNONYMS_PLURAL_PATH).set_index('word')
    synonyms = synonyms_and_plural_df['synonyms'].dropna().apply(lambda x: x.split(',')).to_dict()
    plural = synonyms_and_plural_df['plural'].dropna().apply(lambda x: x.split(',')).to_dict()
    return synonyms, plural


class Var:
    def __init__(self, name, words, norm_name, separator):
        self.name = name
        self.words = words
        self.norm_name = norm_name
        self.separator = separator  # A letter that isn't included in THIS name, for using ANOTHER names
                                    # (and promised no matching will be with this name)


class MatchMaker:
    NUMBERS_SEPARATE_WORD = 0
    NUMBERS_IGNORE = 1
    NUMBERS_LEAVE = 1

    Synonyms = Plural = None

    def __init__(self, name_1=None, name_2=None, case_sensitivity=False, word_separators='_', separate_by_big_letters=True,
                 numbers_behavior=NUMBERS_SEPARATE_WORD, literal_comparison=False):
        self.var_1 = None
        self.var_2 = None
        self.case_sensitivity = case_sensitivity
        self.word_separators = word_separators    # Characters THE USER used for separating between words in the variables
        self.separate_by_big_letters = separate_by_big_letters
        self.numbers_behavior = numbers_behavior
        self.literal_comparison = literal_comparison

        self.set_names(name_1, name_2)

    def set_name_1(self, name):
        self.var_1 = Var(name, (l := self._divide(name)), ''.join(l), self._find_separator(name, self.var_2))

    def set_name_2(self, name):
        self.var_2 = Var(name, (l := self._divide(name)), ''.join(l), self._find_separator(name, self.var_1))

    def set_names(self, name_1, name_2):
        if name_1 is not None:
            self.set_name_1(name_1)
        if name_2 is not None:
            self.set_name_2(name_2)
        return self

    def set_case_sensitivity(self, case_sensitivity):
        self.case_sensitivity = case_sensitivity

    def set_word_separators(self, word_separators):
        self.word_separators = word_separators

    def set_literal_comparison(self, literal_comparison):
        self.literal_comparison = literal_comparison

    def _divide(self, name):
        if self.literal_comparison:
            return [name]

        name = re.sub(f'[^0-9A-Za-z{self.word_separators}]', self.word_separators[0], name)

        if self.separate_by_big_letters:
            name = re.sub('(.)([A-Z][a-z]+)', fr'\1{self.word_separators[0]}\2', name)
            name = re.sub('([a-z0-9])([A-Z])', fr'\1{self.word_separators[0]}\2', name)

            if self.numbers_behavior == MatchMaker.NUMBERS_SEPARATE_WORD:
                name = re.sub('([A-Za-z])([0-9])', fr'\1{self.word_separators[0]}\2', name)
                name = re.sub('([0-9])([a-z])', fr'\1{self.word_separators[0]}\2', name)
            elif self.numbers_behavior == MatchMaker.NUMBERS_IGNORE:
                name = re.sub('[0-9]', '', name)

        if not self.case_sensitivity:
            name = name.lower()

        return list(filter(None, name.split(self.word_separators)))

    @staticmethod
    def _find_separator(name, other_var):
        for i in range(0x21, 0x80):
            if (c := chr(i)) not in name and (other_var is None or c != other_var.separator):
                return c
        raise Exception(f'Error: illegal characters in the name: {name}')

    def edit_distance(self, enable_transposition=False):
        return ed.eval(self.var_1.norm_name, self.var_2.norm_name) \
            if not enable_transposition else Damerau().distance(self.var_1.norm_name, self.var_2.norm_name)

    def edist(self, enable_transposition=False):
        return self.edit_distance(enable_transposition) \
               / max(len(self.var_1.norm_name), len(self.var_2.norm_name))

    def match(self):
        return SequenceMatcher(a=self.var_1.norm_name, b=self.var_2.norm_name).ratio()

    def all_match(self, min_len=2):
        name_1 = self.var_1.norm_name[:]
        name_2 = self.var_2.norm_name[:]
        len_1 = len(name_1)
        len_2 = len(name_2)

        # matching_blocks = []
        match_len = 0

        sm = SequenceMatcher(a=name_1, b=name_2)
        while True:
            i, j, k = x = sm.find_longest_match(0, len_1, 0, len_2)
            if k < min_len:
                break

            # matching_blocks.append(x)
            match_len += k
            name_1 = name_1[:i] + self.var_2.separator * k + name_1[i + k:]
            name_2 = name_2[:j] + self.var_1.separator * k + name_2[j + k:]
            sm.set_seq1(name_1)
            sm.update_matching_seq2(name_2, j, k)

        return 2 * match_len / (len_1 + len_2)

    def unedit_match(self, min_len=2):
        name_1 = self.var_1.norm_name[:]
        name_2 = self.var_2.norm_name[:]

        match_len = 0
        sm = SequenceMatcher(a=name_1, b=name_2)
        while True:
            i, j, k = sm.find_longest_match(0, len(name_1), 0, len(name_2))

            if k < min_len:
                break

            match_len += k
            name_1 = name_1[:i] + name_1[i+k:]
            name_2 = name_2[:j] + name_2[j+k:]
            sm.set_seq1(name_1)
            sm.set_seq2(name_2)

        return 2 * match_len / (len(self.var_1.norm_name) + len(self.var_2.norm_name))

    @classmethod
    def words_distance(cls, word_1, word_2, min_word_match_degree, use_meanings):
        if word_1 == word_2:
            return 0, True
        elif use_meanings:
            if cls.Synonyms is None:
                cls.Synonyms, cls.Plural = get_synonyms_plural_df()

            if word_2 in cls.Synonyms.get(word_1, []) \
                    or word_1 in cls.Synonyms.get(word_2, []):
                return 1, True
            elif word_2 == cls.Plural.get(word_1) \
                    or word_1 == cls.Plural.get(word_2):
                return 1, True

        distance = ed.eval(word_1, word_2)  # TODO: enable also Damerau Edit Distance?
        is_similar = distance / min(len(word_1), len(word_2)) <= (1-min_word_match_degree)

        return distance, is_similar

    @classmethod
    def find_longest_match(cls, var_1_list, var_2_list, min_word_match_degree, prefer_num_of_letters, use_meanings):
        longest_len = 0
        longest_idx_1 = None
        longest_idx_2 = None
        most_of_letters = 0
        shortest_distance = float('inf')
        checked_points = {}

        len_a = len(var_1_list)
        len_b = len(var_2_list)

        for i in range(len_a):
            for j in range(len_b):
                if checked_points.get((i, j)) is not None:  # Because or the aren't similar, or, if the are similar,
                    continue                                # they already a part of a longer sequence

                k = d = l = 0   # k: word index, d: distance, l: number of letters
                while i+k < len_a and j+k < len_b and \
                        (ed := cls.words_distance(var_1_list[i + k], var_2_list[j + k],
                                                  min_word_match_degree, use_meanings))[1]:
                    checked_points[(i+k, j+k)] = True
                    d += ed[0]
                    l += len(var_1_list[i + k]) + len(var_2_list[j + k])
                    k += 1

                    if not prefer_num_of_letters and (
                            k > longest_len or
                            k == longest_len and (d < shortest_distance or
                                                  (d == shortest_distance and l > most_of_letters))
                    ) or prefer_num_of_letters and (
                        l > most_of_letters or
                        l == most_of_letters and (d < shortest_distance or
                                                  (d == shortest_distance and k > longest_len))):
                        longest_len = k
                        shortest_distance = d
                        most_of_letters = l

                        if k == 1:
                            longest_idx_1 = i
                            longest_idx_2 = j
                else:
                    if i+k < len_a and j+k < len_b:
                        checked_points[(i+k, j+k)] = False

        return longest_idx_1, longest_idx_2, longest_len, shortest_distance

    def calc_matching_blocks(self, min_word_match_degree, prefer_num_of_letters, use_meanings):
        modified_var_1 = self.var_1.words.copy()
        modified_var_2 = self.var_2.words.copy()

        matching_blocks = []
        while True:
            i, j, k, d = x = self.find_longest_match(modified_var_1, modified_var_2,
                                                     min_word_match_degree, prefer_num_of_letters, use_meanings)
            if k == 0:
                break

            matching_blocks.append(x)
            modified_var_1 = modified_var_1[:i] + [self.var_2.separator] * k + modified_var_1[i+k:]
            modified_var_2 = modified_var_2[:j] + [self.var_1.separator] * k + modified_var_2[j+k:]

        return matching_blocks

    def _words_and_meaning_match(self, min_word_match_degree, order_change_penalty, prefer_num_of_letters, meaning):
        matching_blocks = self.calc_matching_blocks(min_word_match_degree, prefer_num_of_letters, meaning)
        num_of_match_blocks = len(matching_blocks)

        num_of_match_words = 0
        ratio_match_letters_vs_letters = 1

        for (i, j, k, d) in matching_blocks:
            num_of_match_words += k
            max_letters_in_block = max(sum(len(w) for w in self.var_1.words[i:i+k]),
                                       sum(len(w) for w in self.var_2.words[j:j+k]))

            ratio_match_letters_vs_letters *= (max_letters_in_block - d) / max_letters_in_block

        return 2 * num_of_match_words / (len(self.var_1.words) + len(self.var_2.words)) \
                 * ratio_match_letters_vs_letters \
                 * pow(1 - order_change_penalty, max(num_of_match_blocks - 1, 0))

    def words_match(self, min_word_match_degree=1, order_change_penalty=0.04, prefer_num_of_letters=False):
        return self._words_and_meaning_match(min_word_match_degree, order_change_penalty, prefer_num_of_letters,
                                             meaning=False)

    def semantic_match(self, min_word_match_degree=1, order_change_penalty=0.04, prefer_num_of_letters=False):
        return self._words_and_meaning_match(min_word_match_degree, order_change_penalty, prefer_num_of_letters,
                                             meaning=True)


def run_test(match_maker, pairs, func, **kwargs):
    for var_1, var_2 in pairs:
        match_maker.set_names(var_1, var_2)
        print(f'>>> MatchMaker("{var_1}", "{var_2}").{func.__name__}('
              f'{" ".join([k + "=" + str(v) for k, v in kwargs.items()])})\n{func(**kwargs)}')
    print()

if __name__ == '__main__':
    set_bit = lambda bit, num=0: num | (1 << bit)

    TEST_EDIT_DISTANCE = set_bit(0)
    TEST_NORMALIZED_EDIT_DISTANCE = set_bit(1)
    TEST_SEQUENCE_MATCHER_RATIO = set_bit(2)
    TEST_SEQUENCE_ALL_MATCHES_RATIO = set_bit(3)
    TEST_SEQUENCE_UNEDIT_MATCHES_RATIO = set_bit(4)
    TEST_WARDS_MATCH = set_bit(5)
    TEST_MEANING_MATCH = set_bit(6)

    scriptIndex = (len(sys.argv) > 1 and int(sys.argv[1], 0)) or 0

    match_maker = MatchMaker()


    if scriptIndex & TEST_EDIT_DISTANCE:
        var_names = [('CA', 'ABC')]
        run_test(match_maker, var_names, match_maker.edit_distance)
        run_test(match_maker, var_names, match_maker.edit_distance, enable_transposition=True)

    if scriptIndex & TEST_NORMALIZED_EDIT_DISTANCE:
        var_names = [('CA', 'ABC')]
        run_test(match_maker, var_names, match_maker.edist)
        run_test(match_maker, var_names, match_maker.edist, enable_transposition=True)

    if scriptIndex & TEST_SEQUENCE_MATCHER_RATIO:
        var_names = [('AB_CD_EF', 'EF_CD_AB')]
        run_test(match_maker, var_names, match_maker.match)

    if scriptIndex & TEST_SEQUENCE_ALL_MATCHES_RATIO:
        var_names = [('A_CD_EF_B', 'A_EF_CD_B')]
        run_test(match_maker, var_names, match_maker.all_match)

    if scriptIndex & TEST_SEQUENCE_UNEDIT_MATCHES_RATIO:
        var_names = [('A_CD_EF_B', 'A_EF_CD_B')]
        run_test(match_maker, var_names, match_maker.unedit_match)

    if scriptIndex & TEST_WARDS_MATCH:
        var_names = [('TheSchoolBusIsYellow', 'YellowIsSchoolBosColor'),
                     ('TheSchoolBusIsYellow', 'TheSchooolBosIsYellow'),
                     ('multiply_digits_exponent', 'multiply_digits_power')]
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=1)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=2/3)

    if scriptIndex & TEST_MEANING_MATCH:
        var_names = [('multiply_digits_exponent', 'multiply_digits_power')]
        run_test(match_maker, var_names, match_maker.semantic_match)

    # vnames = ['Print_Gui_Data','Print_Data_Gui','Gui_Print_Data','Gui_Data_Print',
    #           'Data_Print_Gui','Data_Gui_Print','Printing_Gui_Data','Print_Data',
    #           'Gui_Print']
    # vnames = ['TheSchoolBusIsYellow', 'TheSchoolBosIsYellow', 'SchoolBusIsYellow', 'YellowIsSchoolBus', 'YellowIsSchoolBusColor',
    #           'TookBusToSchool', 'TookBusToSchoool', 'PrintGuiData']
    # vnames = ['of_num_sum_to_target', 'sum_of_index', 'index_sum_of', 'Calculate_complementary_indices',
    #           'indices_Calculate_complementary', 'sum_index_target', 'index_sum_target', 'Sum_indices',
    #           'indices_Sum', 'slices_val_indices_', 'indices_slices_val_', 'find_indices_sum_target',
    #           'indices_sum_find_target', 'diff_squares_sum', 'sum_squares_diff', 'Calc_squares_sum_diff',
    #           'Calc_diff_sum_squares', 'diff_of_square', 'of_square_diff', 'square_sum_diff', 'diff_sum_square',
    #           'sum_square_diff', 'calc_diff_squares', 'calc_squares_diff',
    #           'multiply_digits_exponent', 'multiply_exponent_digits',
    #           'num_exp_sum', 'sum_exp_num', 'Sum_of_exp', 'of_exp_Sum', 'Exp_sum_digits', 'sum_Exp_digits',
    #           'digits_sum', 'sum_digits', '2_n_sum_digits', 'sum_2_n_digits', 'sum_digits_power', 'sum_power_digits',
    #           'exponent_sum', 'sum_exponent', 'power_sum', 'sum_power']
    #
    # # synonyms_df = get_synonyms_plural_df()
    # synonyms, plural = get_synonyms_plural_df()
    #
    # for a in range(len(vnames)):
    #     for b in range(a, len(vnames)):
    #         a_words = Variable(vnames[a]).get_words()
    #         b_words = Variable(vnames[b]).get_words()
    #
    #         s = MatchMaker(a_words, b_words)
    #         s.calc_matching_blocks()
    #
    #         print(f'{a+1}.{b+1}.\na="{vnames[a]}"\nb="{vnames[b]}"\nSimilarity Score: {s.calc_similarity_score()}')
    #
    #         for (i, j, k, d) in s.get_matching_blocks():
    #             print(f'''\
    # a[{i}] and b[{j}] match for {k} elements with distance {d}:
    #     {a_words[i:i+k]}
    #     {b_words[j:j+k]}''')
    #         print('\n', end='')
