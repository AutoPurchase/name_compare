import sys
from os.path import abspath, dirname, join
from modificated_difflib import SequenceMatcher
import editdistance as ed
from strsimpy.damerau import Damerau
from divide_to_words import Variable
import pandas as pd
from itertools import chain

SYNONYMS_PLURAL_PATH = abspath(join(dirname(__file__), r'synonyms_and_plural.csv'))


def get_synonyms_plural_df():
    synonyms_and_plural_df = pd.read_csv(SYNONYMS_PLURAL_PATH).set_index('word')
    synonyms = synonyms_and_plural_df['synonyms'].dropna().apply(lambda x: x.split(',')).to_dict()
    plural = synonyms_and_plural_df['plural'].dropna().apply(lambda x: x.split(',')).to_dict()
    return synonyms, plural


class MatchMaker:
    SEPARATOR_1 = '#'
    SEPARATOR_2 = '!'
    Synonyms = Plural = None

    def __init__(self, case_sensitivity=False, word_separator='_', separate_by_big_letters=True,
                 numbers_behavior=Variable.NUMBERS_SEPARATE_WORD):
        self.case_sensitivity = case_sensitivity
        self.word_separator = word_separator
        self.var_1 = Variable(case_sensitivity, word_separator, separate_by_big_letters, numbers_behavior)
        self.var_2 = Variable(case_sensitivity, word_separator, separate_by_big_letters, numbers_behavior)

    def set_case_sensitivity(self, case_sensitivity):
        self.case_sensitivity = case_sensitivity

    def set_word_separator(self, word_separator):
        self.word_separator = word_separator

    @staticmethod
    def edit_distance(str_1, str_2, enable_transposition=False):
        return ed.eval(str_1, str_2) if not enable_transposition else Damerau().distance(str_1, str_2)

    def edist(self, name_1, name_2, literal_comparison=False, enable_transposition=False):
        var_1_str = self.var_1.get_normalized_name(name_1, literal_comparison)
        var_2_str = self.var_2.get_normalized_name(name_2, literal_comparison)

        max_var_len = max(len(var_1_str), len(var_2_str))

        return self.edit_distance(var_1_str, var_2_str, enable_transposition) / max_var_len

    def match(self, name_1, name_2, literal_comparison=False):
        var_1_str = self.var_1.get_normalized_name(name_1, literal_comparison)
        var_2_str = self.var_2.get_normalized_name(name_2, literal_comparison)

        return SequenceMatcher(a=var_1_str, b=var_2_str).ratio()

    def get_not_exist_char_separator(self, name):
        for i in range(0x20, 0x100):
            if (c := chr(i)) not in name:
                return c
        raise Exception(f'Error: illegal characters in the name: {name}')

    def get_not_exist_word_separator(self, name, separator_char):
        i = 1
        while (sep := separator_char * i) in name:
            i += 1
        return sep

    def get_separators(self, name_1, name_2):
        words_div_to_list = isinstance(name_1, list)

        if words_div_to_list:
            separator_1 = [MatchMaker.SEPARATOR_1]
            separator_2 = [MatchMaker.SEPARATOR_2]

            if separator_1 in name_2:
                separator_1 = self.get_not_exist_word_separator(name_2, separator_1)
            if separator_2 in name_1:
                separator_2 = self.get_not_exist_word_separator(name_1, separator_2)
        else:
            separator_1 = MatchMaker.SEPARATOR_1
            separator_2 = MatchMaker.SEPARATOR_2

            if separator_1 in name_2:
                separator_1 = self.get_not_exist_char_separator(name_2)
            if separator_2 in name_1:
                separator_2 = self.get_not_exist_char_separator(name_1)

        return separator_1, separator_2

    def replace_matches_by_separators(self, var_1_str, var_2_str, i, j, k, separator_1, separator_2):
        return var_1_str[:i] + separator_1 * k + var_1_str[i+k:], \
               var_2_str[:j] + separator_2 * k + var_2_str[j+k:]

    def cross_match(self, name_1, name_2, separator_1, separator_2, min_len=1):
        len_1 = len(name_1)
        len_2 = len(name_2)
        matching_blocks = []
        match_len = 0

        sm = SequenceMatcher(a=name_1, b=name_2)
        while True:
            i, j, k = x = sm.find_longest_match(0, len_1, 0, len_2)

            if k < min_len:
                break

            matching_blocks.append(x)
            match_len += k
            name_1, name_2 = self.replace_matches_by_separators(name_1, name_2, i, j, k, separator_1, separator_2)
            sm.set_seq1(name_1)
            sm.update_matching_seq2(name_2, j, k)

        return match_len, matching_blocks

    def all_match(self, name_1, name_2, literal_comparison=False, min_len=2):
        var_1_str = self.var_1.get_normalized_name(name_1, literal_comparison)
        var_2_str = self.var_2.get_normalized_name(name_2, literal_comparison)
        separator_1, separator_2 = self.get_separators(var_1_str, var_2_str)

        return self.cross_match(var_1_str, var_2_str, separator_1, separator_2, min_len)[0] / \
               max(len(var_1_str), len(var_2_str))

    def remove_matches(self, var_1_str, var_2_str, i, j, k):
        return var_1_str[:i] + var_1_str[i+k:], \
               var_2_str[:j] + var_2_str[j+k:]

    def unedit_match(self, name_1, name_2, literal_comparison=False, min_len=2):
        var_1_str = self.var_1.get_normalized_name(name_1, literal_comparison)
        var_2_str = self.var_2.get_normalized_name(name_2, literal_comparison)
        len_1 = len(var_1_str)
        len_2 = len(var_2_str)

        match_len = 0
        sm = SequenceMatcher(a=var_1_str, b=var_2_str)
        while True:
            i, j, k = sm.find_longest_match(0, len(var_1_str), 0, len(var_2_str))

            if k < min_len:
                break

            match_len += k
            var_1_str, var_2_str = self.remove_matches(var_1_str, var_2_str, i, j, k)
            sm.set_seq1(var_1_str)
            sm.set_seq2(var_2_str)

        return match_len / max(len_1, len_2)




    @staticmethod
    def is_words_similar(word_1, word_2, min_word_match_degree, use_meanings=False):
        if MatchMaker.Synonyms is None:
            MatchMaker.Synonyms, MatchMaker.Plural = get_synonyms_plural_df()

        if word_1 == word_2:
            return True, 0
        elif use_meanings:
            if word_2 in MatchMaker.Synonyms.get(word_1, []) \
                    or word_1 in MatchMaker.Synonyms.get(word_2, []):
                return True, 1
            elif word_2 == MatchMaker.Plural.get(word_1) \
                    or word_1 == MatchMaker.Plural.get(word_2):
                return True, 1

        similarity_threshold = lambda a, b, d: d / min(len(a), len(a)) <= (1-min_word_match_degree)

        distance = ed.eval(word_1, word_2)
        return similarity_threshold(word_1, word_2, distance), distance   # TODO: TBD the exact value

    def find_longest_match(self, var_1_list, var_2_list, min_word_match_degree):
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
                        (similarity := self.is_words_similar(var_1_list[i + k], var_2_list[j + k], min_word_match_degree))[0]:
                    checked_points[(i+k, j+k)] = True
                    d += similarity[1]
                    l += len(var_1_list[i + k]) + len(var_2_list[j + k])
                    k += 1

                    if k > longest_len or \
                        k == longest_len and \
                            (d < shortest_distance or (d == shortest_distance and l > most_of_letters)):
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

    def calc_matching_blocks(self, var_1_list, var_2_list, min_word_match_degree, account_word_num_of_letters):
        modified_var_1 = var_1_list.copy()
        modified_var_2 = var_2_list.copy()
        separator_1, separator_2 = self.get_separators(modified_var_1, modified_var_2)

        matching_blocks = []
        while True:
            i, j, k, d = x = self.find_longest_match(modified_var_1, modified_var_2, min_word_match_degree)

            if k == 0:
                break

            matching_blocks.append(x)
            modified_var_1, modified_var_2 = self.replace_matches_by_separators(
                modified_var_1, modified_var_2, i, j, k, separator_1, separator_2)

        return matching_blocks

    def get_matching_blocks(self):
        return self.matching_blocks

    def words_match(self, name_1, name_2, min_word_match_degree=2/3, order_change_penalty=0.04,
                    account_word_num_of_letters=True):
        var_1_list = self.var_1.get_words(name_1)
        var_2_list = self.var_2.get_words(name_2)
        num_of_words_1 = len(var_1_list)
        num_of_words_2 = len(var_2_list)
        possible_pairs = max([num_of_words_1, num_of_words_2])

        matching_blocks = self.calc_matching_blocks(var_1_list, var_2_list, min_word_match_degree, account_word_num_of_letters)
        num_of_match_blocks = len(matching_blocks)

        num_of_match_words = 0
        ratio_match_letters_vs_letters = 1

        for (i, j, k, d) in matching_blocks:
            num_of_match_words += k
            max_letters_in_block = max(sum(len(w) for w in var_1_list[i:i+k]),
                                       sum(len(w) for w in var_2_list[j:j+k]))

            ratio_match_letters_vs_letters *= (max_letters_in_block - d) / max_letters_in_block

        return num_of_match_words / possible_pairs * ratio_match_letters_vs_letters / max(1, pow(1.04, num_of_match_blocks-1))


if __name__ == '__main__':
    set_bit = lambda bit, num=0: num | (1 << bit)

    TEST_EDIT_DISTANCE = set_bit(0)
    TEST_NORMALIZED_EDIT_DISTANCE = set_bit(1)
    TEST_SEQUENCE_MATCHER_RATIO = set_bit(2)
    TEST_SEQUENCE_ALL_MATCHES_RATIO = set_bit(3)
    TEST_SEQUENCE_UNEDIT_MATCHES_RATIO = set_bit(4)
    TEST_WARDS_MATCH = set_bit(5)

    scriptIndex = (len(sys.argv) > 1 and int(sys.argv[1], 0)) or 0

    match_maker = MatchMaker()

    if scriptIndex & TEST_EDIT_DISTANCE:
        var_names = ['CA', 'ABC']
        print(f'''Edit distanse between "{var_names[0]}" and "{var_names[1]}":
    Without swapping: {match_maker.edit_distance(var_names[0], var_names[1])}
    With swapping: {match_maker.edit_distance(var_names[0], var_names[1], enable_transposition=True)}''')

    if scriptIndex & TEST_NORMALIZED_EDIT_DISTANCE:
        var_names = ['CA', 'ABC']
        print(f'''Normalized edit distanse between "{var_names[0]}" and "{var_names[1]}":
    Without swapping: {match_maker.edist(var_names[0], var_names[1])}
    With swapping: {match_maker.edist(var_names[0], var_names[1], enable_transposition=True)}''')

    if scriptIndex & TEST_SEQUENCE_MATCHER_RATIO:
        var_names = ['AB_CD_EF', 'EF_CD_AB']
        print(f'''Sequence Matcher between "{var_names[0]}" and "{var_names[1]}":
    {match_maker.match(var_names[0], var_names[1])}''')

    if scriptIndex & TEST_SEQUENCE_ALL_MATCHES_RATIO:
        var_names = ['A_CD_EF_B', 'A_EF_CD_B']
        print(f'''All matches between "{var_names[0]}" and "{var_names[1]}":
    {match_maker.all_match(var_names[0], var_names[1])}''')

    if scriptIndex & TEST_SEQUENCE_UNEDIT_MATCHES_RATIO:
        var_names = ['A_CD_EF_B', 'A_EF_CD_B']
        print(f'''Unedit matches between "{var_names[0]}" and "{var_names[1]}":
    {match_maker.unedit_match(var_names[0], var_names[1])}''')

    if scriptIndex & TEST_WARDS_MATCH:
        var_names = ['TheSchoolBusIsYellow', 'YellowIsSchoolBosColor']
        print(f'''Word matches between "{var_names[0]}" and "{var_names[1]}":
    {match_maker.words_match(var_names[0], var_names[1])}''')


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
