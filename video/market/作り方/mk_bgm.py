# 説明動画の後ろに小さく流す、ヒーリング風の音楽を一から組み立てる（人の曲を使わない＝権利の心配なし・お金もかからない）
# 2026-11-07 本人の決め
#   ElevenLabs の音楽は使わない＝音楽の規約（2026-10-09 更新）で Starter は「For Individual Use Only」（会社の動画に使えない）
# 使い方：py mk_bgm.py <長さ秒> → BGM\A_ピアノ.wav・B_和音だけ.wav・C_オルゴール.wav（48kHz・ステレオ）
# 中身：ゆっくり（1拍1秒）・打楽器なし・長調の和音4つのくり返し（Cmaj9 → Am9 → Fmaj9 → G6sus2）・残響つき
import os, sys
import numpy as np
SR = 48000
HERE = os.path.dirname(os.path.abspath(__file__))
LENGTH = float(sys.argv[1]) if len(sys.argv) > 1 else 137.1
# 2026-11-07 足した：2つ目＝置き場所（作業場の中のフォルダ名・既定 BGM）／3つ目＝作る曲（A・B・C の組み合わせ・既定 ABC）
#   例 py mk_bgm.py 144.61 BGM_v5 A ＝ピアノだけを BGM_v5\A_ピアノ.wav に（同じ種＝同じ曲で長さだけ違う）
OUT = os.path.join(HERE, sys.argv[2] if len(sys.argv) > 2 else 'BGM')
ONLY = sys.argv[3] if len(sys.argv) > 3 else 'ABC'
assert ONLY and set(ONLY) <= set('ABC'), ONLY
N = int(LENGTH * SR)
def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12)
# 和音（MIDIの番号）＝ゆったりした長調。低い所はひかえめ
CHORDS = [[48, 55, 59, 62, 64], [45, 52, 55, 59, 60], [41, 48, 52, 55, 57], [43, 50, 57, 59, 64]]
ROOTS = [36, 33, 29, 31]
PENTA = [72, 74, 76, 79, 81, 84]          # C5 D5 E5 G5 A5 C6（五音＝ぶつからない音）
def env_lin(n, a, r):
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = 0.5 - 0.5 * np.cos(np.linspace(0, np.pi, na))
    if nr: e[-nr:] *= 0.5 + 0.5 * np.cos(np.linspace(0, np.pi, nr))
    return e
def pad_note(m, dur, rng, bright=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    f0 = hz(m)
    for k in range(1, 7):
        if f0 * k > 2600:
            break
        amp = (1.0 / k ** 1.7) * (bright if k > 1 else 1.0)
        for cents in (-5.0, 5.0):
            f = f0 * k * 2 ** (cents / 1200)
            y += amp * np.sin(2 * np.pi * f * t + rng.uniform(0, 2 * np.pi))
    y *= 1 + 0.06 * np.sin(2 * np.pi * rng.uniform(0.07, 0.13) * t + rng.uniform(0, 6.28))
    return y
def pluck(m, rng, kind):
    """kind＝'piano'（やわらかいピアノ風）／'box'（オルゴール風）"""
    dur = 4.0 if kind == 'piano' else 2.6
    n = int(dur * SR)
    t = np.arange(n) / SR
    f0 = hz(m)
    if kind == 'piano':
        parts = [(1, 1.0, 2.2), (2, 0.42, 1.2), (3, 0.18, 0.8), (4, 0.08, 0.5)]
    else:
        parts = [(1, 1.0, 1.4), (3.0, 0.22, 0.45), (5.4, 0.08, 0.25)]
    y = np.zeros(n)
    for ratio, amp, tau in parts:
        y += amp * np.exp(-t / tau) * np.sin(2 * np.pi * f0 * ratio * t + rng.uniform(0, 6.28))
    att = int(0.006 * SR)
    y[:att] *= np.linspace(0, 1, att)
    return y
def add(buf, x, start, pan):
    s = int(start * SR)
    if s >= N:
        return
    x = x[:N - s]
    l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[0, s:s + len(x)] += x * l
    buf[1, s:s + len(x)] += x * r
def reverb(x, rt60, seed):
    rng = np.random.default_rng(seed)
    n = int(rt60 * 1.2 * SR)
    t = np.arange(n) / SR
    out = np.zeros_like(x)
    L = 1 << int(np.ceil(np.log2(x.shape[1] + n)))
    for ch in range(2):
        ir = rng.standard_normal(n) * np.exp(-6.9 * t / rt60)
        for _ in range(3):                    # 高い音を少し落として暗めに
            ir = np.convolve(ir, [0.25, 0.5, 0.25], mode='same')
        ir[:int(0.02 * SR)] = 0                # 少しだけ遅れて響く
        ir /= np.sqrt(np.sum(ir ** 2))
        out[ch] = np.fft.irfft(np.fft.rfft(x[ch], L) * np.fft.rfft(ir, L), L)[:x.shape[1]]
    return out
def make(name, plucks, chord_len, seed):
    rng = np.random.default_rng(seed)
    pad = np.zeros((2, N)); bell = np.zeros((2, N))
    xf = 3.0                                   # 和音の入れ替わりの重なり
    t0, ci = 0.0, 0
    while t0 < LENGTH:
        ch, root = CHORDS[ci % 4], ROOTS[ci % 4]
        dur = chord_len + xf
        e = env_lin(int(dur * SR), xf, xf)
        for j, m in enumerate(ch):
            add(pad, pad_note(m, dur, rng, bright=0.8) * e * 0.16, t0, (j - 2) * 0.22)
        add(pad, pad_note(root, dur, rng, bright=0.4) * e * 0.10, t0, 0.0)
        if plucks:
            beat = 1.0 if plucks == 'piano' else 0.5
            prob = 0.38 if plucks == 'piano' else 0.42
            k = 0
            last = rng.integers(0, len(PENTA))
            while k * beat < chord_len:
                if rng.random() < prob:
                    last = int(np.clip(last + rng.choice([-2, -1, -1, 1, 1, 2]), 0, len(PENTA) - 1))
                    m = PENTA[last] + (12 if plucks == 'box' else 0)
                    vel = rng.uniform(0.55, 1.0) * (0.10 if plucks == 'piano' else 0.06)
                    add(bell, pluck(m, rng, plucks) * vel, t0 + xf * 0.5 + k * beat, rng.uniform(-0.5, 0.5))
                k += 1
        t0 += chord_len
        ci += 1
    mix = pad * 0.75 + reverb(pad, 3.2, seed + 1) * 0.45 + bell * 0.55 + reverb(bell, 3.6, seed + 2) * 0.6
    # 入り2秒・最後の4秒で消える
    fi, fo = int(2.0 * SR), int(4.0 * SR)
    mix[:, :fi] *= np.linspace(0, 1, fi)
    mix[:, -fo:] *= np.linspace(1, 0, fo) ** 1.5
    mix /= np.max(np.abs(mix)) / 0.5           # 山を -6dB に
    pcm = (np.clip(mix, -1, 1).T * 32767).astype('<i2').tobytes()
    import wave
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    assert not os.path.exists(p), f'もうあるので書かない: {p}'
    tmp = p + '.tmp'
    with wave.open(tmp, 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm)
    os.replace(tmp, p)
    print('できた', name, round(LENGTH, 1), '秒')
if 'A' in ONLY:
    make('A_ピアノ.wav', 'piano', 8.0, 11)
if 'B' in ONLY:
    make('B_和音だけ.wav', None, 12.0, 21)
if 'C' in ONLY:
    make('C_オルゴール.wav', 'box', 8.0, 31)
