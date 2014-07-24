# I can't remember where I found this, please reach out to me if you are the author or if you know where this comes from.

class MersenneTwister19937:
    def __init__(self, seed):
        self.N = 624
        self.M = 397
        self.MATRIX_A = 0x9908b0df   # constant vector a
        self.UPPER_MASK = 0x80000000 # most significant w-r bits
        self.LOWER_MASK = 0x7fffffff # least significant r bits
        self.mt = [None] * self.N    # the array for the state vector
        self.init_genrand(seed)

    def unsigned32(self, n1):
        if n1 < 0: return (n1 ^ self.UPPER_MASK) + self.UPPER_MASK
        return n1

    def addition32(self, n1, n2):
        return self.unsigned32((n1 + n2) & 0xffffffff)

    def multiplication32(self, n1, n2):
        sum = 0;
        for i in range(32):
            if (n1 >> i) & 1:
                sum = self.addition32(sum, self.unsigned32(n2 << i))
        return sum

    def init_genrand(self, s):  # initializes mt[N] with a seed
        self.mt[0] = self.unsigned32(s & 0xffffffff)
        self.mti = 1
        while self.mti < self.N:
            self.mt[self.mti] = self.addition32(self.multiplication32(1812433253, self.unsigned32(self.mt[self.mti-1] ^ (self.mt[self.mti-1] >> 30))), self.mti)
            self.mt[self.mti] = self.unsigned32(self.mt[self.mti] & 0xffffffff)
            self.mti += 1

    def genrand_int32(self):    # generates a random number on [0,0xffffffff]-interval
        mag01 = [0, self.MATRIX_A]

        if (self.mti >= self.N): # generate N words at one time
            kk = 0
            while kk < self.N-self.M:
                y = self.unsigned32((self.mt[kk]&self.UPPER_MASK) | (self.mt[kk+1]&self.LOWER_MASK))
                self.mt[kk] = self.unsigned32(self.mt[kk+self.M] ^ (y >> 1) ^ mag01[y & 1])
                kk += 1

            while kk < self.N-1:
                y = self.unsigned32((self.mt[kk]&self.UPPER_MASK) | (self.mt[kk+1]&self.LOWER_MASK))
                self.mt[kk] = self.unsigned32(self.mt[kk+(self.M-self.N)] ^ (y >> 1) ^ mag01[y & 1])
                kk += 1

            y = self.unsigned32((self.mt[self.N-1]&self.UPPER_MASK) | (self.mt[0]&self.LOWER_MASK))
            self.mt[self.N-1] = self.unsigned32(self.mt[self.M-1] ^ (y >> 1) ^ mag01[y & 1])
            self.mti = 0

        y = self.mt[self.mti]
        self.mti += 1

        # Tempering
        y = self.unsigned32(y ^ (y >> 11))
        y = self.unsigned32(y ^ ((y << 7) & 0x9d2c5680))
        y = self.unsigned32(y ^ ((y << 15) & 0xefc60000))
        y = self.unsigned32(y ^ (y >> 18))

        return y;
    
    def genrand_real1(self):
        return (self.genrand_int32() * (1.0/4294967295.0))