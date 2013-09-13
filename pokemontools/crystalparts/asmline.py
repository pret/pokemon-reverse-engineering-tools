class AsmLine:
    # TODO: parse label lines
    def __init__(self, line, bank=None):
        self.line = line
        self.bank = bank

    def to_asm(self):
        return self.line
