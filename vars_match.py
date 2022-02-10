import divide_to_words
# from modificated_difflib import SequenceMatcher
from difflib import SequenceMatcher

def bs_find_predecessor_val(arr, x, l=0, r=None):
    if r is None:
        r = len(arr)-1

    while l <= r:
        mid = l + (r - l) // 2

        if arr[mid] == x:
            return arr[mid]
        elif arr[mid] < x:
            l = mid + 1
        else:
            r = mid - 1

    # arr[r] < x < arr[l]
    return arr[r]

class SubSequencesMatcher:
    A = 0
    B = 1
    AB = 2
    SS_SEPARATORS = [['-'], ['+']]

    def __init__(self, sequence_a, sequence_b, isjunk=None):
        self.isjunk = isjunk
        self.original_sequence = [sequence_a,  sequence_b]
        self.sub_seq = [{0: sequence_a}, {0: sequence_b}]

        self.matching_blocks = []

    def empty(self):
        return len(self.sub_seq[SubSequencesMatcher.A]) == 0 or len(self.sub_seq[SubSequencesMatcher.B]) == 0

    def calc_original_indices(self, concat_ss_index, *ss):
        ss_pred = [bs_find_predecessor_val(sorted(concat_ss_index[a_b].keys()), ss[a_b])
                   for a_b in range(SubSequencesMatcher.AB)]
        i, j = [concat_ss_index[a_b][ss_pred[a_b]] + ss[a_b] - ss_pred[a_b] for a_b in range(SubSequencesMatcher.AB)]

        return (concat_ss_index[SubSequencesMatcher.A][ss_pred[SubSequencesMatcher.A]],
                concat_ss_index[SubSequencesMatcher.B][ss_pred[SubSequencesMatcher.B]],
                i, j)

    def concat_ss(self):
        seq_of_ss = [[], []]
        concat_ss_index = [{}, {}]

        for a_b in range(SubSequencesMatcher.AB):
            index = 0
            for k, ss in sorted(self.sub_seq[a_b].items()):
                concat_ss_index[a_b][index] = k
                seq_of_ss[a_b] += ss + SubSequencesMatcher.SS_SEPARATORS[a_b]
                index += len(ss) + 1
                
        return seq_of_ss, concat_ss_index

    def update_ss(self, pred_i, pred_j, i, j, k):
        pred_i_j = [pred_i, pred_j]
        i_j = [i, j]

        for a_b in range(SubSequencesMatcher.AB):
            curr_sub_seq = self.sub_seq[a_b].pop(pred_i_j[a_b])
            sub_seq_start_match_index = i_j[a_b] - pred_i_j[a_b]
            sub_seq_end_match_index = sub_seq_start_match_index + k

            if pred_i_j[a_b] < i_j[a_b]:
                self.sub_seq[a_b][pred_i_j[a_b]] = curr_sub_seq[:sub_seq_start_match_index]
            if sub_seq_end_match_index < len(curr_sub_seq):
                self.sub_seq[a_b][i_j[a_b] + k] = curr_sub_seq[sub_seq_end_match_index:]

    def get_matching_blocks(self):
        while not self.empty():
            seq_of_ss, concat_ss_index = self.concat_ss()
            sm = SequenceMatcher(self.isjunk, seq_of_ss[SubSequencesMatcher.A], seq_of_ss[SubSequencesMatcher.B])
            ssi, ssj, k = sm.find_longest_match(0, len(seq_of_ss[SubSequencesMatcher.A]), 0, len(seq_of_ss[SubSequencesMatcher.B]))

            if k == 0:
                break

            pred_i, pred_j, i, j = self.calc_original_indices(concat_ss_index, ssi, ssj)
            self.matching_blocks.append((i, j, k))

            self.update_ss(pred_i, pred_j, i, j, k)

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