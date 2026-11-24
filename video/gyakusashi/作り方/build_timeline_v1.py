# 時間割（timeline_v1.json）と、間を入れた声（声_間入り_v1.wav）を作る＝逆指値かんたん設定 v1（2026-11-24・大株主の build_timeline_v2.py の写し）
# 声の元＝声_Hatake_案1（通し読み・本人の決め＝フヤセルAI は今の読みのまま）。字幕の文＝原稿_案1.txt（章の分け目は【】の見出し）
# 切る所＝章の頭の言葉の出だしの少し前〜章の終わりの言葉の後（無音を測って決める）→ 章の間はどこも同じ長さの間（STOP）
# 同じ声の切り出しが重なれば止まる（相場環境 v1 の「答えの、答えの最後」の二度聞こえを防ぐ点検）
import json, os, re, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
FF = r"C:\Users\vioma\OneDrive\デスクトップ\Claudcode\王ディオ\_ffmpeg\ffmpeg.exe"
SR = 48000
SCRIPT = '原稿_案1.txt'
OUT_TL = 'timeline_v1.json'
OUT_WAV = '声_間入り_v1.wav'
STOP = 1.0     # 章の変わり目で声が止まる長さ（相場環境と同じ）
LEAD = 0.9     # 最初の声の前（相場環境と同じ）
TAIL = 4.5     # 最後の声の後（終わりの画面と音楽が消える分・相場環境と同じ）
PRE, POST = 0.12, 0.2   # 言葉の前後に残す余白
SRC = {'A': '声_Hatake_案1'}
OWN = {}   # 章だけ読み直した声は無い（通し読み1本）

chs, want = [], []
for raw in open(os.path.join(HERE, SCRIPT), encoding='utf-8').read().splitlines():
    s = raw.strip()
    m = re.match(r'#\s*【(.+?)】', s)
    if m:
        chs.append([m.group(1), len(want)]); continue
    if s and not s.startswith('#'):
        want.append(s.split('｜')[0].strip().rstrip('。、'))
NAMES = ['はじめに', '使い方', '押す順を答える', 'いくらに置くか', 'つまずきも先回り', '銘柄も聞ける', 'まとめ']
assert [c[0] for c in chs] == NAMES, [c[0] for c in chs]

# 声の元を読む
V = {}
for k, d in SRC.items():
    J = json.load(open(os.path.join(HERE, d, '時刻.json'), encoding='utf-8'))
    raw = subprocess.run([FF, '-v', 'error', '-i', os.path.join(HERE, d, '声.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'], capture_output=True).stdout
    x = np.frombuffer(raw, np.float32)
    hop = int(SR * 0.01)
    db = np.array([10 * np.log10(np.mean(x[i:i + 2 * hop] ** 2) + 1e-12) for i in range(0, len(x) - 2 * hop, hop)])
    ref = np.percentile(db[db > -70], 90)
    V[k] = dict(dir=d, S=J['captions'], AL=J['alignment'], dur=len(x) / SR, loud=db >= ref - 35)

# 章ごとの声の元と、その中の字幕の番号
CH = []
for j, (nm, f) in enumerate(chs):
    l = (chs[j + 1][1] if j + 1 < len(chs) else len(want)) - 1
    if nm in OWN:
        k, sf = OWN[nm], 0
        assert len(V[k]['S']) == l - f + 1, ('読み直しの字幕の数が章と違う', nm, len(V[k]['S']), l - f + 1)
    else:
        k, sf = 'A', f
    CH.append((nm, f, l, k, sf))
# 字幕の文が原稿と同じか（声の元の字幕を、原稿の順に並べて照らす）
got = []
for nm, f, l, k, sf in CH:
    got += [V[k]['S'][sf + i]['text'].rstrip('。、') for i in range(l - f + 1)]
assert got == want, [(i, g, w) for i, (g, w) in enumerate(zip(got, want)) if g != w][:3]


def onset(k, t0, t1):
    L = V[k]['loud']; a, b = max(0, int(t0 / .01)), min(len(L) - 1, int(t1 / .01))
    idx = [i for i in range(a, b + 1) if L[i]]
    assert idx, ('言葉の出だしが見つからない', k, t0, t1)
    return idx[0] * .01


def run_at(k, tt):
    """字幕の出だし tt のそばの、0.2秒以上続く無音のかたまり（始め・終わりの秒）＝【PRO】の build_timeline_v7.py と同じ考え方"""
    Q = ~V[k]['loud']; c = int(tt / .01)
    runs = []
    for j in range(max(0, c - 80), min(len(Q), c + 30)):
        if not Q[j]: continue
        lo = hi = j
        while lo > 0 and Q[lo - 1]: lo -= 1
        while hi < len(Q) - 1 and Q[hi + 1]: hi += 1
        if (lo, hi) not in runs and (hi + 1 - lo) * .01 >= .2: runs.append((lo, hi))
    assert runs, ('文の間の無音が見つからない', k, tt)
    lo, hi = min(runs, key=lambda r: 0 if r[0] <= c <= r[1] else min(abs(r[0] - c), abs(r[1] - c)))
    return lo * .01, (hi + 1) * .01


def offset(k, t0, t1):
    L = V[k]['loud']; a, b = max(0, int(t0 / .01)), min(len(L) - 1, int(t1 / .01))
    idx = [i for i in range(a, b + 1) if L[i]]
    assert idx, ('言葉の終わりが見つからない', k, t0, t1)
    return (idx[-1] + 2) * .01


segs, chapters, caps, t = [], [], [], 0.0
for n, (nm, f, l, k, sf) in enumerate(CH):
    S = V[k]['S']
    sl = sf + (l - f)
    # 出だし：同じ声の前に文がある＝その間の無音の終わり／無い＝声の出始め
    if sf > 0:
        lo, hi = run_at(k, S[sf]['start']); a = max(hi - PRE, (lo + hi) / 2)
    else:
        a = max(0, onset(k, max(0, S[sf]['start'] - .35), S[sf]['end']) - PRE)
    # 終わり：同じ声の後に文がある＝その間の無音の始め／無い＝声の終わり
    if sl + 1 < len(S):
        lo, hi = run_at(k, S[sl + 1]['start']); b = min(lo + POST, (lo + hi) / 2)
    else:
        b = min(V[k]['dur'], offset(k, S[sl]['start'], V[k]['dur']) + POST)
    gap = LEAD if n == 0 else round(STOP - PRE - POST, 3)
    gap_start = t
    t += gap
    o = t - a
    first = len(caps)
    for i in range(l - f + 1):
        c = S[sf + i]
        caps.append(dict(i=len(caps), text=want[f + i], start=round(max(c['start'], a) + o, 3), end=round(min(c['end'], b) + o, 3)))
    chapters.append(dict(name=nm, first=first, last=len(caps) - 1, src=V[k]['dir'], gap=gap, gap_start=round(gap_start, 3), start=round(t, 3), cut=[round(a, 3), round(b, 3)]))
    segs.append((k, gap, a, b, o, sf, f))
    t += b - a
total = t + TAIL
for p, q in zip(segs, segs[1:]):
    if p[0] == q[0]:
        assert p[3] <= q[2] + 1e-6, ('同じ声の切り出しが重なる', p[0], round(p[3], 3), round(q[2], 3))
for j in range(len(chapters)):
    chapters[j]['end'] = round(chapters[j + 1]['gap_start'], 3) if j + 1 < len(chapters) else round(total, 3)
assert [c['i'] for c in caps] == list(range(len(want)))


def word_at(word, gi):
    """字幕 gi（原稿の番号）の中で word を話し始める時刻（時間割の秒）"""
    n = next(j for j, ch in enumerate(chapters) if ch['first'] <= gi <= ch['last'])
    k, _g, _a, _b, o, sf, f = segs[n]
    S, AL = V[k]['S'], V[k]['AL']
    txt, st = ''.join(AL['characters']), AL['character_start_times_seconds']
    sk = sf + (gi - f)
    s0 = S[sk]['start'] - .05
    i = txt.find(word)
    while i >= 0 and st[i] < s0:
        i = txt.find(word, i + 1)
    assert i >= 0 and st[i] < S[sk]['end'], (word, gi, S[sk]['text'])
    return round(st[i] + o, 3)


MARKS = {
    # 使い方
    'plus': ('プラスから', 7), 'pick': ('選んで', 7), 'nani': ('何も打たずに', 8), 'arrow': ('矢印', 8), 'push': ('押すだけ', 8), 'ichiran': ('一覧', 9),
    # 押す順を答える
    'okutte': ('送って', 10), 'erabu': ('選ぶと', 11), 'osujun': ('おす順', 12), 'hitotsu': ('ひとつずつ', 13), 'jissha': ('じっしゃ', 14),
    # いくらに置くか
    'katta': ('買った値', 17), 'minus': ('マイナス', 17), 'go': ('ごにち線', 18), 'niju': ('にじゅうごにち線', 18), 'choku': ('ちょっきん', 18),
    'oku': ('置く値', 19), 'shikin': ('しきん', 20), 'kabusu': ('株数', 20),
    # つまずきも先回り
    'genin': ('原因', 24), 'naoshi': ('直し方', 24),
    # 銘柄も聞ける
    'motikabu': ('持ち株', 25), 'code': ('銘柄名か', 26), 'okuru': ('送るだけ', 26), 'saishin': ('最新の', 27), 'meyasu': ('目安', 28),
    'saigo': ('最後', 29), 'bango': ('番号を', 29), 'tsuzuki': ('続きも', 30),
}
marks = {k: word_at(w, gi) for k, (w, gi) in MARKS.items()}

tl = dict(total=round(total, 3), fps=30, script=SCRIPT, chapters=chapters, captions=caps, marks=marks)
txt = json.dumps(tl, ensure_ascii=False, indent=1)
tmp = os.path.join(HERE, OUT_TL + '.tmp')
with open(tmp, 'w', encoding='utf-8', newline='\n') as fh:
    fh.write(txt)
os.replace(tmp, os.path.join(HERE, OUT_TL))
if '--時刻だけ' in sys.argv:
    print('時間割だけ作り直した', round(total, 2), '秒'); sys.exit(0)

# 声：間（無音）＋切り出し、を順につなぐ（48kHz・モノラル）
ins, parts, labels = [], [], []
for k in SRC:
    ins += ['-i', os.path.join(HERE, SRC[k], '声.mp3')]
idx = {k: i for i, k in enumerate(SRC)}
for n, (k, gap, a, b, _o, _sf, _f) in enumerate(segs):
    parts.append(f"aevalsrc=0:d={gap:.3f}:s=48000,aformat=sample_fmts=fltp:channel_layouts=mono[g{n}]")
    parts.append(f"[{idx[k]}:a]atrim=start={a:.3f}:end={b:.3f},asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=mono[s{n}]")
    labels += [f"[g{n}]", f"[s{n}]"]
parts.append(f"aevalsrc=0:d={TAIL:.3f}:s=48000,aformat=sample_fmts=fltp:channel_layouts=mono[tail]")
labels.append('[tail]')
fc = ';'.join(parts) + ';' + ''.join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]"
out = os.path.join(HERE, OUT_WAV)
assert not os.path.exists(out), f'{OUT_WAV} はもうある＝消さずに止めた（別の名前で作り直す）'
tmpw = os.path.join(HERE, OUT_WAV.replace('.wav', '.tmp.wav'))
if os.path.exists(tmpw):
    os.remove(tmpw)
r = subprocess.run([FF, '-v', 'error'] + ins + ['-filter_complex', fc, '-map', '[out]', tmpw], capture_output=True, text=True, encoding='utf-8', errors='replace')
assert r.returncode == 0, r.stderr
os.replace(tmpw, out)
print('時間割', round(total, 2), '秒')
for c in chapters:
    print(' ', c['name'], c['src'], '字幕', c['first'], '〜', c['last'], '扉', c['gap_start'], '話', c['start'], '〜', c['end'], '切る', c['cut'])
print('言葉の時刻', marks)
