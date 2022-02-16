import editdistance as ed
from divide_to_words import Variable

class SubSequencesMatcher:
    ILLEGAL_VALUE_A = '#'
    ILLEGAL_VALUE_B = '!'

    def __init__(self, sequence_a, sequence_b):
        self.sequence_a = sequence_a
        self.sequence_b = sequence_b
        self.modified_seq_a = sequence_a[:]
        self.modified_seq_b = sequence_b[:]
        self.sequences = [self.sequence_a, self.sequence_b]
        self.matching_blocks = []

        self.illegal_value_a, self.illegal_value_b = \
            (SubSequencesMatcher.ILLEGAL_VALUE_A, SubSequencesMatcher.ILLEGAL_VALUE_B) if isinstance(sequence_a, str) \
            else ([SubSequencesMatcher.ILLEGAL_VALUE_A], [SubSequencesMatcher.ILLEGAL_VALUE_B])

    def modify_seqs(self, i, j, k):
        self.modified_seq_a = self.modified_seq_a[:i] + self.illegal_value_a * k + self.modified_seq_a[i+k:]
        self.modified_seq_b = self.modified_seq_b[:j] + self.illegal_value_b * k + self.modified_seq_b[j+k:]

    @staticmethod
    def is_words_similar(word_a, word_b):
        distance = ed.eval(word_a, word_b)
        return distance < min(len(word_a), len(word_b)) / 3, distance   # TODO: TBD the exact value

    def find_longest_match(self):
        longest_len = 0
        # longest_score = 0     # TODO: maybe it is better to work with a score for each pair of words, and score for a sequence accordingly (like num of equal letters)
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

        return longest_idx_a, longest_idx_b, longest_len

    def get_matching_blocks(self):
        while True:
            i, j, k = x = self.find_longest_match()

            if k == 0:
                break

            self.matching_blocks.append(x)
            self.modify_seqs(i, j, k)

        return self.matching_blocks


if __name__ == '__main__':
    vnames = ['Print_Gui_Data','Print_Data_Gui','Gui_Print_Data','Gui_Data_Print',
              'Data_Print_Gui','Data_Gui_Print','Printing_Gui_Data','Print_Data',
              'Gui_Print']
    vnames = ['TheSchoolBusIsYellow', 'TookBusToSchool', 'TookBusToSchoool']

    for b in range(len(vnames)):
        for a in range(b):
            a_words = Variable(vnames[a]).get_words()
            b_words = Variable(vnames[b]).get_words()

            s = SubSequencesMatcher(a_words, b_words)

            print(f'{b + 1}.{a + 1}.\na="{vnames[a]}"\nb="{vnames[b]}"')

            for (i, j, k) in s.get_matching_blocks():
                print(f'\ta[{i}] and b[{j}] match for {k} elements: \n\t\t{a_words[i:i+k]} \n\t\t{b_words[j:j+k]}')
            print('\n', end='')
