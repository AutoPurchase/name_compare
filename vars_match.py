import sys
from os.path import abspath, dirname, join
import re
from extended_difflib import ExtendedSequenceMatcher
import editdistance as ed
from strsimpy.damerau import Damerau
import pandas as pd

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

    def __init__(self, name_1=None, name_2=None, case_sensitivity=False, word_separators='_', support_camel_case=True,
                 numbers_behavior=NUMBERS_SEPARATE_WORD, literal_comparison=False):
        self.var_1 = None
        self.var_2 = None
        self.case_sensitivity = case_sensitivity
        self.word_separators = word_separators    # Characters THE USER used for separating between words in the variables
        self.support_camel_case = support_camel_case
        self.numbers_behavior = numbers_behavior
        self.literal_comparison = literal_comparison

        self.set_names(name_1, name_2)

    def set_name_1(self, name):
        self.var_1 = Var(name, (l := self._divide(name)), ''.join(l), self._find_separator(name, self.var_2, '?'))

    def set_name_2(self, name):
        self.var_2 = Var(name, (l := self._divide(name)), ''.join(l), self._find_separator(name, self.var_1, '!'))

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

        name = re.sub(f'[^ -~]', self.word_separators[0], name) # remove all non-visible characters

        if self.support_camel_case:
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
    def _find_separator(name, other_var, default_sep):
        if (sep_condition := lambda x: x not in name and (other_var is None or x != other_var.separator))(default_sep):
            return default_sep

        for i in range(0x21, 0x80):
            if sep_condition(c := chr(i)):
                return c

    def edit_distance(self, enable_transposition=False):
        return ed.eval(self.var_1.norm_name, self.var_2.norm_name) \
            if not enable_transposition else Damerau().distance(self.var_1.norm_name, self.var_2.norm_name)

    def normalized_edit_distance(self, enable_transposition=False):
        return self.edit_distance(enable_transposition) \
               / max(len(self.var_1.norm_name), len(self.var_2.norm_name))

    def difflib_seq_match_ratio(self):
        return ExtendedSequenceMatcher(a=self.var_1.norm_name, b=self.var_2.norm_name).ratio()

    def calc_max_matches(self, str_1_len, str_2_len, str_1_start, str_2_start, min_len,
                         sequence_matcher, ratio_table):
        str_1_end = str_1_start + str_1_len + 1
        str_2_end = str_2_start + str_2_len + 1

        matches = []
        max_matches = 0

        i, j, k = match = sequence_matcher.find_longest_match(str_1_start, str_1_end, str_2_start, str_2_end)

        if (longest_match_len := k) < min_len:
            return 0

        aux_sequence_matcher = ExtendedSequenceMatcher()
        str_1 = self.var_1.norm_name[:]
        str_2 = self.var_2.norm_name[:]

        while match[2] == longest_match_len:
            matches.append(match)

            str_1 = str_1[:i] + self.var_2.separator * k + str_1[i + k:]
            str_2 = str_2[:j] + self.var_1.separator * k + str_2[j + k:]
            aux_sequence_matcher.set_seq1(str_1)
            aux_sequence_matcher.update_matching_seq2(str_2, j, k)
            i, j, k = match = aux_sequence_matcher.find_longest_match(str_1_start, str_1_end, str_2_start, str_2_end)

        for i, j, k in matches:
            left_max_ratio = 0 if i == str_1_start or j == str_2_start \
                else ratio_table[i - str_1_start - 1][j - str_2_start - 1][str_1_start][str_2_start]
            right_max_ratio = 0 if i + k == str_1_end or j + k == str_2_end \
                else ratio_table[str_1_end - (i + k) - 1][str_2_end - (j + k) - 1][i + k][j + k]

            if (curr_match_ratio := k + left_max_ratio + right_max_ratio) > max_matches:
                max_matches = curr_match_ratio

        return max_matches

    def ordered_match_ratio(self, min_len=1):
        len_1 = len(self.var_1.norm_name)
        len_2 = len(self.var_2.norm_name)
        sequence_matcher = ExtendedSequenceMatcher(a=self.var_1.norm_name, b=self.var_2.norm_name)

        ratio_table = [[[[0 for _ in range(len_2 - str_2_len)] for _ in range(len_1 - str_1_len)]
                        for str_2_len in range(len_2)] for str_1_len in range(len_1)]

        for str_1_len in range(len_1):      # Actually the length is plus one
            for str_2_len in range(len_2):  # Actually the length is plus one
                for str_1_start in range(len_1 - str_1_len):
                    for str_2_start in range(len_2 - str_2_len):
                        ratio_table[str_1_len][str_2_len][str_1_start][str_2_start] = self.calc_max_matches(
                            str_1_len, str_2_len, str_1_start, str_2_start, min_len, sequence_matcher, ratio_table)

        return (2 * ratio_table[-1][-1][-1][-1] / sum_len) if (sum_len := len_1 + len_2) > 0 else 0

    def unordered_match_ratio(self, min_len=2):
        name_1 = self.var_1.norm_name[:]
        name_2 = self.var_2.norm_name[:]
        len_1 = len(name_1)
        len_2 = len(name_2)

        # matching_blocks = []
        match_len = 0

        sm = ExtendedSequenceMatcher(a=name_1, b=name_2)
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
        sm = ExtendedSequenceMatcher(a=name_1, b=name_2)
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
    def words_meaning(cls, word_1, word_2):
        if cls.Synonyms is None:
            cls.Synonyms, cls.Plural = get_synonyms_plural_df()

        syn_word_1 = set(cls.Synonyms.get(word_1, []) +
                         cls.Synonyms.get(word_1.rstrip('s'), []) + cls.Synonyms.get(word_1.rstrip('es'), []))
        syn_word_2 = set(cls.Synonyms.get(word_2, []) +
                         cls.Synonyms.get(word_2.rstrip('s'), []) + cls.Synonyms.get(word_2.rstrip('es'), []))

        if len({word_2, word_2.rstrip('s'), word_2.rstrip('es')}.intersection(syn_word_1)) > 0 or \
           len({word_1, word_1.rstrip('s'), word_1.rstrip('es')}.intersection(syn_word_2)) > 0:
            return True
        elif word_2 == cls.Plural.get(word_1) \
                or word_1 == cls.Plural.get(word_2):
            return True

        return False

    @classmethod
    def words_distance(cls, word_1, word_2):
        if word_1 == word_2:
            return 0

        return ed.eval(word_1, word_2)

    @classmethod
    def find_longest_match(cls, var_1_list, var_2_list, min_word_match_degree, prefer_num_of_letters,
                           use_meanings, meaning_distance):
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
                if checked_points.get((i, j)) is not None:  # Because or they aren't similar, or, if they are similar,
                    continue                                # they already a part of a longer sequence

                k = d = l = 0   # k: word index, d: distance, l: number of letters
                while i + k < len_a and j + k < len_b:
                    if var_1_list[i + k] == var_2_list[j + k]:
                        distance = 0
                    elif use_meanings and cls.words_meaning(var_1_list[i + k], var_2_list[j + k]):
                        distance = meaning_distance
                    else:
                        distance = cls.words_distance(var_1_list[i + k], var_2_list[j + k])
                        if distance / min(len(var_1_list[i + k]), len(var_2_list[j + k])) > \
                                     (1 - min_word_match_degree):
                            checked_points[(i + k, j + k)] = False
                            break

                    checked_points[(i + k, j + k)] = True
                    d += distance
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
                        longest_idx_1 = i
                        longest_idx_2 = j
                        longest_len = k
                        shortest_distance = d
                        most_of_letters = l

        return longest_idx_1, longest_idx_2, longest_len, shortest_distance

    def calc_matching_blocks(self, min_word_match_degree, prefer_num_of_letters, use_meanings, meaning_distance):
        modified_var_1 = self.var_1.words.copy()
        modified_var_2 = self.var_2.words.copy()

        matching_blocks = []
        while True:
            i, j, k, d = x = self.find_longest_match(modified_var_1, modified_var_2, min_word_match_degree,
                                                     prefer_num_of_letters, use_meanings, meaning_distance)
            if k == 0:
                break

            matching_blocks.append(x)
            modified_var_1 = modified_var_1[:i] + [self.var_2.separator] * k + modified_var_1[i+k:]
            modified_var_2 = modified_var_2[:j] + [self.var_1.separator] * k + modified_var_2[j+k:]

        return matching_blocks

    def _words_and_meaning_match(self, min_word_match_degree, discontinuous_penalty, prefer_num_of_letters,
                                 meaning, meaning_distance=1):
        matching_blocks = self.calc_matching_blocks(min_word_match_degree, prefer_num_of_letters, meaning, meaning_distance)
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
                 * pow(1 - discontinuous_penalty, max((num_of_match_blocks - 1) / (num_of_match_words - 1), 0))

    def words_match(self, min_word_match_degree=1, discontinuous_penalty=0.04, prefer_num_of_letters=False):
        return self._words_and_meaning_match(min_word_match_degree, discontinuous_penalty, prefer_num_of_letters,
                                             meaning=False)

    def semantic_match(self, min_word_match_degree=1, discontinuous_penalty=0.04, prefer_num_of_letters=False,
                       meaning_distance=1):
        return self._words_and_meaning_match(min_word_match_degree, discontinuous_penalty, prefer_num_of_letters,
                                             meaning=True, meaning_distance=meaning_distance)


def run_test(match_maker, pairs, func, **kwargs):
    for var_1, var_2 in pairs:
        match_maker.set_names(var_1, var_2)
        print(f'>>> MatchMaker("{var_1}", "{var_2}").{func.__name__}('
              f'{", ".join([k + "=" + str(v) for k, v in kwargs.items()])})\n{func(**kwargs)}')
    print()


if __name__ == '__main__':
    set_bit = lambda bit, num=0: num | (1 << bit)

    TEST_EDIT_DISTANCE = set_bit(0)
    TEST_NORMALIZED_EDIT_DISTANCE = set_bit(1)
    TEST_DIFFLIB_MATCHER_RATIO = set_bit(2)
    TEST_SEQUENCE_ALL_ORDERED_MATCHES_RATIO = set_bit(3)
    TEST_SEQUENCE_UNORDERED_MATCHES_RATIO = set_bit(4)
    TEST_SEQUENCE_UNEDIT_MATCHES_RATIO = set_bit(5)
    TEST_WARDS_MATCH = set_bit(6)
    TEST_MEANING_MATCH = set_bit(7)

    scriptIndex = (len(sys.argv) > 1 and int(sys.argv[1], 0)) or 0

    match_maker = MatchMaker()


    if scriptIndex & TEST_EDIT_DISTANCE:
        var_names = [('CA', 'ABC'), ('TotalArraySize', 'ArrayTotalSize')]
        run_test(match_maker, var_names, match_maker.edit_distance)
        run_test(match_maker, var_names, match_maker.edit_distance, enable_transposition=True)

    if scriptIndex & TEST_NORMALIZED_EDIT_DISTANCE:
        var_names = [('CA', 'ABC')]
        run_test(match_maker, var_names, match_maker.normalized_edit_distance)
        run_test(match_maker, var_names, match_maker.normalized_edit_distance, enable_transposition=True)

    if scriptIndex & TEST_DIFFLIB_MATCHER_RATIO:
        var_names = [('AB_CD_EF', 'EF_CD_AB'),
                     ('FirstLightAFire', 'LightTheFireFirst'), ('LightTheFireFirst', 'FirstLightAFire'),
                     ('FirstLightAFire', 'AFireLightFlickersAtFirst'), ('AFireLightFlickersAtFirst', 'FirstLightAFire')]
        run_test(match_maker, var_names, match_maker.difflib_seq_match_ratio)

    if scriptIndex & TEST_SEQUENCE_ALL_ORDERED_MATCHES_RATIO:
        var_names = [('AB_CD_EF', 'EF_CD_AB'),
                     ('FirstLightAFire', 'LightTheFireFirst'), ('LightTheFireFirst', 'FirstLightAFire'),
                     ('FirstLightAFire', 'AFireLightFlickersAtFirst'), ('AFireLightFlickersAtFirst', 'FirstLightAFire')]
        # run_test(match_maker, var_names, match_maker.ordered_match_ratio, min_len=2)
        run_test(match_maker, var_names, match_maker.ordered_match_ratio, min_len=1)

    if scriptIndex & TEST_SEQUENCE_UNORDERED_MATCHES_RATIO:
        var_names = [('A_CD_EF_B', 'A_EF_CD_B'),
                     ('FirstLightAFire', 'LightTheFireFirst'), ('LightTheFireFirst', 'FirstLightAFire'),
                     ('FirstLightAFire', 'AFireLightFlickersAtFirst'), ('AFireLightFlickersAtFirst', 'FirstLightAFire'),
                     ('ABCDEFGHIJKLMNOP', 'PONMLKJIHGFEDCBA'), ('ABCDEFGHIJKLMNOP', 'ONLPBCJIHGFKAEDM')]
        # run_test(match_maker, var_names, match_maker.unordered_match_ratio, min_len=2)
        run_test(match_maker, var_names, match_maker.unordered_match_ratio, min_len=1)

        var_names = [('ABCDEFGHIJKLMNOP', 'PONMLKJIHGFEDCBA')]
        run_test(match_maker, var_names, match_maker.unordered_match_ratio, min_len=1)


    if scriptIndex & TEST_SEQUENCE_UNEDIT_MATCHES_RATIO:
        var_names = [('A_CD_EF_B', 'A_EF_CD_B')]
        run_test(match_maker, var_names, match_maker.unedit_match, min_len=2)

    if scriptIndex & TEST_WARDS_MATCH:
        var_names = [('TheSchoolBusIsYellow', 'TheSchooolBosIsYellow'),
                     ('multiply_digits_exponent', 'multiply_digits_power'),
                     ('TheChildArrivesToTheClassroom', 'TheKidGetToSchoolroom'),
                     ('multiply_digits_exponent', 'multiply_digits_power')]
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=1)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=2/3)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=1, prefer_num_of_letters=True)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=2/3, prefer_num_of_letters=True)

        var_names = [('TheSchoolBusIsYellow', 'YellowIsSchoolBosColor'),
                     ('TheSchoolBusIsYellow', 'YellowIsSchoolBus'),
                     ('TheWhiteHouse', 'TheHouseIsWhite')]
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=1, discontinuous_penalty=0.04)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=1, discontinuous_penalty=0.1)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=2/3, discontinuous_penalty=0.04)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=2/3, discontinuous_penalty=0.1)

        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=1, discontinuous_penalty=0.04, prefer_num_of_letters=True)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=1, discontinuous_penalty=0.1, prefer_num_of_letters=True)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=2/3, discontinuous_penalty=0.04, prefer_num_of_letters=True)
        run_test(match_maker, var_names, match_maker.words_match, min_word_match_degree=2/3, discontinuous_penalty=0.1, prefer_num_of_letters=True)

    if scriptIndex & TEST_MEANING_MATCH:
        var_names = [('multiply_digits_exponent', 'multiply_digits_power'),
                     ('TheChildArrivesToTheClassroom', 'TheChildArrivesToTheSchoolroom'),
                     ('TheChildArrivesToTheClassroom', 'TheChildGetToTheSchoolroom'),
                     ('TheChildArrivesToTheClassroom', 'TheKidGetToTheSchoolroom')]
        run_test(match_maker, var_names, match_maker.semantic_match, min_word_match_degree=1)
        run_test(match_maker, var_names, match_maker.semantic_match, min_word_match_degree=2/3)
        run_test(match_maker, var_names, match_maker.semantic_match, min_word_match_degree=1, prefer_num_of_letters=True)
        run_test(match_maker, var_names, match_maker.semantic_match, min_word_match_degree=2/3, prefer_num_of_letters=True)
