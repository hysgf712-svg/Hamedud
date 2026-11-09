# Native Marimo notebook; complete user program is embedded below.
import marimo

app = marimo.App()

@app.cell
def _():
    _embedded_source = r'''
        import sys, subprocess, os

        RUNTIME_ROOT = '/content' if os.path.isdir('/content') else os.getcwd()

        def _run_setup_command(command, label):
            try:
                result = subprocess.run(command, check=False)
                if result.returncode != 0:
                    print(f"⚠️ دستور نصب {label} با کد {result.returncode} تمام شد؛ ادامه می‌دهم.")
            except Exception as exc:
                print(f"⚠️ اجرای دستور نصب {label} ممکن نشد: {exc}")

        #================== نصب پیش‌نیازها ==================
        # ⚠️ بعد از هر ری‌استارت رانتایم کل فایل رو دوباره اجرا کن؛ نصب‌ها ایدمپوتن
        # ⚠️ numpy عمداً اینجا نصب/آپدیت نمی‌شود — OpenCV فقط در کد و در صورت نیاز نصب می‌شود
        _run_setup_command(["apt-get", "update", "-y"], "apt-get update")
        _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"], "pip/setuptools/wheel")
        _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "yt-dlp[default,curl-cffi]"], "yt-dlp")  # stable release; avoid nightly/pre-release regressions
        _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "cryptg", "requests-toolbelt", "telethon", "nest_asyncio", "ffmpeg-python", "requests", "beautifulsoup4", "playwright"], "Python dependencies")
        _run_setup_command([sys.executable, "-m", "pip", "install", "-U", "Pillow>=10.0", "arabic-reshaper", "python-bidi"], "Pillow/Persian text dependencies")
        _run_setup_command([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"], "Playwright Chromium")

        #================== تنظیمات پایه و ایمپورت‌ها ==================
        import nest_asyncio, asyncio, os, tempfile, subprocess, math, shutil, time, random, sys
        import requests
        import base64
        import json
        from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor
        from telethon import TelegramClient, events
        from telethon.tl.types import DocumentAttributeVideo
        from yt_dlp import YoutubeDL
        import subprocess
        # playwright chromium توی سلول اول نصب میشه؛ اینجا فقط یه چک بی‌صداست
        # (با check=True نباشه تا یه خطای گذرای شبکه کل سلول رو کرش نکنه)
        try:
            subprocess.run([sys.executable, "-m", "playwright", "install", "--with-deps", "chromium"],
                           capture_output=True, timeout=900, check=False)
        except Exception as e:
            print("⚠️ chromium playwright (بی‌خطر):", e)

        # OpenCV — فقط اگه واقعاً در دسترس نباشه نصب میشه.
        # (نصب قاطی‌شدهٔ numpy/opencv روی Colab دلیل اصلی کرش‌ها بود؛
        #  اگه cv2 هست، دست به numpy نمی‌زنیم که خراب نشه)
        try:
            import cv2 as _cv2_check
            print("✅ OpenCV موجود:", _cv2_check.__version__)
        except Exception:
            print("📥 OpenCV در دسترس نیست — نصب می‌شود...")
            _cv2_res = subprocess.run(
                [sys.executable, "-m", "pip", "install", "opencv-python-headless"],
                capture_output=True, text=True, timeout=900
            )
            if _cv2_res.returncode == 0:
                print("✅ OpenCV نصب شد")
            else:
                print("⚠️ نصب OpenCV خطا داد (تشخیص چهره غیرفعال می‌شود، بقیه ربات کار می‌کنه):")
                print(((_cv2_res.stderr or "") + (_cv2_res.stdout or ""))[-300:])

        def _pil_smoke_test():
            """تست واردسازی واقعیِ ماژول‌هایی که ربات استفاده می‌کند — نسخهٔ قاطی همین‌جا لو می‌رود"""
            import importlib
            for m in list(sys.modules):
                if m.lower() in ("pil", "pillow") or m.lower().startswith(("pil.", "pillow.")):
                    del sys.modules[m]
            import PIL
            for mod in ("Image", "ImageDraw", "ImageFont", "ImageOps", "ImageChops"):
                importlib.import_module(f"PIL.{mod}")
            return PIL.__version__

        def _pil_repair():
            """ترمیم کامل Pillow: uninstall → حذف دستی هرچه مونده → نصب تازه → تأیید.
            بازگشت: True اگر بعد از ترمیم Pillow سالم واردسازی شود."""
            import shutil, glob, site
            print("📥 ترمیم کامل Pillow (حذف فایل‌های قاطی‌شده)...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", "Pillow"],
                               capture_output=True, timeout=300)
            except Exception:
                pass
            # حذف دستی — حتی فایل‌هایی که uninstall حذفشان نکرده (RECORD خراب)
            site_dirs = set()
            try: site_dirs.update(site.getsitepackages() or [])
            except Exception: pass
            try: site_dirs.add(site.getusersitepackages())
            except Exception: pass
            try:
                import PIL as _p
                site_dirs.add(os.path.dirname(os.path.dirname(_p.__file__)))
            except Exception:
                pass
            site_dirs.discard(None)
            for d in site_dirs:
                if not d or not os.path.isdir(d):
                    continue
                for pat in (os.path.join(d, "PIL"), os.path.join(d, "pillow-*"), os.path.join(d, "Pillow-*")):
                    for p in glob.glob(pat):
                        try: shutil.rmtree(p)
                        except Exception: pass
            res = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--no-cache-dir", "Pillow"],
                capture_output=True, text=True, timeout=900)
            ok = False
            if res.returncode == 0:
                try:
                    _pil_smoke_test(); ok = True
                except Exception as e:
                    print("⚠️ بعد از نصب اول هنوز خراب:", e)
            if not ok:
                print("📥 تلاش دوم با نسخهٔ ثابت Pillow==11.3.0 ...")
                res2 = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--no-cache-dir", "Pillow==11.3.0"],
                    capture_output=True, text=True, timeout=900)
                if res2.returncode == 0:
                    try:
                        _pil_smoke_test(); ok = True
                    except Exception as e:
                        print("❌ ترمیم ممکن نشد:", e)
            if ok:
                print("✅ Pillow ترمیم شد — ربات با نسخهٔ سالم ادامه می‌دهد")
            return ok

        # سلامت‌چک Pillow — اگه فایل‌های دو نسخه قاطی شده باشند (مثلاً از Stop زدن وسط نصب)،
        # خطای «cannot import name ... from PIL._typing» همهٔ اسکرین‌شات‌ها را از بین می‌برد
        try:
            print("✅ Pillow:", _pil_smoke_test())
        except Exception as _pil_err:
            print("⚠️ Pillow خراب است (فایل‌های دو نسخه قاطی شده):", _pil_err)
            _pil_repair()

        from playwright.async_api import async_playwright
        from urllib.parse import urlparse
        import aiohttp
        import re
        from urllib.parse import urljoin
        from xml.etree import ElementTree as ET
        from telethon.errors import MessageNotModifiedError

        async def safe_edit(msg, text):
            try:
                current = msg.message or ""
                if current.strip() != text.strip():
                    await msg.edit(text)
            except MessageNotModifiedError:
                pass
            except Exception as e:
                print("safe_edit error:", e)

        nest_asyncio.apply()

        # --------- مشخصات تلگرام ----------
        api_id = 17275707
        api_hash = "21e40998ca4bb43c6b3e0192547042d4"
        phone = "+989202730147"
        OWNER_ID = 1232259973

        # === تنظیمات واترمارک و اورلی ===
        WATERMARK_TEXT = "@INO_BOKHOR1"
        WATERMARK_ENABLED = True
        OVERLAY_ENABLED = True
        cancel_flag = False

        # === تنظیم کیفیت دانلود ===
        DOWNLOAD_QUALITY = 720  # سقف کیفیت؛ با دستور «کیفیت 480» و ... تغییر می‌کند
        HLS_CONCURRENT_FRAGMENTS = 16  # دانلود هم‌زمان قطعه‌های HLS برای افزایش throughput
        # اگه برای سایتی لاگین لازمه، کوکی‌ها رو با افزونه "Get cookies.txt LOCALLY" بگیر و اینجا آپلود کن
        USER_COOKIES_FILE = os.path.join(RUNTIME_ROOT, "cookies.txt")


        def _download_format_selector(quality):
            """HLS اول؛ همهٔ مسیرهای جایگزین هم محدود به سقف کیفیت هستند."""
            q = int(quality)
            if q <= 0:
                raise ValueError("کیفیت باید عددی مثبت باشد")
            return (
                f"best[height<={q}][protocol^=m3u8]/"
                f"bestvideo[height<={q}][protocol^=m3u8]+bestaudio/"
                f"bestvideo[height<={q}]+bestaudio/"
                f"best[height<={q}]/"
                f"best[height<=?{q}]"
            )

        # === فونت برای واترمارک ===
        FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

        # ================== تنظیمات اسکرین‌شات‌ها ==================
        # کلمه‌ای که روی هر ۸ اسکرین‌شات نوشته میشه
        SCREENSHOT_TEXT = "کودن هاب"
        # "png" = بالاترین کیفیت ممکن (بی‌فقد) | "jpg" = حجم کمتر
        SCREENSHOT_FORMAT = "png"
        # اندازه متن نسبت به عرض تصویر (۰.۰۷۵ = ۷.۵٪ عرض تصویر)
        SCREENSHOT_TEXT_RATIO = 0.080
        # حالت رنگ: "auto" = خودکار کاملاً متضاد | "white" = همیشه سفید | "yellow" = همیشه زرد
        SCREENSHOT_TEXT_COLOR_MODE = "auto"
        # اگه True باشه، چهرهٔ افراد در کادر تشخیص داده میشه
        # و متن روی ناحیه‌ای گذاشته میشه که به چهره و بدن اون‌ها برخورد نکنه
        SCREENSHOT_AVOID_FACES = True
        # رنگ کاور پشت متن (سه‌تایی RGB) — مشکی
        SCREENSHOT_COVER_COLOR = (0, 0, 0)
        # شفافیت کاور (۰ تا ۲۵۵) — ۲۵۵ = کاملاً صاف، بدون هیچ شفافیتی
        SCREENSHOT_COVER_ALPHA = 255

        # === اگر True باشه، توی هر استارت session پاک میشه و دوباره لاگین می‌کنی ===
        # (False = با همون session قبلی سریع وصل میشه — توصیه میشه)
        FORCE_RELOGIN = False

        _PERSIAN_FONT_CACHE = None
        _PERSIAN_FONT_FAILED = False

        def _setup_persian_font():
            """دانلود فونت فارسی — مقاوم در برابر قطعی شبکه:
            چند آینه مختلف با timeout ۴۵ ثانیه + اعتبارسنجی فایل + فیل‌بک apt.
            نتیجه (موفق یا ناموفق) کش میشه تا دفعات بعد بلافاصله برگرده."""
            global _PERSIAN_FONT_CACHE, _PERSIAN_FONT_FAILED
            if _PERSIAN_FONT_CACHE:
                return _PERSIAN_FONT_CACHE
            if _PERSIAN_FONT_FAILED:
                return None
            persian_font = os.path.join(RUNTIME_ROOT, "Vazir.ttf")

            def _valid_font(path):
                try:
                    from PIL import ImageFont
                    if not (os.path.exists(path) and os.path.getsize(path) > 50000):
                        return False
                    ImageFont.truetype(path, 20)  # فایل واقعاً فونت سالم باشه
                    return True
                except Exception:
                    return False

            if _valid_font(persian_font):
                _PERSIAN_FONT_CACHE = persian_font
                return persian_font
            try:
                if os.path.exists(persian_font):
                    os.remove(persian_font)  # فایل ناقص/خراب از اجرای قبل
            except Exception:
                pass

            # آینه‌های مختلف (هرکدوم با timeout تا جا نمونه)
            font_urls = [
                "https://cdn.jsdelivr.net/npm/vazirmatn@33.0.3/fonts/ttf/Vazirmatn-Regular.ttf",
                "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.0.3/fonts/ttf/Vazirmatn-Regular.ttf",
                "https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@master/fonts/ttf/Vazirmatn-Regular.ttf",
                "https://raw.githubusercontent.com/rastikerdar/vazirmatn/master/fonts/ttf/Vazirmatn-Regular.ttf",
                "https://github.com/rastikerdar/vazirmatn/raw/master/fonts/ttf/Vazirmatn-Regular.ttf",
            ]
            for font_url in font_urls:
                try:
                    print(f"📥 دانلود فونت فارسی از: {font_url}")
                    r = requests.get(font_url, timeout=45,
                                     headers={"User-Agent": "Mozilla/5.0"})
                    r.raise_for_status()
                    if len(r.content) < 50000:
                        raise Exception(f"پاسخ ناقص است ({len(r.content)} بایت)")
                    with open(persian_font, "wb") as f:
                        f.write(r.content)
                    if _valid_font(persian_font):
                        print("✅ فونت فارسی دانلود شد")
                        _PERSIAN_FONT_CACHE = persian_font
                        return persian_font
                    raise Exception("فایل دانلودشده فونت سالم نبود")
                except Exception as e:
                    print(f"❌ خطا: {e} — تلاش بعدی...")
                    try:
                        if os.path.exists(persian_font):
                            os.remove(persian_font)
                    except Exception:
                        pass
                    continue

            # اگه هیچ لینکی کار نکرد از apt نصب کن (دو بسته، هرکدوم که درش بود)
            try:
                print("📥 نصب فونت فارسی از apt...")
                subprocess.run(
                    ["apt-get", "install", "-y", "fonts-farsiweb", "fonts-sil-scheherazade"],
                    capture_output=True, timeout=180
                )
                import glob
                for pat in ("/usr/share/fonts/truetype/farsiweb/*.ttf",
                            "/usr/share/fonts/truetype/sil-scheherazade/*.ttf"):
                    hits = sorted(glob.glob(pat))
                    if hits and _valid_font(hits[0]):
                        print("✅ فونت از apt نصب شد")
                        _PERSIAN_FONT_CACHE = hits[0]
                        return hits[0]
            except Exception as e:
                print(f"❌ apt هم کار نکرد: {e}")

            _PERSIAN_FONT_FAILED = True  # دفعات بعد دوباره جا نبیند
            print("⚠️ فونت فارسی پیدا نشد — متن اسکرین‌شات اعمال نمی‌شود")
            return None

        # === تنظیمات حافظه موقت ===
        TEMP_PATH = "/content/temp" if os.path.exists("/content") else "./temp"
        os.makedirs(TEMP_PATH, exist_ok=True)

        # ================== پاک‌سازی فایل‌های ناقص ==================
        def cleanup_incomplete_files(reason=""):
            """حذف فایل‌های ناقص/موقت باقی‌مانده از اجرای قبلی
            همهٔ فایل‌های داخل TEMP_PATH فایل‌های کاری موقتی‌ان،
            پس پاک کردن کل پوشه کاملاً بی‌خطر است."""
            removed = 0
            freed = 0
            try:
                if os.path.exists(TEMP_PATH):
                    for name in os.listdir(TEMP_PATH):
                        p = os.path.join(TEMP_PATH, name)
                        try:
                            if os.path.isfile(p):
                                freed += os.path.getsize(p)
                                os.remove(p)
                                removed += 1
                            else:
                                shutil.rmtree(p, ignore_errors=True)
                                removed += 1
                        except Exception:
                            pass
            except Exception as e:
                print("⚠️ خطا در پاک‌سازی:", e)
            print(f"🧹 پاک‌سازی ({reason or 'خروج'}): {removed} فایل حذف شد | {freed/1024/1024:.1f} MB آزاد شد")

        def _install_exit_handlers():
            """با هر توقف (دکمه Stop، سیگنال، خروج) فایل‌های ناقص پاک بشن
            تا دفعهٔ بعد ربات تمیز و بدون مشکل روشن بشه."""
            import signal
            import atexit
            def _handler(signum, frame):
                print("\n🛑 سیگنال دریافت شد — پاک‌سازی فایل‌های ناقص قبل از خروج...")
                try:
                    for pat in ("ffmpeg", "yt-dlp", "chromium", "curl"):
                        subprocess.run(["pkill", "-f", pat], capture_output=True, timeout=10)
                except Exception:
                    pass
                cleanup_incomplete_files("خروج")
                os._exit(0)
            try:
                signal.signal(signal.SIGTERM, _handler)
                signal.signal(signal.SIGINT, _handler)
            except Exception as e:
                print("⚠️ ثبت signal handler:", e)
            atexit.register(lambda: cleanup_incomplete_files("atexit"))

        # === Telegram Client ===
        client = TelegramClient("userbot_session", api_id, api_hash)

        # === دانلود موازی و سریع از تلگرام ===
        TG_DL_WORKERS = 8                # تعداد درخواست‌های هم‌زمان
        TG_DL_PART = 512 * 1024          # حداکثر مجاز تلگرام برای هر تکه

        try:
            import cryptg  # رمزگشایی C؛ بدون این telethon خیلی کند است
            print("✅ cryptg فعال است")
        except ImportError:
            print("⚠️ cryptg نصب نیست؛ سرعت دانلود تلگرام پایین می‌ماند")

        async def fast_tg_download(message, dest_path, status_msg=None):
            """دانلود موازی فایل تلگرام؛ اگه نشد به download_media معمولی برمی‌گرده."""
            f = getattr(message, "file", None)
            size = int(getattr(f, "size", 0) or 0)
            if size < 10 * 1024 * 1024:
                return await client.download_media(message, file=dest_path)
            try:
                total_parts = math.ceil(size / TG_DL_PART)
                workers = min(TG_DL_WORKERS, total_parts)
                per = math.ceil(total_parts / workers)
                done_bytes = 0
                last_pct = -10
                t0 = time.monotonic()
                with open(dest_path, "wb") as fh:
                    fh.truncate(size)
                fd = os.open(dest_path, os.O_WRONLY)

                async def seg(start_part, n_parts):
                    nonlocal done_bytes, last_pct
                    pos = start_part * TG_DL_PART
                    async for chunk in client.iter_download(
                            message.media, offset=pos, limit=n_parts,
                            request_size=TG_DL_PART, chunk_size=TG_DL_PART, file_size=size):
                        if cancel_flag:
                            raise asyncio.CancelledError()
                        await asyncio.to_thread(os.pwrite, fd, chunk, pos)
                        pos += len(chunk)
                        done_bytes += len(chunk)
                        pct = int(done_bytes * 100 / size)
                        if status_msg and pct - last_pct >= 10:
                            last_pct = pct
                            spd = done_bytes / max(time.monotonic() - t0, 0.1) / 1024 / 1024
                            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
                            asyncio.create_task(safe_edit(
                                status_msg, f"⬇️ دانلود از تلگرام (موازی)...\n[{bar}] {pct}%\n⚡ {spd:.1f} MB/s"))

                try:
                    tasks = [seg(i * per, min(per, total_parts - i * per))
                             for i in range(workers) if i * per < total_parts]
                    await asyncio.gather(*tasks)
                finally:
                    os.close(fd)
                if done_bytes < size:
                    raise IOError(f"ناقص: {done_bytes}/{size}")
                print(f"✅ دانلود تلگرام: {size/1024/1024:.1f} MB در {time.monotonic()-t0:.0f}s")
                return dest_path
            except asyncio.CancelledError:
                if os.path.exists(dest_path): os.remove(dest_path)
                return None
            except Exception as e:
                print(f"⚠️ دانلود موازی نشد ({e}) → روش معمولی")
                if os.path.exists(dest_path): os.remove(dest_path)
                return await client.download_media(message, file=dest_path)

        # === تنظیمات Pixeldrain ===
        API_KEY = "c971b300-5ff3-4f12-b7e6-f526e54a5663"
        auth_header = {
            "Authorization": "Basic " + base64.b64encode(f":{API_KEY}".encode("utf-8")).decode("utf-8")
        }

        # ---------- تنظیمات محدودیت حجم ----------
        CHUNK_LIMIT = 1_950_000_000
        MAX_PART_SIZE = 1_950_000_000


        if os.path.exists("/content"):
            tempfile.gettempdir = lambda: TEMP_PATH

        # ================== Encoder Mode ==================
        # NVENC در این Runtime قابل استفاده نیست؛ مستقیم از CPU/libx264 استفاده می‌کنیم.

        # ================== توابع تعمیر ==================
        def is_valid_video(video_path):
            if not os.path.exists(video_path) or os.path.getsize(video_path) < 100_000:
                return False
            try:
                result = subprocess.run([
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", video_path
                ], capture_output=True, text=True, timeout=10)
                return result.returncode == 0 and result.stdout.strip()
            except:
                return False

        def fix_video_file(video_path):
            if is_valid_video(video_path):
                return video_path
            fixed_path = video_path.replace(".mp4", "_fixed.mp4")
            cmd = [
                "ffmpeg", "-v", "error", "-err_detect", "ignore_err", "-i", video_path,
                "-c", "copy", "-avoid_negative_ts", "make_zero", "-fflags", "+genpts",
                "-y", fixed_path
            ]
            ret = subprocess.run(cmd, capture_output=True)
            if ret.returncode == 0 and os.path.exists(fixed_path) and os.path.getsize(fixed_path) > 100_000:
                try:
                    os.remove(video_path)
                    print(f"✅ فایل تعمیر شد: {fixed_path}")
                except: pass
                return fixed_path
            return None

        def run(cmd):
            global cancel_flag
            print("EXEC:", " ".join(cmd))
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            try:
                for line in p.stdout:
                    if cancel_flag:
                        p.kill()
                        break
                    print(line.rstrip())
            except Exception as e:
                print("run() read error:", e)
            p.wait()
            return p.returncode

        #================== توابع کمکی ==================
        def _get_video_dimensions_sync(video_path):
            try:
                out = subprocess.check_output(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height", "-of", "csv=s=x:p=0", video_path]
                ).decode().strip().split('\n')[0]
                width, height = map(int, out.split('x'))
                if width > 0 and height > 0:
                    return width, height
            except:
                pass
            try:
                out = subprocess.check_output(
                    ["ffprobe", "-v", "error", "-select_streams", "v:0",
                     "-show_entries", "stream=width,height", "-of", "json", video_path]
                ).decode()
                data = json.loads(out)
                stream = data.get('streams', [{}])[0]
                width = int(stream.get('width', 0))
                height = int(stream.get('height', 0))
                if width > 0 and height > 0:
                    return width, height
            except:
                pass
            return 1280, 720

        def _get_fontsize_sync(video_path):
            try:
                width, _ = _get_video_dimensions_sync(video_path)
                return min(max(25, int(width * 0.046)), 72)
            except:
                return 25

        def _get_duration_sync(video_path):
            try:
                out = subprocess.check_output(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                     "-of", "default=noprint_wrappers=1:nokey=1", video_path]
                ).decode().strip()
                return out
            except:
                return None

        def remux_for_faststart(input_path):
            if not is_valid_video(input_path):
                return input_path
            output_path = tempfile.mktemp(suffix=".mp4")
            cmd = ["ffmpeg", "-y", "-i", input_path, "-c", "copy", "-map_metadata", "0",
                   "-movflags", "+faststart", output_path]
            ret = subprocess.run(cmd, capture_output=True)
            if (ret.returncode == 0 and os.path.exists(output_path)
                    and os.path.getsize(output_path) > 100_000
                    and is_valid_video(output_path)):
                try:
                    if output_path != input_path:
                        os.remove(input_path)
                except: pass
                return output_path
            return input_path

        def _get_thumbnail_sync(video_path):
            thumb = tempfile.mktemp(suffix=".jpg", dir=tempfile.gettempdir())
            try:
                duration_str = _get_duration_sync(video_path)
                duration = float(duration_str) if duration_str else 10
                capture_time = min(450, max(1, duration / 2))
                subprocess.run(
                    ["ffmpeg", "-y", "-ss", str(capture_time), "-i", video_path,
                     "-vframes", "1", "-q:v", "1", thumb],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                )
            except:
                try:
                    subprocess.run(
                        ["ffmpeg", "-y", "-i", video_path, "-vframes", "1", thumb],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True
                    )
                except:
                    return None
            return thumb if os.path.exists(thumb) else None

        # ================== اسکرین‌شات با کیفیت بالا + کلمه ==================
        # --- تشخیص چهره (YuNet با فیل‌بک Haar) ---
        _FACE_YUNET_MODEL = "/content/face_yunet.onnx" if os.path.exists("/content") else "./face_yunet.onnx"
        _FACE_YUNET = None      # detector کش‌شده
        _FACE_CASCADES = {}     # فیل‌بک Haar برای نسخه‌های قدیمی OpenCV

        def _get_face_yunet():
            """دریافت/ساخت detector YuNet — مدل یکبار دانلود و کش میشه (~۲۲۷ KB)"""
            global _FACE_YUNET
            if _FACE_YUNET is not None:
                return _FACE_YUNET
            try:
                import cv2
                if not hasattr(cv2, "FaceDetectorYN"):
                    return None
                if not (os.path.exists(_FACE_YUNET_MODEL) and os.path.getsize(_FACE_YUNET_MODEL) > 100000):
                    print("📥 دانلود مدل تشخیص چهره (YuNet)...")
                    import urllib.request
                    urls = [
                        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                        "https://cdn.jsdelivr.net/gh/opencv/opencv_zoo@main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
                    ]
                    for u in urls:
                        try:
                            urllib.request.urlretrieve(u, _FACE_YUNET_MODEL)
                            if os.path.exists(_FACE_YUNET_MODEL) and os.path.getsize(_FACE_YUNET_MODEL) > 100000:
                                break
                        except Exception:
                            continue
                if os.path.exists(_FACE_YUNET_MODEL) and os.path.getsize(_FACE_YUNET_MODEL) > 100000:
                    # score_threshold=0.55 → یادگیری بهتر، nms=0.3
                    _FACE_YUNET = cv2.FaceDetectorYN.create(
                        _FACE_YUNET_MODEL, "", (320, 320), 0.55, 0.3, 5000
                    )
                    return _FACE_YUNET
            except Exception as e:
                print("⚠️ خطا در آماده‌سازی YuNet:", e)
            return None

        def _detect_face_boxes(rgb_img):
            """تشخیص چهره‌ها (YuNet، در نبودش Haar).
            برمی‌گردونه: لیست (x, y, w, h) در مختصات خود تصویر،
            هر باکس کمی بزرگ‌تر شده تا کل سر (مو، پیشونی، گوش) پوشش داده بشه.
            اگه تشخیص در دسترس نباشه یا خطا بده، لیست خالی (رفتار قبلی حفظ میشه)."""
            try:
                import cv2
                import numpy as np
                arr = np.asarray(rgb_img)
                if arr.ndim == 2:
                    gray = arr
                    bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
                else:
                    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
                    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                h, w = gray.shape[:2]
                boxes = []
                # ۱) YuNet — دقیق‌تر و برای چهره‌های کج/نیم‌رخ هم جواب میده (نیاز به BGR سه‌کاناله)
                yunet = _get_face_yunet()
                if yunet is not None:
                    try:
                        yunet.setInputSize((w, h))
                        _, faces = yunet.detect(bgr)
                        if faces is not None:
                            for row in faces:
                                x, y, fw, fh = [int(v) for v in row[:4]]
                                boxes.append((x, y, fw, fh))
                    except Exception:
                        pass
                # ۲) Haar — فقط برای نسخه‌های قدیمی OpenCV که YuNet ندارن
                if not boxes and hasattr(cv2, "CascadeClassifier"):
                    min_size = max(20, int(w * 0.03))
                    for name in ("haarcascade_frontalface_default.xml", "haarcascade_profileface.xml"):
                        try:
                            if name not in _FACE_CASCADES:
                                path = os.path.join(cv2.data.haarcascades, name)
                                if not os.path.exists(path):
                                    continue
                                _FACE_CASCADES[name] = cv2.CascadeClassifier(path)
                            det = _FACE_CASCADES[name].detectMultiScale(
                                gray, scaleFactor=1.1, minNeighbors=5,
                                minSize=(min_size, min_size)
                            )
                            for (x, y, fw, fh) in det:
                                boxes.append((int(x), int(y), int(fw), int(fh)))
                        except Exception:
                            pass
                # بزرگ‌تر کردن باکس‌ها برای پوشش کل سر
                out = []
                for (x, y, fw, fh) in boxes:
                    x0 = max(0, x - int(fw * 0.45))
                    y0 = max(0, y - int(fh * 0.55))
                    x1 = min(w, x + fw + int(fw * 0.45))
                    y1 = min(h, y + fh + int(fh * 0.55))
                    out.append((x0, y0, x1 - x0, y1 - y0))
                return out
            except Exception as e:
                print("⚠️ خطا در تشخیص چهره:", e)
                return []

        # --- تشخیص بدن (PP-HumanSeg از OpenCV Zoo — حتی وقتی صورت در کادر نیست) ---
        _PERSON_SEG_MODEL = "/content/pphumanseg.onnx" if os.path.exists("/content") else "./pphumanseg.onnx"
        _PERSON_SEG = None

        def _get_person_segmenter():
            """دریافت مدل سگمنتیشن بدن — یکبار دانلود و کش میشه (~۶ مگابایت)"""
            global _PERSON_SEG
            if _PERSON_SEG is not None:
                return _PERSON_SEG
            try:
                import cv2
                if not (os.path.exists(_PERSON_SEG_MODEL) and os.path.getsize(_PERSON_SEG_MODEL) > 1_000_000):
                    print("📥 دانلود مدل تشخیص بدن (PP-HumanSeg, ~۶MB)...")
                    import urllib.request
                    urls = [
                        "https://github.com/opencv/opencv_zoo/raw/main/models/human_segmentation_pphumanseg/human_segmentation_pphumanseg_2023mar.onnx",
                        "https://raw.githubusercontent.com/opencv/opencv_zoo/main/models/human_segmentation_pphumanseg/human_segmentation_pphumanseg_2023mar.onnx",
                    ]
                    for u in urls:
                        try:
                            urllib.request.urlretrieve(u, _PERSON_SEG_MODEL)
                            if os.path.exists(_PERSON_SEG_MODEL) and os.path.getsize(_PERSON_SEG_MODEL) > 1_000_000:
                                break
                        except Exception:
                            continue
                if os.path.exists(_PERSON_SEG_MODEL) and os.path.getsize(_PERSON_SEG_MODEL) > 1_000_000:
                    _PERSON_SEG = cv2.dnn.readNet(_PERSON_SEG_MODEL)
                    return _PERSON_SEG
            except Exception as e:
                print("⚠️ خطا در آماده‌سازی مدل بدن:", e)
            return None

        def _detect_person_mask(rgb_img):
            """ماسک بدنِ انسان‌های کادر (HxW حقیقی) — حتی وقتی صورت دیده نمی‌شود.
            در صورت خطا None برمی‌گردونه (رفتار قبلی حفظ میشه)."""
            try:
                import cv2
                import numpy as np
                seg = _get_person_segmenter()
                if seg is None:
                    return None
                arr = np.asarray(rgb_img)
                if arr.ndim == 2:
                    bgr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
                else:
                    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
                h, w = bgr.shape[:2]
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                blob_in = cv2.resize(rgb, (192, 192)).astype(np.float32) / 255.0
                blob_in = (blob_in - 0.5) / 0.5
                seg.setInput(cv2.dnn.blobFromImage(blob_in))
                out = seg.forward()
                out = cv2.resize(out[0].transpose(1, 2, 0), (w, h), interpolation=cv2.INTER_LINEAR)
                mask = out.argmax(axis=2) == 1
                # کمی بزرگ‌تر کردن ماسک تا حاشیهٔ امن دور بدن هم رعایت بشه
                if mask.any():
                    k = max(3, int(max(w, h) * 0.03))
                    if k % 2 == 0:
                        k += 1
                    mask = cv2.dilate(mask.astype(np.uint8), np.ones((k, k), np.uint8)).astype(bool)
                return mask
            except Exception as e:
                print("⚠️ خطا در تشخیص بدن:", e)
                return None

        def _rect_overlap(a, b):
            """مساحت اشتراک دو باکس (x, y, w, h)"""
            x0 = max(a[0], b[0]); y0 = max(a[1], b[1])
            x1 = min(a[0] + a[2], b[0] + b[2]); y1 = min(a[1] + a[3], b[1] + b[3])
            return max(0, x1 - x0) * max(0, y1 - y0)

        def _pick_text_region(small_img, box_w, box_h, person_mask=None, avoid_boxes=()):
            """بهترین محل برای باکس متن+کاور — ترجیح به پایین تصویر.
            تصویر کوچیک رو به ۹ ناحیه تقسیم می‌کنه و بر اساس «شلوغی» هر ناحیه
            بهترین محل رو انتخاب می‌کنه (گوشهٔ پایین چپ/راست → پایین وسط → بالا → میانی).
            مهم‌تر از همه: باکسِ واقعیِ متن روی بدن (person_mask) و چهره (avoid_boxes)
            نیفتد — هم‌پوشانی باکس با ماسک بدن محاسبه و با جریمهٔ سنگین رد می‌شود."""
            try:
                import numpy as np
                g = np.asarray(small_img.convert("L"), dtype=np.float32)
                h, w = g.shape
                cells = {}
                for r in range(3):
                    for c in range(3):
                        cell = g[r*h//3:(r+1)*h//3, c*w//3:(c+1)*w//3]
                        cells[(r, c)] = float(cell.std())
            except Exception:
                w, h = small_img.size
                g = small_img.convert("L")
                cells = {}
                for r in range(3):
                    for c in range(3):
                        box = (c*w//3, r*h//3, (c+1)*w//3, (r+1)*h//3)
                        data = list(g.crop(box).getdata())
                        mean = sum(data) / len(data)
                        cells[(r, c)] = (sum((v-mean)**2 for v in data) / len(data)) ** 0.5

            # (ترجیح، ردیف، ستون) — ترجیح ۰ = پایین تصویر
            candidates = [
                (0, 2, 0), (0, 2, 2), (0, 2, 1),   # اولویت ۰ = پایین: چپ، راست، وسط
                (1, 1, 0), (1, 1, 2),              # اولویت ۱ = میانی: چپ، راست
                (2, 0, 2), (2, 0, 1),              # اولویت ۲ = بالا: راست، وسط (بالا-چپ عمداً کاندید نیست — آیکون‌های تلگرام)
            ]
            W = person_mask.shape[1] if person_mask is not None else None
            H = person_mask.shape[0] if person_mask is not None else None
            mx = int(W * 0.01) if W else 0
            my = int(H * 0.01) if H else 0
            # نقشهٔ فاصله از بدن (برای اینکه متن به بدن «چسبیده» هم نشود)
            dist_map = None
            if person_mask is not None and person_mask.any():
                try:
                    import cv2
                    dist_map = cv2.distanceTransform((~person_mask).astype(np.uint8), cv2.DIST_L2, 5)
                except Exception:
                    dist_map = None
            results = {}
            for prio, r, c in candidates:
                cx_n = (c + 0.5) / 3.0
                cy_n = (r + 0.5) / 3.0
                # ناحیهٔ سلول در مختصات نرمال (برای باکس‌های چهره)
                cell_box = (c / 3.0, r / 3.0, 1 / 3.0, 1 / 3.0)
                # حتی کمترین برخورد با باکس چهره/بدن → جریمه سنگین
                face_penalty = 0
                for fb in avoid_boxes:
                    if _rect_overlap(cell_box, fb) > 0:
                        face_penalty = 10000
                        break
                # هم‌پوشانی باکسِ واقعی با ماسک بدن — معیار اولِ انتخاب (مطلق)
                person_ratio = 0.0
                dist = 0.0
                if person_mask is not None:
                    x0 = max(mx, min(W - box_w - mx, int(cx_n * W) - box_w // 2))
                    y0 = max(my, min(H - box_h - my, int(cy_n * H) - box_h // 2))
                    sub = person_mask[y0:y0 + box_h, x0:x0 + box_w]
                    person_ratio = float(sub.mean())
                    if dist_map is not None:
                        dist = float(dist_map[y0:y0 + box_h, x0:x0 + box_w].min())
                score = prio * 150 + cells[(r, c)] + face_penalty
                # انتخاب: ۱) بدون هم‌پوشانی با بدن  ۲) دورترین از بدن  ۳) پایین‌تر و خلوت‌تر
                # (گوشهٔ بالا-چپ اصلاً کاندید نیست — آیکون زمان/حجم/دانلود تلگرام روی همان ناحیه است)
                dist_band = int(round(dist / 10) * 10)
                key = (round(person_ratio, 3), -dist_band, score)
                results[(r, c)] = (key, cx_n, cy_n)

            best = min(results.values(), key=lambda t: t[0])
            return best[1], best[2]

        # ================== رندر متن فارسی (سازگار با همه نسخه‌های Pillow) ==================
        _RENDERER_SHAPES = None

        def _renderer_shapes_arabic(font_path):
            """آزمون یک‌بار: آیا موتور رندرِ Pillow خودش چیدمان RTL و چسبندگی
            حروف عربی را انجام می‌دهد؟ (Pillowهای جدید بله، قدیمی‌ها نه)
            روش: «با» و «اب» را رندر می‌کنیم و می‌بینیم نقطهٔ ب در کدام سمت است."""
            global _RENDERER_SHAPES
            if _RENDERER_SHAPES is not None:
                return _RENDERER_SHAPES
            _RENDERER_SHAPES = False
            try:
                from PIL import Image, ImageDraw, ImageFont
                import numpy as np
                font = ImageFont.truetype(font_path, 44)
                def dot_x(s):
                    img = Image.new("L", (300, 200), 0)
                    d = ImageDraw.Draw(img)
                    l, t, r, b = d.textbbox((0, 0), s, font=font)
                    d.text((150 - (r - l) // 2 - l, 60 - t), s, font=font, fill=255)
                    a = np.asarray(img)
                    ink = a > 100
                    ys, xs = np.where(ink)
                    if len(xs) == 0:
                        return None
                    y0, y1 = ys.min(), ys.max()
                    x0, x1 = xs.min(), xs.max()
                    if x1 - x0 < 10:
                        return None
                    band = ink[int(y1 - (y1 - y0) * 0.13):y1, :]
                    cols = band.any(axis=0)
                    runs = []
                    start = None
                    for i in range(len(cols)):
                        if cols[i] and start is None:
                            start = i
                        elif not cols[i] and start is not None:
                            runs.append((start, i - 1)); start = None
                    if start is not None:
                        runs.append((start, len(cols) - 1))
                    if not runs:
                        return None
                    dot = min(runs, key=lambda rr: rr[1] - rr[0])
                    return ((dot[0] + dot[1]) / 2 - x0) / (x1 - x0)
                x1 = dot_x("با")
                x2 = dot_x("اب")
                if x1 is not None and x2 is not None:
                    # اگر رندر RTL باشد: در «با» حرف ب سمت راست و در «اب» سمت چپ است
                    _RENDERER_SHAPES = x1 > x2
            except Exception as e:
                print("⚠️ آزمون shaping:", e)
            return _RENDERER_SHAPES

        def _prepare_arabic_text(text, font_path):
            """متن را برای رندر آماده می‌کند — در همهٔ نسخه‌های Pillow درست نمایش داده میشه:
            - اگه خودِ Pillow shaping عربی (bidi+چسبندگی) را بدهد → متن منطقی همان‌طور که
              تایپ شده می‌رود (دوباره وارونه نمی‌شود).
            - اگه ندهد (Pillow قدیمی) → از روش کلاسیک reshaper+bidi استفاده می‌شود."""
            if not any('\u0600' <= ch <= '\u06FF' for ch in text):
                return text
            try:
                if _renderer_shapes_arabic(font_path):
                    return text
            except Exception:
                pass
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
                return get_display(arabic_reshaper.reshape(text))
            except Exception:
                return text

        def _watermark_screenshot_sync(src_path, out_path):
            """کلمه روی اسکرین‌شات:
            - خودکار در خالی‌ترین ناحیه (اولویت پایین تصویر)
            - رنگ کاملاً متضاد با پس‌زمینه (سفید روی تیره / مشکی روی روشن)
            - کاور (کادر) نیمه‌شفاف پشت متن برای خوانایی کامل"""
            global SCREENSHOT_TEXT, SCREENSHOT_FORMAT, SCREENSHOT_TEXT_RATIO, FONT_PATH, SCREENSHOT_COVER_COLOR, SCREENSHOT_COVER_ALPHA
            try:
                from PIL import Image, ImageDraw, ImageFont
            except Exception as _pil_e:
                print("⚠️ خطای واردسازی Pillow — ترمیم خودکار و تلاش دوباره:", _pil_e)
                if not _pil_repair():
                    print("❌ Pillow ترمیم نشد — این اسکرین‌شات رد می‌شود")
                    return None
                from PIL import Image, ImageDraw, ImageFont
            try:
                img = Image.open(src_path).convert("RGB")
            except Exception as e:
                print("❌ خطا در خواندن اسکرین‌شات:", e)
                return None

            W, H = img.size

            # ۱) چهره‌ها + ماسک بدن (تا متن روی هیچ‌کدوم نیفتد)
            small = img.copy()
            small.thumbnail((240, 240))
            faces_norm = []
            person_mask = None
            try:
                if SCREENSHOT_AVOID_FACES:
                    # تشخیص چهره با رزولوشن کامل تصویر (دقیق‌تر)
                    fw, fh = img.size
                    for (fx, fy, fww, fhh) in _detect_face_boxes(img):
                        faces_norm.append((fx / fw, fy / fh, fww / fw, fhh / fh))
                    # سگمنتیشن کل بدن — حتی وقتی صورت در کادر دیده نمی‌شود
                    person_mask = _detect_person_mask(img)
            except Exception as e:
                print("⚠️ خطا در تشخیص چهره/بدن:", e)
            if faces_norm:
                print(f"👤 {len(faces_norm)} چهره شناسایی شد — متن دور از چهره و بدن قرار می‌گیرد")
            elif person_mask is not None and person_mask.any():
                print("🧍 بدن در کادر دیده شد (بدون صورت) — متن دور از آن قرار می‌گیرد")

            text = (SCREENSHOT_TEXT or "").strip()
            if text:
                has_persian = any('\u0600' <= ch <= '\u06FF' for ch in text)
                font_path = _setup_persian_font() if has_persian else FONT_PATH
                can_draw = font_path is not None and os.path.exists(font_path)
                if has_persian and not can_draw:
                    print("⚠️ فونت فارسی پیدا نشد — متن اسکرین‌شات اعمال نمی‌شود")
                if can_draw:
                    try:
                        font_size = max(24, min(112, int(W * SCREENSHOT_TEXT_RATIO)))
                        font = ImageFont.truetype(font_path, font_size)

                        # شکل‌دهی فارسی — سازگار با همهٔ محیط‌ها (Pillow قدیمی و جدید)
                        shaped = _prepare_arabic_text(text, font_path)

                        probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
                        l, t, r, b = probe.textbbox((0, 0), shaped, font=font)
                        tw, th = r - l, b - t
                        if tw > 12 and th > 12:
                            # کاور: عرض فقط دور متن (کم‌پدینگ)، ارتفاع فقط کمی بیشتر از متن
                            pad_x = int(tw * 0.08) + 6
                            pad_y = int(th * 0.15) + 5
                            box_w, box_h = tw + 2*pad_x, th + 2*pad_y
                            # باکس‌های چهره را به ناحیهٔ سر+بدن تبدیل می‌کنیم
                            avoid_norm = []
                            for (fx, fy, fww, fhh) in faces_norm:
                                cx = fx + fww / 2.0
                                pw = fww * 2.6
                                px = max(0.0, cx - pw / 2.0)
                                py = max(0.0, fy * 0.8)
                                avoid_norm.append((px, py, min(pw, 1.0 - px), max(0.0, 1.0 - py)))
                            # انتخاب مکان — باکس واقعی نباید روی بدن/چهره بیفتد
                            try:
                                cx_n, cy_n = _pick_text_region(small, box_w, box_h, person_mask, avoid_norm)
                            except Exception:
                                cx_n, cy_n = 0.5, 0.85
                            mx, my = int(W*0.01), int(H*0.01)
                            x0 = max(mx, min(W - box_w - mx, int(cx_n*W) - box_w//2))
                            y0 = max(my, min(H - box_h - my, int(cy_n*H) - box_h//2))

                            # ۲) کاور پررنگ + رنگ متن کاملاً متضاد با خودِ کاور
                            mode = (SCREENSHOT_TEXT_COLOR_MODE or "auto").lower()
                            cover_rgb = SCREENSHOT_COVER_COLOR or (0, 0, 0)
                            cover_fill = (int(cover_rgb[0]), int(cover_rgb[1]), int(cover_rgb[2]),
                                          int(max(60, min(255, SCREENSHOT_COVER_ALPHA))))
                            if mode == "white":
                                text_fill = (255, 255, 255, 255)
                            elif mode == "yellow":
                                text_fill = (255, 215, 0, 255)
                            else:  # auto — بر اساس روشنایی خودِ رنگ کاور
                                lum = 0.299*cover_rgb[0] + 0.587*cover_rgb[1] + 0.114*cover_rgb[2]
                                text_fill = (255, 255, 255, 255) if lum < 140 else (15, 15, 15, 255)

                            # ۳) کاور پررنگ + متن
                            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
                            od = ImageDraw.Draw(overlay)
                            od.rounded_rectangle(
                                [x0, y0, x0+box_w, y0+box_h],
                                radius=max(8, int(box_h*0.24)), fill=cover_fill
                            )
                            od.text(
                                (x0 + (box_w - tw)//2 - l, y0 + (box_h - th)//2 - t),
                                shaped, font=font, fill=text_fill
                            )
                            img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
                    except Exception as e:
                        print("⚠️ خطا در رسم متن اسکرین‌شات:", e)

            # ۴) ذخیره با بالاترین کیفیت
            try:
                if (SCREENSHOT_FORMAT or "png").lower() == "png":
                    img.save(out_path, "PNG", optimize=True)
                else:
                    img.save(out_path, "JPEG", quality=95, subsampling=0)
                return out_path
            except Exception as e:
                print("❌ خطا در ذخیره اسکرین‌شات:", e)
                return None

        def _get_multiple_screenshots_sync(video_path, count=8):
            """۸ اسکرین‌شات با بالاترین کیفیت ممکن (PNG بی‌فقد، رزولوشن کامل ویدیو)
            + کلمه روی هرکدوم در خالی‌ترین ناحیه با رنگ متضاد و کاور."""
            screenshots = []
            try:
                duration_str = _get_duration_sync(video_path)
                duration = float(duration_str) if duration_str else 100
                src = video_path
                if not is_valid_video(src):
                    src = fix_video_file(src) or video_path
                capture_points = [
                    duration * 0.08, duration * 0.2, duration * 0.3, duration * 0.4, duration * 0.45,
                    duration * 0.5, duration * 0.7, duration * 0.8, duration * 0.98, duration * 0.25,
                ]
                ext = ".png" if (SCREENSHOT_FORMAT or "png").lower() == "png" else ".jpg"
                for i, t in enumerate(capture_points):
                    base = tempfile.mktemp(suffix=f"_pt{i}.png", dir=tempfile.gettempdir())
                    out = tempfile.mktemp(suffix=f"_pt{i}_wm{ext}", dir=tempfile.gettempdir())
                    try:
                        # -c:v png = بدون هیچ افت کیفیتی، با رزولوشن کامل
                        subprocess.run(
                            ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", src,
                             "-frames:v", "1", "-c:v", "png", base],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180
                        )
                    except Exception as e:
                        print(f"⚠️ خطا در گرفتن اسکرین‌شات {i}:", e)
                    if os.path.exists(base):
                        wm_path = _watermark_screenshot_sync(base, out)
                        try: os.remove(base)
                        except Exception: pass
                        if wm_path:
                            screenshots.append(wm_path)
                return screenshots
            except Exception as e:
                print("❌ خطا در گرفتن اسکرین‌شات‌ها:", e)
                return []

        async def get_duration_async(video_path):
            duration_str = await asyncio.to_thread(_get_duration_sync, video_path)
            try:
                return float(duration_str)
            except:
                return None

        #================== اورلی ==================
        OVERLAY_PATH_FILE = os.path.join(RUNTIME_ROOT, "overlay_path.txt")

        def get_overlay_path():
            if os.path.exists(OVERLAY_PATH_FILE):
                try:
                    with open(OVERLAY_PATH_FILE) as f:
                        p = f.read().strip()
                        if p and os.path.exists(p):
                            return p
                except: pass
            return None

        async def save_overlay_image(event):
            try:
                msg = event.message
                if not (msg.photo or msg.video or (
                    msg.document and (msg.document.mime_type or "").startswith(("video", "image"))
                )):
                    await event.reply("لطفاً عکس یا ویدیو (یا فایل ویدیویی) ارسال کنید.")
                    return
                if msg.photo:
                    ext = ".jpg"
                elif msg.video:
                    if not getattr(msg, "document", None):
                        await event.reply("⚠️ ویدیو را به صورت فایل ارسال کنید.")
                        return
                    ext = ".mp4"
                elif msg.document:
                    mime = (msg.document.mime_type or "").lower()
                    if "video" in mime: ext = ".mp4"
                    elif "image" in mime: ext = ".jpg"
                    else:
                        await event.reply("فقط عکس یا ویدیو قبول می‌شود.")
                        return
                else:
                    await event.reply("فقط عکس یا ویدیو ارسال کنید.")
                    return
                dest = os.path.join(RUNTIME_ROOT, f"overlay{ext}")
                path = await client.download_media(msg, file=dest)
                if path and os.path.exists(path) and os.path.getsize(path) > 0:
                    with open(OVERLAY_PATH_FILE, "w") as f:
                        f.write(path)
                    overlay_type = "ویدیو متحرک" if ext == ".mp4" else "عکس"
                    await event.reply(f"{overlay_type} اورلی با موفقیت ذخیره شد!")
                else:
                    await event.reply("خطا در ذخیرهٔ اورلی — فایل دانلود نشد یا خالی است.")
            except Exception as e:
                await event.reply(f"خطا: {e}")

        #================== APPLY WATERMARK + OVERLAY ==================
        def _apply_watermark_sync(video_path, max_overlay_limit=25, progress_callback=None):
            global cancel_flag, WATERMARK_TEXT, FONT_PATH
            if cancel_flag: return None

            fixed_path = fix_video_file(video_path)
            if not fixed_path or not is_valid_video(fixed_path): return None

            overlay_file = get_overlay_path()
            apply_wm = WATERMARK_ENABLED
            apply_ol = OVERLAY_ENABLED and overlay_file and os.path.exists(overlay_file)

            if not apply_wm and not apply_ol:
                return None

            final_out = tempfile.mktemp(suffix=".mp4")
            fontsize = _get_fontsize_sync(fixed_path) if apply_wm else 0

            try:
                main_w, main_h = _get_video_dimensions_sync(fixed_path)
            except:
                main_w, main_h = 1280, 720

            try:
                total_duration = float(_get_duration_sync(fixed_path) or 0)
            except:
                total_duration = 0

            try:
                orig_bitrate_str = subprocess.check_output([
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=bit_rate",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    fixed_path
                ]).decode().strip()
                orig_bitrate = int(orig_bitrate_str)
            except:
                orig_bitrate = 2_500_000

            target_bitrate = f"{int(orig_bitrate * 0.95 / 1000)}k"
            maxrate        = f"{int(orig_bitrate * 1.0  / 1000)}k"
            bufsize        = f"{int(orig_bitrate * 2.0  / 1000)}k"
            print(f"📊 bitrate ورودی: {orig_bitrate/1000:.0f}k → خروجی: {target_bitrate}")

            cmd = ["ffmpeg", "-y", "-fflags", "+genpts", "-i", fixed_path]
            filter_complex = ""
            vout_label = "[0:v]"
            aout_label = "0:a?"

            if apply_wm:
                # تشخیص فارسی بودن متن
                has_persian = any('\u0600' <= c <= '\u06FF' for c in WATERMARK_TEXT)
                if has_persian:
                    current_font = _setup_persian_font() or FONT_PATH
                    font_option = f":fontfile='{current_font}'"
                else:
                    font_option = ""

                filter_complex = (
                    f"[0:v]drawtext=text='{WATERMARK_TEXT}'{font_option}:fontcolor=red:fontsize={fontsize}:borderw=2:bordercolor=yellow:"
                    f"x='(w-text_w)/2 + (w/2-50)*sin(t*0.5 + sin(t*0.5)*2)':y='(h-text_h)/2 + (h/2-50)*cos(t*0.4 + cos(t*0.3)*2)':"
                    f"enable='lt(mod(t,300),60)'[v1];"
                    f"[v1]drawtext=text='{WATERMARK_TEXT}'{font_option}:fontcolor=red:fontsize={fontsize}:borderw=3:bordercolor=yellow:"
                    f"x=(w-text_w)/2:y=(h-text_h)/2:enable='between(mod(t,300),60,65)'[v2];"
                    f"[v2]drawtext=text='{WATERMARK_TEXT}'{font_option}:fontcolor=red:fontsize={fontsize}:borderw=3:bordercolor=yellow:"
                    f"x=(w-text_w)/2:y=h-text_h-10:enable='gte(mod(t,300),65)'[vbase]"
                )
                vout_label = "[vbase]"

            if apply_ol:
                cmd += ["-i", overlay_file]
                try:
                    ov_dur = float(subprocess.check_output([
                        "ffprobe", "-v", "error",
                        "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1",
                        overlay_file
                    ]).decode().strip())
                    ov_dur = min(ov_dur, max_overlay_limit)
                except:
                    ov_dur = max_overlay_limit

                has_audio = False
                try:
                    audio_check = subprocess.check_output([
                        "ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=codec_type",
                        "-of", "csv=s=x:p=0", overlay_file
                    ]).decode().strip()
                    if "audio" in audio_check:
                        has_audio = True
                except:
                    pass

                ol_filter = (
                    f";[1:v]scale={main_w}:{main_h}:"
                    f"force_original_aspect_ratio=decrease,"
                    f"pad={main_w}:{main_h}:(ow-iw)/2:(oh-ih)/2,"
                    f"setsar=1[ol];"
                    f"{vout_label}[ol]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,{ov_dur})'[vout]"
                )
                if apply_wm:
                    filter_complex += ol_filter
                else:
                    filter_complex = ol_filter.lstrip(";")

                vout_label = "[vout]"
                if has_audio:
                    aout_label = "[aout]"
                    filter_complex += (
                        f";[0:a]atrim=start={ov_dur},asetpts=PTS-STARTPTS[a0];"
                        f"[1:a]atrim=0:{ov_dur},asetpts=PTS-STARTPTS[a1];"
                        f"[a1][a0]concat=n=2:v=0:a=1[aout]"
                    )
                else:
                    aout_label = "0:a?"

            cmd += [
                "-filter_complex", filter_complex,
                "-map", vout_label, "-map", aout_label,
                "-pix_fmt", "yuv420p", "-map_metadata", "0", "-movflags", "+faststart"
            ]

            # انکود مستقیم با CPU؛ بدون جست‌وجوی GPU و بدون تلاش ناموفق NVENC
            cmd += [
                "-c:v", "libx264", "-preset", "ultrafast",
                "-b:v", target_bitrate, "-maxrate", maxrate, "-bufsize", bufsize,
                "-c:a", "aac", "-b:a", "192k", final_out
            ]

            if cancel_flag: return None

            print("EXEC:", " ".join(cmd))
            start_time = time.time()
            last_pct = -1

            p = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, bufsize=1
            )
            try:
                for line in p.stdout:
                    if cancel_flag:
                        p.kill()
                        break
                    print(line.rstrip())
                    if total_duration > 0 and progress_callback and "time=" in line:
                        try:
                            time_match = re.search(r'time=(\d+):(\d+):(\d+\.\d+)', line)
                            if time_match:
                                h = int(time_match.group(1))
                                m = int(time_match.group(2))
                                s = float(time_match.group(3))
                                current_sec = h * 3600 + m * 60 + s
                                pct = min(int(current_sec * 100 / total_duration), 99)
                                if pct - last_pct >= 10:
                                    last_pct = pct
                                    elapsed = time.time() - start_time
                                    if pct > 0:
                                        total_est = elapsed * 100 / pct
                                        remaining = total_est - elapsed
                                        mins = int(remaining // 60)
                                        secs = int(remaining % 60)
                                        eta_str = f"{mins}:{secs:02d}"
                                    else:
                                        eta_str = "..."
                                    progress_callback(pct, eta_str)
                        except:
                            pass
            except Exception as e:
                print("run() read error:", e)

            p.wait()

            # چون فقط libx264 اجرا می‌شود، هر خطای FFmpeg مستقیماً گزارش می‌شود.
            if p.returncode != 0:
                print(f"❌ پردازش ویدیو ناموفق بود (کد {p.returncode}).")
                return None
            if not os.path.exists(final_out): return None
            if cancel_flag: return None

            if os.path.exists(final_out) and is_valid_video(final_out):
                in_mb  = os.path.getsize(fixed_path) / 1024 / 1024
                out_mb = os.path.getsize(final_out)  / 1024 / 1024
                print(f"✅ فایل نهایی آماده | ورودی: {in_mb:.1f} MB → خروجی: {out_mb:.1f} MB")
                return final_out
            return None

        # ================== Upload to Pixeldrain ==================
        async def upload_to_pixeldrain(file_path, status_msg, retries=3):
            global cancel_flag
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            file_size_mb = file_size / (1024 * 1024)
            for attempt in range(retries):
                if cancel_flag: return None
                try:
                    await safe_edit(status_msg, f"🚀 آپلود به Pixeldrain... ({attempt+1}/{retries})")
                    uploaded = 0
                    last_pct = -1
                    async def file_sender():
                        nonlocal uploaded, last_pct
                        chunk_size = 1024 * 1024
                        with open(file_path, "rb") as f:
                            while True:
                                if cancel_flag: break
                                chunk = f.read(chunk_size)
                                if not chunk: break
                                uploaded += len(chunk)
                                pct = int(uploaded * 100 / file_size)
                                if pct - last_pct >= 5 or pct == 100:
                                    last_pct = pct
                                    filled = int(pct / 5)
                                    bar = "█" * filled + "░" * (20 - filled)
                                    asyncio.create_task(safe_edit(
                                        status_msg,
                                        f"⬆️ آپلود به Pixeldrain...\n[{bar}] {pct}%\n📦 {file_size_mb:.1f} MB"
                                    ))
                                yield chunk
                    timeout = aiohttp.ClientTimeout(total=7200)
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.put(
                            f"https://pixeldrain.com/api/file/{file_name}",
                            data=file_sender(), headers=auth_header
                        ) as response:
                            if response.status not in [200, 201]: continue
                            try: data = await response.json()
                            except: continue
                            if "id" not in data: continue
                            file_id = data["id"]
                            viewer_link   = f"https://pixeldrain.com/u/{file_id}"
                            direct_link   = f"https://pixeldrain.com/api/file/{file_id}"
                            download_link = f"https://pixeldrain.com/api/file/{file_id}?download"
                            await safe_edit(status_msg,
                                "✅ آپلود Pixeldrain موفق!\n\n"
                                f"🌐 مشاهده:\n{viewer_link}\n\n"
                                f"📥 مستقیم:\n{direct_link}\n\n"
                                f"⬇️ دانلود:\n{download_link}"
                            )
                            return {"viewer": viewer_link, "direct": direct_link, "download": download_link}
                except Exception as e:
                    print(f"PIXELDRAIN RETRY {attempt+1} ERROR:", e)
                await asyncio.sleep(5)
            await safe_edit(status_msg, "❌ آپلود Pixeldrain شکست خورد.")
            return None

        # =====================================================================================
        #  لایهٔ دانلود — بازنویسی‌شده (نسخهٔ ۲)
        #  ------------------------------------------------------------------------------------
        #  سه باگ اصلی که باعث می‌شد لینک‌های CDN (مثل pvvstream/ukdevilz) ۴۰۳ بگیرند:
        #   ۱) هدر Referer اشتباه: برای لینک فایل، Referer روی دامنهٔ خودِ CDN ست می‌شد
        #      (https://pvvstream.pro/) و هات‌لینک‌پروتکشن CDN دقیقاً همین را ۴۰۳ می‌کند.
        #   ۲) لینک‌های امضاشده (secure=...) در HTML با \\u0026 نوشته شده‌اند؛ رجکس قبلی
        #      آن‌ها را نصفه برمی‌داشت (vid_720p.mp4?rs=720000) و توکن گم می‌شد → ۴۰۳.
        #   ۳) دانلود تک‌اتصالی و بدون تأیید حجم: فایل ۹۷۰ مگی نصفه دانلود می‌شد،
        #      ffprobe خطا می‌داد و کل نتیجه دور ریخته می‌شد.
        #  حالا: probe با ماتریس هدر/بک‌اند → دانلود تکه‌ای چنداتصاله با Range →
        #  تمدید خودکار توکن منقضی → تأیید حجم دقیق → remux/ ffprobe ایمن.
        # =====================================================================================

        UA_CHROME = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"

        DIRECT_CONNECTIONS = 12                  # تعداد اتصال هم‌زمان برای فایل مستقیم
        DIRECT_SEGMENT_SIZE = 8 * 1024 * 1024    # اندازهٔ هر تکه در صف دانلود
        _PROBE_CACHE = {}
        _CURL_CFFI_OK = None

        _TEXT_ESCAPES = (
            ("\\u0026", "&"), ("\\u002F", "/"), ("\\u002f", "/"), ("\\/", "/"),
            ("\\u003D", "="), ("\\u003d", "="),
            ("&amp;", "&"), ("&#38;", "&"), ("&#x26;", "&"), ("&quot;", '"'), ("&#x2F;", "/"),
        )


        def _unescape_text(text):
            """\\u0026 / &amp; / \\/ را باز می‌کند؛ بدون این کار لینک‌های امضاشدهٔ CDN ناقص می‌شوند."""
            if not text:
                return ""
            out = text
            for a, b in _TEXT_ESCAPES:
                out = out.replace(a, b)
            return out


        def _normalize_url(url):
            u = _unescape_text((url or "").strip().strip("'\"").strip())
            return u.rstrip(".,;")


        _MEDIA_EXT_RE = re.compile(
            r"\.(mp4|m4v|mkv|webm|mov|flv|f4v|3gp|ts|m3u8|m3u|mpd|mp3|m4a|aac|ogg|zip)$", re.I
        )


        def _looks_like_media(url):
            try:
                p = urlparse(_normalize_url(url))
            except Exception:
                return False
            path = (p.path or "").rstrip("/")
            if _MEDIA_EXT_RE.search(path):
                return True
            q = (p.query or "").lower()
            return any(k in q for k in ("download=true", "download=1", "dl=1", "filename="))


        def _looks_like_hls(url):
            low = _normalize_url(url).lower()
            return ".m3u8" in low or ".m3u" in low or ".mpd" in low


        def _origin_of(url):
            try:
                p = urlparse(url)
            except Exception:
                return None
            if not p.scheme or not p.hostname:
                return None
            return f"{p.scheme}://{p.hostname}"


        # ================== هدر هوشمند ==================
        def _get_smart_headers(url, referer=None, for_media=None):
            """هدر مناسب همان میزبان.

            قاعدهٔ طلایی: برای «فایل/CDN» هرگز Referer دامنهٔ خودِ CDN را نفرست؛
            یا باید Referer صفحهٔ میزبان (page_referer) باشد یا هیچ Referer ای.
            """
            url = _normalize_url(url)
            lower = (url or "").lower()
            ua = UA_CHROME
            if for_media is None:
                for_media = _looks_like_media(url)

            if "phncdn.com" in lower or "pornhub" in lower:
                return {
                    "User-Agent": ua, "Referer": "https://www.pornhub.com/",
                    "Origin": "https://www.pornhub.com", "Accept": "*/*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Cookie": "accessAgeDisclaimer=1; platform=pc; ua=1; bs=1",
                }
            if "ahcdn.com" in lower or "beeg" in lower:
                return {"User-Agent": ua, "Referer": "https://beeg.com/", "Origin": "https://beeg.com", "Accept": "*/*"}
            if "xvideos" in lower or "xvcdn" in lower:
                return {"User-Agent": ua, "Referer": "https://www.xvideos.com/", "Origin": "https://www.xvideos.com", "Accept": "*/*"}
            if "xhamster" in lower or "xhcdn" in lower:
                return {"User-Agent": ua, "Referer": "https://xhamster.com/", "Origin": "https://xhamster.com", "Accept": "*/*"}
            if "spankbang" in lower:
                return {"User-Agent": ua, "Referer": "https://spankbang.com/", "Origin": "https://spankbang.com", "Accept": "*/*"}
            if "eporner" in lower:
                return {"User-Agent": ua, "Referer": "https://www.eporner.com/", "Origin": "https://www.eporner.com", "Accept": "*/*"}
            if "dood" in lower or "do0od" in lower:
                return {"User-Agent": ua, "Referer": "https://doodstream.com/", "Accept": "*/*"}
            if "streamtape" in lower:
                return {"User-Agent": ua, "Referer": "https://streamtape.com/", "Accept": "*/*"}

            headers = {"User-Agent": ua, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}
            if referer:
                headers["Referer"] = _normalize_url(referer)
                org = _origin_of(referer)
                if org:
                    headers["Origin"] = org
            elif not for_media:
                # درخواست یک «صفحهٔ وب» است؛ ارجاع به دامنهٔ خودش طبیعی است.
                org = _origin_of(url)
                if org:
                    headers["Referer"] = org + "/"
                    headers["Origin"] = org
                    headers["Cookie"] = "age_verified=1; ageverified=1; agecheck=1; disclaimer=1; adult=1; over18=1"
            return headers


        # ================== لایهٔ دسترسی (requests / curl_cffi) ==================
        def _has_curl_cffi():
            global _CURL_CFFI_OK
            if _CURL_CFFI_OK is None:
                try:
                    from curl_cffi import requests as _creq  # noqa: F401
                    _CURL_CFFI_OK = True
                except Exception:
                    _CURL_CFFI_OK = False
            return _CURL_CFFI_OK


        def _open_stream(url, headers, backend="requests", timeout=(20, 60)):
            """response استریمی. backend=curl_cffi اثر انگشت TLS کروم را می‌فرستد (ضد Cloudflare)."""
            if backend == "curl_cffi" and _has_curl_cffi():
                from curl_cffi import requests as creq
                return creq.get(url, headers=headers, impersonate="chrome", timeout=timeout,
                                stream=True, allow_redirects=True)
            return requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)


        _MEDIA_CT_HINTS = (
            "video/", "audio/", "application/octet-stream", "application/mp4", "binary/octet-stream",
            "mpegurl", "dash+xml", "matroska", "vnd.apple",
        )


        def _is_media_ct(ct, cd=""):
            ct = (ct or "").lower()
            cd = (cd or "").lower()
            return any(h in ct for h in _MEDIA_CT_HINTS) or "attachment" in cd


        def _probe_media_access(url, page_referer=None):
            """با درخواست ۲ بایتی (Range) کشف می‌کند کدام هدر/بک‌اند جواب می‌دهد.

            خروجی: dict(backend, headers, total, ranges, content_type, kind) یا None
            نکته: هیچ‌وقت بدنهٔ فایل خوانده نمی‌شود؛ پس حتی برای فایل ۱ گیگی هم فوری است.
            """
            url = _normalize_url(url)
            try:
                host = (urlparse(url).hostname or "").lower()
            except Exception:
                host = ""
            try:
                parsed = urlparse(url)
                path_key = (parsed.netloc or "") + (parsed.path or "")
            except Exception:
                path_key = host
            cache_key = (path_key, (page_referer or "")[:120], _looks_like_hls(url))
            if cache_key in _PROBE_CACHE:
                info = dict(_PROBE_CACHE[cache_key])
                info["url"] = url
                return info

            known = any(k in host for k in ("phncdn", "ahcdn", "xhcdn", "xvcdn", "spankbang",
                                            "eporner", "dood", "do0od", "streamtape", "beeg"))
            profiles = []
            if known:
                profiles.append(("site", _get_smart_headers(url)))
            if page_referer:
                profiles.append(("page", _get_smart_headers(url, referer=page_referer, for_media=True)))
            profiles.append(("clean", _get_smart_headers(url, for_media=True)))

            seen_sig, uniq_profiles = set(), []
            for name, h in profiles:
                sig = tuple(sorted(h.items()))
                if sig in seen_sig:
                    continue
                seen_sig.add(sig)
                uniq_profiles.append((name, h))

            backends = ["requests"] + (["curl_cffi"] if _has_curl_cffi() else [])
            tried = []
            for backend in backends:
                for name, base_headers in uniq_profiles:
                    headers = dict(base_headers)
                    headers["Range"] = "bytes=0-1"
                    resp = None
                    try:
                        resp = _open_stream(url, headers, backend, timeout=(15, 25))
                        status = resp.status_code
                        ct = resp.headers.get("content-type") or ""
                        cd = resp.headers.get("content-disposition") or ""
                        content_range = resp.headers.get("content-range") or ""
                        total, ranges = 0, False
                        m = re.search(r"/\s*(\d+)\s*$", content_range)
                        if m:
                            total = int(m.group(1))
                            ranges = True
                        elif status == 206:
                            ranges = True
                        if not total and status == 200:
                            try:
                                total = int(resp.headers.get("content-length") or 0)
                            except Exception:
                                total = 0

                        if status == 416:  # فایل کوچک‌تر از بازهٔ درخواستی
                            try:
                                resp.close()
                            except Exception:
                                pass
                            headers.pop("Range", None)
                            resp = _open_stream(url, headers, backend, timeout=(15, 25))
                            status = resp.status_code
                            ct = resp.headers.get("content-type") or ""
                            cd = resp.headers.get("content-disposition") or ""
                            ranges = False
                            try:
                                total = int(resp.headers.get("content-length") or 0)
                            except Exception:
                                total = 0

                        is_hls = _looks_like_hls(url)
                        # صفحهٔ HTML را هرگز «فایل» حساب نکن (وگرنه اسکرپ/دانلود قاطی می‌شود)
                        looks_like_file = ranges and not ct.startswith("text/html")
                        ok = status in (200, 206) and (_is_media_ct(ct, cd) or is_hls or looks_like_file)
                        print(
                            f"🔎 probe[{backend}/{name}]: {status} | {(ct or '?').split(';')[0]} | "
                            f"size={total or '?'} | range={'yes' if ranges else 'no'}"
                        )
                        if ok:
                            headers.pop("Range", None)
                            headers.pop("range", None)
                            info = {
                                "backend": backend,
                                "headers": headers,
                                "total": total,
                                "ranges": ranges,
                                "content_type": ct,
                                "kind": "hls" if is_hls else "file",
                                "profile": name,
                            }
                            if not is_hls:
                                _PROBE_CACHE[cache_key] = dict(info)
                            return info
                        tried.append(f"{backend}/{name}:{status}")
                    except Exception as e:
                        tried.append(f"{backend}/{name}:ERR {type(e).__name__}")
                    finally:
                        if resp is not None:
                            try:
                                resp.close()
                            except Exception:
                                pass

            print("❌ probe: هیچ پروفایل هدر/بک‌اندی جواب نداد →", "، ".join(tried) or "?")
            return None


        # ================== دانلود تکه‌ای چنداتصاله ==================
        def _download_segmented_sync(url, filepath, headers, backend, total, ranges,
                                    status_msg, loop, resign=None, connections=None):
            """دانلود فایل با Range در چند اتصال هم‌زمان + ادامه از محل قطع + تمدید توکن.

            - نوشتن با os.pwrite (نوشتن در آفست مشخص) → امن برای چند ترد، بدون قفل.
            - اگر سرور Range نداشت، تک‌اتصالی و ترتیبی دانلود می‌کند.
            - اگر وسط کار ۴۰۱/۴۰۳/۴۱۰ گرفت (توکن امضاشده منقضی شد) با resign لینک تازه می‌گیرد.
            """
            import threading
            import queue as _queue

            url = _normalize_url(url)
            if not ranges or total <= 0:
                connections = 1
            else:
                try:
                    connections = max(1, min(int(connections or DIRECT_CONNECTIONS), 16))
                except Exception:
                    connections = DIRECT_CONNECTIONS

            state = {
                "done": 0,
                "url": url,
                "stop": False,
                "error": None,
                "last_edit": 0.0,
                "started": time.time(),
            }
            lock = threading.Lock()

            os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
            fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
            try:
                if total > 0:
                    try:
                        os.ftruncate(fd, total)
                    except Exception:
                        pass

                tasks = _queue.Queue()
                if total > 0:
                    if ranges:
                        offset = 0
                        while offset < total:
                            end = min(offset + DIRECT_SEGMENT_SIZE, total) - 1
                            tasks.put((offset, end))
                            offset = end + 1
                    else:
                        tasks.put((0, total - 1))

                def _worker():
                    while True:
                        if state["stop"] or cancel_flag:
                            return
                        try:
                            seg_start, seg_end = tasks.get_nowait()
                        except _queue.Empty:
                            return
                        pos = seg_start
                        attempts = 0
                        while pos <= seg_end:
                            if state["stop"] or cancel_flag:
                                return
                            current_url = state["url"]
                            req_headers = dict(headers)
                            if ranges:
                                req_headers["Range"] = f"bytes={pos}-{seg_end}"
                            resp = None
                            try:
                                resp = _open_stream(current_url, req_headers, backend, timeout=(20, 60))
                                code = resp.status_code

                                if code in (401, 403, 410):
                                    try:
                                        resp.close()
                                    except Exception:
                                        pass
                                    resp = None
                                    new_url = None
                                    if resign is not None and attempts < 3:
                                        try:
                                            new_url = resign(current_url)
                                        except Exception as _exc:
                                            print("⚠️ تمدید لینک ناموفق:", _exc)
                                    if new_url and _normalize_url(new_url) != current_url:
                                        with lock:
                                            state["url"] = _normalize_url(new_url)
                                        print("🔗 توکن لینک تمدید شد → ادامهٔ دانلود")
                                        attempts += 1
                                        continue
                                    state["error"] = f"HTTP {code} (CDN اجازه نداد / لینک منقضی)"
                                    state["stop"] = True
                                    return

                                if code not in (200, 206):
                                    try:
                                        resp.close()
                                    except Exception:
                                        pass
                                    resp = None
                                    attempts += 1
                                    if attempts >= 5:
                                        state["error"] = f"HTTP {code}"
                                        state["stop"] = True
                                        return
                                    time.sleep(min(2 * attempts, 8))
                                    continue

                                # سرور Range را نادیده گرفته و کل فایل را فرستاده؛ نوشتن آن در آفست
                                # غلط فایل را خراب می‌کند → فقط برای تکهٔ اول (آفست ۰) مجاز است.
                                if ranges and code == 200 and pos != 0:
                                    try:
                                        resp.close()
                                    except Exception:
                                        pass
                                    resp = None
                                    attempts += 1
                                    if attempts >= 3:
                                        state["error"] = "سرور Range را نادیده گرفت"
                                        state["stop"] = True
                                        return
                                    time.sleep(1)
                                    continue

                                got = 0
                                for chunk in resp.iter_content(chunk_size=262144):
                                    if not chunk:
                                        continue
                                    if state["stop"] or cancel_flag:
                                        break
                                    if ranges and pos + len(chunk) - 1 > seg_end:
                                        chunk = chunk[: seg_end - pos + 1]
                                    os.pwrite(fd, chunk, pos)
                                    pos += len(chunk)
                                    got += len(chunk)
                                    with lock:
                                        state["done"] += len(chunk)
                                try:
                                    resp.close()
                                except Exception:
                                    pass
                                resp = None

                                if got == 0 and pos <= seg_end and not ranges:
                                    attempts += 1
                                    if attempts >= 5:
                                        state["error"] = "هیچ داده‌ای دریافت نشد"
                                        state["stop"] = True
                                        return
                                    time.sleep(1)
                            except Exception as e:
                                if resp is not None:
                                    try:
                                        resp.close()
                                    except Exception:
                                        pass
                                attempts += 1
                                if attempts >= 5:
                                    state["error"] = f"{type(e).__name__}: {e}"
                                    state["stop"] = True
                                    return
                                time.sleep(min(2 * attempts, 8))

                threads = [threading.Thread(target=_worker, daemon=True) for _ in range(connections)]
                for t in threads:
                    t.start()

                while True:
                    if cancel_flag:
                        state["stop"] = True
                    alive = any(t.is_alive() for t in threads)
                    now = time.time()
                    if now - state["last_edit"] >= 2 or (not alive):
                        state["last_edit"] = now
                        done = state["done"]
                        elapsed = max(0.001, now - state["started"])
                        speed = done / 1048576 / elapsed
                        if total > 0:
                            pct = min(100, int(done * 100 / total))
                            filled = min(20, pct // 5)
                            bar = "█" * filled + "░" * (20 - filled)
                            remaining = max(0, total - done) / 1048576
                            eta = int(remaining / speed) if speed > 0.01 else 0
                            text = (
                                f"⚡ دانلود تکه‌ای ({connections} اتصال)\n[{bar}] {pct}%\n"
                                f"📦 {done / 1048576:.1f}/{total / 1048576:.1f} MB | "
                                f"{speed:.1f} MB/s | {eta // 60}:{eta % 60:02d}"
                            )
                        else:
                            text = f"⬇️ دانلود مستقیم...\n📦 {done / 1048576:.1f} MB | {speed:.1f} MB/s"
                        try:
                            asyncio.run_coroutine_threadsafe(safe_edit(status_msg, text), loop)
                        except Exception:
                            pass
                    if not alive:
                        break
                    time.sleep(0.5)
            finally:
                try:
                    os.close(fd)
                except Exception:
                    pass

            if cancel_flag or state["stop"]:
                raise IOError(state["error"] or "دانلود متوقف شد")

            final_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
            if total > 0 and final_size != total:
                # فایل sparse ممکن است اندازهٔ ظاهری درست داشته باشد ولی داده کم داشته باشد
                if state["done"] != total:
                    raise IOError(f"فایل ناقص است: {state['done']}/{total} بایت")
            return True


        async def _download_from_access(url, filepath, status_msg, access, resign=None, connections=None):
            """دانلود با اطلاعاتی که probe پیدا کرده (هدر درست + بک‌اند درست)."""
            url = _normalize_url(url)
            if not access:
                return None
            if access.get("kind") == "hls":
                print("ℹ️ محتوا HLS است؛ دانلود تکه‌ای HTTP انجام نشد")
                return None

            backend = access.get("backend") or "requests"
            headers = dict(access.get("headers") or {})
            total = int(access.get("total") or 0)
            ranges = bool(access.get("ranges"))

            if total > 0:
                await safe_edit(
                    status_msg,
                    f"⚡ دانلود تکه‌ای ({DIRECT_CONNECTIONS} اتصال) — {total / 1048576:.1f} MB"
                    if ranges else f"⬇️ دانلود مستقیم — {total / 1048576:.1f} MB",
                )
            else:
                await safe_edit(status_msg, "⬇️ دانلود مستقیم (حجم نامشخص)...")

            loop = asyncio.get_event_loop()
            try:
                await asyncio.to_thread(
                    _download_segmented_sync, url, filepath, headers, backend, total,
                    ranges, status_msg, loop, resign, connections,
                )
            except Exception as e:
                print(f"❌ دانلود مستقیم ناموفق: {e}")
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except OSError:
                    pass
                return None

            if cancel_flag:
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                return None

            if os.path.isfile(filepath) and os.path.getsize(filepath) > 100_000:
                print(f"✅ دانلود کامل شد: {os.path.getsize(filepath) / 1048576:.1f} MB")
                return filepath
            print("❌ فایل خروجی خیلی کوچک/ناموجود است")
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except OSError:
                pass
            return None


        def _resign_media_url_sync(page_url, old_url, quality):
            """لینک امضاشده منقضی شده → نسخهٔ تازه را از همان صفحه می‌گیرد (همان مسیر/کیفیت)."""
            if not page_url:
                return None
            try:
                html = _http_get(page_url)
            except Exception as e:
                print("⚠️ تمدید لینک:", e)
                return None
            candidates = _media_candidates_from_html(html, page_url, page_url)
            if not candidates:
                return None
            old_path = urlparse(old_url).path
            same_path = [c for c in candidates if urlparse(c["url"]).path == old_path]
            if same_path:
                return same_path[0]["url"]
            best = _pick_best_candidate(candidates, quality)
            return best["url"] if best else None


        # ================== Chromium sniff + session capture ==================
        _CHROMIUM_SESSION_HEADERS = {}
        _SAFE_BROWSER_HEADERS = (
            "accept", "accept-language", "referer", "origin", "cookie", "user-agent",
            "sec-fetch-dest", "sec-fetch-mode", "sec-fetch-site",
            "sec-ch-ua", "sec-ch-ua-mobile", "sec-ch-ua-platform",
        )
        _SKIP_BROWSER_HEADERS = {"range", "host", "connection", "content-length", "accept-encoding", "priority", "te"}


        def _filter_browser_headers(raw):
            """هدرهای ضبط‌شدهٔ مرورگر را به یک مجموعهٔ امن/قابل استفاده تبدیل می‌کند."""
            out = {}
            for key, value in (raw or {}).items():
                if not key or value is None:
                    continue
                k = str(key).strip().lower()
                if k in _SKIP_BROWSER_HEADERS:
                    continue
                if k in _SAFE_BROWSER_HEADERS or k.startswith("sec-"):
                    out[key if key != k else k] = str(value)
            # کلیدها را استاندارد کن
            return {("-".join(part.capitalize() for part in k.split("-")) if "-" in k else k.capitalize()): v
                    for k, v in out.items()}


        async def download_with_chromium_enhanced(url, status_msg, quality=None):
            global _CHROMIUM_SESSION_HEADERS
            url = _normalize_url(url)
            video_url = None
            exts = (".m3u8", ".mpd", ".mp4", ".mkv", ".webm", ".flv", ".mov", ".m4v", ".m3u")
            REAL_UA = UA_CHROME
            captured_headers = {}
            try:
                await safe_edit(status_msg, "🌐 Chromium: باز کردن صفحه و پیدا کردن لینک ویدیو...")
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-blink-features=AutomationControlled",
                              "--disable-dev-shm-usage", "--ignore-certificate-errors"],
                    )
                    context = await browser.new_context(
                        user_agent=REAL_UA, viewport={"width": 1920, "height": 1080},
                        locale="en-US", extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                    )
                    page = await context.new_page()
                    found_urls = []

                    def _is_thumb(low):
                        return any(x in low for x in ("/vts:", "rs:fit:", "/thumb", "/thumbnail",
                                                      "preview", "poster", "sprite", "/ads", "splash"))

                    async def handle_request(req):
                        try:
                            raw = _normalize_url(req.url)
                            low = raw.lower()
                            if (any(e in low for e in exts) and raw not in found_urls
                                    and "seg-" not in low and not _is_thumb(low)):
                                found_urls.append(raw)
                                # هدرهای واقعی همان درخواست را نگه می‌داریم: CDN دقیقاً همین‌ها را قبول کرد
                                captured_headers[raw] = dict(req.headers)
                                print(f"🎯 Chromium Request: {raw[:160]}")
                        except Exception:
                            pass

                    async def handle_response(resp):
                        try:
                            raw = _normalize_url(resp.url)
                            low = raw.lower()
                            h = await resp.all_headers()
                            ct = (h.get("content-type") or "").lower()
                            if ((any(e in low for e in exts) or "video" in ct)
                                    and raw not in found_urls and "seg-" not in low and not _is_thumb(low)):
                                found_urls.append(raw)
                                print(f"🎯 Chromium Response: {raw[:160]}")
                        except Exception:
                            pass

                    page.on("request", handle_request)
                    page.on("response", handle_response)
                    try:
                        await page.goto(url, timeout=90000, wait_until="domcontentloaded")
                    except Exception as e:
                        print(f"⚠️ Chromium page.goto: {e}")
                    await asyncio.sleep(8)
                    try:
                        await page.evaluate(
                            """() => { const v=document.querySelector('video'); if(v){v.muted=true;v.play().catch(()=>{});} }"""
                        )
                        for sel in ["button.play", ".play-btn", ".play-button", ".plyr__control--overlaid",
                                    ".video-player__play", ".vjs-big-play-button"]:
                            try:
                                btn = await page.query_selector(sel)
                                if btn:
                                    await btn.click(force=True)
                                    break
                            except Exception:
                                pass
                    except Exception:
                        pass
                    for _ in range(8):
                        if found_urls:
                            break
                        await asyncio.sleep(5)

                    cookies = await context.cookies()
                    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
                    _CHROMIUM_SESSION_HEADERS = {
                        "User-Agent": REAL_UA, "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9",
                        "Referer": url,
                    }
                    if cookie_str:
                        _CHROMIUM_SESSION_HEADERS["Cookie"] = cookie_str

                    def score(u):
                        low = u.lower()
                        for q, marks in [(1080, ("1080", "1920")), (720, ("720", "1280")),
                                         (480, ("480", "854")), (360, ("360", "640"))]:
                            if any(x in low for x in marks):
                                return q
                        m = re.search(r"(\d{3,4})p", low)
                        return int(m.group(1)) if m else 0

                    candidates = [u for u in found_urls if any(e in u.lower() for e in exts)
                                  and "seg-" not in u.lower()]
                    if candidates:
                        q = int(DOWNLOAD_QUALITY if quality is None else quality)
                        ranked = sorted((score(u), u) for u in candidates)
                        below = [item for item in ranked if 0 < item[0] <= q]
                        unknown = [item for item in ranked if item[0] == 0]
                        hls = [item for item in below + unknown if ".m3u8" in item[1].lower()]
                        pool = hls or below or unknown
                        video_url = pool[-1][1] if pool else None
                        print(f"🎯 بهترین لینک Chromium: {video_url}")

                        if video_url and captured_headers.get(video_url):
                            browser_headers = _filter_browser_headers(captured_headers[video_url])
                            if browser_headers:
                                _CHROMIUM_SESSION_HEADERS.update(browser_headers)
                                print("📋 هدرهای مرورگر برای همان لینک ذخیره شد")
                        if video_url:
                            _CHROMIUM_SESSION_HEADERS.setdefault("Referer", url)
                    await browser.close()
                return video_url
            except Exception as e:
                print(f"❌ خطا Chromium: {e}")
                return None


        async def _chromium_api_download(url, filepath, status_msg, headers):
            """آخرین راه: دانلود با استک شبکهٔ خودِ Playwright (هدر/کوکی/اثر انگشت TLS همان مرورگر).

            برای فایل‌های بزرگ تکه‌تکه (Range) می‌گیرد تا RAM پر نشود.
            """
            REAL_UA = UA_CHROME
            block = 16 * 1024 * 1024
            try:
                await safe_edit(status_msg, "🌐 Chromium API → دانلود فایل...")
                async with async_playwright() as p:
                    browser = await p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage", "--ignore-certificate-errors"],
                    )
                    try:
                        context = await browser.new_context(
                            user_agent=REAL_UA, locale="en-US",
                            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                        )
                        api = context.request

                        total = 0
                        head = None
                        try:
                            head = await api.head(url, headers=headers, timeout=120000,
                                                  fail_on_status_code=False)
                        except Exception as e:
                            print("⚠️ Chromium API HEAD:", e)
                        if head is not None and head.status < 400:
                            try:
                                total = int(head.headers.get("content-length") or 0)
                            except Exception:
                                total = 0

                        probe = await api.get(url, headers={**headers, "Range": "bytes=0-0"},
                                              timeout=120000, fail_on_status_code=False)
                        if probe.status not in (200, 206):
                            print(f"❌ Chromium API: HTTP {probe.status}")
                            return None
                        if not total:
                            cr = probe.headers.get("content-range") or ""
                            m = re.search(r"/\s*(\d+)\s*$", cr)
                            if m:
                                total = int(m.group(1))
                            elif probe.status == 200:
                                try:
                                    total = int(probe.headers.get("content-length") or 0)
                                except Exception:
                                    total = 0

                        with open(filepath, "wb") as f:
                            if total <= 0:
                                f.write(await probe.body())      # حجم نامشخص: ناچار یک‌جا
                            else:
                                offset = 0
                                while offset < total:
                                    if cancel_flag:
                                        break
                                    end = min(offset + block, total) - 1
                                    resp = await api.get(
                                        url, headers={**headers, "Range": f"bytes={offset}-{end}"},
                                        timeout=300000, fail_on_status_code=False,
                                    )
                                    if resp.status not in (200, 206):
                                        print(f"❌ Chromium API: HTTP {resp.status} در آفست {offset}")
                                        raise IOError(f"HTTP {resp.status}")
                                    data = await resp.body()
                                    if not data:
                                        break
                                    f.write(data)
                                    offset += len(data)
                                    await safe_edit(
                                        status_msg,
                                        f"🌐 Chromium API... 🧩 {offset / 1048576:.1f}/{total / 1048576:.1f} MB",
                                    )
                    finally:
                        await browser.close()

                size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
                print(f"✅ Chromium API download: {size / 1048576:.1f} MB")
                complete = (size == total) if total else True
                if size > 100_000 and complete:
                    return filepath
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                return None
            except Exception as e:
                print(f"❌ Chromium API download error: {e}")
                try:
                    if os.path.exists(filepath):
                        os.remove(filepath)
                except OSError:
                    pass
                return None


        async def _chromium_session_download(url, filepath, status_msg, quality=None):
            """دانلود واقعی لینکی که Chromium پیدا کرد، با همان نشست/هدرهای مرورگر."""
            url = _normalize_url(url)
            headers = dict(_CHROMIUM_SESSION_HEADERS or {})
            page_referer = headers.get("Referer")
            quality = int(DOWNLOAD_QUALITY if quality is None else quality)

            if _looks_like_hls(url):
                await safe_edit(status_msg, "🌐 استریم مرورگر → yt-dlp با کیفیت تنظیم‌شده...")
                stream_dir = tempfile.mkdtemp(prefix="stream_", dir=os.path.dirname(filepath) or ".")
                try:
                    result = await _ytdlp_subprocess(url, stream_dir, status_msg, headers,
                                                     timeout_sec=900, quality=quality)
                    if result:
                        shutil.move(result, filepath)
                        return filepath
                    return None
                finally:
                    shutil.rmtree(stream_dir, ignore_errors=True)

            await safe_edit(status_msg, "⬇️ دانلود با نشست Chromium (هدر واقعی مرورگر)...")
            access = await asyncio.to_thread(_probe_media_access, url, page_referer)
            if access and access.get("kind") != "hls":
                resign = None
                if page_referer:
                    resign = lambda old: _resign_media_url_sync(page_referer, old, quality)
                result = await _download_from_access(url, filepath, status_msg, access, resign=resign)
                if result:
                    return result

            if cancel_flag:
                return None
            return await _chromium_api_download(url, filepath, status_msg, headers)


        # ================== yt-dlp ==================
        async def _ytdlp_subprocess(url, output_dir, status_msg, headers, timeout_sec=600,
                                    extra_args=None, quality=None):
            """yt-dlp به‌صورت زیرفرایند، با محدودیت کیفیت، پیشرفت زنده و لغوپذیری.

            تغییر مهم نسبت به نسخهٔ قبل: دیگر دانلودر خارجی aria2 اجباری نیست (اثر انگشت TLS
            آن شناسایی و ۴۰۳ می‌شود) و هدر Referer فقط وقتی معتبر است فرستاده می‌شود.
            """
            global cancel_flag
            from http.cookies import SimpleCookie
            from http.cookiejar import Cookie, MozillaCookieJar

            url = _normalize_url(url)
            q = int(DOWNLOAD_QUALITY if quality is None else quality)
            out_tmpl = os.path.join(output_dir, "video.%(ext)s")
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "--no-playlist",
                "--retries", "10", "--fragment-retries", "10", "--file-access-retries", "3",
                "--socket-timeout", "30",
                "--concurrent-fragments", str(HLS_CONCURRENT_FRAGMENTS),
                "--skip-unavailable-fragments",
                "--retry-sleep", "fragment:exp=1:8",
                "--merge-output-format", "mp4", "--remux-video", "mp4",
                "--format", _download_format_selector(q),
                "--output", out_tmpl, "--newline", "--progress", "--progress-delta", "1",
                "--print", "before_dl:SELECTED: %(format_id)s | %(height)sp | %(protocol)s",
                "--print", "after_move:FINAL_FILE: %(filepath)s",
            ]
            if extra_args:
                cmd.extend(extra_args)

            cookie_path = None
            proc = None
            error_lines = []
            try:
                for key, value in (headers or {}).items():
                    if not key or value is None:
                        continue
                    if key.lower() == "cookie":
                        if os.path.isfile(USER_COOKIES_FILE):
                            continue  # کوکی‌های واقعی کاربر اولویت دارند
                        host = (urlparse(url).hostname or "").lower()
                        if not host or not value:
                            continue
                        try:
                            parsed = SimpleCookie()
                            parsed.load(value)
                            if not parsed:
                                continue
                            domain = ".pornhub.com" if host == "pornhub.com" or host.endswith(".pornhub.com") else host
                            fd, cookie_path = tempfile.mkstemp(prefix="ytdlp_cookies_", suffix=".txt", dir=output_dir)
                            os.close(fd)
                            os.chmod(cookie_path, 0o600)
                            jar = MozillaCookieJar(cookie_path)
                            for name, morsel in parsed.items():
                                jar.set_cookie(Cookie(
                                    version=0, name=name, value=morsel.value,
                                    port=None, port_specified=False,
                                    domain=domain, domain_specified=domain.startswith("."),
                                    domain_initial_dot=domain.startswith("."),
                                    path="/", path_specified=True,
                                    secure=urlparse(url).scheme == "https",
                                    expires=None, discard=True, comment=None, comment_url=None,
                                    rest={}, rfc2109=False,
                                ))
                            jar.save(ignore_discard=True, ignore_expires=True)
                            cmd += ["--cookies", cookie_path]
                        except Exception as e:
                            print("⚠️ ساخت کوکی برای yt-dlp:", e)
                        continue
                    cmd += ["--add-header", f"{key}:{value}"]
                if not cookie_path and os.path.isfile(USER_COOKIES_FILE):
                    cmd += ["--cookies", USER_COOKIES_FILE]
                cmd.extend(["--", url])

                print(f"🎬 سقف کیفیت: {q}p | تکه‌های هم‌زمان: {HLS_CONCURRENT_FRAGMENTS}")
                print("📋 FORMAT:", _download_format_selector(q))
                proc = await asyncio.create_subprocess_exec(
                    *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
                )
                last_pct = -20
                last_time = time.monotonic()
                final_path = None
                read_task = asyncio.create_task(proc.stdout.readline())
                try:
                    while True:
                        if cancel_flag:
                            return None
                        done, _ = await asyncio.wait({read_task}, timeout=1)
                        if not done:
                            if time.monotonic() - last_time > timeout_sec:
                                print("❌ yt-dlp: مهلت بی‌خبری از پردازش تمام شد")
                                return None
                            continue
                        line_bytes = read_task.result()
                        if not line_bytes:
                            break
                        read_task = asyncio.create_task(proc.stdout.readline())
                        last_time = time.monotonic()
                        line = line_bytes.decode("utf-8", errors="replace").strip()
                        if not line:
                            continue
                        print(f"YTDLP: {line}")
                        if line.startswith("FINAL_FILE: "):
                            final_path = line[len("FINAL_FILE: "):].strip()
                        elif "ERROR" in line:
                            error_lines.append(line)
                        match = re.search(r"\b(\d+(?:\.\d+)?)%", line)
                        if match and "[download]" in line.lower():
                            pct = max(0, min(100, int(float(match.group(1)))))
                            if pct < last_pct:
                                last_pct = -20
                            if pct - last_pct >= 20 or (pct == 100 and last_pct != 100):
                                last_pct = pct
                                filled = pct // 5
                                bar = "█" * filled + "░" * (20 - filled)
                                await safe_edit(status_msg, f"⬇️ دانلود؛ سقف {q}p\n[{bar}] {pct}%")
                finally:
                    if not read_task.done():
                        read_task.cancel()
                        await asyncio.gather(read_task, return_exceptions=True)

                await proc.wait()
                print(f"📋 yt-dlp exit: {proc.returncode}")
                if proc.returncode == 0 and final_path and os.path.isfile(final_path):
                    if os.path.getsize(final_path) > 100_000:
                        return final_path
                return None
            except Exception as e:
                print(f"❌ yt-dlp subprocess error: {e}")
                return None
            finally:
                if proc and proc.returncode is None:
                    try:
                        proc.kill()
                        await proc.wait()
                    except ProcessLookupError:
                        pass
                if cookie_path:
                    try:
                        os.remove(cookie_path)
                    except FileNotFoundError:
                        pass


        # ================== استخراج لینک ویدیو از HTML ==================
        _VID_RE = re.compile(
            r"""(?:https?:)?//[^\s"'<>()\\,]+?\.(?:mp4|m3u8|webm|mkv|m4v|mpd)(?:\?[^\s"'<>()\\,]*)?""",
            re.I,
        )
        _IFRAME_RE = re.compile(r"""<iframe[^>]+src=["']([^"']+)["']""", re.I)
        _ALT_RE = re.compile(r"""altplayer\.php\?i=([^"'&\s]+)""", re.I)
        _JUNK = ("preview", "thumb", "trailer", "/ads", "banner", "promo", "sprite", "poster",
                 "sample", "splash", "/tr_", "_trailer", "/teaser", "watermark")


        def _abs(u, base):
            u = _unescape_text(u).strip()
            if u.startswith("//"):
                u = "https:" + u
            return urljoin(base, u)


        def _height_of(u):
            nums = [int(n) for n in re.findall(r"(?<!\d)(2160|1440|1080|720|540|480|360|240|144)(?!\d)", u or "")]
            return max(nums) if nums else 0


        def _http_get(url, referer=None, max_bytes=4_000_000, timeout=(20, 45)):
            """HTML را با سقف حجم می‌گیرد.

            باگ قبلی: برای لینک مستقیمِ ۹۷۰ مگی، همین تابع سعی می‌کرد کل فایل را در حافظه
            بخواند و بعد از ۳۰ ثانیه با ۳۶ مگ دانلود timeout می‌داد. حالا:
            اگر content-type رسانه باشد اصلاً بدنه خوانده نمی‌شود و حداکثر ۴ مگ خوانده می‌شود.
            """
            url = _normalize_url(url)
            headers = {
                "User-Agent": UA_CHROME,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
            if referer:
                headers["Referer"] = _normalize_url(referer)
            resp = None
            try:
                if _has_curl_cffi():
                    from curl_cffi import requests as creq
                    resp = creq.get(url, headers=headers, impersonate="chrome", timeout=timeout,
                                    stream=True, allow_redirects=True)
                else:
                    resp = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
                if resp.status_code >= 400:
                    print(f"🔎 GET {url[:110]} → {resp.status_code}")
                    return ""
                ct = (resp.headers.get("content-type") or "").lower()
                if ct and not any(x in ct for x in ("html", "text", "json", "javascript", "xml")):
                    print(f"⏭️ GET {url[:110]} نوع محتوا {ct.split(';')[0]} است → اسکرپ رد شد")
                    return ""
                chunks, got = [], 0
                for chunk in resp.iter_content(chunk_size=65536):
                    if not chunk:
                        continue
                    chunks.append(chunk)
                    got += len(chunk)
                    if got >= max_bytes:
                        break
                return b"".join(chunks).decode("utf-8", errors="replace")
            finally:
                if resp is not None:
                    try:
                        resp.close()
                    except Exception:
                        pass


        def _page_video_ids(page_url):
            """شناسهٔ ویدیو از آدرس صفحه (مثل -205966838_456239117) تا لینک‌های ویدیوهای
            دیگر/تیزرهای داخل همان صفحه اشتباهی انتخاب نشوند."""
            if not page_url:
                return []
            try:
                m = re.search(r"(-?\d{5,})[_/](\d{5,})", _normalize_url(page_url))
            except Exception:
                m = None
            if not m:
                return []
            return [m.group(1), m.group(2)]


        def _media_candidates_from_html(html, base, page_url=None):
            """همهٔ کاندیدهای ویدیو در HTML، با اولویت: ویدیوی خودِ صفحه ← امضاشده ← کیفیت بالاتر."""
            if not html:
                return []
            text = _unescape_text(html)
            page_ids = _page_video_ids(page_url or base)
            urls = []
            for raw in _VID_RE.findall(text):
                full = _abs(raw, base)
                low = full.lower()
                if any(j in low for j in _JUNK):
                    continue
                if "seg-" in low or low.endswith(".ts"):
                    continue
                urls.append(full)
            urls = list(dict.fromkeys(urls))
            candidates = []
            for u in urls:
                candidates.append({
                    "url": u,
                    "height": _height_of(u),
                    "signed": bool(re.search(r"(secure|token|sig|signature|expires|exp)=", u, re.I)),
                    "matches_page": bool(page_ids) and all(pid in u for pid in page_ids),
                })
            candidates.sort(key=lambda c: (0 if c["matches_page"] else 1,
                                           0 if c["signed"] else 1,
                                           -(c["height"] or 0)))
            return candidates


        def _pick_best_candidate(candidates, quality):
            """بهترین کاندید در سقف کیفیت: بالاترین کیفیت زیر سقف، وگرنه نزدیک‌ترین بالای سقف."""
            if not candidates:
                return None
            try:
                q = int(quality)
            except Exception:
                q = 720
            matched = [c for c in candidates if c.get("matches_page")]
            if matched:                      # ویدیوی خودِ صفحه، نه تیزر/ویدیوی پیشنهادی
                candidates = matched
            under = [c for c in candidates if c["height"] and 0 < c["height"] <= q]
            if under:
                return max(under, key=lambda c: c["height"])
            over = [c for c in candidates if c["height"] and c["height"] > q]
            if over:
                return min(over, key=lambda c: c["height"])
            unknown = [c for c in candidates if not c["height"]]
            return unknown[0] if unknown else candidates[0]


        def _html_scrape_video(url, quality, max_pages=6):
            """صفحه و iframeهایش را می‌گردد و بهترین mp4/m3u8 زیر سقف کیفیت را برمی‌گرداند: (link, referer)."""
            url = _normalize_url(url)
            if _looks_like_media(url):
                print("⏭️ خودِ لینک فایل است → اسکرپ HTML لازم نیست")
                return None
            pages = [(url, None)]
            if "://m." in url:
                pages.append((url.replace("://m.", "://", 1), None))
            candidates, seen, index = [], set(), 0
            while index < len(pages) and index < max_pages:
                page, ref = pages[index]
                index += 1
                if page in seen:
                    continue
                seen.add(page)
                try:
                    html = _http_get(page, ref)
                except Exception as e:
                    print(f"⚠️ scrape {page[:110]}: {e}")
                    continue
                if not html:
                    continue
                for cand in _media_candidates_from_html(html, page, page):
                    candidates.append((cand, page))
                text = _unescape_text(html)
                for match in _IFRAME_RE.findall(text) + _ALT_RE.findall(text):
                    frame = _abs(match, page)
                    if (frame.startswith("http") and frame not in seen
                            and not any(j in frame.lower() for j in ("ads", "banner", "chat", "splash", "promo"))):
                        pages.append((frame, page))
            if not candidates:
                return None

            unique = []
            seen_urls = set()
            for cand, page in candidates:
                if cand["url"] in seen_urls:
                    continue
                seen_urls.add(cand["url"])
                unique.append((cand, page))
            for cand, _ in unique:
                print(f"🎯 کاندید: {cand['height'] or '?'}p | signed={'yes' if cand['signed'] else 'no'} | {cand['url'][:130]}")
            best = _pick_best_candidate([c for c, _ in unique], quality)
            if not best:
                return None
            page_of_best = next(p for c, p in unique if c["url"] == best["url"])
            print(f"✅ انتخاب شد: {best['height'] or '?'}p | {best['url'][:130]}")
            return best["url"], page_of_best


        # ================== بررسی سلامت و ابعاد فایل ==================
        def _ffprobe_json(path, extra_args=None):
            args = ["ffprobe", "-v", "error"]
            if extra_args:
                args.extend(extra_args)
            args.extend(["-show_entries", "stream=width,height,codec_type", "-of", "json", path])
            try:
                return subprocess.run(args, capture_output=True, text=True, timeout=120)
            except Exception as e:
                print("⚠️ ffprobe:", e)
                return None


        def _sniff_container(path):
            """نوع کانتینر را از امضای بایت‌های اول تشخیص می‌دهد (پسوند هیچ ارزشی ندارد)."""
            try:
                with open(path, "rb") as f:
                    head = f.read(16)
            except Exception:
                return "unknown"
            if len(head) >= 8 and head[4:8] == b"ftyp":
                return "mp4"
            if head[:4] == b"\x1aE\xdf\xa3":
                return "mkv"
            if head[:3] == b"FLV":
                return "flv"
            if head[:1] == b"\x47":
                return "ts"
            return "unknown"


        def _ensure_mp4(path):
            """اگر فایل واقعاً MP4 نیست (مثلاً HLS به‌صورت TS ذخیره شده) بدون افت کیفیت به mp4 تبدیل می‌کند.

            نکته: بعضی دانلودرها دادهٔ MPEG-TS را با پسوند .mp4 می‌نویسند؛ همان فایل
            برای ffprobe/تلگرام مشکل‌ساز می‌شود.
            """
            if not path or not os.path.isfile(path):
                return path
            kind = _sniff_container(path)
            if kind == "mp4":
                return path
            if kind not in ("ts", "mkv", "flv", "unknown"):
                return path
            print(f"🔧 کانتینر «{kind}» شناسایی شد → remux به mp4 (بدون افت کیفیت)...")
            base = path.rsplit(".", 1)[0]
            for extra in (["-bsf:a", "aac_adtstoasc"], []):
                out = base + "_remux.mp4"
                cmd = ["ffmpeg", "-v", "error", "-y", "-err_detect", "ignore_err", "-i", path,
                       "-c", "copy", *extra, "-movflags", "+faststart", "-f", "mp4", out]
                try:
                    result = subprocess.run(cmd, capture_output=True, timeout=7200)
                except Exception as e:
                    print("⚠️ remux:", e)
                    continue
                if result.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 100_000:
                    print(f"✅ remux شد: {os.path.getsize(out) / 1048576:.1f} MB")
                    try:
                        os.remove(path)
                    except OSError:
                        pass
                    return out
                try:
                    if os.path.exists(out):
                        os.remove(out)
                except OSError:
                    pass
            print("⚠️ remux نشد؛ فایل همان‌طور ادامه می‌دهد")
            return path


        def _probe_dimensions(path):
            """(path, width, height) — اگر فایل moov انتهایی/ناقص باشد اول remux می‌کند.

            نسخهٔ قبلی با check=True مستقیم استثنا می‌داد و کل دانلود سالم را دور می‌ریخت.
            """
            result = _ffprobe_json(path, ["-select_streams", "v:0"])
            if result is None or result.returncode != 0 or not (result.stdout or "").strip():
                print("🔧 ffprobe نخواند → تلاش برای remux/تعمیر فایل...")
                fixed = fix_video_file(path)
                if fixed and fixed != path and os.path.isfile(fixed):
                    path = fixed
                    result = _ffprobe_json(path, ["-select_streams", "v:0"])
            if result is None or result.returncode != 0 or not (result.stdout or "").strip():
                result = _ffprobe_json(path)
            if result is None or result.returncode != 0:
                raise ValueError("ffprobe نتوانست فایل را بخواند (فایل ناقص یا خراب)")
            try:
                streams = json.loads(result.stdout or "{}").get("streams", []) or []
            except Exception:
                streams = []
            video = [s for s in streams if (s.get("codec_type") == "video")] or streams
            if not video:
                raise ValueError("هیچ استریم ویدیویی در فایل نیست")
            w = int(video[0].get("width") or 0)
            h = int(video[0].get("height") or 0)
            return path, w, h


        # ================== تابع اصلی دانلود ==================
        async def download_link(url, status_msg):
            global cancel_flag, DOWNLOAD_QUALITY
            url = _normalize_url(url)
            base_dir = "/content" if os.path.isdir("/content") else None
            tmpdir = tempfile.mkdtemp(dir=base_dir) if base_dir else tempfile.mkdtemp()
            quality = int(DOWNLOAD_QUALITY)

            async def finalize(result_path, clean_dir=None):
                try:
                    result_path = await asyncio.to_thread(_ensure_mp4, result_path)
                    result_path, w, h = await asyncio.to_thread(_probe_dimensions, result_path)
                    short = min(w, h) if (w > 0 and h > 0) else 0
                    if short <= 0:
                        print("⚠️ ابعاد ویدیو معلوم نشد؛ فایل بدون تغییر ارسال می‌شود")
                    elif short > quality:
                        await safe_edit(status_msg, f"🔧 فایل {short}p است → تبدیل به {quality}p...")
                        scale = f"scale=-2:{quality}" if h <= w else f"scale={quality}:-2"
                        scaled = os.path.join(tmpdir, "scaled.mp4")
                        run_result = await asyncio.to_thread(
                            subprocess.run,
                            ["ffmpeg", "-y", "-i", result_path, "-vf", scale,
                             "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                             "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", scaled],
                            capture_output=True, timeout=7200,
                        )
                        if run_result.returncode != 0 or not os.path.isfile(scaled):
                            raise ValueError("تبدیل کیفیت ناموفق بود")
                        result_path = scaled
                except Exception as e:
                    print(f"❌ بررسی کیفیت خروجی: {e}")
                    await safe_edit(status_msg, f"❌ فایل ارسال نشد: فایل سالم/قابل تأیید نیست ({e})")
                    if clean_dir:
                        shutil.rmtree(clean_dir, ignore_errors=True)
                    shutil.rmtree(tmpdir, ignore_errors=True)
                    return None

                final = tempfile.mktemp(suffix=".mp4", dir=TEMP_PATH)
                try:
                    shutil.move(result_path, final)   # جابه‌جایی به‌جای کپی: نصف دیسک و چند برابر سریع‌تر
                except Exception:
                    shutil.copy2(result_path, final)
                if clean_dir:
                    shutil.rmtree(clean_dir, ignore_errors=True)
                shutil.rmtree(tmpdir, ignore_errors=True)
                print(f"✅ دانلود موفق: {os.path.getsize(final) / 1048576:.1f} MB")
                return final

            try:
                is_direct = _looks_like_media(url)

                # ---------- ۱) لینک فایل/استریم مستقیم ----------
                if is_direct:
                    await safe_edit(status_msg, "🔗 لینک فایل مستقیم → تست دسترسی و دانلود...")
                    access = await asyncio.to_thread(_probe_media_access, url, None)
                    if access and access.get("kind") == "hls":
                        res = await _ytdlp_subprocess(url, tmpdir, status_msg, access.get("headers") or {},
                                                      timeout_sec=900, quality=quality)
                        if res:
                            return await finalize(res)
                    elif access:
                        res = await _download_from_access(url, os.path.join(tmpdir, "direct.mp4"),
                                                         status_msg, access)
                        if res:
                            return await finalize(res)
                else:
                    # صفحه‌ای که ممکن است خودش فایل تحویل دهد (مثل ?hash=...&download=true)
                    access = await asyncio.to_thread(_probe_media_access, url, None)
                    if access and access.get("kind") != "hls":
                        res = await _download_from_access(url, os.path.join(tmpdir, "direct.mp4"),
                                                         status_msg, access)
                        if res:
                            return await finalize(res)

                if cancel_flag:
                    return None

                is_pornhub = "pornhub.com" in (urlparse(url).hostname or "").lower()

                # ---------- ۲) اسکرپ HTML: سریع‌ترین راه برای سایت‌های بدون extractor ----------
                if not is_pornhub:
                    await safe_edit(status_msg, "🔍 استخراج لینک ویدیو از صفحه...")
                    scraped = await asyncio.to_thread(_html_scrape_video, url, quality)
                    if scraped:
                        vurl, vref = scraped
                        if _looks_like_hls(vurl):
                            hdrs = _get_smart_headers(vurl, referer=vref, for_media=True)
                            res = await _ytdlp_subprocess(vurl, tmpdir, status_msg, hdrs,
                                                          timeout_sec=900, quality=quality)
                            if res:
                                return await finalize(res)
                        else:
                            resign = (lambda old: _resign_media_url_sync(url, old, quality))
                            res = await _download_direct_smart(
                                vurl, os.path.join(tmpdir, "scraped.mp4"), status_msg, quality,
                                page_referer=vref, resign=resign, tmpdir=tmpdir,
                            )
                            if res:
                                return await finalize(res)

                if cancel_flag:
                    return None

                # ---------- ۳) yt-dlp (اکسترکتورهای واقعی؛ بدون Referer اشتباه) ----------
                await safe_edit(status_msg, "⬇️ تلاش با yt-dlp...")
                page_headers = _get_smart_headers(url)
                res = await _ytdlp_subprocess(url, tmpdir, status_msg, page_headers,
                                              timeout_sec=600, quality=quality)
                if res:
                    return await finalize(res)

                if cancel_flag:
                    return None

                # ---------- ۴) yt-dlp با شبیه‌سازی مرورگر (ضد Cloudflare) ----------
                await safe_edit(status_msg, "🛡️ تلاش با شبیه‌سازی مرورگر...")
                res = await _ytdlp_subprocess(url, tmpdir, status_msg, page_headers, timeout_sec=600,
                                              extra_args=["--impersonate", "chrome", "--extractor-retries", "3"],
                                              quality=quality)
                if res:
                    return await finalize(res)

                if cancel_flag:
                    return None

                # ---------- ۵) yt-dlp generic ----------
                await safe_edit(status_msg, "⬇️ تلاش با yt-dlp generic...")
                res = await _ytdlp_subprocess(url, tmpdir, status_msg, page_headers, timeout_sec=300,
                                              extra_args=["--force-generic-extractor"], quality=quality)
                if res:
                    return await finalize(res)

                if cancel_flag:
                    return None

                # ---------- ۶) Chromium: پیدا کردن لینک + دانلود با همان نشست ----------
                extracted = await download_with_chromium_enhanced(url, status_msg, quality=quality)
                if extracted:
                    await safe_edit(status_msg, "🌐 Chromium لینک را پیدا کرد → دانلود با نشست مرورگر...")
                    dl_path = os.path.join(tmpdir, "chromium_direct.mp4")
                    res = await _chromium_session_download(extracted, dl_path, status_msg, quality=quality)
                    if res:
                        return await finalize(res)

                if cancel_flag:
                    return None

                # ---------- ۷) آخرین تلاش: خودِ آدرس ورودی به‌عنوان فایل ----------
                if not is_direct:
                    await safe_edit(status_msg, "🔗 آخرین تلاش: دانلود مستقیم HTTP...")
                    res = await _download_direct_smart(url, os.path.join(tmpdir, "last_try.mp4"),
                                                       status_msg, quality, page_referer=None,
                                                       tmpdir=tmpdir)
                    if res:
                        return await finalize(res)
            except Exception as e:
                print(f"❌ خطای غیرمنتظره در دانلود: {type(e).__name__}: {e}")
                await safe_edit(status_msg, f"❌ خطای غیرمنتظره: {type(e).__name__}")
                return None
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)

            await safe_edit(status_msg, "❌ همه روش‌ها شکست خوردند.")
            return None


        async def _download_direct_smart(url, filepath, status_msg, quality, page_referer=None,
                                         resign=None, tmpdir=None):
            """probe → اگر HLS بود yt-dlp، وگرنه دانلود تکه‌ای چنداتصاله."""
            url = _normalize_url(url)
            access = await asyncio.to_thread(_probe_media_access, url, page_referer)
            if not access:
                return None
            if access.get("kind") == "hls":
                out_dir = tmpdir or os.path.dirname(filepath) or "."
                headers = dict(access.get("headers") or {})
                result = await _ytdlp_subprocess(url, out_dir, status_msg, headers,
                                                timeout_sec=900, quality=quality)
                if result and os.path.normpath(result) != os.path.normpath(filepath):
                    try:
                        shutil.move(result, filepath)
                        return filepath
                    except Exception as e:
                        print("⚠️ جابه‌جایی فایل HLS:", e)
                        return result
                return result
            return await _download_from_access(url, filepath, status_msg, access, resign=resign)

        #================== صف و پردازش ==================
        queue = asyncio.Queue()
        processing = False

        async def worker():
            global processing, cancel_flag
            if processing: return
            processing = True
            while not queue.empty():
                if cancel_flag:
                    cancel_flag = False
                    break
                event, original_path = await queue.get()
                try:
                    await process_message(event, original_path)
                except Exception as e:
                    await event.reply(f"❌ خطا: {e}")
                finally:
                    queue.task_done()
                await asyncio.sleep(1)
            processing = False

        # ================= تابع پردازش پیام ==================
        async def process_message(event, original_path):
            global cancel_flag
            status = await event.reply("🔍 در حال پردازش ویدیو...")
            main_thumb = await asyncio.to_thread(_get_thumbnail_sync, original_path)
            album_pics = await asyncio.to_thread(_get_multiple_screenshots_sync, original_path, 10)
            final_path = original_path

            if cancel_flag:
                await safe_edit(status, "⏹️ عملیات لغو شد.")
                return

            if WATERMARK_ENABLED or OVERLAY_ENABLED:
                action_text = []
                if WATERMARK_ENABLED: action_text.append("واترمارک")
                if OVERLAY_ENABLED: action_text.append("اورلی")
                await safe_edit(status, f"🎬 اعمال {' + '.join(action_text)}...")
                loop = asyncio.get_event_loop()

                def on_progress(pct, eta):
                    filled = int(pct / 10)
                    bar = "█" * filled + "░" * (10 - filled)
                    text = (
                        f"🎬 اعمال {' + '.join(action_text)}...\n"
                        f"[{bar}] {pct}%\n"
                        f"⏱ زمان باقیمانده: {eta}"
                    )
                    asyncio.run_coroutine_threadsafe(safe_edit(status, text), loop)

                processed = await asyncio.to_thread(
                    _apply_watermark_sync, original_path, 25, on_progress
                )
                if processed:
                    await safe_edit(status,
                        f"🎬 اعمال {' + '.join(action_text)}...\n"
                        f"[██████████] 100%\n"
                        f"✅ پردازش کامل شد"
                    )
                    final_path = processed

            if cancel_flag:
                await safe_edit(status, "⏹️ عملیات لغو شد.")
                return

            file_name       = os.path.basename(final_path)
            file_size_bytes = os.path.getsize(final_path)
            file_size_mb    = file_size_bytes / (1024 * 1024)
            await safe_edit(status, "🚀 شروع آپلود به Pixeldrain...")

            pixel_result = await upload_to_pixeldrain(final_path, status)

            if cancel_flag:
                await safe_edit(status, "⏹️ عملیات لغو شد.")
                return

            album_caption = f"✅ **ویدیو پردازش شد**\n📂 `{file_name}` | `{file_size_mb:.1f} MB`"
            if album_pics:
                album_messages = await client.send_file(
                    event.chat_id, album_pics, caption=album_caption, reply_to=event.id
                )
                album_msg = album_messages[-1] if isinstance(album_messages, list) else album_messages
            else:
                album_msg = await event.reply(album_caption)

            links = []
            if pixel_result:
                links.append(
                    "🌐 Pixeldrain:\n"
                    f"`{pixel_result['viewer']}`\n\n"
                    f"📥 دانلود مستقیم:\n"
                    f"`{pixel_result['download']}`"
                )
            links_text = "\n\n".join(links) if links else "❌ آپلود Pixeldrain موفق نشد."
            await client.send_message(event.chat_id, links_text, reply_to=album_msg.id)
            await status.delete()

            try:
                to_clean = [original_path, final_path, main_thumb] + (album_pics or [])
                for f in to_clean:
                    if f and os.path.exists(f): os.remove(f)
            except: pass

        #================== هندلر اصلی ==================
        def is_video_message(msg):
            return (
                msg.video or msg.document or msg.web_preview or msg.video_note or msg.forward or
                (msg.media and hasattr(msg.media, 'document') and msg.media.document) or
                (msg.media and hasattr(msg.media, 'video') and msg.media.video)
            )

        @client.on(events.NewMessage(chats=OWNER_ID))
        async def handler(event):
            global processing, WATERMARK_ENABLED, OVERLAY_ENABLED, cancel_flag, DOWNLOAD_QUALITY, WATERMARK_TEXT, FONT_PATH, SCREENSHOT_TEXT

            raw_text = (event.message.message or "").strip()
            caption = raw_text.lower()
            is_link = raw_text.startswith("http://") or raw_text.startswith("https://")
            is_overlay_intent = caption in ["اورلی", "overlay", "save overlay", "ذخیره اورلی", "اورلی ذخیره"]

            if getattr(event.message, "forward", None):
                print(f"🔍 FORWARD: video={bool(event.message.video)}, doc={bool(event.message.document)}")

            # ========== استارت ==========
            if caption == "استارت":
                wm_s = "✅ روشن" if WATERMARK_ENABLED else "❌ خاموش"
                ol_s = "✅ روشن" if OVERLAY_ENABLED else "❌ خاموش"
                help_text = (
                    "📖 **راهنمای کامل دستورات ربات**\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"

                    "🏠 **دستورات اصلی:**\n\n"
                    "🔹 `استارت`\n"
                    "     نمایش این راهنما\n\n"
                    "🔹 ارسال لینک ویدیو\n"
                    "     ربات لینک رو دانلود و پردازش میکنه\n\n"
                    "🔹 ارسال ویدیو یا فایل\n"
                    "     ربات فایل رو مستقیم پردازش میکنه\n\n"

                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "💧 **تنظیمات واترمارک:**\n\n"
                    "🔹 `واترمارک روشن`\n"
                    "     فعال کردن واترمارک روی ویدیو\n\n"
                    "🔹 `واترمارک خاموش`\n"
                    "     غیرفعال کردن واترمارک\n\n"
                    "🔹 `متن واترمارک @channel`\n"
                    "     تغییر متن واترمارک به انگلیسی\n\n"
                    "🔹 `متن واترمارک کانال من`\n"
                    "     تغییر متن واترمارک به فارسی\n"
                    "     (فونت فارسی خودکار دانلود میشه)\n\n"

                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🖼️ **اسکرین‌شات‌ها:**\n\n"
                    "🔹 `متن اسکرین‌شات ...`\n"
                    "     تغییر کلمه‌ای که روی ۸ اسکرین‌شات\n"
                    "     نوشته میشه — خودکار در خالی‌ترین\n"
                    "     ناحیه، دور از چهره و بدن افراد (حتی\n"
                    "     بدون صورت)، با کاور مشکی و متن سفید\n\n"

                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🎞️ **تنظیمات اورلی:**\n\n"
                    "🔹 `اورلی روشن`\n"
                    "     فعال کردن اورلی روی ویدیو\n\n"
                    "🔹 `اورلی خاموش`\n"
                    "     غیرفعال کردن اورلی\n\n"
                    "🔹 `اورلی` + ارسال عکس یا ویدیو\n"
                    "     کپشن عکس/ویدیو رو «اورلی» بنویس\n\n"

                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🎬 **کیفیت دانلود (سقف کیفیت، اولویت HLS):**\n\n"
                    "     ابتدا بهترین HLS تا سقف انتخابی؛ در نبود آن فرمت دیگر.\n"
                    "     اگر HLS پایین‌تر موجود باشد، به فایل مستقیمِ بالاتر ترجیح داده می‌شود.\n"
                    "     کیفیت بالاتر از سقف ارسال نمی‌شود؛ تبدیل کیفیت انجام نمی‌شود.\n"
                    "     اعداد فارسی هم پذیرفته می‌شوند: `کیفیت ۷۲۰`\n\n"
                    "🔹 `کیفیت 1080`\n"
                    "     حداکثر Full HD\n\n"
                    "🔹 `کیفیت 720`\n"
                    "     حداکثر HD — پیشفرض\n\n"
                    "🔹 `کیفیت 480`\n"
                    "     حداکثر 480p\n\n"
                    "🔹 `کیفیت 360`\n"
                    "     حداکثر 360p\n\n"

                    "━━━━━━━━━━━━━━━━━━━━\n"
                    "🛑 **لغو عملیات:**\n\n"
                    "🔹 `لغو`\n"
                    "     لغو فوری همه عملیات‌های در حال اجرا\n\n"

                    "━━━━━━━━━━━━━━━━━━━━\n"
                    f"📊 **وضعیت فعلی:**\n"
                    f"   💧 واترمارک: {wm_s}\n"
                    f"   📝 متن واترمارک: `{WATERMARK_TEXT}`\n"
                    f"   🖼️ متن اسکرین‌شات: `{SCREENSHOT_TEXT}`\n"
                    f"   🎞️ اورلی: {ol_s}\n"
                    f"   🎬 کیفیت دانلود: `{DOWNLOAD_QUALITY}p`"
                )
                await event.reply(help_text)
                return

            # ========== واترمارک روشن/خاموش ==========
            if caption == "واترمارک روشن":
                WATERMARK_ENABLED = True
                await event.reply("✅ واترمارک **روشن** شد.")
                return

            if caption == "واترمارک خاموش":
                WATERMARK_ENABLED = False
                await event.reply("❌ واترمارک **خاموش** شد.")
                return

            # ========== تغییر متن واترمارک ==========
            if raw_text.startswith("متن واترمارک "):
                new_text = raw_text[len("متن واترمارک "):].strip()
                if not new_text:
                    await event.reply(
                        "⚠️ متن واترمارک نمیتونه خالی باشه!\n\n"
                        "مثال انگلیسی:\n`متن واترمارک @MyChannel`\n\n"
                        "مثال فارسی:\n`متن واترمارک کانال من`"
                    )
                    return
                forbidden = ["'", '"', "\\", "\n"]
                if any(c in new_text for c in forbidden):
                    await event.reply(
                        "⚠️ متن نمیتونه شامل این کاراکترها باشه:\n"
                        "` ' \" \\ `"
                    )
                    return
                WATERMARK_TEXT = new_text
                has_persian = any('\u0600' <= c <= '\u06FF' for c in new_text)
                if has_persian:
                    await event.reply("⏳ متن فارسی شناسایی شد، در حال دانلود فونت...")
                    font = await asyncio.to_thread(_setup_persian_font)
                    # ⚠️ FONT_PATH را دست نمی‌زنیم — بازمحافظهٔ آن باعث می‌شد متن اسکرین‌شات حذف بشود
                    font_status = "✅ فونت Vazir" if (font and "Vazir" in font) else "⚠️ فونت پیشفرض"
                    await event.reply(
                        f"✅ متن واترمارک تغییر کرد:\n`{WATERMARK_TEXT}`\n\n"
                        f"🔤 فونت: {font_status}"
                    )
                else:
                    await event.reply(
                        f"✅ متن واترمارک تغییر کرد:\n`{WATERMARK_TEXT}`"
                    )
                return

            # ========== تغییر متن اسکرین‌شات ==========
            if raw_text.startswith("متن اسکرین‌شات "):
                new_text = raw_text[len("متن اسکرین‌شات "):].strip()
                if not new_text:
                    await event.reply("⚠️ متن اسکرین‌شات نمی‌تونه خالی باشه!")
                    return
                forbidden = ["'", '"', "\\", "\n"]
                if any(c in new_text for c in forbidden):
                    await event.reply("⚠️ متن نمی‌تونه شامل این کاراکترها باشه: ` ' \" \\ `")
                    return
                SCREENSHOT_TEXT = new_text
                has_persian = any('\u0600' <= c <= '\u06FF' for c in new_text)
                if has_persian:
                    await asyncio.to_thread(_setup_persian_font)
                await event.reply(
                    f"✅ متن اسکرین‌شات تغییر کرد:\n`{SCREENSHOT_TEXT}`\n"
                    f"(روی اسکرین‌شات‌های ویدیوهای بعدی اعمال میشه)"
                )
                return

            # ========== اورلی روشن/خاموش ==========
            if caption == "اورلی روشن":
                OVERLAY_ENABLED = True
                await event.reply("✅ اورلی **روشن** شد.")
                return

            if caption == "اورلی خاموش":
                OVERLAY_ENABLED = False
                await event.reply("❌ اورلی **خاموش** شد.")
                return

            # ========== کیفیت دانلود: اعداد انگلیسی، فارسی و عربی ==========
            quality_text = caption.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
            quality_match = re.fullmatch(r"کیفیت\s+(\d{1,4})\s*p?", quality_text)
            if quality_match:
                requested = int(quality_match.group(1))
                if not 1 <= requested <= 8640:
                    await event.reply("⚠️ کیفیت باید عددی مثبت تا 8640 باشد؛ مثلاً: کیفیت 720")
                    return
                DOWNLOAD_QUALITY = requested
                await event.reply(
                    f"✅ سقف کیفیت دانلود روی **{DOWNLOAD_QUALITY}p** تنظیم شد.\n"
                    "⚡ اولویت با HLS است؛ اگر موجود نباشد، فرمت دیگر در همین سقف انتخاب می‌شود.\n"
                    "این تنظیم برای دانلودهای بعدی اعمال می‌شود."
                )
                return
            if caption.startswith("کیفیت"):
                await event.reply(
                    f"🎬 سقف کیفیت فعلی: **{DOWNLOAD_QUALITY}p**\n"
                    "برای تغییر: `کیفیت 480` یا `کیفیت 720` یا `کیفیت 1080`"
                )
                return

            # ========== لغو ==========
            if caption == "لغو":
                cancel_flag = True
                while not queue.empty():
                    try:
                        _, q_path = queue.get_nowait()
                        queue.task_done()
                        if q_path and os.path.exists(q_path):
                            try: os.remove(q_path)
                            except: pass
                    except: break
                subprocess.run(["pkill", "-f", "ffmpeg"], capture_output=True)
                subprocess.run(["pkill", "-f", "yt-dlp"], capture_output=True)
                subprocess.run(["pkill", "-f", "curl"], capture_output=True)
                subprocess.run(["pkill", "-f", "chromium"], capture_output=True)
                processing = False
                await event.reply("✅ تمام عملیات‌ها لغو شدند.")
                await asyncio.sleep(3)
                cancel_flag = False
                return

            # ========== ذخیره اورلی ==========
            if is_overlay_intent:
                if event.message.photo or event.message.video or (
                    event.message.document and (
                        "video" in getattr(event.message.document, "mime_type", "") or
                        "image" in getattr(event.message.document, "mime_type", "")
                    )
                ):
                    await save_overlay_image(event)
                else:
                    await event.reply("⚠️ لطفاً عکس یا ویدیو را همراه با کلمه «اورلی» ارسال کنید.")
                return

            # ========== دانلود لینک ==========
            if is_link:
                status = await event.reply("📥 لینک دریافت شد، شروع دانلود آنی...")
                url = raw_text.split()[0]
                downloaded_path = await download_link(url, status)
                if cancel_flag:
                    await safe_edit(status, "⏹️ عملیات لغو شد.")
                    return
                if downloaded_path:
                    await queue.put((event, downloaded_path))
                    wm_status = "با واترمارک" if WATERMARK_ENABLED else "بدون واترمارک"
                    ol_status = "با اورلی" if OVERLAY_ENABLED else "بدون اورلی"
                    await status.edit(
                        f"✅ دانلود کامل شد.\n"
                        f"({wm_status} | {ol_status} | {DOWNLOAD_QUALITY}p)\n"
                        f"صف: {queue.qsize()}"
                    )
                    if not processing: asyncio.create_task(worker())
                    return
                else:
                    await status.edit("❌ دانلود لینک انجام نشد.")
                    return

            # ========== ویدیو ارسال شده ==========
            is_video_file = is_video_message(event.message) and not is_overlay_intent
            if is_video_file:
                status = await event.reply("⬇️ در حال دانلود ویدیو...")
                dest_path = tempfile.mktemp(
                    suffix=".mp4",
                    dir=TEMP_PATH
                )
                try:
                    path = await fast_tg_download(event.message, dest_path, status)
                except Exception as e:
                    await status.edit(f"❌ خطا در دانلود ویدیو: {e}")
                    return
                if not path or not os.path.exists(path):
                    await status.edit("❌ فایل دریافت نشد.")
                    return
                file_size = os.path.getsize(path)
                if file_size < 500_000:
                    await status.edit("⚠️ فایل ناقص است. دوباره به صورت فایل بفرستید.")
                    try: os.remove(path)
                    except: pass
                    return
                await queue.put((event, path))
                wm_status = "با واترمارک" if WATERMARK_ENABLED else "بدون واترمارک"
                ol_status = "با اورلی" if OVERLAY_ENABLED else "بدون اورلی"
                await status.edit(f"📋 در صف پردازش: {queue.qsize()} ({wm_status} | {ol_status})")
                if not processing: asyncio.create_task(worker())
                return

        #================== اجرا ==================
        async def main():
            print("🔌 در حال اتصال...")
            # 🧹 پاک‌سازی فایل‌های ناقص/موقت باقی‌مانده از اجرای قبلی
            #    (خروج ناگهانی، دکمه Stop و...) — تا ربات همیشه تمیز روشن بشه
            cleanup_incomplete_files("شروع")
            # اگه FORCE_RELOGIN = True باشه، session قدیمی پاک و دوباره لاگین میشه
            if FORCE_RELOGIN:
                session_paths = [
                    os.path.join(os.getcwd(), "userbot_session.session"),
                    os.path.join(TEMP_PATH, "userbot_session.session"),
                ]
                for sf in session_paths:
                    if os.path.exists(sf):
                        try:
                            os.remove(sf)
                            print(f"⚠️ session قدیمی حذف شد: {sf}")
                        except Exception as e:
                            print(f"❌ خطا در حذف session: {e}")
            # چک سلامت OpenCV — اگه numpy/opencv خراب باشه فقط هشدار میده، ربات قطع نمیشه
            try:
                import cv2
                print("✅ OpenCV:", cv2.__version__)
            except Exception as e:
                print("⚠️ OpenCV در دسترس نیست:", e)
                print("   (تشخیص چهره موقتا غیرفعاله؛ بقیهٔ ربات کار می‌کنه)")
                print("   برای رفع: ری‌استارت رانتایم + اجرای دوبارهٔ سلول نصب — بعدش دیگه نیازی نیست)")
            try:
                await client.start(phone=phone)
            except Exception as e:
                m = str(e).upper()
                print("❌ خطا در اتصال تلگرام:", e)
                if "FLOOD" in m:
                    print("⏳ تلگرام دسترسی را موقتاً محدود کرده — ۱۰ دقیقه صبر کن و دوباره اجرا کن")
                elif any(k in m for k in ("BLOCKED", "BANNED", "DEACTIVATED", "TERMINATED")):
                    print("🚫 اکانت تلگرام محدود یا غیرفعال شده است (از اپ تلگرام چک کن)")
                elif any(k in m for k in ("SESSION", "AUTH", "PHONE")):
                    print("🛠️ session قبلی نامعتبر است (معمولاً از ری‌استارت وسط لاگین).")
                    print("   فایل session پاک شد — در اجرای بعد فقط یک‌بار کد تلگرام را وارد کن")
                    for sf in ("userbot_session.session", os.path.join(TEMP_PATH, "userbot_session.session")):
                        if os.path.exists(sf):
                            try:
                                os.remove(sf)
                                print(f"   🗑️ {sf} پاک شد")
                            except Exception:
                                pass
                raise
            await asyncio.sleep(2)  # یه نفس کوتاه تا فلودِ تلگرام شروع نشه
            print(f"✅ ربات آماده — OWNER_ID: {OWNER_ID}")
            await client.run_until_disconnected()

        # ثبت handlerها برای پاک‌سازی هنگام هرگونه توقف
        _install_exit_handlers()

        upload_tasks = set()
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(main())
        except KeyboardInterrupt:
            print("⏹️ متوقف شد.")
        finally:
            for t in upload_tasks:
                if not t.done(): t.cancel()
            try:
                loop.run_until_complete(asyncio.sleep(0.1))
            except Exception:
                pass
            cleanup_incomplete_files("پایان")
            print("🧹 پاکسازی کامل شد.")
        '''
    import textwrap as _textwrap
    _embedded_source = _textwrap.dedent(_embedded_source).lstrip("\n")
    exec(compile(_embedded_source, "pixeldrain_fixed.py", "exec"), globals(), globals())
    return


if __name__ == "__main__":
    app.run()
