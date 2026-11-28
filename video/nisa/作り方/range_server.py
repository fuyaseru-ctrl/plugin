# 動画の途中へ飛べる配り口（Range 対応）＝見比べの画面を Playwright の窓に出す時に使う（2026-11-12・11/05 の scratchpad の物は会話と一緒に消えたので作業場に置いた）
# 使い方：py range_server.py <ポート> <配るフォルダ>   例）py range_server.py 8766 .
# 127.0.0.1 だけで待つ（外からは見えない）。読むだけ（書き込みの口は無い）
import os, re, sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class H(SimpleHTTPRequestHandler):
    def send_head(self):
        rng = self.headers.get('Range')
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r'bytes=(\d*)-(\d*)', rng)
        size = os.path.getsize(path)
        a = int(m.group(1)) if m and m.group(1) else 0
        b = int(m.group(2)) if m and m.group(2) else size - 1
        b = min(b, size - 1)
        if a > b:
            self.send_error(416)
            return None
        f = open(path, 'rb')
        f.seek(a)
        self.send_response(206)
        self.send_header('Content-Type', self.guess_type(path))
        self.send_header('Accept-Ranges', 'bytes')
        self.send_header('Content-Range', f'bytes {a}-{b}/{size}')
        self.send_header('Content-Length', str(b - a + 1))
        self.end_headers()
        self._left = b - a + 1
        return f

    def copyfile(self, src, dst):
        left = getattr(self, '_left', None)
        if left is None:
            return super().copyfile(src, dst)
        while left > 0:
            buf = src.read(min(65536, left))
            if not buf:
                break
            try:
                dst.write(buf)
            except (ConnectionResetError, BrokenPipeError, ConnectionAbortedError):
                break
            left -= len(buf)

    def log_message(self, *a):
        pass


if __name__ == '__main__':
    port, root = int(sys.argv[1]), os.path.abspath(sys.argv[2] if len(sys.argv) > 2 else '.')
    ThreadingHTTPServer(('127.0.0.1', port), partial(H, directory=root)).serve_forever()
