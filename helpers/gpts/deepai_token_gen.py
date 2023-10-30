import math
from ctypes import c_int32
from random import random


def int32(val):
    return c_int32(int(val)).value


t = [0] * 64
for p in range(64):
    t[p] = 0 | int32(4294967296 * math.sin((p + 1) % math.pi))


def rshift(val, n):
    return (val % 0x100000000) >> n % 32


def g(m):
    v = 1732584193
    r = 4023233417
    E = [v, r, ~int32(v), ~int32(r)]
    H = m + "\u0080"
    F = len(H)

    F -= 1
    m = int32(F / 4 + 2) | 15
    # print(m)

    I = [0] * m * 2
    m -= 1
    I[m] = 8 * F
    for i in range(F, -1, -1):
        # print(m, i, i >> 2, ord(H[i]), int32(ord(H[i]) << 8 * i % 32))
        I[i >> 2] |= int32(ord(H[i]) << 8 * i % 32)

    # print(I)
    for p in range(0, m, 16):
        F = E
        for H in range(64):
            v = int32(F[1]) | 0
            r = F[2]
            # print(H, F, p, H, p | [H, 5 * H + 1, 3 * H + 5, 7 * H][H >> 4] & 15)
            F = [q := F[3], v + int32(int32(q := F[0] + [
                int32(v) & int32(r) | ~int32(v) & int32(q),
                int32(q) & int32(v) | ~int32(q) & int32(r),
                int32(v) ^ int32(r) ^ int32(q),
                int32(r) ^ (int32(v) | ~int32(q))][F := H >> 4] + t[H] +
                                                 I[p | [H, 5 * H + 1, 3 * H + 5, 7 * H][F] & 15]) << int32(
                F := [7, 12, 17, 22, 5, 9, 14, 20, 4, 11, 16, 23, 6, 10, 15, 21][
                    4 * F + H % 4]) | int32(rshift(q, -F))), v, r]
        # print(H, F)
        # print('abc')
        for H in range(3, -1, -1):
            E[H] += F[H]

    # print(E)

    m = ""
    for H in range(32):
        # print(E[H >> 3] >> (4 * (1 ^ H)%32), E[H >> 3] >> 4 * (1 ^ H) & 15, hex(E[H >> 3] >> 4 * (1 ^ H) & 15)[2:], H)
        m += hex(E[H >> 3] >> (4 * (1 ^ H) % 32) & 15)[2:]
    return m[::-1]


def generate_tryit(user_agent):
    e = round(1E11 * random())
    return f"tryit-{e}-{g(user_agent + g(user_agent + g(user_agent + str(e) + 'x')))}"


if __name__ == "__main__":  # test
    print(generate_tryit(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 '
        'Safari/537.36'))
