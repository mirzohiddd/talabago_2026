"""
Kompozitor sahifasini (compose.html) kadrma-kadr chizib, FFmpeg bilan 1080×1920 / 30 fps MP4 ga yig‘adi.
Ishlatish: python3 render.py <compose papkasi> <music.wav> <chiqish.mp4> [fps]
"""
import asyncio, subprocess, sys, time
from playwright.async_api import async_playwright

SRC, MUSIC, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
FPS = int(sys.argv[4]) if len(sys.argv) > 4 else 30
DUR = 75.0


async def main():
    n = int(DUR * FPS)
    ff = subprocess.Popen([
        'ffmpeg', '-v', 'error', '-y', '-f', 'image2pipe', '-framerate', str(FPS), '-c:v', 'mjpeg', '-i', '-',
        '-i', MUSIC, '-filter_complex', '[1:a]loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=out:st=73.2:d=1.8[a]',
        '-map', '0:v', '-map', '[a]', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-profile:v', 'high', '-pix_fmt', 'yuv420p',
        '-r', str(FPS), '-g', str(FPS * 2), '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-shortest', '-movflags', '+faststart', OUT,
    ], stdin=subprocess.PIPE)
    async with async_playwright() as p:
        br = await p.chromium.launch(executable_path='/usr/bin/google-chrome', args=['--allow-file-access-from-files', '--hide-scrollbars'])
        pg = await br.new_page(viewport={'width': 1080, 'height': 1920})
        await pg.goto(f'file://{SRC}/compose.html')
        await pg.wait_for_timeout(1000)
        t0 = time.time()
        for i in range(n):
            await pg.evaluate(f'render({i / FPS})')
            ff.stdin.write(await pg.screenshot(type='jpeg', quality=95))
            if i % 300 == 0:
                print(f'{i}/{n} kadr · {time.time() - t0:.0f} s', flush=True)
        await br.close()
    ff.stdin.close()
    ff.wait()
    print('tayyor:', OUT, f'{time.time() - t0:.0f} s')


asyncio.run(main())
