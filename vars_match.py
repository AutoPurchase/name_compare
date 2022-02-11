import divide_to_words
# from modificated_difflib import SequenceMatcher
from difflib import SequenceMatcher


class SubSequencesMatcher:
    ILLEGAL_VALUE = ['#']

    def __init__(self, sequence_a, sequence_b):
        self.sequence_a = sequence_a
        self.modified_seq_a = sequence_a.copy()
        self.sequence_b = sequence_b
        self.sequences = [self.sequence_a, self.sequence_b]
        self.matching_blocks = []

    def modify_seq_a(self, i, k):
        self.modified_seq_a = self.modified_seq_a[:i] + \
        SubSequencesMatcher.ILLEGAL_VALUE * k + \
        self.modified_seq_a[i+k:]

    def get_matching_blocks(self):
        len_a = len(self.sequence_a)
        len_b = len(self.sequence_b)
        sm = SequenceMatcher(a=self.sequence_a, b=self.sequence_b)

        while True:
            sm.set_seq1(self.modified_seq_a)
            i, j, k = x = sm.find_longest_match(0, len_a, 0, len_b)

            if k == 0:
                break

            self.matching_blocks.append(x)
            self.modify_seq_a(i, k)

        return self.matching_blocks


if __name__ == '__main__':
    vnames = [['Print', 'Gui', 'Data'], ['Print', 'Data', 'Gui'], ['Gui', 'Print', 'Data'], ['Gui', 'Data', 'Print'],
              ['Data', 'Print', 'Gui'], ['Data', 'Gui', 'Print'], ['Printing', 'Gui', 'Data'], ['Print', 'Data'],
              ['Gui', 'Print']]
    # vnames = [['Print', 'Gui', 'Data'], ['Print', 'Data', 'Gui']]

    for b in range(len(vnames)):
        for a in range(b + 1):
            s = SubSequencesMatcher(vnames[a], vnames[b])
            # s = SubSequencesMatcher(vnames[a], vnames[b], lambda x: x == "_")

            print(f'({a + 1}/{b + 1}):\na="{vnames[a]}"\nb="{vnames[b]}"')
            for (i, j, k) in s.get_matching_blocks():
                print(f'\ta[{i}] and b[{j}] match for {k} elements: {vnames[a][i:i+k]}')
            print('\n', end='')
