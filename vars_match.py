import sys
from os.path import abspath, dirname, join
import editdistance as ed
from divide_to_words import Variable
import pandas as pd
from itertools import chain

SYNONYMS_PLURAL_PATH = abspath(join(dirname(__file__), r'synonyms_and_plural.csv'))


def get_synonyms_plural_df():
    synonyms_and_plural_df = pd.read_csv(SYNONYMS_PLURAL_PATH).set_index('word')
    synonyms = synonyms_and_plural_df['synonyms'].dropna().to_dict()
    plural = synonyms_and_plural_df['plural'].dropna().to_dict()
    return synonyms, plural


class MatchMaker:
    ILLEGAL_VALUE_A = '#'
    ILLEGAL_VALUE_B = '!'
    Synonyms = Plural = None

    def __init__(self, case_sensitivity=False, word_separator='_', separate_by_big_letters=True):
        self.case_sensitivity = case_sensitivity
        self.word_separator = word_separator
        self.separate_by_big_letters = separate_by_big_letters

    def set_case_sensitivity(self, case_sensitivity):
        self.case_sensitivity = case_sensitivity

    def set_word_separator(self, word_separator):
        self.word_separator = word_separator

    def set_separate_by_big_letters(self, separate_by_big_letters):
        self.separate_by_big_letters = separate_by_big_letters

    def edist(self, name_1, name_2, literal_comparison=False):
        var_1 = Variable(name_1, self.case_sensitivity, self.word_separator, literal_comparison).get_normalized_name()
        var_2 = Variable(name_2, self.case_sensitivity, self.word_separator, literal_comparison).get_normalized_name()
        max_var_len = max(len(var_1), len(var_2))

        return ed.eval(var_1, var_2) / max_var_len

    # def __init__(self, sequence_a, sequence_b):
    #     self.sequence_a = sequence_a
    #     self.sequence_b = sequence_b
    #     self.modified_seq_a = sequence_a[:]
    #     self.modified_seq_b = sequence_b[:]
    #     self.sequences = [self.sequence_a, self.sequence_b]
    #     self.matching_blocks = []
    #
    #     self.illegal_value_a, self.illegal_value_b = \
    #         (MatchMaker.ILLEGAL_VALUE_A, MatchMaker.ILLEGAL_VALUE_B) if isinstance(sequence_a, str) \
    #         else ([MatchMaker.ILLEGAL_VALUE_A], [MatchMaker.ILLEGAL_VALUE_B])

    def modify_seqs(self, i, j, k):
        self.modified_seq_a = self.modified_seq_a[:i] + self.illegal_value_a * k + self.modified_seq_a[i+k:]
        self.modified_seq_b = self.modified_seq_b[:j] + self.illegal_value_b * k + self.modified_seq_b[j+k:]

    @staticmethod
    def is_words_similar(word_1, word_2):
        if MatchMaker.Synonyms is None:
            MatchMaker.Synonyms, MatchMaker.Plural = get_synonyms_plural_df()

        if word_1 == word_2:
            return True, 0
        elif word_2 in MatchMaker.Synonyms.get(word_1, []) \
                or word_1 in MatchMaker.Synonyms.get(word_2, []):
            return True, 1
        elif word_2 ==  MatchMaker.Plural.get(word_1) \
                or word_1 ==  MatchMaker.Plural.get(word_2):
            return True, 1

        similarity_threshold = lambda a, b, d: d <= min(len(a), len(a)) / 3

        distance = ed.eval(word_1, word_2)
        return similarity_threshold(word_1, word_2, distance), distance   # TODO: TBD the exact value

    def find_longest_match(self):
        longest_len = 0
        longest_idx_a = None
        longest_idx_b = None
        most_of_letters = 0
        shortest_distance = float('inf')
        checked_points = {}

        len_a = len(self.sequence_a)
        len_b = len(self.sequence_b)

        for i in range(len_a):
            for j in range(len_b):
                if checked_points.get((i, j)) is not None:  # Because or the aren't similar, or, if the are similar,
                                                            # they already a part of a longer sequence
                    continue

                k = d = l = 0   # k: word index, d: distance, l: number of letters
                while i+k < len_a and j+k < len_b and \
                        (similarity := self.is_words_similar(self.modified_seq_a[i + k], self.modified_seq_b[j + k]))[0]:
                    checked_points[(i+k, j+k)] = True
                    d += similarity[1]
                    l += len(self.modified_seq_a[i + k]) + len(self.modified_seq_b[j + k])
                    k += 1

                    if k > longest_len or \
                        k == longest_len and \
                            (d < shortest_distance or (d == shortest_distance and l > most_of_letters)):
                        longest_len = k
                        shortest_distance = d
                        most_of_letters = l

                        if k == 1:
                            longest_idx_a = i
                            longest_idx_b = j
                else:
                    if i+k < len_a and j+k < len_b:
                        checked_points[(i+k, j+k)] = False

        return longest_idx_a, longest_idx_b, longest_len, shortest_distance

    def calc_matching_blocks(self):
        while True:
            i, j, k, d = x = self.find_longest_match()

            if k == 0:
                break

            self.matching_blocks.append(x)
            self.modify_seqs(i, j, k)

        return self.matching_blocks

    def get_matching_blocks(self):
        return self.matching_blocks

    def calc_similarity_score(self):
        a_words = len(self.sequence_a)
        b_words = len(self.sequence_b)
        possible_pairs = max([a_words, b_words])
        num_of_match_blocks = len(self.matching_blocks)

        num_of_match_words = 0
        ratio_match_letters_vs_letters = 1

        for (i, j, k, d) in self.matching_blocks:
            num_of_match_words += k
            max_letters_in_block = max(sum(len(w) for w in self.sequence_a[i:i+k]),
                                       sum(len(w) for w in self.sequence_b[j:j+k]))

            ratio_match_letters_vs_letters *= (max_letters_in_block - d) / max_letters_in_block

        return num_of_match_words / possible_pairs * ratio_match_letters_vs_letters / max(1, pow(1.04, num_of_match_blocks-1))


if __name__ == '__main__':
    TEST_EDIT_DISTANCE = 0

    scriptIndex = (len(sys.argv) > 1 and int(sys.argv[1])) or 0

    if scriptIndex == TEST_EDIT_DISTANCE:
        var_names = ['TheSchoolBusIsYellow', 'YellowIsSchoolBus']
        print(MatchMaker().edist(var_names[0], var_names[1]))



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
