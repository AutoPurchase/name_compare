import sys
from os.path import abspath, dirname, join
import re
import difflib
from extended_difflib import ExtendedSequenceMatcher
from strsimpy.levenshtein import Levenshtein
from strsimpy.damerau import Damerau
import csv
from datetime import datetime
from itertools import chain


def get_synonyms_plural_df():
    """
        Reads the files of synonyms and plurals, and merge them to one Pandas DataFrame.
    Returns:
        Pandas DataFrame that for each word contains its synonyms and plurals.
    """
    SYNONYMS_PATH = abspath(join(dirname(__file__), r'synonyms.csv'))
    PLURAL_PATH = abspath(join(dirname(__file__), r'plurals.csv'))

    with open(SYNONYMS_PATH, newline='') as csvfile:
        synonyms = {row['word']: row['synonyms'].split(',') for row in csv.DictReader(csvfile)}

    with open(PLURAL_PATH, newline='') as csvfile:
        plurals = {row['word']: row['plural'].split(',') for row in csv.DictReader(csvfile)}

    return synonyms, plurals


class Var:
    """
        Saves all data about a var
    """

    def __init__(self, name, words, norm_name, separator):
        """
        Args:
            name: raw name
            words: a list of the normalized name divided to words
            norm_name: the name in lowercase without spaces
            separator: A letter that isn't included in THIS name, for using ANOTHER names
                        (and promised no matching will be with this name)
        """
        self.name = name
        self.words = words
        self.norm_name = norm_name
        self.separator = separator


class OneMatch:
    """
    Saves all the data about one match
    """

    def __init__(self, i, j, k=0, l=0, r=0):
        """
        Args:
            i: match in the first var (if matches must be continuous, it contains the first index of the match, else it
                contains a list of all the matching indices)
            j: like i, but in the second var
            k: length of the match (unused in discontinuous matches)
            d: different between matches (if imperfect matches is enabled)
        """
        self.i = i
        self.j = j
        self.k = k
        self.l = l
        self.r = r

    def __radd__(self, other):
        if isinstance(other, int):
            return self.k, self.l, self.r, self.k - 1
        elif isinstance(other, tuple):
            return self.k + other[0], self.l + other[1], self.r + other[2], self.k - 1 + other[3]

    # def __le__(self, other):
    #     return (self.k, self.i, self.j) < (other.k, other.i, other.j)

class SubMatch:
    def __init__(self, length, longest_match, ratio=1, all_matches=None):
        self.length = length
        self.ratio = ratio
        self.longest_match = longest_match
        self.all_matches = all_matches


class MatchingBlocks:
    """
    saves all the data about matches between two variables.
    """
    LETTERS_MATCH = 0
    WORDS_MATCH = 1

    CONTINUOUS_MATCH = 0
    DISCONTINUOUS_MATCH = 1

    def __init__(self, a, b, matching_type, ratio, matches=None, cont_type=CONTINUOUS_MATCH,
                 continuity_heavy_weight=False):
        """
        Args:
            a: first variable
            b: second variable
            ratio: ratio between the variables
            cont_type: if the match must be continuous or not. Means, if after a match we can cut it from the text
                and concatenate the text before it to the text after it, or not.
        """
        self.a = a
        self.b = b
        self.ratio = ratio
        self.matching_type = matching_type
        self.continuity_heavy_weight = continuity_heavy_weight

        self.matches = []
        if matches is not None:
            self.set_matching_blocks(matches)

        self.cont_type = cont_type

    def set_matching_blocks(self, matching_blocks):
        for m in matching_blocks:
            self.append(m)

    def append(self, m):
        """
        Add a match to matching list
        Args:
            m: a match
        Returns:
            None
        """
        if isinstance(m, difflib.Match):
            if m.size > 0:
                self.matches.append(OneMatch(m.a, m.b, m.size))
        elif isinstance(m, (list, tuple)):
            self.matches.append(OneMatch(*m))
        elif isinstance(m, OneMatch):
            self.matches.append(m)
        else:
            raise Exception(f'Unknown match format for the match {m} of type {type(m)}.')

    def set_ratio(self, ratio):
        """
        Set the ratio (float in [0,1]) between the variables
        Args:
            ratio: the ratio between the variables
        Returns:
            None
        """
        self.ratio = ratio

    def __str__(self):
        """
        Returns:
            Printable data about the relation between the two variables
        """
        res = f'var_1: {self.a}, var_2: {self.b}\n' \
              f'Ratio: {round(self.ratio, 3)}\n' \
              'Matches:\n'

        num_of_spaces = len(self.a) + len(self.b) - 2
        space_weight = ((2 / num_of_spaces) if num_of_spaces > 0 else 0) if not self.continuity_heavy_weight else 1
        length = (len(self.a) + len(self.b) + space_weight * num_of_spaces)

        for m in self.matches:
            partial_ratio = round(
                2 * ((m.k if self.matching_type == self.LETTERS_MATCH else m.r) + (m.k - 1) * space_weight) / length, 3)
            if self.matching_type == self.WORDS_MATCH:
                local_ratio = round(2 * (m.r + (m.k - 1) * space_weight) / (2 * (m.k + (m.k - 1) * space_weight)), 3)

            if self.cont_type == MatchingBlocks.CONTINUOUS_MATCH:
                res += f'\tvar_1[{m.i}:{m.i + m.k}], var_2[{m.j}:{m.j + m.k}], length: {m.k}, '
                if self.matching_type == self.LETTERS_MATCH:
                    res += f'partial ratio: {partial_ratio}: \t"{self.a[m.i: m.i + m.k]}"\n'
                else:
                    res += f'local ratio: {local_ratio}, partial ratio: {partial_ratio}:\n' \
                           f'\t\t{self.a[m.i: m.i + m.k]} vs. \n\t\t{self.b[m.j: m.j + m.k]}\n'
            else:
                res += f'\tvar_1{m.i}, var_2{m.j}, length: {len(m.i)}, '

                if self.matching_type == self.LETTERS_MATCH:
                    res += f'partial ratio: {partial_ratio}: \t"{"".join([self.a[i] for i in m.i])}"\n'
                else:
                    res += f'local ratio: {local_ratio}, partial ratio: {partial_ratio}:\n' \
                           f'\t\t{"".join([self.a[i] for i in m.i])} ' \
                           f'vs. \n\t\t{"".join([self.b[j] for j in m.j])}\n'
        return res


class VarsMatcher:
    """
    A class that finds many types of matches between two variables
    """
    NUMBERS_SEPARATE_WORD = 0
    NUMBERS_IGNORE = 1
    NUMBERS_LEAVE = 2

    Synonyms = Plural = None

    levenshtein = Levenshtein()
    damerau = Damerau()

    def __init__(self, name_1=None, name_2=None, case_sensitivity=False, word_separators='_ \t\n',
                 support_camel_case=True, numbers_behavior=NUMBERS_SEPARATE_WORD):
        """
        Args:
            name_1: first variable
            name_2: second variable
            case_sensitivity: match case sensitivity
            word_separators: Characters THE USER used for separating between words in the variables (like underscore)
            support_camel_case: use a capital letter to separate between words
            numbers_behavior: the behavior with a number in a variable:
                                    0: for use the number as a different word
                                    1: for deleting the number
                                    3: for leaving it to be a part of the word before or after it (or both),
                                        depend of another separators
        """
        self.var_1 = None
        self.var_2 = None
        self.case_sensitivity = case_sensitivity
        self.word_separators = word_separators
        self.support_camel_case = support_camel_case
        self.numbers_behavior = numbers_behavior

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

    def set_support_camel_case(self, support_camel_case):
        self.support_camel_case = support_camel_case

    def set_numbers_behavior(self, numbers_behavior):
        self.numbers_behavior = numbers_behavior

    def get_norm_names(self):
        return self.var_1.norm_name if self.var_1 is not None else None,\
               self.var_2.norm_name if self.var_2 is not None else None

    def get_words(self):
        return self.var_1.words if self.var_1 is not None else None,\
               self.var_2.words if self.var_2 is not None else None

    def _divide(self, name):
        """
        Divide the name to words (depends on the properties defined in the class's members)

        Args:
            name: variable raw name

        Returns:
            a list of all the words of the variable
        """
        name = re.sub(f'[^ -~]', self.word_separators[0], name)  # remove all non-visible characters

        if self.support_camel_case:
            name = re.sub('(.)([A-Z][a-z]+)', fr'\1{self.word_separators[0]}\2', name)
            name = re.sub('([a-z0-9])([A-Z])', fr'\1{self.word_separators[0]}\2', name)

            if self.numbers_behavior == VarsMatcher.NUMBERS_SEPARATE_WORD:
                name = re.sub('([A-Za-z])([0-9])', fr'\1{self.word_separators[0]}\2', name)
                name = re.sub('([0-9])([a-z])', fr'\1{self.word_separators[0]}\2', name)
            elif self.numbers_behavior == VarsMatcher.NUMBERS_IGNORE:
                name = re.sub('[0-9]', '', name)

        if not self.case_sensitivity:
            name = name.lower()

        return list(filter(None, re.split(fr'[{self.word_separators}]', name)))

    @staticmethod
    def _find_separator(name, other_var, default_sep):
        """
            After finding a match between the two variables and wanting to find another ones, we have to replace the
            previous matches with a special character that isn't exists in the other variable. This function finds it.

        Args:
            name: variable's name
            other_var: the name of the another variable (if already defined, or None if not)
            default_sep: preferred separator

        Returns:
            a separator for this variable
        """
        if (sep_condition := lambda x: x not in name and (other_var is None or x != other_var.separator))(default_sep):
            return default_sep

        for i in range(0x1, 0x100):
            if sep_condition(c := chr(i)):
                return c
        raise Exception('No separator can be found. You used all the characters in ASCII!')

    def edit_distance(self, enable_transposition=False):
        """
        Calculates (by calling another libraries functions) the edit distance between self.var_1 and self.var_2
        (after normalization)

        Args:
            enable_transposition: supporting Damerau distance - relating to swap between letters as a one action.
            For example: the distance between ABC and CA is 2 - swapping A and C, and removing B.

        Returns:
            The distance value
        """
        return VarsMatcher.levenshtein.distance(self.var_1.norm_name, self.var_2.norm_name) \
            if not enable_transposition else VarsMatcher.damerau.distance(self.var_1.norm_name, self.var_2.norm_name)

    def normalized_edit_distance(self, enable_transposition=False):
        """
        Calculates the edit distance as the edit_distance function, but normalized to be in the range [0,1]
        Args:
            enable_transposition: as at edit_distance function

        Returns:
            The distance value divided by the length of the longest normalized variable
        """

        return round(self.edit_distance(enable_transposition)
                     / max(len(self.var_1.norm_name), len(self.var_2.norm_name)), 3)

    def difflib_match_ratio(self):
        """
        Use the ratio of "difflib" library between self.var_1 and self.var_2 (after normalization)

        Returns:
            The ratio returned by difflib
        """
        seq_matcher = ExtendedSequenceMatcher(a=self.var_1.norm_name, b=self.var_2.norm_name)

        return MatchingBlocks(self.var_1.norm_name, self.var_2.norm_name, MatchingBlocks.LETTERS_MATCH,
                              seq_matcher.ratio(), seq_matcher.get_matching_blocks())

    @staticmethod
    def _calc_max_matches(str_1, str_2, str_1_len, str_2_len, str_1_start, str_2_start, separator_1, separator_2,
                          min_len, sequence_matcher, matches_table):
        """
        A function that implements dynamic programming methodology for finding for each two substrings of two strings
        the longest match that it plus the (smaller) matches in both sides of it will maximizes the total
        match.

        Args:
            str_1: first string to be compared
            str_2: second string to be compared
            str_1_len: the length of the substring of str_1
            str_2_len: the length of the substring of str_2
            str_1_start: the start point of the substring of str_1
            str_2_start: the start point of the substring of str_2
            min_len: minimum length to be counted as match
            sequence_matcher: an instance of ExtendedSequenceMatcher (that inherits difflib.SequenceMatcher)
            matches_table: a table that contains all the matches in smaller substrings

        Returns:
            the maximal match for this substring.
        """
        str_1_end = str_1_start + str_1_len + 1
        str_2_end = str_2_start + str_2_len + 1

        matching_blocks = []
        max_matches = None

        i, j, k = match = sequence_matcher.find_longest_match(str_1_start, str_1_end, str_2_start, str_2_end)

        if (longest_match_len := k) < min_len:
            return None

        aux_sequence_matcher = sequence_matcher

        while k == longest_match_len:
            matching_blocks.append(OneMatch(*match))

            j_, k_ = j, k
            while True:
                i_, j_, k_ = match_ = aux_sequence_matcher.find_longest_match(i, i + k, j_ + k_, str_2_end)
                if k_ < k:
                    break
                matching_blocks.append(OneMatch(*match_))

            i_, k_ = i, k
            while True:
                i_, j_, k_ = match_ = aux_sequence_matcher.find_longest_match(i_ + k_, str_1_end, j, j + k)
                if k_ < k:
                    break
                matching_blocks.append(OneMatch(*match_))

            str_1 = str_1[:i] + separator_2 * k + str_1[i + k:]
            str_2 = str_2[:j] + separator_1 * k + str_2[j + k:]

            if aux_sequence_matcher is sequence_matcher:
                aux_sequence_matcher = ExtendedSequenceMatcher()

            aux_sequence_matcher.set_seq1(str_1)
            aux_sequence_matcher.update_matching_seq2(str_2, j, k)
            i, j, k = match = aux_sequence_matcher.find_longest_match(str_1_start, str_1_end, str_2_start, str_2_end)

        for m in matching_blocks:
            left_max_matches = (0, 0) if m.i == str_1_start or m.j == str_2_start or (
                left_match := matches_table[m.i - str_1_start - 1][m.j - str_2_start - 1][str_1_start][str_2_start]
            ) is None else (left_match.length, left_match.ratio)
            right_max_matches = (0, 0) if m.i + m.k == str_1_end or m.j + m.k == str_2_end or (
                right_match := matches_table[str_1_end - (m.i + m.k) - 1][str_2_end - (m.j + m.k) - 1][m.i + m.k][m.j + m.k]
            ) is None else (right_match.length, right_match.ratio)

            curr_all_matches = (m.k + left_max_matches[0] + right_max_matches[0],
                                pow(m.k, 2) + left_max_matches[1] + right_max_matches[1])

            if max_matches is None or curr_all_matches > (max_matches.length, max_matches.ratio):
                max_matches = SubMatch(curr_all_matches[0], OneMatch(m.i, m.j, m.k), curr_all_matches[1])

        return max_matches

    @staticmethod
    def backtrack_matches(matches_table, len_1, len_2, min_len=1):
        """
        Calculates the matches that take part in the maximal ordered matching

        Args:
            matches_table: the table that contains all the maximal matches for each subtext in var_a and var_b
            len_1: length of var_a
            len_2: length of var_b
            min_len: minimum length that related as a match

        Returns:
            a list of all the matches (sorted desc. by their length) involved in the maximal ordered matching.
        """
        matching_indices = []
        matching_blocks = []

        len_1_idx = len_1 - 1
        len_2_idx = len_2 - 1
        start_1_idx = 0
        start_2_idx = 0

        matching_indices.append((len_1_idx, len_2_idx, start_1_idx, start_2_idx))

        range_idx = 0

        while range_idx < len(matching_indices):
            len_1_idx, len_2_idx, start_1_idx, start_2_idx = matching_indices[range_idx]
            x = matches_table[len_1_idx][len_2_idx][start_1_idx][start_2_idx]
            if x:
                m = x.longest_match

                if m.i - start_1_idx >= min_len and m.j - start_2_idx >= min_len:
                    matching_indices.append((m.i - start_1_idx - 1, m.j - start_2_idx - 1, start_1_idx, start_2_idx))

                if (str_1_end := start_1_idx + len_1_idx + 1) - (m.i + m.k) >= min_len and \
                        (str_2_end := start_2_idx + len_2_idx + 1) - (m.j + m.k) >= min_len:
                    matching_indices.append((str_1_end - (m.i + m.k) - 1, str_2_end - (m.j + m.k) - 1, m.i + m.k, m.j + m.k))

            range_idx += 1

        for len_1_idx, len_2_idx, start_1_idx, start_2_idx in matching_indices:
            if (match_data := matches_table[len_1_idx][len_2_idx][start_1_idx][start_2_idx]) is not None and \
                    (match := match_data.longest_match) is not None:
                matching_blocks.append(match)

        return matching_blocks

    @staticmethod
    def calc_final_ratios(matching_blocks, len_1, len_2, continuity_heavy_weight=False):
        if matching_blocks is None or len(matching_blocks) == 0:
            return 0, 0

        num_of_spaces = len_1 + len_2 - 2
        space_weight = ((2 / num_of_spaces) if num_of_spaces > 0 else 0) if not continuity_heavy_weight else 1

        k, l, r, s = sum(matching_blocks)

        simple_ratio = ((2 * k + 2 * s * space_weight) / denominator) \
            if (denominator := (len_1 + len_2 + space_weight * num_of_spaces)) > 0 else 0

        deeper_ratio = ((2 * r + 2 * s * space_weight) / denominator) \
            if (denominator := len_1 + len_2 + space_weight * num_of_spaces) > 0 else 0

        return simple_ratio, deeper_ratio

    @classmethod
    def str_ordered_match(cls, str_1, str_2, separator_1, separator_2, min_len=2, continuity_heavy_weight=False):
        len_1 = len(str_1)
        len_2 = len(str_2)
        sequence_matcher = ExtendedSequenceMatcher(a=str_1, b=str_2)

        matches_table = [[[[None for _ in range(len_2 - str_2_len)] for _ in range(len_1 - str_1_len)]
                          for str_2_len in range(len_2)] for str_1_len in range(len_1)]

        for str_1_len in range(len_1):  # Actually the length is plus one
            for str_2_len in range(len_2):  # Actually the length is plus one
                for str_1_start in range(len_1 - str_1_len):
                    for str_2_start in range(len_2 - str_2_len):
                        matches_table[str_1_len][str_2_len][str_1_start][str_2_start] = cls._calc_max_matches(
                            str_1, str_2, str_1_len, str_2_len, str_1_start, str_2_start, separator_1, separator_2,
                            min_len, sequence_matcher, matches_table)

        continuity_ratio = cls.calc_final_ratios((
            matches := cls.backtrack_matches(
                matches_table, len_1, len_2, min_len)), len_1, len_2, continuity_heavy_weight)[0]

        return MatchingBlocks(
            str_1, str_2, MatchingBlocks.LETTERS_MATCH, continuity_ratio, matches,
            continuity_heavy_weight=continuity_heavy_weight)

    def ordered_match(self, min_len=2, continuity_heavy_weight=False):
        """
        A function that calculates the maximal ordered matches between two variables.
        Note: the function of difflib library doesn't find always the maximal match. For example, when comparing the two
        names: 'FirstLightAFire' and 'LightTheFireFirst', it will find at first the match 'first' at the beginning of
        the first name and at the end of the second name, and then stopping because it saves the order of the matches,
        and any other match will be AFTER the first one in the first match and BEFORE it in the second name.
        However, Our algorithm, will check all the options, and in that case will find at first the match 'light', and
        then 'Fire' (9 letters total, vs. 5 letter in the difflib library).

        Args:
            min_len: minimum length of letters that related as a match

        Returns:
            MatchingBlocks
        """
        return self.str_ordered_match(self.var_1.norm_name, self.var_2.norm_name,
                                      self.var_1.separator, self.var_2.separator, min_len, continuity_heavy_weight)

    @staticmethod
    def str_unordered_match(str_1, str_2, separator_1, separator_2,
                            min_len=2, continuity_heavy_weight=False):
        modified_str_1 = str_1[:]
        modified_str_2 = str_2[:]

        len_1 = len(modified_str_1)
        len_2 = len(modified_str_2)
        space_weight = 1 if continuity_heavy_weight \
            else ((2 / num_of_spaces) if (num_of_spaces := len_1 + len_2 - 2) > 0 else 0)

        matching_blocks = []
        match_len = 0
        match_spaces_weight = 0

        sm = ExtendedSequenceMatcher(a=modified_str_1, b=modified_str_2)
        while True:
            i, j, k = x = sm.find_longest_match(0, len_1, 0, len_2)
            if k < min_len:
                break

            matching_blocks.append(x)
            match_len += k
            match_spaces_weight += (k - 1) * space_weight
            modified_str_1 = modified_str_1[:i] + separator_2 * k + modified_str_1[i + k:]
            modified_str_2 = modified_str_2[:j] + separator_1 * k + modified_str_2[j + k:]
            sm.set_seq1(modified_str_1)
            sm.update_matching_seq2(modified_str_2, j, k)

        continuity_ratio = ((2 * match_len + 2 * match_spaces_weight) / denominator) \
            if (denominator := (len_1 + len_2 + space_weight * (len_1 + len_2 - 2))) > 0 else 0

        return MatchingBlocks(str_1, str_2, MatchingBlocks.LETTERS_MATCH, continuity_ratio, matching_blocks,
                              continuity_heavy_weight=continuity_heavy_weight)

    def unordered_match(self, min_len=2, continuity_heavy_weight=False):
        """
        A function that calculates match ratio between two names, but doesn't requires order between matches. It means that
        it could match the first word from the first name to the last in the second name, and, in addition, the second
        word in the first name to the first word in the second name
        Args:
            min_len: minimum length of letters that related as a match
            continuity_heavy_weight: The weight of continuity between two letters: Because in this function we find
                matches also when they are unordered, we have to give match of "AB" vs. "AB" more weight than
                "AB" vs. "BA" (even though in this function we recognized both "A" and "B" as a match even when the
                order is different).
                As a result, we give a weight also to continuity of letters. Means, when we find a match of two letters
                continuously, we give a score also to "the continuity", and as a result we relate to the string as it
                composed of letters and continuities.
                This score could let "the continuity" a HEAVY weight (True) - as it was a letter, or LIGHT weight
                (False) - 1/N when N is the average number of the letters in the two words.

        Returns:
            MatchingBlocks
        """
        return self.str_unordered_match(self.var_1.norm_name, self.var_2.norm_name,
                                        self.var_1.separator, self.var_2.separator, min_len, continuity_heavy_weight)

    def unedit_match(self, min_len=2, continuity_heavy_weight=False):
        """
        A function that calculates the ratio between two variables, but after finding a match it removes it from the
        string, and search again. As a result, if, for example one required min_len to be 2, and the two names will be:
        'ABCDE' and 'ADEBC', after matching 'BC' both names will be 'ADE', so 'A' will be part of the match in spite of
        in the original names it isn't a part of a word with at least 2 letters.
        Args:
            min_len: minimum length of letters that related as a match

        Returns:
            MatchingBlocks
        """
        name_1 = self.var_1.norm_name[:]
        name_2 = self.var_2.norm_name[:]

        len_1 = len(self.var_1.norm_name)
        len_2 = len(self.var_2.norm_name)

        space_weight = 1 if continuity_heavy_weight \
            else ((2 / num_of_spaces)
                  if (num_of_spaces := len_1 + len_2 - 2) > 0 else 0)

        indices_1 = list(range(len(name_1)))
        indices_2 = list(range(len(name_2)))

        matching_blocks = []
        match_len = 0
        match_spaces_weight = 0

        sm = ExtendedSequenceMatcher(a=name_1, b=name_2)
        while True:
            i, j, k = sm.find_longest_match(0, len(name_1), 0, len(name_2))

            if k < min_len:
                break

            matching_blocks.append((indices_1[i:i + k], indices_2[j:j + k]))

            match_len += k
            match_spaces_weight += (k - 1) * space_weight
            name_1 = name_1[:i] + name_1[i + k:]
            name_2 = name_2[:j] + name_2[j + k:]
            indices_1 = indices_1[:i] + indices_1[i + k:]
            indices_2 = indices_2[:j] + indices_2[j + k:]
            sm.set_seq1(name_1)
            sm.set_seq2(name_2)

        continuity_ratio = ((2 * match_len + 2 * match_spaces_weight) / denominator) \
            if (denominator := len_1 + len_2 + space_weight * (len_1 + len_2 - 2)) > 0 else 0

        return MatchingBlocks(self.var_1.norm_name, self.var_2.norm_name, MatchingBlocks.LETTERS_MATCH,
                              continuity_ratio, matching_blocks, MatchingBlocks.DISCONTINUOUS_MATCH,
                              continuity_heavy_weight)

    @classmethod
    def words_meaning(cls, word_1, word_2):
        """
        A function that check if one word is a synonym or the plural of another
        Args:
            word_1: a word
            word_2: a word

        Returns:
            True if there is a relationship (synonym or plural) between the two words, False otherwise.
        """
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
        elif (len(word_1) > 2 and word_2.startswith(word_1)) or \
                (len(word_2) > 2 and word_1.startswith(word_2)):
            return True

        return False

    @classmethod
    def find_longest_words_matches(cls, var_1_list, var_2_list, separator_1, separator_2,
                                   min_word_match_degree, prefer_num_of_letters, use_meanings,
                                   continuity_heavy_weight=None):
        """
        A function that finds the longest match OF WHOLE WORDS, means the longest list of matched words.

        Args:
            separator_1: a letter that does not exist in var_1
            separator_2: a letter that does not exist in var_2
            var_1_list: list of words
            var_2_list: list of words
            letters_match_func: a function that compares two strings of letters (not words), and returns MatchingBlocks
                                object. Used for finding the maximal match when the words aren't equal.
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters
            use_meanings: boolean value that set if to match two words with similar meaning, or not
            continuity_heavy_weight: continuity_heavy_weight: The weight of continuity between two words: Because in this function we find
                matches also when they are unordered, we have to give match of "AB" vs. "AB" (when "A" and "B" are
                words) more weight than "AB" vs. "BA" (even though in this function we recognized both "A" and "B" as a
                match even when the order is different).
                As a result, we give a weight also to continuity of words. Means, when we find a match of two words
                continuously, we give a score also to "the continuity", and as a result we relate to the string as it
                composed of words and continuities.
                This score could let "the continuity" a HEAVY weight (True) - as it was a word, or LIGHT weight
                (False) - 1/N when N is the average number of the words in the two strings.


        Returns:
            A tuple that contains:
                - The starting index if the first word in the longest match
                - The starting index if the second word in the longest match
                - The length of the match (the number of words in it)
                - Sum of the distances between all the words in this match
        """
        checked_points = {}

        len_a = len(var_1_list)
        len_b = len(var_2_list)

        res = None

        for i in range(len_a):
            for j in range(len_b):
                if checked_points.get((i, j)) is not None:  # Because or they aren't similar, or, if they are similar,
                    continue  # they already a part of a longer sequence

                k = r = l = 0  # k: word index, r: sum of ratios, l: number of letters
                while i + k < len_a and j + k < len_b:
                    if var_1_list[i + k] == var_2_list[j + k]:
                        ratio = 1
                    else:
                        ratio = cls.str_ordered_match(var_1_list[i + k], var_2_list[j + k], separator_1, separator_2, 1,
                                                      continuity_heavy_weight).ratio

                    if ratio < min_word_match_degree:
                        if use_meanings and cls.words_meaning(var_1_list[i + k], var_2_list[j + k]):
                            ratio = min_word_match_degree
                        else:
                            checked_points[(i + k, j + k)] = False
                            break

                    checked_points[(i + k, j + k)] = True
                    r += ratio
                    l += (len(var_1_list[i + k]) + len(var_2_list[j + k])) / 2
                    k += 1

                    lengths = (k, l) if not prefer_num_of_letters else (l, k)
                    if res is not None:
                        longest_lengths = (res[0].k, res[0].l) if not prefer_num_of_letters \
                            else (res[0].l, res[0].k)

                    if res is None or (curr := (r, *lengths)) > (longest := (res[0].r, *longest_lengths)):
                        res = [OneMatch(i, j, k, l, r)]
                    elif curr == longest:
                        res.append(OneMatch(i, j, k, l, r))

        return res

    def _unordered_words_find_max_sub_match(self, words_1, words_2, min_word_match_degree, prefer_num_of_letters,
                                            use_meanings, continuity_heavy_weight):
        max_sub_match = SubMatch((0, 0), 0, 0, [])

        longest_matches = self.find_longest_words_matches(words_1, words_2,
                                                          self.var_1.separator, self.var_2.separator,
                                                          min_word_match_degree, prefer_num_of_letters, use_meanings,
                                                          continuity_heavy_weight)
        if longest_matches is None:
            return max_sub_match

        for m in longest_matches:
            curr_sub_match = self._unordered_words_find_max_sub_match(
                words_1[:m.i] + [self.var_2.separator] * m.k + words_1[m.i+m.k:],
                words_2[:m.j] + [self.var_1.separator] * m.k + words_2[m.j+m.k:],
                min_word_match_degree, prefer_num_of_letters, use_meanings, continuity_heavy_weight)

            curr_sub_match.longest_match = m
            curr_sub_match.ratio += m.r
            curr_sub_match.length = (curr_sub_match.length[0] + m.k, curr_sub_match.length[1] + m.l) \
                if not prefer_num_of_letters else (curr_sub_match.length[0] + m.l, curr_sub_match.length[1] + m.k)
            curr_sub_match.all_matches.insert(0, m)

            if (curr_sub_match.ratio, *curr_sub_match.length) > (max_sub_match.ratio, *max_sub_match.length):
                max_sub_match = curr_sub_match

        return max_sub_match

    def _unordered_words_and_meaning_match(self, min_word_match_degree, prefer_num_of_letters,
                                           use_meanings, continuity_heavy_weight=False):
        """
            A function that finds all the matches between the words of var_1 and var_2, in In descending order of number
            of the words or letters.
        Args:
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters
            use_meanings: boolean value that set if to match two words with similar meaning, or not.
            continuity_heavy_weight: The weight of continuity between two words: Because in this function we find
                matches also when they are unordered, we have to give match of "AB" vs. "AB" (when "A" and "B" are
                words) more weight than "AB" vs. "BA" (even though in this function we recognized both "A" and "B" as a
                match even when the order is different).
                As a result, we give a weight also to continuity of words. Means, when we find a match of two words
                continuously, we give a score also to "the continuity", and as a result we relate to the string as it
                composed of words and continuities.
                This score could let "the continuity" a HEAVY weight (True) - as it was a word, or LIGHT weight
                (False) - 1/N when N is the average number of the words in the two strings.

        Returns:
            MatchingBlocks
        """
        len_1 = len(self.var_1.words)
        len_2 = len(self.var_2.words)

        space_weight = 1 if continuity_heavy_weight \
            else ((2 / num_of_spaces) if (num_of_spaces := len_1 + len_2 - 2) > 0 else 0)

        max_sub_match = self._unordered_words_find_max_sub_match(self.var_1.words, self.var_2.words,
                                                                 min_word_match_degree, prefer_num_of_letters,
                                                                 use_meanings, continuity_heavy_weight)

        match_spaces_weight = sum((m_i.k - 1) * space_weight for m_i in max_sub_match.all_matches)
        ratio = sum(m_i.r for m_i in max_sub_match.all_matches)

        matching_ratio = ((2 * ratio + 2 * match_spaces_weight) / denominator) \
            if (denominator := len_1 + len_2 + space_weight * (len_1 + len_2 - 2)) > 0 else 0

        return MatchingBlocks(self.var_1.words, self.var_2.words, MatchingBlocks.WORDS_MATCH,
                              matching_ratio, max_sub_match.all_matches,
                              continuity_heavy_weight=continuity_heavy_weight)

    def unordered_words_match(self, min_word_match_degree=2/3, prefer_num_of_letters=False,
                              continuity_heavy_weight=False):
        """
        A function that calculates the ratio and the matches between the words of var_1 and var_2, but doesn't
        relate synonyms and plurals as a match.
        Args:
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters
            continuity_heavy_weight: The weight of continuity between two words: Because in this function we find
                matches also when they are unordered, we have to give match of "AB" vs. "AB" (when "A" and "B" are
                words) more weight than "AB" vs. "BA" (even though in this function we recognized both "A" and "B" as a
                match even when the order is different).
                As a result, we give a weight also to continuity of words. Means, when we find a match of two words
                continuously, we give a score also to "the continuity", and as a result we relate to the string as it
                composed of words and continuities.
                This score could let "the continuity" a HEAVY weight (True) - as it was a word, or LIGHT weight
                (False) - 1/N when N is the average number of the words in the two strings.

        Returns:
            MatchingBlocks
        """
        return self._unordered_words_and_meaning_match(min_word_match_degree, prefer_num_of_letters, use_meanings=False,
                                                       continuity_heavy_weight=continuity_heavy_weight)

    def unordered_semantic_match(self, min_word_match_degree=2 / 3, prefer_num_of_letters=False,
                                 continuity_heavy_weight=False):
        """

        A function that calculates the ratio and the matches between the words of var_1 and var_2, and relates synonyms
        and plurals as a match.

        Args:
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters
            continuity_heavy_weight: The weight of continuity between two words: Because in this function we find
                matches also when they are unordered, we have to give match of "AB" vs. "AB" (when "A" and "B" are
                words) more weight than "AB" vs. "BA" (even though in this function we recognized both "A" and "B" as a
                match even when the order is different).
                As a result, we give a weight also to continuity of words. Means, when we find a match of two words
                continuously, we give a score also to "the continuity", and as a result we relate to the string as it
                composed of words and continuities.
                This score could let "the continuity" a HEAVY weight (True) - as it was a word, or LIGHT weight
                (False) - 1/N when N is the average number of the words in the two strings.

        Returns:
            MatchingBlocks
        """
        return self._unordered_words_and_meaning_match(min_word_match_degree, prefer_num_of_letters,
                                                       use_meanings=True, continuity_heavy_weight=continuity_heavy_weight)

    def _calc_max_words_matches(self, var_1_len, var_2_len, var_1_start, var_2_start, matches_table,
                                min_word_match_degree, prefer_num_of_letters, use_meanings,
                                continuity_heavy_weight=False):
        """

        Args:
            var_1_len: the length minus 1 of the substring of self.var_1
            var_2_len: the length minus 1 of the substring of self.var_2
            var_1_start: the start point of the substring of self.var_1
            var_2_start: the start point of the substring of self.var_2
            matches_table: a table that contains all the matches in smaller substrings
            min_word_match_degree: the minimum ratio between two words to be consider as a match
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters
            use_meanings: boolean value that set if to match two words with similar meaning, or not

        Returns:
            the maximal match for this substring.
        """
        var_1_end = var_1_start + var_1_len + 1
        var_2_end = var_2_start + var_2_len + 1

        params = (self.var_1.separator, self.var_2.separator, min_word_match_degree, prefer_num_of_letters,
                  use_meanings, continuity_heavy_weight)

        max_matches = None

        longest_matches = self.find_longest_words_matches(self.var_1.words[var_1_start: var_1_end],
                                          self.var_2.words[var_2_start: var_2_end], *params)

        if longest_matches is None or longest_matches[0].k < 1:
            return None

        for long_match in longest_matches:
            long_match.i += var_1_start
            long_match.j += var_2_start

            left_match = right_match = None
            lengths = (long_match.k, long_match.l) if not prefer_num_of_letters else (long_match.l, long_match.k)

            left_max_matches = ([0, 0], 0) if long_match.i == var_1_start or long_match.j == var_2_start or (
                left_match := matches_table[long_match.i - var_1_start - 1][long_match.j - var_2_start - 1][var_1_start][var_2_start]
            ) is None else (left_match.length, left_match.ratio)
            right_max_matches = ([0, 0], 0) if long_match.i + long_match.k == var_1_end or long_match.j + long_match.k == var_2_end or (
                right_match := matches_table[var_1_end - (long_match.i + long_match.k) - 1][var_2_end - (long_match.j + long_match.k) - 1][long_match.i + long_match.k][long_match.j + long_match.k]
            ) is None else (right_match.length, right_match.ratio)

            curr_lengths = [sum(len_type) for len_type in zip(lengths, left_max_matches[0], right_max_matches[0])]
            curr_ratio = long_match.r + left_max_matches[1] + right_max_matches[1]

            if max_matches is None or (curr_ratio, *curr_lengths) > (max_matches.ratio, *max_matches.length):
                max_matches = SubMatch(curr_lengths, long_match, curr_ratio)

        return max_matches

    def _words_and_meaning_match(self, min_word_match_degree=2 / 3, prefer_num_of_letters=False,
                                 use_meanings=False, continuity_heavy_weight=False):
        """
        A function that calculates the maximal ordered matches between two variables.
        Note: the function of difflib library doesn't find always the maximal match. For example, when comparing the two
        names: 'FirstLightAFire' and 'LightTheFireFirst', it will find at first the match 'first' at the beginning of
        the first name and at the end of the second name, and then stopping because it saves the order of the matches,
        and any other match will be AFTER the first one in the first match and BEFORE it in the second name.
        However, Our algorithm, will check all the options, and in that case will find at first the match 'light', and
        then 'Fire' (9 letters total, vs. 5 letter in the difflib library).

        Args:
            min_len: minimum length of letters that related as a match
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters
            use_meanings: boolean that set if to relate to synonyms or singular/plural words as match even the Edit
                                    Distance between them is high, or not.

        Returns:
            MatchingBlocks
        """
        len_1 = len(self.var_1.words)
        len_2 = len(self.var_2.words)

        matches_table = [[[[None for _ in range(len_2 - str_2_len)] for _ in range(len_1 - str_1_len)]
                          for str_2_len in range(len_2)] for str_1_len in range(len_1)]

        for str_1_len in range(len_1):  # Actually the length is plus one
            for str_2_len in range(len_2):  # Actually the length is plus one
                for str_1_start in range(len_1 - str_1_len):
                    for str_2_start in range(len_2 - str_2_len):
                        matches_table[str_1_len][str_2_len][str_1_start][str_2_start] = self._calc_max_words_matches(
                            str_1_len, str_2_len, str_1_start, str_2_start, matches_table, min_word_match_degree,
                            prefer_num_of_letters, use_meanings, continuity_heavy_weight)

        matching_blocks = self.backtrack_matches(matches_table, len_1, len_2)

        len_continuity_matching_ratio = self.calc_final_ratios(matching_blocks,
            len_1, len_2, continuity_heavy_weight=continuity_heavy_weight)[1]

        return MatchingBlocks(self.var_1.words, self.var_2.words, MatchingBlocks.WORDS_MATCH,
                              len_continuity_matching_ratio, matching_blocks,
                              continuity_heavy_weight=continuity_heavy_weight)

    def ordered_words_match(self, min_word_match_degree=2/3, prefer_num_of_letters=False,
                            continuity_heavy_weight=False):
        """
        A function that calculates the maximal ordered matches between two variables, while the comparisons are done
        on each word of the variables as a unit, and not on the letters.
        Note: the function of difflib library doesn't find always the maximal match. For example, when comparing the two
        lists of words: ['first', 'light', 'a', 'fire'] and ['light', 'the', 'fire', 'first'], it will find at first the
        match 'first' at the beginning of the first list and at the end of the second list, and then stopping, because
        it saves the order of the matches, and any other match will be AFTER the first one in the first match and BEFORE
        it in the second name.
        However, Our algorithm, will check all the options, and in that case will find at first the match 'light', and
        then 'fire' (2 words total, vs. 1 word in the difflib library).

        Args:
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters

        Returns:
            MatchingBlocks
        """
        return self._words_and_meaning_match(min_word_match_degree, prefer_num_of_letters,
                                             continuity_heavy_weight=continuity_heavy_weight)

    def ordered_semantic_match(self, min_word_match_degree=2/3, prefer_num_of_letters=False,
                               continuity_heavy_weight=False):
        """
        A function that calculates the maximal ordered matches between two variables, while the comparisons are done
        on each word of the variables as a unit, and not on the letters.
        In addition, this function relates synonyms and plurals as a match.
        Note: the function of difflib library doesn't find always the maximal match. For example, when comparing the two
        lists of words: ['first', 'light', 'a', 'fire'] and ['light', 'the', 'fire', 'first'], it will find at first the
        match 'first' at the beginning of the first list and at the end of the second list, and then stopping, because
        it saves the order of the matches, and any other match will be AFTER the first one in the first match and BEFORE
        it in the second name.
        However, Our algorithm, will check all the options, and in that case will find at first the match 'light', and
        then 'fire' (2 words total, vs. 1 word in the difflib library).

        Args:
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters
            min_word_match_degree: float value in the range (0, 1] that set the min Match Degree between two words.
                                    Match Degree between two words equal to:
                                    1 - (edit distance between the words / length of the shortest word)
            prefer_num_of_letters: boolean value that set if 'longest match' (that we search at first) will be the one
                                    with more words, or with more letters

        Returns:
            MatchingBlocks
        """
        return self._words_and_meaning_match(min_word_match_degree, prefer_num_of_letters,
                                             use_meanings=True, continuity_heavy_weight=continuity_heavy_weight)


def run_test(match_maker, pairs, func, **kwargs):
    for var_1, var_2 in pairs:
        match_maker.set_names(var_1, var_2)
        start_time = datetime.now()
        print(f'>>> MatchMaker("{var_1}", "{var_2}").{func.__name__}('
              f'{", ".join([k + "=" + str(v if not isinstance(v, float) else round(v, 3)) for k, v in kwargs.items()])})\n{func(**kwargs)}')
        # print(f'Test time for {func.__name__}: {datetime.now() - start_time}')
    print()


if __name__ == '__main__':
    set_bit = lambda bit, num=0: num | (1 << bit)

    TEST_EDIT_DISTANCE = set_bit(0)
    TEST_NORMALIZED_EDIT_DISTANCE = set_bit(1)
    TEST_DIFFLIB_MATCHER_RATIO = set_bit(2)
    TEST_ORDERED_MATCH = set_bit(3)
    TEST_ORDERED_WORD_MATCH = set_bit(4)
    TEST_ORDERED_SEMANTIC_MATCH = set_bit(5)
    TEST_UNORDERED_MATCH = set_bit(6)
    TEST_UNORDERED_WORDS_MATCH = set_bit(7)
    TEST_UNORDERED_SEMANTIC_MATCH = set_bit(8)
    TEST_UNEDIT_MATCH = set_bit(9)

    scriptIndex = (len(sys.argv) > 1 and int(sys.argv[1], 0)) or -1
    files_path = (sys.argv[2], sys.argv[3]) if len(sys.argv) > 3 else None

    files = [(open(files_path[0]).read(), open(files_path[1]).read())] if files_path else None

    match_maker = VarsMatcher()

    if scriptIndex & TEST_EDIT_DISTANCE:
        var_names = files or [('CA', 'ABC'), ('TotalArraySize', 'ArrayTotalSize')]
        run_test(match_maker, var_names, match_maker.edit_distance)
        run_test(match_maker, var_names, match_maker.edit_distance, enable_transposition=True)

    if scriptIndex & TEST_NORMALIZED_EDIT_DISTANCE:
        var_names = files or [('CA', 'ABC')]
        run_test(match_maker, var_names, match_maker.normalized_edit_distance)
        run_test(match_maker, var_names, match_maker.normalized_edit_distance, enable_transposition=True)

    if scriptIndex & TEST_DIFFLIB_MATCHER_RATIO:
        var_names = files or [('AB_CD_EF', 'EF_CD_AB'),
                              ('FirstLightAFire', 'LightTheFireFirst'), ('LightTheFireFirst', 'FirstLightAFire'),
                              ('FirstLightAFire', 'AFireLightFlickersAtFirst'),
                              ('AFireLightFlickersAtFirst', 'FirstLightAFire'),
                              ('MultiplyDigitExponent', 'DigitsPowerMultiplying'),
                              ('DigitPowerMultiplying', 'MultiplyDigitExponent')]
        run_test(match_maker, var_names, match_maker.difflib_match_ratio)

    if scriptIndex & TEST_ORDERED_MATCH:
        var_names = files or [
            ('AB_CD_EF', 'EF_CD_AB'),
            ('AB_X_CDE', 'CDE_Y_AB_Y_CDE'),
            ('FirstLightAFire', 'LightTheFireFirst'),
            ('LightTheFireFirst', 'FirstLightAFire'),
            ('FirstLightAFire', 'AFireLightFlickersAtFirst'), ('AFireLightFlickersAtFirst', 'FirstLightAFire'),
            ('MultiplyDigitExponent', 'DigitsPowerMultiplying'),
            ('multiword_name', 'multiple_words_name'),
        ]
        run_test(match_maker, var_names, match_maker.ordered_match, min_len=1)
        run_test(match_maker, var_names, match_maker.ordered_match, min_len=2)

    if scriptIndex & TEST_ORDERED_WORD_MATCH:
        var_names = [
            ('FirstLightAFire', 'LightTheFireFirst'),
            ('multiply_digits_exponent', 'multiply_digits_power'),
            ('TheChildArrivesToTheClassroom', 'TheChildArrivesToTheSchoolroom'),
            ('TheChildArrivesToTheClassroom', 'TheChildGetToTheSchoolroom'),
            ('TheChildArrivesToTheClassroom', 'TheKidGetToBallroom'),
            ('TheChildArrivesToTheClassroom', 'TheKidGetToTheSchoolroom'),
            ('TheWhiteHouse', 'TheHouseIsWhite'),
            ('MultiplyDigitExponent', 'DigitsPowerMultiplying'),
            ('multiword_name', 'multiple_words_name'),
            ('words_name', 'multiple_words_name'),
        ]
        run_test(match_maker, var_names, match_maker.ordered_words_match, min_word_match_degree=1)
        run_test(match_maker, var_names, match_maker.ordered_words_match, min_word_match_degree=2 / 3)
        run_test(match_maker, var_names, match_maker.ordered_words_match, min_word_match_degree=0.5)
        run_test(match_maker, var_names, match_maker.ordered_words_match, min_word_match_degree=2 / 3,
                 prefer_num_of_letters=True)

    if scriptIndex & TEST_ORDERED_SEMANTIC_MATCH:
        var_names = files or [('FirstLightAFire', 'LightTheFireFirst'),
                              ('TheChildArrivesToTheClassroom', 'TheKidGetToTheSchoolroom'),
                              ('MultiplyDigitExponent', 'DigitsPowerMultiplying')]
        run_test(match_maker, var_names, match_maker.ordered_semantic_match, min_word_match_degree=2 / 3)

    if scriptIndex & TEST_UNORDERED_MATCH:
        var_names = files or [('A_CD_EF_B', 'A_EF_CD_B'),
                              ('FirstLightAFire', 'LightTheFireFirst'), ('LightTheFireFirst', 'FirstLightAFire'),
                              ('FirstLightAFire', 'AFireLightFlickersAtFirst'),
                              ('AFireLightFlickersAtFirst', 'FirstLightAFire'),
                              ('ABCDEFGHIJKLMNOP', 'PONMLKJIHGFEDCBA'), ('ABCDEFGHIJKLMNOP', 'ONLPBCJIHGFKAEDM'),
                              ('MultiplyDigitExponent', 'DigitsPowerMultiplying')]
        run_test(match_maker, var_names, match_maker.unordered_match, min_len=1)
        run_test(match_maker, var_names, match_maker.unordered_match, min_len=1, continuity_heavy_weight=True)
        run_test(match_maker, var_names, match_maker.unordered_match, min_len=2)
        run_test(match_maker, var_names, match_maker.unordered_match, min_len=2, continuity_heavy_weight=True)

    if scriptIndex & TEST_UNORDERED_WORDS_MATCH:
        var_names = files or [
            ('TheSchoolBusIsYellow', 'TheSchoolBosIsYellow'),
            ('TheSchoolBusIsYellow', 'TheSchooolBosIsYellow'),
            ('FirstLightAFire', 'LightTheFireFirst'),
            ('FirstLightFire', 'LightFireFirst'),
            ('TheSchoolBusIsYellow', 'YellowIsTheSchoolBusColor'),
            ('multiply_digits_exponent', 'multiply_digits_power'),
            ('TheChildArrivesToTheClassroom', 'TheKidGetToSchoolroom'),
            ('TheChildArrivesToTheClassroom', 'TheKidGetToBallroom'),
            ('TheWhiteHouse', 'TheHouseIsWhite'),
            ('MultiplyDigitExponent', 'DigitsPowerMultiplying'),
            ('abcdefghijk_abcdefgh', 'bcdefghijkl_efghijkl'),
            ('abcdefghijk', 'bcdefghijkl'),
            ('abcdefghijk', 'efghijkl'),
            ('abcdefgh', 'bcdefghijkl'),
            ('abcdefgh', 'efghijkl'),
            ('bcdefghijkl_efghijkl', 'abcdefghijk_abcdefgh'),
            ('EFGHIJKL_ABCDEFGH', 'CDEFGHIJ_GHIJKLMN'),
        ]
        run_test(match_maker, var_names, match_maker.unordered_words_match, min_word_match_degree=2/3)
        run_test(match_maker, var_names, match_maker.unordered_words_match, min_word_match_degree=1)
        run_test(match_maker, var_names, match_maker.unordered_words_match, min_word_match_degree=1,
                 continuity_heavy_weight=True)
        run_test(match_maker, var_names, match_maker.unordered_words_match, min_word_match_degree=2 / 3,
                 continuity_heavy_weight=True)
        run_test(match_maker, var_names, match_maker.unordered_words_match, min_word_match_degree=1 / 2,
                 continuity_heavy_weight=True)

    if scriptIndex & TEST_UNORDERED_SEMANTIC_MATCH:
        var_names = files or [
            ('FirstLightAFire', 'LightTheFireFirst'),
            ('multiply_digits_exponent', 'multiply_digits_power'),
            ('TheChildArrivesToTheClassroom', 'TheChildArrivesToTheSchoolroom'),
            ('TheChildArrivesToTheClassroom', 'TheChildGetToTheSchoolroom'),
            ('TheChildArrivesToTheClassroom', 'TheKidGetToBallroom'),
            ('TheChildArrivesToTheClassroom', 'TheKidGetToTheSchoolroom'),
            ('MultiplyDigitExponent', 'DigitsPowerMultiplying')]
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=1)
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=2 / 3)
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=1,
                 prefer_num_of_letters=True)
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=2 / 3,
                 prefer_num_of_letters=True)
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=1,
                 continuity_heavy_weight=True)
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=2 / 3,
                 continuity_heavy_weight=True)
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=1,
                 prefer_num_of_letters=True, continuity_heavy_weight=True)
        run_test(match_maker, var_names, match_maker.unordered_semantic_match, min_word_match_degree=2 / 3,
                 prefer_num_of_letters=True, continuity_heavy_weight=True)

    if scriptIndex & TEST_UNEDIT_MATCH:
        var_names = files or [('A_CD_EF_B', 'A_EF_CD_B')]
        run_test(match_maker, var_names, match_maker.unedit_match, min_len=2)
