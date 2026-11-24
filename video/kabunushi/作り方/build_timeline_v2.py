# 時間割（timeline_v2.json）と、間を入れた声（声_間入り_v2.wav）を作る＝大株主の動き v2（2026-11-23・build_timeline_v1.py の写し＝はじめに・まとめを「フ ヤセル エーアイ」で読み直した声に）
# 声の元＝章ごとに選ぶ：はじめに＝声_Satomi_案3はじめに（「どのめいがら」）／3つまで探す・判断と合図＝声_Satomi_案2（かいましした・まえむきに）／ほか＝声_Satomi_案1
# 字幕の文＝原稿_案3.txt（章の分け目は【】の見出し）
# 切る所＝章の頭の言葉の出だしの少し前〜章の終わりの言葉の後（無音を測って決める）→ 章の間はどこも同じ長さの間（STOP）
# 同じ声の切り出しが重なれば止まる（相場環境 v1 の「答えの、答えの最後」の二度聞こえを防ぐ点検）
import json, os, re, subprocess, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
FF = r"C:\Users\vioma\OneDrive\デスクトップ\Claudcode\王ディオ\_ffmpeg\ffmpeg.exe"
SR = 48000
SCRIPT = '原稿_案4.txt'
OUT_TL = 'timeline_v2.json'
OUT_WAV = '声_間入り_v2.wav'
STOP = 0.9     # 章の変わり目で声が止まる長さ（v2：はじめに・まとめの読み直しで 120.8秒＝2分を超えたので 1.0→0.9）
LEAD = 0.7     # 最初の声の前（v2：0.9→0.7）
TAIL = 4.0     # 最後の声の後（終わりの画面と音楽が消える分・v2：4.5→4.0）
PRE, POST = 0.12, 0.2   # 言葉の前後に残す余白
SRC = {'A': '声_Satomi_案1', 'B': '声_Satomi_案4はじめに', 'C': '声_Satomi_案23つまで探す', 'D': '声_Satomi_案2判断と合図', 'E': '声_Satomi_案4まとめ'}
# 読み直した章＝Satomi が「買い増した」を「買いました」と読んだ・「前向き」「どの銘柄」の聞き取りが怪しかった章
OWN = {'はじめに': 'B', '3つまで探す': 'C', '判断と合図': 'D', 'まとめ': 'E'}   # v2：はじめに・まとめ＝フヤセルAI を「フ ヤセル エーアイ」（本人の決め）   # 章だけ読み直した声（字幕の番号は0から）

chs, want = [], []
for raw in open(os.path.join(HERE, SCRIPT), encoding='utf-8').read().splitlines():
    s = raw.strip()
    m = re.match(r'#\s*【(.+?)】', s)
    if m:
        chs.append([m.group(1), len(want)]); continue
    if s and not s.startswith('#'):
        want.append(s.split('｜')[0].strip().rstrip('。、'))
NAMES = ['はじめに', '使い方', '3つまで探す', '答えの中身', '判断と合図', '銘柄も聞ける', 'まとめ']
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
    'plus': ('プラスから', 6), 'pick': ('選んで', 6), 'nani': ('何も打たずに', 7), 'arrow': ('矢印', 7), 'push': ('押すだけ', 7),
    # 3つまで探す
    'go5': ('ごパーセント', 8), 'hokoku': ('たいりょうほゆう', 9), 'saikin': ('最近出た', 10), 'teian': ('提案', 11), 'monoiu': ('ものいう', 11),
    'atarashiku': ('新しく', 12), 'kaimashi': ('かいましした', 12), 'mittsu': ('みっつ', 13),
    # 答えの中身
    'hachi': ('はちぎょう', 14), 'dare': ('誰か', 15), 'nanpa': ('なんパーセント', 15), 'suitei': ('すいてい', 16), 'sa': ('差', 17),
    'kaikata': ('買い方', 18), 'tejimai': ('てじまい', 18), 'kiwo': ('気をつける', 19),
    # 判断と合図
    'dankai': ('段階', 20), 'monosashi': ('ものさし', 21), 'chikai': ('近いほど', 22), 'maemuki': ('まえむき', 22), 'hanare': ('離れすぎ', 23),
    'miokuri': ('見送り', 23), 'utta': ('売った', 24), 'zouhai': ('増配', 24), 'deteiku': ('出ていく', 25), 'hakkiri': ('はっきり', 26),
    # 銘柄も聞ける
    'code': ('銘柄名か', 28), 'okuru': ('送るだけ', 28), 'gazo': ('画像', 29), 'hatte': ('はって', 29), 'yomitoku': ('読み解いて', 30),
    'saigo': ('最後', 31), 'bango': ('番号を', 31), 'tsuzuki': ('続きも', 32),
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
