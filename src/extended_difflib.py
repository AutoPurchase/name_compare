from src.difflib import SequenceMatcher


class ExtendedSequenceMatcher(SequenceMatcher):
    def update_matching_seq2(self, b, j, k):
        if self.b == '':
            self.set_seq2(b)
            return

        if b is self.b:
            return
        self.__update_chain_b(b, j, k)
        self.b = b
        self.matching_blocks = self.opcodes = None
        self.fullbcount = None

    def __update_chain_b(self, b, j, k):
        for jj in range(j, j+k):
            if self.b[jj] in self.b2j.keys():
                self.b2j[self.b[jj]].remove(jj)
                if len(self.b2j[self.b[jj]]) == 0:
                    del self.b2j[self.b[jj]]

        b2j_illegal_char = self.b2j.setdefault(b[j], [])
        b2j_illegal_char.extend(range(j, j+k))
        self.b2j[b[j]] = sorted(b2j_illegal_char)

