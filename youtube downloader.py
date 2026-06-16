import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import os
import platform
import urllib.request
import subprocess
import threading
import stat
import shutil
import zipfile
import io

class YTDlpApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🎬 YouTube 影片下載器 (yt-dlp)")
        self.root.geometry("600x550")
        self.root.resizable(False, False)

        self.cookie_path = ""
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        self.setup_ui()

    def setup_ui(self):
        # 標題
        tk.Label(self.root, text="YouTube 影片下載小工具", font=("Arial", 16, "bold")).pack(pady=10)

        # 選擇 Cookie 檔案區域
        frame_cookie = tk.Frame(self.root)
        frame_cookie.pack(pady=5, fill=tk.X, padx=20)
        tk.Label(frame_cookie, text="1. 選擇 Cookies 檔案:", font=("Arial", 10)).pack(anchor=tk.W)
        
        self.btn_cookie = tk.Button(frame_cookie, text="瀏覽檔案 (Browse...)", command=self.select_cookie)
        self.btn_cookie.pack(side=tk.LEFT, pady=5)
        
        self.lbl_cookie_path = tk.Label(frame_cookie, text="未選擇檔案", fg="gray")
        self.lbl_cookie_path.pack(side=tk.LEFT, padx=10)

        # 輸入 YouTube Link 區域
        frame_link = tk.Frame(self.root)
        frame_link.pack(pady=10, fill=tk.X, padx=20)
        tk.Label(frame_link, text="2. 輸入 YouTube 連結:", font=("Arial", 10)).pack(anchor=tk.W)
        
        self.entry_link = tk.Entry(frame_link, width=60, font=("Arial", 10))
        self.entry_link.pack(pady=5, fill=tk.X)

        # 下載按鈕
        self.btn_download = tk.Button(self.root, text="⬇️ 開始下載", font=("Arial", 12, "bold"), bg="#4CAF50", fg="white", command=self.start_download_thread)
        self.btn_download.pack(pady=15)

        # 狀態及 Log 顯示區域
        tk.Label(self.root, text="執行紀錄 (Log):", font=("Arial", 10)).pack(anchor=tk.W, padx=20)
        self.log_area = scrolledtext.ScrolledText(self.root, width=70, height=15, state=tk.DISABLED, bg="#f4f4f4")
        self.log_area.pack(padx=20, pady=5)

    def log(self, message):
        """將訊息顯示喺介面嘅 Log 框入面"""
        self.log_area.config(state=tk.NORMAL)
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END) # 自動捲到最底
        self.log_area.config(state=tk.DISABLED)
        self.root.update_idletasks()

    def select_cookie(self):
        filepath = filedialog.askopenfilename(
            title="選擇 cookies 檔案",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filepath:
            self.cookie_path = filepath
            self.lbl_cookie_path.config(text=os.path.basename(filepath), fg="black")
            self.log(f"已選擇 Cookie 檔案: {filepath}")

    def download_file(self, url, dest_path):
        """從網上下載檔案"""
        self.log(f"準備從網絡下載執行檔...\nURL: {url}")
        try:
            urllib.request.urlretrieve(url, dest_path)
            self.log("✅ 下載執行檔完成！")
            return True
        except Exception as e:
            self.log(f"❌ 下載執行檔失敗: {e}")
            return False

    def download_ffmpeg(self, os_type):
        """下載並解壓 ffmpeg"""
        if os_type == "Windows":
            url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-win-64.zip"
            exe_name = "ffmpeg.exe"
        elif os_type == "Darwin":
            url = "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-osx-64.zip"
            exe_name = "ffmpeg"
        else:
            return False

        self.log(f"📥 準備下載 ffmpeg... ({url})")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            response = urllib.request.urlopen(req)
            zip_data = response.read()
            
            self.log("📦 正在解壓縮 ffmpeg...")
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                z.extract(exe_name, path=self.current_dir)

            if os_type == "Darwin":
                binary_path = os.path.join(self.current_dir, exe_name)
                st = os.stat(binary_path)
                os.chmod(binary_path, st.st_mode | stat.S_IEXEC)

            self.log("✅ ffmpeg 下載及準備完成！")
            return True
        except Exception as e:
            self.log(f"❌ ffmpeg 下載或解壓失敗: {e}")
            return False

    def start_download_thread(self):
        """用 Thread 執行，避免卡死 UI"""
        link = self.entry_link.get().strip()
        if not link:
            messagebox.showwarning("警告", "請先輸入 YouTube 連結！")
            return
        if not self.cookie_path:
            # 如果 user 冇揀，可以提吓佢，但照樣畀佢繼續（有啲片唔使登入）
            if not messagebox.askyesno("提示", "你未選擇 cookies 檔案，確定要繼續嗎？（會員影片可能會下載失敗）"):
                return

        # 檢查 FFMPEG
        system_os = platform.system()
        ffmpeg_name = "ffmpeg.exe" if system_os == "Windows" else "ffmpeg"
        
        # 檢查系統環境變數(PATH) 或者 當前目錄 有冇 ffmpeg
        ffmpeg_exists = shutil.which("ffmpeg") or os.path.exists(os.path.join(self.current_dir, ffmpeg_name))
        
        need_download_ffmpeg = False
        if not ffmpeg_exists:
            # 彈出視窗問 user 需唔需要下載
            if messagebox.askyesno("缺少 ffmpeg", "系統搵唔到 ffmpeg，合併 1080p 高畫質影片需要用到佢。\n\n你要我而家自動幫你下載嗎？"):
                need_download_ffmpeg = True
            else:
                self.log("⚠️ 你選擇咗唔下載 ffmpeg，可能會導致合併失敗或只有畫面冇聲。")

        self.btn_download.config(state=tk.DISABLED)
        self.log_area.config(state=tk.NORMAL)
        self.log_area.delete(1.0, tk.END) # 清除舊 log
        self.log_area.config(state=tk.DISABLED)
        
        # 開新 Thread 做嘢，將 need_download_ffmpeg 傳入去
        threading.Thread(target=self.process_download, args=(link, need_download_ffmpeg), daemon=True).start()

    def process_download(self, youtube_link, need_download_ffmpeg):
        system_os = platform.system()
        
        # 如果頭先 user 答「係」，就先下載 ffmpeg
        if need_download_ffmpeg:
            self.download_ffmpeg(system_os)

        # 判斷 OS 並設定對應的檔案名與下載連結
        if system_os == "Windows":
            binary_name = "yt-dlp.exe"
            download_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
        elif system_os == "Darwin": # Mac OS 喺 Python 入面叫 Darwin
            binary_name = "yt-dlp_macos"
            download_url = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
        else:
            self.log(f"❌ 不支援的作業系統: {system_os}")
            self.btn_download.config(state=tk.NORMAL)
            return

        binary_path = os.path.join(self.current_dir, binary_name)

        self.log(f"🔍 偵測到系統: {system_os}")
        self.log(f"🔍 檢查執行檔: {binary_name}")

        # 檢查 yt-dlp 存在與否
        if not os.path.exists(binary_path):
            self.log(f"⚠️ 找不到 {binary_name}，正在為你下載最新版本...")
            success = self.download_file(download_url, binary_path)
            if not success:
                self.btn_download.config(state=tk.NORMAL)
                return
            
            # Mac 機下載完需要畀執行權限 (chmod +x)
            if system_os == "Darwin":
                self.log("🔧 正在為 Mac 執行檔加入執行權限 (chmod +x)...")
                st = os.stat(binary_path)
                os.chmod(binary_path, st.st_mode | stat.S_IEXEC)

        else:
            self.log("✅ 執行檔已存在，直接開始下載程序。")

        # 組合執行指令
        # 最好用 list 形式傳入 subprocess，避免空白字元引發路徑錯誤
        cmd = [binary_path]
        
        if self.cookie_path:
            cmd.extend(["--cookies", self.cookie_path])
            
        # 如果我哋啱啱下載咗 ffmpeg 或者同一個 folder 內有，就明確話畀 yt-dlp 知喺邊度搵
        local_ffmpeg = os.path.join(self.current_dir, "ffmpeg.exe" if system_os == "Windows" else "ffmpeg")
        if os.path.exists(local_ffmpeg):
            cmd.extend(["--ffmpeg-location", self.current_dir])

        cmd.extend([
            "-o", "%(title)s.%(ext)s",
            "--merge-output-format", "mp4",
            "--format", "bv*[height=1080]+ba/b",
            youtube_link
        ])

        self.log("-" * 40)
        self.log(f"🚀 執行指令:\n{' '.join(cmd)}")
        self.log("-" * 40)

        # 執行 yt-dlp
        try:
            # 用 subprocess.Popen 嚟即時讀取輸出，更新到 UI
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True,
                cwd=self.current_dir # 確保下載嘅片會儲存喺呢個資料夾
            )

            for line in process.stdout:
                self.log(line.strip())

            process.wait()

            if process.returncode == 0:
                self.log("\n🎉 下載完成！檔案已經儲存喺同一目錄下。")
                messagebox.showinfo("完成", "影片下載成功！")
            else:
                self.log(f"\n⚠️ 程式執行結束，但可能有錯誤發生 (Return Code: {process.returncode})")

        except Exception as e:
            self.log(f"\n❌ 執行時發生未知錯誤: {e}")

        # 恢復按鈕狀態
        self.root.after(0, lambda: self.btn_download.config(state=tk.NORMAL))

if __name__ == "__main__":
    root = tk.Tk()
    app = YTDlpApp(root)
    root.mainloop()