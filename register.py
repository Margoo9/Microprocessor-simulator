class Register:
    def __init__(self, name):
        self.name = name
        self.high = '00000000'
        self.low = '00000000'

    def clearReg(self):
        self.high = '00000000'
        self.low = '00000000'

    def getReg(self, ind):
        if ind:
            return self.high
        else:
            return self.low

    def getFull(self):
        return self.high + self.low

    def mov(self, number, ind):
        if ind:
            self.high = number
        else:
            self.low = number

    def add(self, number, ind):
        if ind:
            value = int(self.high, 2)
            value += number
            if value > 255:
                value -= 256
            self.high = bin(value)[2:]
            while len(self.high) < 8:
                self.high = '0' + self.high
        else:
            value = int(self.low, 2)
            value += number
            if value > 255:
                 value -= 256
                 self.add(1, True)
            self.low = bin(value)[2:]
            while len(self.low) < 8:
                self.low = '0' + self.low

    def sub(self, number, ind):
        if ind:
            value = int(self.high, 2)
            value -= number
            if value < 0:
                value = 256 + value
            self.high = bin(value)[2:]
            while len(self.high) < 8:
                self.high = '0' + self.high
        else:
            value = int(self.low, 2)
            value -= number
            if value < 0:
                value = 256 + value
            self.low = bin(value)[2:]
            while len(self.low) < 8:
                self.low = '0' + self.low