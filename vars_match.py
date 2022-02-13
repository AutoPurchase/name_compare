import divide_to_words
# from modificated_difflib import SequenceMatcher
from difflib import SequenceMatcher


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

    def get_matching_blocks(self):
        len_a = len(self.sequence_a)
        len_b = len(self.sequence_b)

        while True:
            sm = SequenceMatcher(a=self.modified_seq_a, b=self.modified_seq_b)
            i, j, k = x = sm.find_longest_match(0, len_a, 0, len_b)

            if k == 0:
                break

            self.matching_blocks.append(x)
            self.modify_seqs(i, j, k)

        return self.matching_blocks


if __name__ == '__main__':
    # vnames = [['Print', 'Gui', 'Data'], ['Print', 'Data', 'Gui'], ['Gui', 'Print', 'Data'], ['Gui', 'Data', 'Print'],
    #           ['Data', 'Print', 'Gui'], ['Data', 'Gui', 'Print'], ['Printing', 'Gui', 'Data'], ['Print', 'Data'],
    #           ['Gui', 'Print']]
    vnames = ['PrintGuiData', 'PrintDataGui', 'GuiPrintData', 'GuiDataPrint', 'DataPrintGui', 'DataGuiPrint',
              'PrintingGuiData', 'PrintData', 'GuiPrint']

    # vnames = [['Print', 'Gui', 'Data'], ['Print', 'Data', 'Gui']]

    for b in range(len(vnames)):
        for a in range(b + 1):
            s = SubSequencesMatcher(vnames[a], vnames[b])
            # s = SubSequencesMatcher(vnames[a], vnames[b], lambda x: x == "_")

            print(f'{b + 1}.{a + 1}.\na="{vnames[a]}"\nb="{vnames[b]}"')
            for (i, j, k) in s.get_matching_blocks():
                print(f'\ta[{i}] and b[{j}] match for {k} elements: {vnames[a][i:i+k]}')
            print('\n', end='')
