# 下書き_v2.mp4 を作る（大株主の動き v2＝はじめに・まとめの読み直し・mix_v1.py の写し／・相場環境の mix_v3.py の写し・2026-11-23）＝映像（下書き_v1_映像.mp4）に、声（声_間入り_v1.wav・Satomi）と後ろのピアノ（BGM_v1\A_ピアノ.wav）を混ぜて重ねる。元の見出し：下書き_v1.mp4 を作る（【PRO】の mix_v8.py の写し・2026-11-23 相場環境の説明動画）＝元の見出し：下書き_v8.mp4 を作る＝映像（下書き_v8_映像.mp4・まとめの最後に2つ足した）に、声（声_間入り_v7.wav・Kozy）と後ろのピアノ（BGM_v8\A_ピアノ.wav）を混ぜて重ねる（2026-11-14・mix_v7.py の写し）
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


def graph(gain):
    return (f"[1:a]aresample=48000,aformat=channel_layouts=stereo[voice];[voice]asplit[vo][sc];"
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
