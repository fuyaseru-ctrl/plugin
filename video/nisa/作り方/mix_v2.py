# 下書き_v2.mp4 を作る（新NISA枠の説明動画 v2＝一手の読みを直した・声 Hanano・会話引継ぎの mix_v1.py の写し・2026-11-28）
# 混ぜ方は 11/07 の下書き_v5（完成品）と同じ：
#   ピアノ -18.5dB・声が出ている間だけ下げる（sidechaincompress threshold 0.03・ratio 6・attack 15・release 350＝odio.py 合わせる と同じ）
#   → 全体を同じだけ上げて、上限 -3dB（0.7079）で山だけ抑える（alimiter level=false＝勝手に持ち上げない）→ AAC 192k
# ★全体の上げ幅は声によって違う（11/07 は Otani で +3.6dB）＝一度混ぜて測り、目標の大きさ（-15.3 LUFS＝11/07 の完成品と同じ）との差にする
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
FF = r"C:\Users\vioma\OneDrive\デスクトップ\Claudcode\王ディオ\_ffmpeg\ffmpeg.exe"
VIDEO, VOICE, BGM = '下書き_v2_映像.mp4', '声_間入り_v2.wav', os.path.join('BGM_v2', 'A_ピアノ.wav')
OUT = '下書き_v2.mp4'
TARGET = -15.3
BGM_DB = -18.5
os.chdir(HERE)
assert not os.path.exists(OUT), f'{OUT} はもうある＝消さずに止めた（別の名前で作り直す）'
for f in (VIDEO, VOICE, BGM):
    assert os.path.exists(f), f


# ★Hanano の声は ElevenLabs から届いたままで -31.4 LUFS（前の回の Otani は -18.4）＝そのまま混ぜるとピアノが相対的に13dB大きくなり、
#   全体を15.7dB上げると山を強く押しつぶす → 活用術（mix.py）と同じく、先に声だけを前の回の声の大きさ（REF_VOICE）まで上げ、
#   上がりすぎる所だけ軽く抑える（3:1・-18dB から）＝ピアノとの釣り合いを前の回と同じにする（2026-11-28）
REF_VOICE = -18.4


def lufs_of(path):
    r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return float(json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr)[-1])['input_i'])


V0 = lufs_of(VOICE)
VG = round(REF_VOICE - V0, 2)
print('声', V0, 'LUFS → 声だけ', VG, 'dB 上げる')
assert 0 <= VG < 16, VG
COMP = f"volume={VG}dB,acompressor=threshold=-18dB:ratio=3:attack=3:release=120:knee=6:makeup=1"
# 軽く抑えると声が小さくなる（11/28 測ると -24.1＝前の回より5.7dB小さく、ピアノが目立つ）→ 抑えた後に REF_VOICE までもう一度上げる
def lufs_af(path, af):
    r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', path, '-af', af + ',loudnorm=print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    return float(json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr)[-1])['input_i'])
V1 = lufs_af(VOICE, COMP)
VM = round(REF_VOICE - V1, 2)
print('抑えた後の声', V1, 'LUFS → もう一度', VM, 'dB 上げる')
assert 0 <= VM < 10, VM
VPRE = f"{COMP},volume={VM}dB,"


def graph(gain):
    return (f"[1:a]aresample=48000,{VPRE}aformat=channel_layouts=stereo[voice];[voice]asplit[vo][sc];"
            f"[2:a]aresample=48000,aformat=channel_layouts=stereo,volume={BGM_DB}dB[b0];"
            f"[b0][sc]sidechaincompress=threshold=0.03:ratio=6:attack=15:release=350[bd];"
            f"[vo][bd]amix=inputs=2:duration=first:normalize=0,volume={gain:.2f}dB,"
            f"alimiter=limit=0.7079:attack=5:release=50:level=false[a]")


def measure(path_or_args):
    r = subprocess.run([FF, '-hide_banner', '-nostats', *path_or_args, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    j = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr)[-1])
    return float(j['input_i']), float(j['input_tp'])


# 1回目＝上げ幅0で混ぜた音を測る（ファイルは作らない）
r = subprocess.run([FF, '-hide_banner', '-nostats', '-i', VIDEO, '-i', VOICE, '-i', BGM, '-filter_complex', graph(0) + ';[a]loudnorm=print_format=json[o]',
                    '-map', '[o]', '-f', 'null', '-'], capture_output=True, text=True, encoding='utf-8', errors='replace')
j = json.loads(re.findall(r'\{[^{}]*"input_i"[^{}]*\}', r.stderr)[-1])
i0 = float(j['input_i'])
gain = round(TARGET - i0, 2)
print('混ぜたまま', i0, 'LUFS → 上げ幅', gain, 'dB')
assert -6 < gain < 12, gain
tmp = OUT.replace('.mp4', '.tmp.mp4')
if os.path.exists(tmp):
    os.remove(tmp)
r = subprocess.run([FF, '-v', 'error', '-i', VIDEO, '-i', VOICE, '-i', BGM, '-filter_complex', graph(gain), '-map', '0:v', '-map', '[a]',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', tmp],
                   capture_output=True, text=True, encoding='utf-8', errors='replace')
assert r.returncode == 0, r.stderr
I, TP = measure(['-i', tmp])
print('仕上がり', I, 'LUFS  最大', TP, 'dBTP')
assert TP <= -1.5, ('山が上限を越えた', TP)
os.replace(tmp, OUT)
print('できた', OUT)
