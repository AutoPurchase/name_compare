from difflib import SequenceMatcher, Match


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

    def find_longest_matches(self, alo=0, ahi=None, blo=0, bhi=None):
        a, b, b2j, isbjunk = self.a, self.b, self.b2j, self.bjunk.__contains__
        if ahi is None:
            ahi = len(a)
        if bhi is None:
            bhi = len(b)

        bests = [(alo, blo, 0)]
        besti, bestj, bestsize = alo, blo, 0

        j2len = {}
        nothing = []
        for i in range(alo, ahi):
            j2lenget = j2len.get
            newj2len = {}
            for j in b2j.get(a[i], nothing):
                # a[i] matches b[j]
                if j < blo:
                    continue
                if j >= bhi:
                    break
                k = newj2len[j] = j2lenget(j-1, 0) + 1
                if k > bestsize:
                    bests = [(i-k+1, j-k+1, (bestsize := k))]
                elif k == bestsize:
                    bests.append((i-k+1, j-k+1, k))
            j2len = newj2len

        for idx in range(len(bests)):
            besti, bestj, bestsize = bests[idx]

            while besti > alo and bestj > blo and \
                  not isbjunk(b[bestj-1]) and \
                  a[besti-1] == b[bestj-1]:
                besti, bestj, bestsize = besti-1, bestj-1, bestsize+1
            while besti+bestsize < ahi and bestj+bestsize < bhi and \
                  not isbjunk(b[bestj+bestsize]) and \
                  a[besti+bestsize] == b[bestj+bestsize]:
                bestsize += 1

            while besti > alo and bestj > blo and \
                  isbjunk(b[bestj-1]) and \
                  a[besti-1] == b[bestj-1]:
                besti, bestj, bestsize = besti-1, bestj-1, bestsize+1
            while besti+bestsize < ahi and bestj+bestsize < bhi and \
                  isbjunk(b[bestj+bestsize]) and \
                  a[besti+bestsize] == b[bestj+bestsize]:
                bestsize = bestsize + 1

            bests[idx] = (besti, bestj, bestsize)

        return [Match(*best) for best in bests]

