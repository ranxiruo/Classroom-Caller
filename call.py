import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import random
import os
import sys
import time
import threading
import hashlib
import struct
import pickle
import ctypes
import subprocess
import socket

# ===================== 单实例管理=====================
SINGLE_INSTANCE_PORT = 52077  # 用于单实例检测的固定端口

def ensure_single_instance():
    """通过绑定本地端口确保单实例，重启时通过标志文件跳过"""
    restart_flag = os.path.join(DATA_DIR, "restart.flag")
    if os.path.exists(restart_flag):
        try:
            os.remove(restart_flag)
        except:
            pass
        return  # 重启模式，直接放行

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('127.0.0.1', SINGLE_INSTANCE_PORT))
        sock.listen(5)
        def hold_port():
            while True:
                try:
                    conn, addr = sock.accept()
                    conn.close()
                except:
                    break
        t = threading.Thread(target=hold_port, daemon=True)
        t.start()
        return True
    except socket.error:
        print("程序已在运行，退出当前实例")
        sys.exit(0)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        DATA_DIR = os.path.dirname(sys.executable)
    else:
        DATA_DIR = os.path.dirname(os.path.abspath(__file__))
    ensure_single_instance()

# ========== 其他常量与工具 ==========
STUDENTS_BIN = os.path.join(DATA_DIR, "students.dat")
GROUPS_BIN = os.path.join(DATA_DIR, "groups.dat")
HISTORY_BIN = os.path.join(DATA_DIR, "history.dat")
WEIGHTS_BIN = os.path.join(DATA_DIR, "weights.dat")
CONFIG_BIN = os.path.join(DATA_DIR, "config.dat")
FAIR_HISTORY_BIN = os.path.join(DATA_DIR, "fair_history.dat")

DEFAULT_STUDENTS = ["张三", "李四", "王五", "赵六", "小明", "小红", "小华", "小丽"]
DEFAULT_GROUPS = ["第一组", "第二组", "第三组", "第四组"]
DEFAULT_CONFIG = {
    "bg_color": "#2C3E50",
    "fg_color": "#ECF0F1",
    "btn_color": "#3498DB",
    "font_family": "Microsoft YaHei",
    "font_size": 12,
    "result_font_size": 36,  # 增大默认字体，适配大屏
    "window_width": 420,
    "window_height": 520,
    "tts_enabled": True,
    "display_duration": 2000,
    "mode": "normal",
    "admin_password_hash": hashlib.sha256("114514".encode()).hexdigest(),
    "first_run": True,  # 新增：首次运行标志
}

_XOR_KEY = b'\x5a\x3c\x7e\x1f\x8d\x4b\x2e\x9f\x6c\x3a\x7b\x1e\x8c\x4a\x2d\x9e'

def _xor_encrypt(data: bytes) -> bytes:
    result = bytearray(len(data))
    for i, b in enumerate(data):
        result[i] = b ^ _XOR_KEY[i % len(_XOR_KEY)]
    return bytes(result)

def save_binary_data(file_path, data):
    try:
        pickled = pickle.dumps(data)
        encrypted = _xor_encrypt(pickled)
        if os.path.exists(file_path):
            bak = file_path + ".bak"
            try:
                os.replace(file_path, bak)
            except:
                pass
        with open(file_path, 'wb') as f:
            f.write(b'EWT_DAT\x00')
            f.write(struct.pack('<I', len(encrypted)))
            f.write(encrypted)
        return True
    except Exception as e:
        print(f"保存失败 {file_path}: {e}")
        return False

def load_binary_data(file_path, default_data):
    if not os.path.exists(file_path):
        return default_data
    try:
        with open(file_path, 'rb') as f:
            header = f.read(8)
            if header != b'EWT_DAT\x00':
                return default_data
            len_bytes = f.read(4)
            if len(len_bytes) != 4:
                return default_data
            data_len = struct.unpack('<I', len_bytes)[0]
            encrypted = f.read(data_len)
            if len(encrypted) != data_len:
                return default_data
            pickled = _xor_encrypt(encrypted)
            data = pickle.loads(pickled)
            return data
    except Exception as e:
        print(f"加载失败 {file_path}: {e}")
        bak = file_path + ".bak"
        if os.path.exists(bak):
            try:
                os.replace(bak, file_path)
                return load_binary_data(file_path, default_data)
            except:
                pass
        return default_data

def load_config():
    config = load_binary_data(CONFIG_BIN, DEFAULT_CONFIG)
    if not isinstance(config, dict):
        return DEFAULT_CONFIG.copy()
    for k, v in DEFAULT_CONFIG.items():
        if k not in config:
            config[k] = v
    if "admin_password" in config and "admin_password_hash" not in config:
        try:
            import base64
            plain = base64.b64decode(config["admin_password"].encode()).decode()
            config["admin_password_hash"] = hashlib.sha256(plain.encode()).hexdigest()
        except:
            pass
        if "admin_password" in config:
            del config["admin_password"]
        save_config(config)
    return config

def save_config(config):
    save_binary_data(CONFIG_BIN, config)

class ClassroomCaller:
    def __init__(self):
        # ---------- DPI 感知（修复大屏幕字体马赛克） ----------
        self.set_dpi_awareness()

        self.config = load_config()
        self.bg_color = self.config["bg_color"]
        self.fg_color = self.config["fg_color"]
        self.btn_color = self.config["btn_color"]
        self.font_family = self.config["font_family"]
        self.font_size = self.config["font_size"]
        self.result_font_size = self.config["result_font_size"]
        self.win_width = self.config["window_width"]
        self.win_height = self.config["window_height"]
        self.tts_enabled = self.config.get("tts_enabled", True)
        self.display_duration = self.config.get("display_duration", 2000)
        self.current_mode = self.config.get("mode", "normal")
        self.first_run = self.config.get("first_run", True)  # 读取首次运行标志

        self.students = load_binary_data(STUDENTS_BIN, DEFAULT_STUDENTS.copy())
        self.groups = load_binary_data(GROUPS_BIN, DEFAULT_GROUPS.copy())
        self.history = load_binary_data(HISTORY_BIN, [])
        self.weights = load_binary_data(WEIGHTS_BIN, {})
        # 清理无效权重
        self.weights = {k: v for k, v in self.weights.items() if k in self.students}
        self.fair_history = load_binary_data(FAIR_HISTORY_BIN, [])

        self.rng = random.Random()

        # 初始化可能未定义的属性
        self.roll_after = None
        self.roll_stop = None
        self.group_roll_after = None
        self.group_roll_stop = None
        self.batch_results = []
        self.batch_count = 0
        self.batch_step = 0

        self.busy = False
        self.rolling = False
        self.after_ids = set()
        self.linger_after = None

        self.group_rolling = False

        self.fair_active = False
        self.fair_confirmed = False
        self.fair_pending = []
        self.fair_confirm_after = None

        self.speak_lock = threading.Lock()

        self.mini_window = None
        self.mini_drag_x = 0
        self.mini_drag_y = 0

        self.minimal_win = None
        self.minimal_label = None
        self.minimal_btn = None
        self.minimal_dragging = False
        self.minimal_drag_x = 0
        self.minimal_drag_y = 0
        self.minimal_rolling = False
        self.minimal_after_id = None
        self.minimal_stop_id = None
        self.minimal_busy = False

        self.root = tk.Tk()
        self.root.title("课堂轻松点名助手")
        self.root.overrideredirect(True)
        self.root.geometry(f"{self.win_width}x{self.win_height}")
        self.root.configure(bg=self.bg_color)
        self.root.resizable(False, False)

        self.drag_x = 0
        self.drag_y = 0
        self.root.bind("<Button-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.on_drag)

        self.show_splash()
        self.create_title_bar()

        self.content_frame = tk.Frame(self.root, bg=self.bg_color)
        self.content_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        if self.current_mode != "minimal":
            self.build_ui()
        else:
            self.root.withdraw()
            self.start_minimal_mode()

        self.register_hotkeys()
        self.root.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.root.mainloop()

    # ---------- DPI 感知 ----------
    def set_dpi_awareness(self):
        """启用 Windows DPI 感知，防止高分辨率屏幕字体模糊"""
        try:
            # Windows 10/11
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_PER_MONITOR_DPI_AWARE
        except AttributeError:
            try:
                # 旧版 Windows
                ctypes.windll.user32.SetProcessDPIAware()
            except:
                pass
        except Exception:
            pass

    # ---------- 权重抽取 ----------
    def weighted_choice(self, items):
        """根据 self.weights 进行加权随机选择"""
        if not items:
            return None
        weights = [self.weights.get(name, 1.0) for name in items]
        return self.rng.choices(items, weights=weights, k=1)[0]

    def get_parent_window(self):
        if self.current_mode == "minimal" and self.minimal_win and self.minimal_win.winfo_exists():
            return self.minimal_win
        return self.root

    def _force_topmost(self, win):
        try:
            win.attributes('-topmost', True)
            win.lift()
            win.focus_force()
            win.update_idletasks()
            try:
                user32 = ctypes.WinDLL('user32')
                HWND_TOPMOST = -1
                SWP_NOMOVE = 0x0002
                SWP_NOSIZE = 0x0001
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(win.winfo_id(), HWND_TOPMOST,
                                    0, 0, 0, 0,
                                    SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
            except:
                pass
        except Exception:
            pass

    def start_drag(self, event):
        self.drag_x = event.x
        self.drag_y = event.y

    def on_drag(self, event):
        x = self.root.winfo_x() + (event.x - self.drag_x)
        y = self.root.winfo_y() + (event.y - self.drag_y)
        self.root.geometry(f"+{x}+{y}")

    def show_splash(self):
        splash = tk.Toplevel(self.root)
        splash.title("启动中")
        splash.geometry("450x250")
        splash.configure(bg='#2C3E50')
        splash.overrideredirect(True)
        x = (self.root.winfo_screenwidth() - 450) // 2
        y = (self.root.winfo_screenheight() - 250) // 2
        splash.geometry(f"+{x}+{y}")

        tk.Label(splash, text="✨ 课堂轻松点名助手 ✨",
                 font=("Microsoft YaHei", 20, "bold"),
                 bg='#2C3E50', fg='#ECF0F1').pack(pady=30)
        tk.Label(splash, text="本软件由 陈恩祈 开发",
                 font=("Microsoft YaHei", 12),
                 bg='#2C3E50', fg='#BDC3C7').pack()
        tk.Label(splash, text="软件正在启动中Ciallo～(∠·ω< )⌒★.",
                 font=("Microsoft YaHei", 10),
                 bg='#2C3E50', fg='#95A5A6').pack(pady=10)
        tk.Label(splash, text="© Chenenqi 2026  中国·上海",
                 font=("Microsoft YaHei", 9),
                 bg='#2C3E50', fg='#7F8C8D').pack(side=tk.BOTTOM, pady=20)

        self._force_topmost(splash)
        # 修改：splash 关闭后检查首次运行
        def on_splash_close():
            splash.destroy()
            self.root.after(100, self.check_first_run)
        splash.after(2000, on_splash_close)

    # ---------- 新手导引 ----------
    def check_first_run(self):
        """检查是否为首次运行，若是则显示引导窗口"""
        if not self.first_run:
            return
        # 显示引导窗口
        guide_win = tk.Toplevel(self.root)
        guide_win.title("欢迎使用")
        guide_win.geometry("500x500")
        guide_win.configure(bg='#2C3E50')
        guide_win.overrideredirect(True)
        guide_win.attributes('-topmost', True)
        # 居中
        x = (self.root.winfo_screenwidth() - 500) // 2
        y = (self.root.winfo_screenheight() - 500) // 2
        guide_win.geometry(f"+{x}+{y}")
        guide_win.transient(self.root)
        guide_win.grab_set()  # 模态

        # 标题
        tk.Label(guide_win, text="欢迎使用课堂轻松点名助手 Ciallo～(∠・ω< )⌒☆",
                 font=("Microsoft YaHei", 14, "bold"),
                 bg='#2C3E50', fg='#ECF0F1').pack(pady=10)

        # 内容区域（带滚动条）
        text_area = scrolledtext.ScrolledText(guide_win, height=18,
                                              font=("Microsoft YaHei", 10),
                                              bg='#34495E', fg='#ECF0F1',
                                              wrap=tk.WORD)
        text_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        guide_text = """
本软件提供六种点名模式，满足不同课堂场景需求。

【模式说明】
・普通模式：点名、抽组、连抽（五连/十连）
・精简模式：仅保留点名和抽组，界面清爽
・公平模式：每人抽中一次后才重复，并展示算法步骤
・连抽模式：专用连抽页面，结果汇总展示
・特效模式：全屏飘动特效展示点名结果
・极小化模式：悬浮小挂件，一键抽人，适合PPT全屏

【快捷键】
  F2  - 随机点名
  F3  - 随机抽组
  Ctrl+M - 最小化到悬浮球（双击恢复）

【管理员初始密码】
  114514 （建议首次使用时修改）

您可以在「设置」中调整语音播报、颜色字体、停留时间等。
所有数据自动加密保存，安全可靠。

祝您课堂愉快！ (´▽`ʃ♡)ƪ
        """
        text_area.insert(tk.END, guide_text)
        text_area.config(state=tk.DISABLED)

        # 按钮
        def on_confirm():
            self.first_run = False
            self.config["first_run"] = False
            save_config(self.config)
            guide_win.destroy()

        btn_frame = tk.Frame(guide_win, bg='#2C3E50')
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="我知道了", command=on_confirm,
                  bg='#3498DB', fg='white', padx=20, pady=6,
                  font=("Microsoft YaHei", 11)).pack()

        self._force_topmost(guide_win)

    def create_title_bar(self):
        title_bar = tk.Frame(self.root, bg='#34495E', height=32)
        title_bar.pack(fill=tk.X, side=tk.TOP)
        title_bar.pack_propagate(False)

        title_label = tk.Label(title_bar, text="✨ 课堂轻松点名助手 ✨",
                               bg='#34495E', fg='white',
                               font=(self.font_family, 11, 'bold'))
        title_label.pack(side=tk.LEFT, padx=10)

        menu_btn = tk.Button(title_bar, text="☰", font=('', 12, 'bold'),
                             bg='#34495E', fg='white', bd=0,
                             activebackground='#2C3E50',
                             command=self.show_menu_popup)
        menu_btn.pack(side=tk.RIGHT, padx=2)

        min_btn = tk.Button(title_bar, text="—", font=('', 12, 'bold'),
                            bg='#34495E', fg='white', bd=0,
                            activebackground='#2C3E50',
                            command=self.minimize_window)
        min_btn.pack(side=tk.RIGHT, padx=2)

        close_btn = tk.Button(title_bar, text="×", font=('', 14, 'bold'),
                              bg='#34495E', fg='white', bd=0,
                              activebackground='#C0392B',
                              command=self.quit_app)
        close_btn.pack(side=tk.RIGHT, padx=2)

        title_bar.bind("<Button-1>", self.start_drag)
        title_bar.bind("<B1-Motion>", self.on_drag)
        title_label.bind("<Button-1>", self.start_drag)
        title_label.bind("<B1-Motion>", self.on_drag)

    # ---------- 菜单复用（缓存一份） ----------
    def create_full_menu(self):
        if not hasattr(self, '_menu_cache'):
            popup = tk.Menu(self.root, tearoff=0, bg='#34495E', fg='white')
            file_menu = tk.Menu(popup, tearoff=0, bg='#34495E', fg='white')
            file_menu.add_command(label="导入名单 (TXT/Excel)", command=self.import_data)
            file_menu.add_command(label="编辑名单", command=self.edit_data)
            file_menu.add_separator()
            file_menu.add_command(label="查看历史记录", command=self.show_history)
            file_menu.add_command(label="查看公平模式历史", command=self.show_fair_history)
            file_menu.add_separator()
            file_menu.add_command(label="退出", command=self.quit_app)
            popup.add_cascade(label="文件", menu=file_menu)

            setting_menu = tk.Menu(popup, tearoff=0, bg='#34495E', fg='white')
            mode_menu = tk.Menu(setting_menu, tearoff=0, bg='#34495E', fg='white')
            self.mode_var = tk.StringVar(value=self.current_mode)
            modes = [("普通模式", "normal"), ("精简模式", "simple"), ("公平模式", "fair"),
                     ("连抽模式", "batch"), ("特效模式", "effect"), ("极小化模式", "minimal")]
            for label, mode in modes:
                mode_menu.add_radiobutton(label=label, variable=self.mode_var, value=mode,
                                          command=lambda m=mode: self.switch_mode(m))
            setting_menu.add_cascade(label="模式选择", menu=mode_menu)
            setting_menu.add_separator()
            setting_menu.add_command(label="个性化设置", command=self.open_settings)
            setting_menu.add_command(label="权重设置", command=self.open_weight_settings)
            setting_menu.add_command(label="修改管理员密码", command=self.change_password)
            self.tts_menu_var = tk.BooleanVar(value=self.tts_enabled)
            setting_menu.add_checkbutton(label="语音播报", variable=self.tts_menu_var,
                                         command=lambda: self.toggle_tts(self.tts_menu_var))
            setting_menu.add_command(label="停留时间", command=self.open_duration_settings)
            popup.add_cascade(label="设置", menu=setting_menu)

            help_menu = tk.Menu(popup, tearoff=0, bg='#34495E', fg='white')
            help_menu.add_command(label="使用说明", command=self.show_help)
            help_menu.add_command(label="关于", command=self.show_about)
            popup.add_cascade(label="帮助", menu=help_menu)
            self._menu_cache = popup
        # 同步菜单状态
        self.mode_var.set(self.current_mode)
        self.tts_menu_var.set(self.tts_enabled)
        return self._menu_cache

    def show_menu_popup(self):
        popup = self.create_full_menu()
        x = self.root.winfo_x() + self.win_width - 150
        y = self.root.winfo_y() + 32
        popup.tk_popup(x, y)

    def show_minimal_context_menu(self, event):
        if not self.root.winfo_exists() or not self.minimal_win or not self.minimal_win.winfo_exists():
            return
        try:
            popup = self.create_full_menu()
            popup.tk_popup(event.x_root, event.y_root)
        except tk.TclError:
            pass

    def switch_mode(self, mode):
        if mode == self.current_mode:
            return
        if self.fair_active and mode != "fair":
            if not messagebox.askyesno("切换模式", "公平模式未完成，切换将退出公平模式并重启程序，确定吗？"):
                self.mode_var.set(self.current_mode)
                return
        if self.current_mode == "minimal":
            self.stop_minimal_mode()
        if mode == "minimal":
            self.current_mode = mode
            self.config["mode"] = mode
            save_config(self.config)
            self.start_minimal_mode()
            return
        self.current_mode = mode
        self.config["mode"] = mode
        save_config(self.config)
        self.save_all_data()
        self.restart_program()

    def restart_program(self):
        restart_flag = os.path.join(DATA_DIR, "restart.flag")
        try:
            with open(restart_flag, 'w') as f:
                f.write("1")
        except:
            pass
        try:
            if getattr(sys, 'frozen', False):
                subprocess.Popen([sys.executable])
            else:
                subprocess.Popen([sys.executable, os.path.abspath(__file__)])
        except Exception as e:
            messagebox.showerror("重启失败", f"无法启动新实例: {e}")
            return
        self.root.destroy()
        sys.exit(0)

    def save_all_data(self):
        try:
            save_binary_data(STUDENTS_BIN, self.students)
            save_binary_data(GROUPS_BIN, self.groups)
            save_binary_data(WEIGHTS_BIN, self.weights)
            save_binary_data(HISTORY_BIN, self.history)
            save_binary_data(FAIR_HISTORY_BIN, self.fair_history)
        except Exception as e:
            print(f"保存数据失败: {e}")

    def start_minimal_mode(self):
        self.root.withdraw()
        self.minimal_win = tk.Toplevel(self.root)
        self.minimal_win.overrideredirect(True)
        self.minimal_win.attributes('-topmost', True)
        self.minimal_win.configure(bg=self.bg_color)
        self.minimal_win.geometry("180x40+{}+{}".format(
            self.root.winfo_screenwidth() - 200, 80))

        frame = tk.Frame(self.minimal_win, bg=self.bg_color)
        frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=3)

        self.minimal_label = tk.Label(frame, text="👤 准备", font=(self.font_family, 11, 'bold'),
                                      bg=self.bg_color, fg=self.fg_color)
        self.minimal_label.pack(side=tk.LEFT, padx=(0, 5))

        self.minimal_btn = tk.Button(frame, text="🎲", font=(self.font_family, 14, 'bold'),
                                     bg=self.btn_color, fg='white', padx=8, pady=2,
                                     relief=tk.FLAT, cursor="hand2",
                                     command=self.minimal_draw)
        self.minimal_btn.pack(side=tk.RIGHT)

        def start_drag(event):
            self.minimal_dragging = True
            self.minimal_drag_x = event.x
            self.minimal_drag_y = event.y
        def on_drag(event):
            if self.minimal_dragging:
                x = self.minimal_win.winfo_x() + (event.x - self.minimal_drag_x)
                y = self.minimal_win.winfo_y() + (event.y - self.minimal_drag_y)
                self.minimal_win.geometry(f"+{x}+{y}")
        def stop_drag(event):
            self.minimal_dragging = False

        self.minimal_win.bind("<Button-1>", start_drag)
        self.minimal_win.bind("<B1-Motion>", on_drag)
        self.minimal_win.bind("<ButtonRelease-1>", stop_drag)
        frame.bind("<Button-1>", start_drag)
        frame.bind("<B1-Motion>", on_drag)
        frame.bind("<ButtonRelease-1>", stop_drag)
        self.minimal_label.bind("<Button-1>", start_drag)
        self.minimal_label.bind("<B1-Motion>", on_drag)
        self.minimal_label.bind("<ButtonRelease-1>", stop_drag)

        self.minimal_win.bind("<Button-3>", self.show_minimal_context_menu)
        frame.bind("<Button-3>", self.show_minimal_context_menu)
        self.minimal_label.bind("<Button-3>", self.show_minimal_context_menu)
        self.minimal_btn.bind("<Button-3>", self.show_minimal_context_menu)

        self._force_topmost(self.minimal_win)

    def stop_minimal_mode(self):
        if self.minimal_win:
            try:
                self.minimal_win.destroy()
            except:
                pass
            self.minimal_win = None
            self.minimal_label = None
            self.minimal_btn = None
        if self.minimal_after_id:
            self.root.after_cancel(self.minimal_after_id)
            self.minimal_after_id = None
        if self.minimal_stop_id:
            self.root.after_cancel(self.minimal_stop_id)
            self.minimal_stop_id = None
        self.minimal_rolling = False
        self.minimal_busy = False

    def minimal_draw(self):
        if not self.students:
            messagebox.showwarning("提示", "学生名单为空！")
            return
        if self.minimal_rolling or self.minimal_busy:
            return
        self.minimal_busy = True
        self.minimal_rolling = True
        self.minimal_btn.config(state=tk.DISABLED)

        def roll():
            if not self.minimal_rolling or not self.minimal_label:
                return
            name = self.weighted_choice(self.students)
            self.minimal_label.config(text=f"🎲 {name}")
            self.minimal_after_id = self.root.after(50, roll)

        def stop_roll():
            self.minimal_rolling = False
            if self.minimal_after_id:
                self.root.after_cancel(self.minimal_after_id)
                self.minimal_after_id = None
            if not self.minimal_label:
                return
            name = self.weighted_choice(self.students)
            self.minimal_label.config(text=f"✨ {name} ✨")
            self.speak(name)
            self.history.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 极小化点名: {name}")
            if len(self.history) > 200:
                self.history = self.history[-200:]
            save_binary_data(HISTORY_BIN, self.history)

            if self.minimal_win and self.minimal_win.winfo_exists():
                width = max(180, len(name) * 25 + 80)
                self.minimal_win.geometry(f"{width}x40")
                self._force_topmost(self.minimal_win)

            def restore():
                if self.minimal_win and self.minimal_win.winfo_exists():
                    self.minimal_win.geometry("180x40")
                    self.minimal_label.config(text="👤 准备")
                    self.minimal_busy = False
                    self.minimal_btn.config(state=tk.NORMAL)
            self.root.after(self.display_duration, restore)

        roll()
        self.minimal_stop_id = self.root.after(1500, stop_roll)

    def build_ui(self):
        if self.current_mode == "minimal":
            return
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        for attr in ['result_label', 'fair_btn', 'fair_log_text', 'fair_status_label',
                     'call_btn', 'group_btn', 'batch5_btn', 'batch10_btn', 'student_count_label']:
            if hasattr(self, attr):
                delattr(self, attr)

        if self.current_mode == "normal":
            self.build_normal_ui()
        elif self.current_mode == "simple":
            self.build_simple_ui()
        elif self.current_mode == "fair":
            self.build_fair_ui()
        elif self.current_mode == "batch":
            self.build_batch_ui()
        elif self.current_mode == "effect":
            self.build_effect_ui()

        self.update_status()

    def build_normal_ui(self):
        self.result_var = tk.StringVar(value="准备就绪")
        self.result_label = tk.Label(self.content_frame, textvariable=self.result_var,
                                     font=(self.font_family, self.result_font_size, "bold"),
                                     bg=self.bg_color, fg=self.fg_color,
                                     wraplength=400, justify='center')
        self.result_label.pack(pady=(10, 15), fill=tk.X)

        btn_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=10)

        row1 = tk.Frame(btn_frame, bg=self.bg_color)
        row1.pack(fill=tk.X, pady=4)
        self.call_btn = self.create_button(row1, "🎲 随机点名", self.start_roll_call)
        self.call_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.group_btn = self.create_button(row1, "👥 随机抽组", self.start_roll_group)
        self.group_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        row2 = tk.Frame(btn_frame, bg=self.bg_color)
        row2.pack(fill=tk.X, pady=4)
        self.batch5_btn = self.create_button(row2, "🎯 五连抽", lambda: self.start_batch(5))
        self.batch5_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.batch10_btn = self.create_button(row2, "🎯 十连抽", lambda: self.start_batch(10))
        self.batch10_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.fair_log_text = scrolledtext.ScrolledText(self.content_frame, height=4,
                                                       font=(self.font_family, 10),
                                                       bg='#34495E', fg='#ECF0F1',
                                                       highlightbackground=self.bg_color)
        self.fair_log_text.config(state=tk.DISABLED)

        status_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        self.student_count_label = tk.Label(status_frame,
                                            text=f"👩‍🎓 学生: {len(self.students)}人  |  👥 小组: {len(self.groups)}组",
                                            bg=self.bg_color, fg=self.fg_color,
                                            font=(self.font_family, 9))
        self.student_count_label.pack(side=tk.LEFT)

    def build_simple_ui(self):
        self.result_var = tk.StringVar(value="准备就绪")
        self.result_label = tk.Label(self.content_frame, textvariable=self.result_var,
                                     font=(self.font_family, self.result_font_size, "bold"),
                                     bg=self.bg_color, fg=self.fg_color,
                                     wraplength=400, justify='center')
        self.result_label.pack(pady=(10, 15), fill=tk.X)

        btn_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=30)

        row1 = tk.Frame(btn_frame, bg=self.bg_color)
        row1.pack(fill=tk.X, pady=6)
        self.call_btn = self.create_button(row1, "🎲 随机点名", self.start_roll_call)
        self.call_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.group_btn = self.create_button(row1, "👥 随机抽组", self.start_roll_group)
        self.group_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        status_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=(30, 0))
        self.student_count_label = tk.Label(status_frame,
                                            text=f"👩‍🎓 学生: {len(self.students)}人  |  👥 小组: {len(self.groups)}组",
                                            bg=self.bg_color, fg=self.fg_color,
                                            font=(self.font_family, 9))
        self.student_count_label.pack(side=tk.LEFT)

    def build_fair_ui(self):
        self.result_var = tk.StringVar(value="公平模式")
        self.result_label = tk.Label(self.content_frame, textvariable=self.result_var,
                                     font=(self.font_family, self.result_font_size, "bold"),
                                     bg=self.bg_color, fg=self.fg_color,
                                     wraplength=400, justify='center')
        self.result_label.pack(pady=(10, 15), fill=tk.X)

        fair_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        fair_frame.pack(fill=tk.X, pady=10)

        if self.fair_active and self.fair_confirmed:
            text = "🎲 公平抽奖"
            cmd = self.fair_draw
            color = '#27AE60'
        elif self.fair_active and not self.fair_confirmed:
            text = "⏳ 确认名单中..."
            cmd = self.toggle_fair_mode
            color = '#E67E22'
        else:
            text = "⚖️ 进入公平模式"
            cmd = self.toggle_fair_mode
            color = self.btn_color

        self.fair_btn = self.create_button(fair_frame, text, cmd)
        self.fair_btn.config(bg=color)
        self.fair_btn.pack(fill=tk.X, pady=5)

        self.fair_log_text = scrolledtext.ScrolledText(self.content_frame, height=6,
                                                       font=(self.font_family, 10),
                                                       bg='#34495E', fg='#ECF0F1',
                                                       highlightbackground=self.bg_color)
        self.fair_log_text.pack(fill=tk.X, pady=5)
        self.fair_log_text.config(state=tk.DISABLED)

        self.fair_status_label = tk.Label(self.content_frame, text="",
                                          bg=self.bg_color, fg='#2ECC71',
                                          font=(self.font_family, 10))
        self.fair_status_label.pack(pady=5)

        if self.fair_active:
            if self.fair_confirmed:
                self.fair_status_label.config(text="已确认，可抽奖", fg='#2ECC71')
            else:
                self.fair_status_label.config(text="请确认名单", fg='#F1C40F')

        status_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        self.student_count_label = tk.Label(status_frame,
                                            text=f"👩‍🎓 学生: {len(self.students)}人  |  👥 小组: {len(self.groups)}组",
                                            bg=self.bg_color, fg=self.fg_color,
                                            font=(self.font_family, 9))
        self.student_count_label.pack(side=tk.LEFT)

    def build_batch_ui(self):
        self.result_var = tk.StringVar(value="连抽模式")
        self.result_label = tk.Label(self.content_frame, textvariable=self.result_var,
                                     font=(self.font_family, self.result_font_size, "bold"),
                                     bg=self.bg_color, fg=self.fg_color,
                                     wraplength=400, justify='center')
        self.result_label.pack(pady=(10, 15), fill=tk.X)

        btn_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=10)

        row1 = tk.Frame(btn_frame, bg=self.bg_color)
        row1.pack(fill=tk.X, pady=4)
        self.batch5_btn = self.create_button(row1, "🎯 五连抽", lambda: self.start_batch(5))
        self.batch5_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)
        self.batch10_btn = self.create_button(row1, "🎯 十连抽", lambda: self.start_batch(10))
        self.batch10_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

        self.fair_log_text = scrolledtext.ScrolledText(self.content_frame, height=6,
                                                       font=(self.font_family, 10),
                                                       bg='#34495E', fg='#ECF0F1',
                                                       highlightbackground=self.bg_color)
        self.fair_log_text.pack(fill=tk.X, pady=5)
        self.fair_log_text.config(state=tk.DISABLED)

        status_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=(10, 0))
        self.student_count_label = tk.Label(status_frame,
                                            text=f"👩‍🎓 学生: {len(self.students)}人  |  👥 小组: {len(self.groups)}组",
                                            bg=self.bg_color, fg=self.fg_color,
                                            font=(self.font_family, 9))
        self.student_count_label.pack(side=tk.LEFT)

    def build_effect_ui(self):
        self.result_var = tk.StringVar(value="✨ 特效点名 ✨")
        self.result_label = tk.Label(self.content_frame, textvariable=self.result_var,
                                     font=(self.font_family, self.result_font_size, "bold"),
                                     bg=self.bg_color, fg=self.fg_color,
                                     wraplength=400, justify='center')
        self.result_label.pack(pady=(30, 30), fill=tk.X)

        effect_btn = self.create_button(self.content_frame, "🎉 开始特效点名", self.start_effect)
        effect_btn.pack(pady=30, ipadx=20, ipady=10)

        status_frame = tk.Frame(self.content_frame, bg=self.bg_color)
        status_frame.pack(fill=tk.X, pady=(30, 0))
        self.student_count_label = tk.Label(status_frame,
                                            text=f"👩‍🎓 学生: {len(self.students)}人  |  👥 小组: {len(self.groups)}组",
                                            bg=self.bg_color, fg=self.fg_color,
                                            font=(self.font_family, 9))
        self.student_count_label.pack(side=tk.LEFT)

    def create_button(self, parent, text, command):
        btn = tk.Button(parent, text=text, command=command,
                        font=(self.font_family, self.font_size),
                        bg=self.btn_color, fg='white',
                        relief=tk.FLAT, padx=10, pady=8,
                        activebackground=self.btn_color, activeforeground='white')
        return btn

    def show_log(self):
        if hasattr(self, 'fair_log_text') and not self.fair_log_text.winfo_ismapped():
            self.fair_log_text.pack(fill=tk.X, pady=5)

    def hide_log(self):
        if hasattr(self, 'fair_log_text') and self.fair_log_text.winfo_ismapped():
            self.fair_log_text.pack_forget()

    def minimize_window(self):
        self.root.withdraw()
        if self.mini_window is None:
            self.create_mini_window()
        else:
            self.mini_window.deiconify()

    def create_mini_window(self):
        self.mini_window = tk.Toplevel(self.root)
        self.mini_window.overrideredirect(True)
        self.mini_window.attributes('-topmost', True)
        self.mini_window.configure(bg='#34495E')
        self.mini_window.geometry("120x40+{}+{}".format(
            self.root.winfo_x() + 150, self.root.winfo_y() + 200))

        label = tk.Label(self.mini_window, text="📋 点名器", font=('Microsoft YaHei', 10),
                         bg='#34495E', fg='white')
        label.pack(fill=tk.BOTH, expand=True)

        def restore(event):
            self.restore_window()
        label.bind("<Double-Button-1>", restore)
        self.mini_window.bind("<Double-Button-1>", restore)

        def start_drag(event):
            self.mini_drag_x = event.x
            self.mini_drag_y = event.y
        def on_drag(event):
            x = self.mini_window.winfo_x() + (event.x - self.mini_drag_x)
            y = self.mini_window.winfo_y() + (event.y - self.mini_drag_y)
            self.mini_window.geometry(f"+{x}+{y}")
        self.mini_window.bind("<Button-1>", start_drag)
        self.mini_window.bind("<B1-Motion>", on_drag)
        label.bind("<Button-1>", start_drag)
        label.bind("<B1-Motion>", on_drag)

        self._force_topmost(self.mini_window)

    def restore_window(self):
        if self.mini_window:
            self.mini_window.destroy()
            self.mini_window = None
        self.root.deiconify()

    def speak(self, text):
        if not self.tts_enabled or not text:
            return
        def _speak():
            with self.speak_lock:
                engine = None
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    engine.setProperty('rate', 180)
                    engine.setProperty('volume', 0.9)
                    engine.say(text)
                    engine.runAndWait()
                except Exception as e:
                    print(f"语音播报失败: {e}")
                finally:
                    if engine:
                        try:
                            engine.stop()
                        except:
                            pass
        threading.Thread(target=_speak, daemon=True).start()

    def toggle_tts(self, var):
        self.tts_enabled = var.get()
        self.config["tts_enabled"] = self.tts_enabled
        save_config(self.config)

    def open_duration_settings(self):
        win = tk.Toplevel(self.get_parent_window())
        win.title("停留时间设置")
        win.geometry("300x150")
        win.configure(bg='#ECF0F1')
        win.overrideredirect(True)
        win.transient(self.get_parent_window())
        win.grab_set()
        x = (self.root.winfo_screenwidth() - 300) // 2
        y = (self.root.winfo_screenheight() - 150) // 2
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text="结果停留时间 (毫秒):", bg='#ECF0F1', font=('Microsoft YaHei', 11)).pack(pady=10)
        duration_var = tk.IntVar(value=self.display_duration)
        tk.Entry(win, textvariable=duration_var, width=10, font=('Microsoft YaHei', 12)).pack(pady=5)

        def save_duration():
            val = duration_var.get()
            if val < 500 or val > 10000:
                messagebox.showwarning("提示", "建议设置在 500~10000 毫秒之间")
                return
            self.display_duration = val
            self.config["display_duration"] = val
            save_config(self.config)
            messagebox.showinfo("成功", f"停留时间已设置为 {val} 毫秒")
            win.destroy()

        btn_frame = tk.Frame(win, bg='#ECF0F1')
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="保存", command=save_duration,
                  bg='#2ECC71', fg='white', padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=win.destroy,
                  bg='#E74C3C', fg='white', padx=15).pack(side=tk.LEFT, padx=5)

        self._force_topmost(win)

    def register_hotkeys(self):
        try:
            import keyboard
            keyboard.add_hotkey('f2', lambda: self.root.after(0, self.start_roll_call))
            keyboard.add_hotkey('f3', lambda: self.root.after(0, self.start_roll_group))
            keyboard.add_hotkey('ctrl+m', lambda: self.root.after(0, self.minimize_window))
        except Exception as e:
            print(f"热键注册失败（可能需要管理员权限）: {e}")

    def schedule_after(self, ms, func):
        aid = self.root.after(ms, func)
        self.after_ids.add(aid)
        return aid

    def cancel_after(self, aid):
        if aid:
            try:
                self.root.after_cancel(aid)
            except:
                pass
            self.after_ids.discard(aid)

    def cancel_linger(self):
        self.cancel_after(self.linger_after)
        self.linger_after = None

    def set_busy(self, state):
        self.busy = state
        btns = []
        for attr in ['call_btn', 'group_btn', 'batch5_btn', 'batch10_btn', 'fair_btn']:
            if hasattr(self, attr) and getattr(self, attr) is not None:
                btns.append(getattr(self, attr))
        for btn in btns:
            btn.config(state=tk.DISABLED if state else tk.NORMAL)

    # ---------- 点名逻辑（应用权重） ----------
    def start_roll_call(self):
        if self.busy:
            return
        if not self.students:
            messagebox.showwarning("提示", "学生名单为空！")
            return
        self.set_busy(True)
        self.cancel_linger()
        self.hide_log()
        self.rolling = True
        self.roll_stop = self.schedule_after(1500, self.stop_roll_call)
        self.roll_name()

    def roll_name(self):
        if not self.rolling:
            return
        name = self.weighted_choice(self.students)
        self.result_var.set(f"🎲 {name}")
        self.roll_after = self.schedule_after(50, self.roll_name)

    def stop_roll_call(self):
        if not self.rolling:
            return
        self.rolling = False
        self.cancel_after(self.roll_after)
        self.roll_after = None
        self.cancel_after(self.roll_stop)
        self.roll_stop = None
        name = self.weighted_choice(self.students)
        self.result_var.set(f"🎉 {name} 🎉")
        self.speak(name)
        self.history.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 点名: {name}")
        if len(self.history) > 200:
            self.history = self.history[-200:]
        save_binary_data(HISTORY_BIN, self.history)
        self.linger_after = self.schedule_after(self.display_duration, self.reset_result)
        self.set_busy(False)

    def start_roll_group(self):
        if self.busy:
            return
        if not self.groups:
            messagebox.showwarning("提示", "小组名单为空！")
            return
        self.set_busy(True)
        self.cancel_linger()
        self.hide_log()
        self.group_rolling = True
        self.group_roll_stop = self.schedule_after(1500, self.stop_roll_group)
        self.roll_group()

    def roll_group(self):
        if not self.group_rolling:
            return
        group = self.rng.choice(self.groups)  # 小组均匀随机
        self.result_var.set(f"🏆 {group}")
        self.group_roll_after = self.schedule_after(50, self.roll_group)

    def stop_roll_group(self):
        if not self.group_rolling:
            return
        self.group_rolling = False
        self.cancel_after(self.group_roll_after)
        self.group_roll_after = None
        self.cancel_after(self.group_roll_stop)
        self.group_roll_stop = None
        group = self.rng.choice(self.groups)
        self.result_var.set(f"🏆 {group} 🏆")
        self.speak(group)
        self.history.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 抽组: {group}")
        if len(self.history) > 200:
            self.history = self.history[-200:]
        save_binary_data(HISTORY_BIN, self.history)
        self.linger_after = self.schedule_after(self.display_duration, self.reset_result)
        self.set_busy(False)

    def start_batch(self, count):
        if self.busy:
            return
        if not self.students:
            messagebox.showwarning("提示", "名单为空！")
            return
        if len(self.students) < count:
            messagebox.showwarning("提示", f"人数不足{count}人！")
            return
        self.set_busy(True)
        self.cancel_linger()
        self.show_log()
        # 连抽使用均匀随机，保证去重
        self.batch_results = self.rng.sample(self.students, count)
        self.batch_count = count
        self.batch_step = 0
        if hasattr(self, 'fair_log_text'):
            self.fair_log_text.config(state=tk.NORMAL)
            self.fair_log_text.delete('1.0', tk.END)
            self.fair_log_text.insert(tk.END, f"🎯 开始{count}连抽...\n")
            self.fair_log_text.config(state=tk.DISABLED)
        self.batch_next()

    def batch_next(self):
        if self.batch_step >= self.batch_count:
            self.batch_finish()
            return
        name = self.batch_results[self.batch_step]
        self.result_var.set(f"🎯 第{self.batch_step+1}个: {name}")
        self.speak(name)
        self.history.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 连抽: {name}")
        if hasattr(self, 'fair_log_text'):
            self.fair_log_text.config(state=tk.NORMAL)
            self.fair_log_text.insert(tk.END, f"第{self.batch_step+1}个: {name}\n")
            self.fair_log_text.see(tk.END)
            self.fair_log_text.config(state=tk.DISABLED)
        self.batch_step += 1
        self.schedule_after(400, self.batch_next)

    def batch_finish(self):
        save_binary_data(HISTORY_BIN, self.history)
        self.result_var.set(f"🎉 连抽完成! {len(self.batch_results)}人")
        if hasattr(self, 'fair_log_text'):
            self.fair_log_text.config(state=tk.NORMAL)
            self.fair_log_text.insert(tk.END, "\n🎉 最终结果: " + "、".join(self.batch_results) + "\n")
            self.fair_log_text.config(state=tk.DISABLED)
        self.linger_after = self.schedule_after(self.display_duration, self.reset_result)
        self.set_busy(False)

    # ---------- 公平模式（重写，增加算法原理日志） ----------
    def toggle_fair_mode(self):
        if self.busy and not self.fair_active:
            return
        if self.fair_active:
            self.exit_fair_mode()
            if self.current_mode == "fair":
                self.fair_btn.config(text="⚖️ 进入公平模式", command=self.toggle_fair_mode, bg=self.btn_color)
                self.fair_status_label.config(text="")
                self.hide_log()
                self.result_var.set("公平模式")
            return

        if len(self.students) < 2:
            messagebox.showwarning("提示", "至少需要2名学生！")
            return
        self.fair_active = True
        self.fair_confirmed = False
        self.fair_pending = self.students.copy()
        if self.current_mode == "fair":
            self.fair_btn.config(text="⏳ 确认名单中...", bg='#E67E22')
            self.fair_status_label.config(text="请确认名单", fg='#F1C40F')
        self.show_fair_confirm()

    def show_fair_confirm(self):
        confirm_win = tk.Toplevel(self.get_parent_window())
        confirm_win.title("公平模式 - 确认名单")
        confirm_win.geometry("500x450")
        confirm_win.configure(bg='#2C3E50')
        confirm_win.overrideredirect(True)
        confirm_win.attributes('-topmost', True)
        x = (self.root.winfo_screenwidth() - 500) // 2
        y = (self.root.winfo_screenheight() - 450) // 2
        confirm_win.geometry(f"+{x}+{y}")
        confirm_win.transient(self.get_parent_window())
        confirm_win.grab_set()

        tk.Label(confirm_win, text="📋 公平模式名单确认", font=('Microsoft YaHei', 14, 'bold'),
                 bg='#2C3E50', fg='#ECF0F1').pack(pady=10)
        tk.Label(confirm_win, text=f"总人数: {len(self.fair_pending)} 人",
                 bg='#2C3E50', fg='#BDC3C7').pack()

        text_area = scrolledtext.ScrolledText(confirm_win, height=15,
                                              font=('Microsoft YaHei', 10),
                                              bg='#34495E', fg='#ECF0F1')
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        cols = 4
        for i, name in enumerate(self.fair_pending):
            if i % cols == 0 and i != 0:
                text_area.insert(tk.END, "\n")
            text_area.insert(tk.END, f"{i+1:>3}. {name:<10}")
        text_area.config(state=tk.DISABLED)

        countdown_var = tk.IntVar(value=5)

        def update_countdown():
            if not confirm_win.winfo_exists():
                return
            val = countdown_var.get()
            if val > 0:
                countdown_var.set(val - 1)
                confirm_btn.config(text=f"⏳ 请等待 {val} 秒...", state=tk.DISABLED)
                if self.fair_confirm_after:
                    confirm_win.after_cancel(self.fair_confirm_after)
                self.fair_confirm_after = confirm_win.after(1000, update_countdown)
            else:
                confirm_btn.config(text="✅ 确认名单", state=tk.NORMAL, bg='#2ECC71')
                self.fair_confirm_after = None

        btn_frame = tk.Frame(confirm_win, bg='#2C3E50')
        btn_frame.pack(pady=10)

        def on_confirm():
            if self.fair_confirm_after:
                confirm_win.after_cancel(self.fair_confirm_after)
                self.fair_confirm_after = None
            self.fair_confirmed = True
            if self.current_mode == "fair":
                self.fair_btn.config(text="🎲 公平抽奖", command=self.fair_draw, bg='#27AE60')
                self.fair_status_label.config(text="已确认，可抽奖", fg='#2ECC71')
            confirm_win.destroy()
            # 显示日志框并写入初始信息
            self.show_log()
            if hasattr(self, 'fair_log_text'):
                self.fair_log_text.config(state=tk.NORMAL)
                self.fair_log_text.delete('1.0', tk.END)
                self.fair_log_text.insert(tk.END, "✅ 名单已确认，点击「公平抽奖」开始抽取\n")
                self.fair_log_text.insert(tk.END, "算法原理：每次从剩余名单中随机抽取一人，\n")
                self.fair_log_text.insert(tk.END, "并记录随机种子、索引等过程参数。\n")
                self.fair_log_text.insert(tk.END, "─" * 30 + "\n")
                self.fair_log_text.config(state=tk.DISABLED)

        def on_cancel():
            if self.fair_confirm_after:
                confirm_win.after_cancel(self.fair_confirm_after)
                self.fair_confirm_after = None
            self.exit_fair_mode()
            if self.current_mode == "fair":
                self.fair_btn.config(text="⚖️ 进入公平模式", command=self.toggle_fair_mode, bg=self.btn_color)
                self.fair_status_label.config(text="")
            self.hide_log()
            confirm_win.destroy()

        confirm_btn = tk.Button(btn_frame, text="⏳ 请等待 5 秒...", state=tk.DISABLED,
                                bg='#95A5A6', fg='white', padx=20, pady=8,
                                font=('Microsoft YaHei', 11), command=on_confirm)
        confirm_btn.pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="取消", command=on_cancel,
                  bg='#E74C3C', fg='white', padx=20, pady=8,
                  font=('Microsoft YaHei', 11)).pack(side=tk.LEFT, padx=10)

        def on_win_close():
            if self.fair_confirm_after:
                confirm_win.after_cancel(self.fair_confirm_after)
                self.fair_confirm_after = None
            on_cancel()
        confirm_win.protocol("WM_DELETE_WINDOW", on_win_close)

        self._force_topmost(confirm_win)
        update_countdown()

    def fair_draw(self):
        if self.busy:
            return
        if not self.fair_active or not self.fair_confirmed:
            messagebox.showinfo("提示", "请先确认名单！")
            return
        if not self.fair_pending:
            self.result_var.set("🎉 所有人已抽完！")
            self.fair_status_label.config(text="抽奖结束", fg='#F39C12')
            if hasattr(self, 'fair_log_text'):
                self.fair_log_text.config(state=tk.NORMAL)
                self.fair_log_text.insert(tk.END, "🎉 所有人已抽完！\n")
                self.fair_log_text.config(state=tk.DISABLED)
            self.set_busy(False)
            return

        self.set_busy(True)
        self.cancel_linger()

        # ---- 开始记录算法步骤 ----
        if hasattr(self, 'fair_log_text'):
            self.fair_log_text.config(state=tk.NORMAL)
            self.fair_log_text.insert(tk.END, "🔍 算法步骤:\n")
            self.fair_log_text.insert(tk.END, f"  1. 当前剩余人数: {len(self.fair_pending)}\n")
            # 使用时间种子
            seed = int(time.time() * 1000) % 10000
            random.seed(seed)
            idx = random.randint(0, len(self.fair_pending) - 1)
            name = self.fair_pending.pop(idx)
            self.fair_log_text.insert(tk.END, f"  2. 随机种子: {seed}\n")
            self.fair_log_text.insert(tk.END, f"  3. 抽取索引: {idx} (0-based)\n")
            self.fair_log_text.insert(tk.END, f"  4. 结果: {name}\n")
            self.fair_log_text.insert(tk.END, "─" * 30 + "\n")
            self.fair_log_text.see(tk.END)
            self.fair_log_text.config(state=tk.DISABLED)

        self.result_var.set(f"🎉 {name} 🎉")
        self.speak(name)
        self.fair_history.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 公平抽奖: {name}")
        if len(self.fair_history) > 200:
            self.fair_history = self.fair_history[-200:]
        save_binary_data(FAIR_HISTORY_BIN, self.fair_history)
        remaining = len(self.fair_pending)
        self.fair_status_label.config(text=f"已抽 {len(self.students)-remaining} 人", fg='#2ECC71')

        # 设定恢复
        self.linger_after = self.schedule_after(self.display_duration, self.reset_result)
        self.set_busy(False)

    def exit_fair_mode(self):
        self.fair_active = False
        self.fair_confirmed = False
        self.fair_pending = []
        if self.fair_confirm_after:
            try:
                self.root.after_cancel(self.fair_confirm_after)
            except:
                pass
            self.fair_confirm_after = None
        self.hide_log()

    def start_effect(self):
        if self.busy:
            return
        if not self.students:
            messagebox.showwarning("提示", "学生名单为空！")
            return
        self.set_busy(True)
        name = self.weighted_choice(self.students)
        self.speak(name)
        self.history.append(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 特效点名: {name}")
        if len(self.history) > 200:
            self.history = self.history[-200:]
        save_binary_data(HISTORY_BIN, self.history)

        effect_win = tk.Toplevel(self.root)
        effect_win.overrideredirect(True)
        effect_win.attributes('-topmost', True)
        screen_w = effect_win.winfo_screenwidth()
        screen_h = effect_win.winfo_screenheight()
        effect_win.geometry(f"{screen_w}x{screen_h}+0+0")
        effect_win.configure(bg='white')
        effect_win.attributes('-alpha', 0.88)

        canvas = tk.Canvas(effect_win, width=screen_w, height=screen_h,
                           bg='white', highlightthickness=0)
        canvas.pack()

        canvas.create_text(screen_w//2, screen_h//2 - 30,
                           text=name,
                           font=(self.font_family, 80, 'bold'),
                           fill='#FF6600')

        emoji_list = ['🎉', '✨', '⭐', '🌟', '💫', '🎊', '🎈', '🎁', '❤️', '🔥',
                      '🌈', '🦄', '🎵', '💖', '💎', '🎀', '🌸', '🌺', '🌻', '🌷',
                      '🍀', '🎶', '💝', '🌟', '🌈', '⚡', '🔥', '💥', '🎇', '🎆']
        birds = []
        for _ in range(60):
            x = random.randint(50, screen_w-50)
            y = random.randint(50, screen_h-50)
            emoji = random.choice(emoji_list)
            size = random.randint(24, 50)
            color = random.choice(['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4',
                                   '#FFEAA7', '#DDA0DD', '#FF9F43', '#EE5A24'])
            bird = canvas.create_text(x, y, text=emoji, font=('Segoe UI Emoji', size),
                                      fill=color)
            dx = random.uniform(-3, 3)
            dy = random.uniform(-3, 3)
            if abs(dx) < 0.5: dx = 1
            if abs(dy) < 0.5: dy = 1
            birds.append([bird, x, y, dx, dy])

        def animate_birds():
            if not effect_win.winfo_exists():
                return
            for item in birds:
                bird, x, y, dx, dy = item
                new_x = x + dx
                new_y = y + dy
                if new_x < 20 or new_x > screen_w-20:
                    dx = -dx
                    new_x = x + dx
                if new_y < 20 or new_y > screen_h-20:
                    dy = -dy
                    new_y = y + dy
                canvas.coords(bird, new_x, new_y)
                item[1], item[2], item[3], item[4] = new_x, new_y, dx, dy
            effect_win.after(30, animate_birds)

        animate_birds()

        def close_effect():
            if effect_win.winfo_exists():
                effect_win.destroy()
            self.set_busy(False)
            self.reset_result()

        effect_win.protocol("WM_DELETE_WINDOW", close_effect)
        effect_win.after(3000, close_effect)
        self._force_topmost(effect_win)

    def reset_result(self):
        if self.current_mode == "fair":
            self.result_var.set("公平模式")
        elif self.current_mode == "batch":
            self.result_var.set("连抽模式")
        elif self.current_mode == "effect":
            self.result_var.set("✨ 特效点名 ✨")
        else:
            self.result_var.set("准备就绪")

    def show_history(self):
        if not self.history:
            messagebox.showinfo("历史记录", "暂无记录")
            return
        self._show_text_window("点名历史记录", self.history)

    def show_fair_history(self):
        if not self.fair_history:
            messagebox.showinfo("公平模式历史", "暂无记录")
            return
        self._show_text_window("公平模式历史", self.fair_history)

    def _show_text_window(self, title, data):
        win = tk.Toplevel(self.get_parent_window())
        win.title(title)
        win.geometry("550x400")
        win.configure(bg='#ECF0F1')
        win.attributes('-topmost', True)
        text_area = scrolledtext.ScrolledText(win, wrap=tk.WORD, font=('Microsoft YaHei', 10))
        text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for line in data:
            text_area.insert(tk.END, line + "\n")
        text_area.config(state=tk.DISABLED)
        self._force_topmost(win)

    def import_data(self):
        file_path = filedialog.askopenfilename(
            title="选择导入文件",
            parent=self.get_parent_window(),
            filetypes=[("文本文件", "*.txt"), ("Excel文件", "*.xlsx *.xls")]
        )
        if not file_path:
            return
        try:
            new_list = []
            if file_path.endswith('.txt'):
                for enc in ['utf-8', 'gbk', 'gb2312']:
                    try:
                        with open(file_path, 'r', encoding=enc) as f:
                            new_list = [line.strip() for line in f if line.strip()]
                        break
                    except UnicodeDecodeError:
                        continue
                if not new_list:
                    messagebox.showerror("错误", "文件编码无法识别")
                    return
            elif file_path.endswith(('.xlsx', '.xls')):
                try:
                    import openpyxl
                    wb = openpyxl.load_workbook(file_path, data_only=True)
                    sheet = wb.active
                    for row in sheet.iter_rows(values_only=True):
                        for cell in row:
                            if cell and str(cell).strip():
                                new_list.append(str(cell).strip())
                except ImportError:
                    messagebox.showerror("错误", "请安装 openpyxl: pip install openpyxl")
                    return
            else:
                messagebox.showerror("错误", "不支持的文件格式")
                return
            if not new_list:
                messagebox.showwarning("提示", "未读取到有效名单")
                return
            if messagebox.askyesno("确认", f"将导入 {len(new_list)} 名学生，确认？"):
                self.students = new_list
                self.weights = {k: v for k, v in self.weights.items() if k in self.students}
                save_binary_data(STUDENTS_BIN, self.students)
                save_binary_data(WEIGHTS_BIN, self.weights)
                self.update_status()
                messagebox.showinfo("成功", f"导入 {len(self.students)} 名学生")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    def edit_data(self):
        if not self.verify_password():
            return
        edit_win = tk.Toplevel(self.get_parent_window())
        edit_win.title("编辑名单")
        edit_win.geometry("450x500")
        edit_win.configure(bg='#ECF0F1')
        edit_win.attributes('-topmost', True)
        tk.Label(edit_win, text="学生名单 (每行一个)", font=('Microsoft YaHei', 11),
                 bg='#ECF0F1').pack(pady=5)
        stu_text = scrolledtext.ScrolledText(edit_win, height=12, font=('Microsoft YaHei', 10))
        stu_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        stu_text.insert('1.0', "\n".join(self.students))
        tk.Label(edit_win, text="小组名单 (每行一个)", font=('Microsoft YaHei', 11),
                 bg='#ECF0F1').pack(pady=5)
        group_text = scrolledtext.ScrolledText(edit_win, height=6, font=('Microsoft YaHei', 10))
        group_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        group_text.insert('1.0', "\n".join(self.groups))

        def save_data():
            new_students = [line.strip() for line in stu_text.get('1.0', tk.END).splitlines() if line.strip()]
            new_groups = [line.strip() for line in group_text.get('1.0', tk.END).splitlines() if line.strip()]
            if not new_students:
                messagebox.showwarning("警告", "学生名单不能为空！")
                return
            if not new_groups:
                messagebox.showwarning("警告", "小组名单不能为空！")
                return
            self.students = new_students
            self.groups = new_groups
            self.weights = {k: v for k, v in self.weights.items() if k in self.students}
            save_binary_data(STUDENTS_BIN, self.students)
            save_binary_data(GROUPS_BIN, self.groups)
            save_binary_data(WEIGHTS_BIN, self.weights)
            self.update_status()
            messagebox.showinfo("成功", "名单已保存")
            edit_win.destroy()

        btn_frame = tk.Frame(edit_win, bg='#ECF0F1')
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="保存", command=save_data,
                  bg='#2ECC71', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=edit_win.destroy,
                  bg='#E74C3C', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        self._force_topmost(edit_win)

    def open_weight_settings(self):
        if not self.verify_password():
            return
        win = tk.Toplevel(self.get_parent_window())
        win.title("权重设置")
        win.geometry("450x400")
        win.configure(bg='#ECF0F1')
        win.attributes('-topmost', True)
        tk.Label(win, text="权重越大，被抽中概率越高 (0.1~10.0)",
                 bg='#ECF0F1', font=('Microsoft YaHei', 10)).pack(pady=5)

        frame = tk.Frame(win, bg='#ECF0F1')
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas = tk.Canvas(frame, bg='#ECF0F1', highlightthickness=0)
        scroll = tk.Scrollbar(frame, orient=tk.VERTICAL, command=canvas.yview)
        inner = tk.Frame(canvas, bg='#ECF0F1')
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        def on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", on_mousewheel)
        def unbind_mousewheel():
            canvas.unbind_all("<MouseWheel>")
        win.protocol("WM_DELETE_WINDOW", lambda: [unbind_mousewheel(), win.destroy()])

        weight_vars = {}
        for i, name in enumerate(self.students):
            row = tk.Frame(inner, bg='#ECF0F1')
            row.pack(fill=tk.X, pady=2)
            tk.Label(row, text=f"{i+1}. {name}", bg='#ECF0F1', width=15, anchor='w').pack(side=tk.LEFT)
            var = tk.DoubleVar(value=self.weights.get(name, 1.0))
            weight_vars[name] = var
            spin = tk.Spinbox(row, from_=0.1, to=10.0, increment=0.1, textvariable=var, width=8)
            spin.pack(side=tk.LEFT, padx=5)
            tk.Button(row, text="重置", command=lambda v=var: v.set(1.0),
                      bg='#95A5A6', fg='white', padx=5).pack(side=tk.LEFT, padx=2)

        def save_weights():
            for name, var in weight_vars.items():
                self.weights[name] = var.get()
            save_binary_data(WEIGHTS_BIN, self.weights)
            messagebox.showinfo("成功", "权重已保存")
            unbind_mousewheel()
            win.destroy()

        btn_frame = tk.Frame(win, bg='#ECF0F1')
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="保存", command=save_weights,
                  bg='#2ECC71', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="关闭", command=lambda: [unbind_mousewheel(), win.destroy()],
                  bg='#95A5A6', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        self._force_topmost(win)

    def verify_password(self):
        stored_hash = self.config.get("admin_password_hash", DEFAULT_CONFIG["admin_password_hash"])
        parent = self.get_parent_window()
        pwd_win = tk.Toplevel(parent)
        pwd_win.title("验证密码")
        pwd_win.geometry("300x150")
        pwd_win.configure(bg='#ECF0F1')
        pwd_win.overrideredirect(True)
        x = (self.root.winfo_screenwidth() - 300) // 2
        y = (self.root.winfo_screenheight() - 150) // 2
        pwd_win.geometry(f"+{x}+{y}")
        pwd_win.transient(parent)
        pwd_win.grab_set()

        tk.Label(pwd_win, text="请输入管理员密码", font=('Microsoft YaHei', 12),
                 bg='#ECF0F1').pack(pady=15)
        pwd_var = tk.StringVar()
        entry = tk.Entry(pwd_win, textvariable=pwd_var, show="*", width=20, font=('Microsoft YaHei', 12))
        entry.pack(pady=5)
        entry.focus()

        result = [False]

        def confirm():
            if hashlib.sha256(pwd_var.get().encode()).hexdigest() == stored_hash:
                result[0] = True
                pwd_win.destroy()
            else:
                messagebox.showerror("错误", "密码错误")
                pwd_var.set("")
                entry.focus()

        def cancel():
            result[0] = False
            pwd_win.destroy()

        entry.bind("<Return>", lambda e: confirm())
        btn_frame = tk.Frame(pwd_win, bg='#ECF0F1')
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="确认", command=confirm,
                  bg='#2ECC71', fg='white', padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=cancel,
                  bg='#E74C3C', fg='white', padx=15).pack(side=tk.LEFT, padx=5)

        self._force_topmost(pwd_win)
        self.root.wait_window(pwd_win)
        return result[0]

    def change_password(self):
        if not self.verify_password():
            return
        win = tk.Toplevel(self.get_parent_window())
        win.title("修改密码")
        win.geometry("350x200")
        win.configure(bg='#ECF0F1')
        win.overrideredirect(True)
        x = (self.root.winfo_screenwidth() - 350) // 2
        y = (self.root.winfo_screenheight() - 200) // 2
        win.geometry(f"+{x}+{y}")
        win.transient(self.get_parent_window())
        win.grab_set()

        tk.Label(win, text="新密码:", bg='#ECF0F1', font=('Microsoft YaHei', 10)).pack(pady=5)
        pwd1 = tk.StringVar()
        tk.Entry(win, textvariable=pwd1, show="*", width=20).pack(pady=5)
        tk.Label(win, text="确认密码:", bg='#ECF0F1', font=('Microsoft YaHei', 10)).pack(pady=5)
        pwd2 = tk.StringVar()
        tk.Entry(win, textvariable=pwd2, show="*", width=20).pack(pady=5)

        def save_pwd():
            if pwd1.get() != pwd2.get():
                messagebox.showerror("错误", "两次密码不一致")
                return
            if len(pwd1.get()) < 4:
                messagebox.showwarning("提示", "密码至少4位")
                return
            self.config["admin_password_hash"] = hashlib.sha256(pwd1.get().encode()).hexdigest()
            save_config(self.config)
            messagebox.showinfo("成功", "密码已修改")
            win.destroy()

        btn_frame = tk.Frame(win, bg='#ECF0F1')
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="保存", command=save_pwd,
                  bg='#2ECC71', fg='white', padx=15).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="取消", command=win.destroy,
                  bg='#E74C3C', fg='white', padx=15).pack(side=tk.LEFT, padx=5)
        self._force_topmost(win)

    def open_settings(self):
        win = tk.Toplevel(self.get_parent_window())
        win.title("个性化设置")
        win.geometry("450x550")
        win.configure(bg='#ECF0F1')
        win.overrideredirect(True)
        x = (self.root.winfo_screenwidth() - 450) // 2
        y = (self.root.winfo_screenheight() - 550) // 2
        win.geometry(f"+{x}+{y}")
        win.transient(self.get_parent_window())
        win.grab_set()

        config = self.config.copy()
        row = 0
        tk.Label(win, text="个性化设置", font=('Microsoft YaHei', 14, 'bold'),
                 bg='#ECF0F1').grid(row=row, column=0, columnspan=2, pady=10); row += 1

        tk.Label(win, text="背景色:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        bg_var = tk.StringVar(value=config["bg_color"])
        tk.Entry(win, textvariable=bg_var, width=12).grid(row=row, column=1, sticky='w', pady=5); row += 1

        tk.Label(win, text="文字色:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        fg_var = tk.StringVar(value=config["fg_color"])
        tk.Entry(win, textvariable=fg_var, width=12).grid(row=row, column=1, sticky='w', pady=5); row += 1

        tk.Label(win, text="按钮色:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        btn_var = tk.StringVar(value=config["btn_color"])
        tk.Entry(win, textvariable=btn_var, width=12).grid(row=row, column=1, sticky='w', pady=5); row += 1

        tk.Label(win, text="窗口宽度:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        width_var = tk.IntVar(value=config.get("window_width", 420))
        tk.Spinbox(win, from_=300, to=800, textvariable=width_var, width=8).grid(row=row, column=1, sticky='w', pady=5); row += 1

        tk.Label(win, text="窗口高度:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        height_var = tk.IntVar(value=config.get("window_height", 520))
        tk.Spinbox(win, from_=300, to=800, textvariable=height_var, width=8).grid(row=row, column=1, sticky='w', pady=5); row += 1

        tk.Label(win, text="字体:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        font_var = tk.StringVar(value=config["font_family"])
        font_combo = ttk.Combobox(win, textvariable=font_var,
                                  values=["Microsoft YaHei", "SimHei", "Arial", "Segoe UI", "TkDefaultFont"])
        font_combo.grid(row=row, column=1, sticky='w', pady=5); row += 1

        tk.Label(win, text="按钮字体大小:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        size_var = tk.IntVar(value=config["font_size"])
        tk.Spinbox(win, from_=8, to=24, textvariable=size_var, width=8).grid(row=row, column=1, sticky='w', pady=5); row += 1

        tk.Label(win, text="结果字体大小:", bg='#ECF0F1', anchor='e').grid(row=row, column=0, sticky='e', pady=5)
        result_size_var = tk.IntVar(value=config["result_font_size"])
        tk.Spinbox(win, from_=16, to=60, textvariable=result_size_var, width=8).grid(row=row, column=1, sticky='w', pady=5); row += 1

        def apply_settings():
            config["bg_color"] = bg_var.get()
            config["fg_color"] = fg_var.get()
            config["btn_color"] = btn_var.get()
            config["font_family"] = font_var.get()
            config["font_size"] = size_var.get()
            config["result_font_size"] = result_size_var.get()
            config["window_width"] = width_var.get()
            config["window_height"] = height_var.get()
            save_config(config)
            messagebox.showinfo("提示", "设置已保存，即将重启应用")
            win.destroy()
            self.restart_program()

        btn_frame = tk.Frame(win, bg='#ECF0F1')
        btn_frame.grid(row=row, column=0, columnspan=2, pady=20)
        tk.Button(btn_frame, text="应用并重启", command=apply_settings,
                  bg='#2ECC71', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="关闭", command=win.destroy,
                  bg='#95A5A6', fg='white', padx=20).pack(side=tk.LEFT, padx=5)
        self._force_topmost(win)

    def show_help(self):
        help_text = """
📖 课堂轻松点名助手 - 使用说明

本软件提供6种模式，可在「设置」→「模式选择」中切换（切换后自动重启）。

1. 普通模式：点名、抽组、五连抽、十连抽。
2. 精简模式：仅保留点名和抽组。
3. 公平模式：每人抽中一次后才重复，需确认名单，并展示算法步骤。
4. 连抽模式：专用连抽页面，结果汇总展示。
5. 特效模式：全屏Emoji飘动特效展示。
6. 极小化模式：悬浮小挂件，一键抽人，适合PPT全屏时使用。

快捷键：
   F2: 随机点名
   F3: 随机抽组
   Ctrl+M: 最小化（悬浮球双击恢复）

设置中可调整语音播报、结果停留时间、颜色字体等。

管理员初始密码是114514（哼~哼~哼~啊啊啊啊啊啊啊啊啊啊↗(っ °Д °;)っ）
"""
        messagebox.showinfo("使用说明", help_text)

    def show_about(self):
        about_text = """
课堂轻松点名助手
版本 2.5

开发者: 陈恩祈 (Chenenqi)
(=^·ω·^=)
© 2026 Chenenqi  中国·上海

基于 Python + tkinter 开发。
开源协议: MIT
"""
        messagebox.showinfo("关于", about_text)

    def update_status(self):
        if hasattr(self, 'student_count_label'):
            self.student_count_label.config(
                text=f"👩‍🎓 学生: {len(self.students)}人  |  👥 小组: {len(self.groups)}组"
            )

    def quit_app(self):
        for aid in list(self.after_ids):
            try:
                self.root.after_cancel(aid)
            except:
                pass
        self.after_ids.clear()
        self.cancel_linger()

        self.rolling = False
        self.group_rolling = False
        self.exit_fair_mode()
        self.stop_minimal_mode()

        if self.mini_window:
            try:
                self.mini_window.destroy()
            except:
                pass
            self.mini_window = None

        save_binary_data(HISTORY_BIN, self.history)
        save_binary_data(FAIR_HISTORY_BIN, self.fair_history)
        self.root.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = ClassroomCaller()
