import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont
from PIL import Image, ImageTk
import os, csv

class MapFilterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("夜渡り地図帳")
        self.root.geometry("1400x900")

        self.data = self.load_csv("data.csv")

        self.nightlord_var = tk.IntVar(value=-1)
        self.area_var = tk.IntVar(value=-1)
        self.loc117_var = tk.IntVar(value=-1)
        self.loc313_var = tk.IntVar(value=-1)
        self.loc112_127_var = tk.IntVar(value=-1)

        self.zoom = 0.4
        self.initial_image_path = "assets/initial_image.jpg"

        self.ifchurch_var = tk.IntVar(value=-1)
        self.all_buttons = {
            "nightlord": [],
            "area": [],
            "ifchurch": [],
            "loc112_127": [],
            "loc117": [],
            "loc313": []
        }

        self.current_image = None
        self.current_photo = None
        self.map_image_id = None

        self.create_widgets()

    def load_csv(self, filename):
        rows = []
        with open(filename, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames

            # 表のヘッダーを自動修正
            fixed_fieldnames = []
            for name in fieldnames:
                if name == "loc112/127":   # 位置ずれを検出
                    if "area" not in fieldnames:
                        fixed_fieldnames.append("area")  # area プレースホルダーを挿入
                    fixed_fieldnames.append("loc112_127")
                else:
                    fixed_fieldnames.append(name.replace("112/127", "112_127"))

            for row in reader:
                parsed = {}
                for k, v in zip(fixed_fieldnames, row.values()):
                    try:
                        parsed[k] = int(v)
                    except (ValueError, TypeError):
                        parsed[k] = v
                rows.append(parsed)
        return rows

    def create_widgets(self):
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)

        outer_canvas = tk.Canvas(container, highlightthickness=0)
        vbar = ttk.Scrollbar(container, orient="vertical", command=outer_canvas.yview)
        hbar = ttk.Scrollbar(container, orient="horizontal", command=outer_canvas.xview)
        outer_canvas.configure(yscrollcommand=vbar.set, xscrollcommand=hbar.set)

        vbar.pack(side="right", fill="y")
        hbar.pack(side="bottom", fill="x")
        outer_canvas.pack(side="left", fill="both", expand=True)

        scrollable_frame = ttk.Frame(outer_canvas)
        outer_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

        prefs = ("Yu Gothic UI", "Meiryo UI", "Hiragino Sans", "Noto Sans JP", "MS UI Gothic")
        base = tkfont.nametofont("TkDefaultFont").copy()
        base.configure(size=14, weight="bold")
        for fam in prefs:
            try:
                base.configure(family=fam); break
            except: pass

        def resize_outer(event=None):
            outer_canvas.configure(scrollregion=outer_canvas.bbox("all"))
        scrollable_frame.bind("<Configure>", resize_outer)

        # === 追加：画像の上以外では、外枠（outer_canvas）をホイールでスクロール ===
        def on_global_wheel(e):
            # 今のマウス位置の下にあるウィジェットを取得
            widget_under = self.root.winfo_containing(e.x_root, e.y_root)
            # 画像キャンバス上なら、ここでは何もしない（on_zoom が処理している）
            if widget_under == self.map_canvas:
                return "break"

            # 画像以外の場所 → 外枠をスクロール
            if getattr(e, "delta", 0):  # Windows / macOS
                outer_canvas.yview_scroll(-1 * (e.delta // 120), "units")
            elif getattr(e, "num", None) in (4, 5):  # Linux
                outer_canvas.yview_scroll(-1 if e.num == 4 else 1, "units")
            return "break"

        # グローバルにバインド（画像キャンバス側の on_zoom が 'break' を返すので衝突しない）
        self.root.bind_all("<MouseWheel>", on_global_wheel)  # Win / macOS
        self.root.bind_all("<Button-4>",  on_global_wheel)   # Linux 上スクロール
        self.root.bind_all("<Button-5>",  on_global_wheel)   # Linux 下スクロール
        
        # 左側
        left_frame = ttk.Frame(scrollable_frame)
        left_frame.grid(row=0, column=0, sticky="n", padx=10, pady=5)

        # 右側
        right_frame = ttk.Frame(scrollable_frame)
        right_frame.grid(row=0, column=1, sticky="n", pady=5)

        # ===== 左側の選択エリア =====
        # 上部：夜の王 + 地変
        options_frame = ttk.Frame(right_frame)
        options_frame.grid(row=0, column=0, sticky="ew", pady=5)

        nightlord_frame = ttk.LabelFrame(left_frame, text="夜の王を選択してください", padding="5")
        nightlord_frame.grid(row=0, column=0, sticky="ew", pady=5)
        for idx in range(8):
            img = self.load_image(f"assets/nightlord_{idx}.png", (100, 100))
            btn = tk.Button(nightlord_frame, image=img, relief="flat",
                            command=lambda i=idx: self.select("nightlord", i))
            btn.image = img
            btn.grid(row=idx // 4, column=idx % 4, padx=3, pady=3)
            self.all_buttons["nightlord"].append((btn, idx))

        area_frame = ttk.LabelFrame(left_frame, text="地変を選択してください", padding="5")
        area_frame.grid(row=1, column=0, sticky="ew", pady=5)
        area_options = [("地変なし", 0), ("山嶺", 1), ("火口", 2), ("腐れ森", 3), ("隠れ都ノクラテオ", 5)]
        for i, (name, val) in enumerate(area_options):
            btn = tk.Button(area_frame, text=name, relief="flat",
                            command=lambda v=val: self.select("area", v))
            btn.grid(row=0, column=i, padx=5)
            self.all_buttons["area"].append((btn, val))

        # 下部：各拠点
        ifchurch_frame = ttk.LabelFrame(left_frame, text="黄色で囲った場所は教会ですか？", padding="5")
        ifchurch_frame.grid(row=2, column=0, sticky="ew", pady=5)
        yes_or_no = ttk.LabelFrame(ifchurch_frame, padding="5")
        yes_or_no.grid(row=0,column=0,sticky="ew",pady=5)
        yes_btn = tk.Button(yes_or_no, text="はい", relief="flat",
                            command=lambda: self.select("ifchurch", 1))
        no_btn = tk.Button(yes_or_no, text="いいえ", relief="flat",
                           command=lambda: self.select("ifchurch", 0))
        yes_btn.grid(row=3, column=0, pady=30)
        no_btn.grid(row=1, column=0, pady=30)
        self.all_buttons["ifchurch"] = [(yes_btn, 1), (no_btn, 0)]
        sample_img = self.load_image("assets/sample.jpg", (200, 200))
        sample_label = ttk.Label(ifchurch_frame, image=sample_img)
        sample_label.image = sample_img
        sample_label.grid(row=0, column=2, padx=10)

        # loc117
        loc117_frame = ttk.LabelFrame(left_frame, text="赤枠の拠点Aを選択してください", padding="5")
        loc117_frame.grid(row=4, column=0, sticky="ew", pady=5)
        self.create_loc_widgets(loc117_frame, "loc117")

        # loc112/127
        loc112_127_frame = ttk.LabelFrame(left_frame, text="赤枠の拠点Bを選択してください", padding="5")
        loc112_127_frame.grid(row=5, column=0, sticky="ew", pady=5)
        self.create_loc_widgets(loc112_127_frame, "loc112_127")

        # loc313
        loc313_frame = ttk.LabelFrame(left_frame, text="赤枠の拠点Cを選択してください", padding="5")
        loc313_frame.grid(row=6, column=0, sticky="ew", pady=5)
        self.create_loc_widgets(loc313_frame, "loc313")

        # ===== 右側 =====
        # 上部：マップ表示エリア
        map_frame = ttk.Frame(right_frame, width=800, height=800)
        map_frame.grid_propagate(False)
        map_frame.grid(row=0, column=0, sticky="n", pady=5)

        self.map_canvas = tk.Canvas(map_frame, bg="white", width=800, height=800,
                                    scrollregion=(0, 0, 800, 800))
        self.map_canvas.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(map_frame, orient="vertical", command=self.map_canvas.yview)
        x_scroll = ttk.Scrollbar(map_frame, orient="horizontal", command=self.map_canvas.xview)
        self.map_canvas.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)

        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        self.map_canvas.bind("<ButtonPress-1>", self.start_drag)
        self.map_canvas.bind("<B1-Motion>", self.do_drag)

        self.map_canvas.bind("<MouseWheel>", self.on_zoom)     # Windows / macOS
        self.map_canvas.bind("<Button-4>",  self.on_zoom)      # Linux 上スクロール
        self.map_canvas.bind("<Button-5>",  self.on_zoom)      # Linux 下スクロール

        # 下部：リセットボタンのみ（ズームはマウスホイール）
        control_frame = ttk.Frame(right_frame)
        control_frame.grid(row=1, column=0, pady=10, sticky="ew")
        control_frame.columnconfigure(0, weight=1)

        hint = ttk.Label(control_frame, text="マウスホイールでズーム / ドラッグで移動")
        hint.grid(row=0, column=0, sticky="w")

        reset_btn = ttk.Button(control_frame, text="リセット", command=self.reset_scale)
        reset_btn.grid(row=0, column=1, padx=(6, 0))

        self.map_name_label = ttk.Label(right_frame, text="initial_image.jpg", font=base, anchor="center")
        self.map_name_label.grid(row=2, column=0, pady=10, sticky="ew")

        style = ttk.Style(self.root)
        style.configure(
            "Filter.TButton",
            font=base,   # 文字を大きく太めに
            padding=(16, 10)              # 左右/上下パディングで見た目を大型化
        )
        filter_btn = ttk.Button(
            right_frame, 
            text="絞り込み",
            command=self.filter_data,
            style="Filter.TButton"
        )
        filter_btn.grid(row=3, column=0, pady=10, ipadx=8, ipady=6)

        self.load_initial_image()

    # === ドラッグ ===
    def start_drag(self, event):
        self.map_canvas.scan_mark(event.x, event.y)

    def do_drag(self, event):
        self.map_canvas.scan_dragto(event.x, event.y, gain=1)

    # === ボタンの処理 ===
    def create_loc_widgets(self, parent, loc_type):
        rows = [
            (1, ["なし"]),
            (2, [f"{loc_type}_1", f"{loc_type}_2"]),
            (4, [f"{loc_type}_1", f"{loc_type}_2", f"{loc_type}_3", f"{loc_type}_4"]),
            (9, [f"{loc_type}_{i}" for i in range(1, 10)]),
            (3, [f"{loc_type}_1", f"{loc_type}_2", f"{loc_type}_3"])
        ]
        for row_idx, (btn_count, btn_names) in enumerate(rows):
            row_frame = ttk.Frame(parent)
            row_frame.grid(row=row_idx, column=0, sticky="w", pady=2)
            for col_idx in range(btn_count):
                if row_idx == 0:
                    value = 0
                    btn = tk.Button(row_frame, text=btn_names[col_idx], relief="flat", width=6,
                                    command=lambda v=value, t=loc_type: self.select_loc(v, t))
                else:
                    value = (row_idx * 10 + col_idx + 1) if row_idx < 4 else ((row_idx + 1) * 10 + col_idx + 1)
                    img = self.load_image(f"assets/construct_{row_idx+1}_{col_idx+1}.png", (50, 50))
                    btn = tk.Button(row_frame, image=img, relief="flat",
                                    command=lambda v=value, t=loc_type: self.select_loc(v, t))
                    btn.image = img
                    btn.config(width=50, height=50)
                btn.grid(row=0, column=col_idx, padx=2)
                self.all_buttons[loc_type].append((btn, value))

    def load_image(self, path, max_size):
        try:
            img = Image.open(path)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except Exception:
            return ImageTk.PhotoImage(Image.new("RGB", max_size, "gray"))

    def update_button_states(self, category, selected_value):
        for btn, value in self.all_buttons[category]:
            if value == selected_value:
                btn.config(bg="#90EE90", relief="solid", borderwidth=3)
            else:
                btn.config(bg="SystemButtonFace", relief="flat", borderwidth=1)

    def select(self, category, value):
        if category == "nightlord":
            self.nightlord_var.set(value)
        elif category == "area":
            self.area_var.set(value)
        elif category == "ifchurch":
            self.ifchurch_var.set(value)
        self.update_button_states(category, value)


    def select_loc(self, value, loc_type):
        if loc_type == "loc117":
            self.loc117_var.set(value)
        elif loc_type == "loc313":
            self.loc313_var.set(value)
        elif loc_type == "loc112_127":
            self.loc112_127_var.set(value)
        self.update_button_states(loc_type, value)

    def load_initial_image(self):
        """
        固定パス self.initial_image_path の画像を初期表示する。
        """
        p = self.initial_image_path
        if p and os.path.exists(p):
            try:
                self.current_image = Image.open(p)
                self.scale_image()  # 既存の描画処理を再利用
                return
            except Exception as e:
                self.current_image = None
                self.map_canvas.delete("all")
                self.map_name_label.config(text=f"初期画像の読み込み失敗: {e}")
                return

        # パスが無い／見つからない場合
        self.current_image = None
        self.map_canvas.delete("all")
        self.map_name_label.config(text=f"初期画像が見つかりません: {p}")

    def filter_data(self):
        if -1 in (self.nightlord_var.get(), self.area_var.get(),
                self.ifchurch_var.get(),
                self.loc117_var.get(), self.loc313_var.get(), self.loc112_127_var.get()):
            messagebox.showwarning("メッセージ", "すべてのフィルター条件を選択してください")
            return

        filtered = [
            row for row in self.data
            if row.get("nightlord") == self.nightlord_var.get()
            and row.get("area") == self.area_var.get()
            and row.get("ifchurch") == self.ifchurch_var.get()
            and row.get("loc117") == self.loc117_var.get()
            and row.get("loc313") == self.loc313_var.get()
            and row.get("loc112_127") == self.loc112_127_var.get()
        ]

        if not filtered:
            self.map_canvas.delete("all")
            self.map_name_label.config(text="一致するマップが見つかりません")
            self.load_initial_image()
        else:
            map_id = filtered[0]["map id"]
            image_path = f"JPEG/map_{map_id}.jpg"
            if os.path.exists(image_path):
                self.current_image = Image.open(image_path)
                self.scale_image()
            else:
                self.map_canvas.delete("all")
                self.map_name_label.config(text=f"画像が見つかりません: {image_path}")
                self.load_initial_image()
            self.map_name_label.config(text=f"map_{map_id}.jpg")

    def scale_image(self, *args):
        if self.current_image:
            s = float(self.zoom)
            width  = max(1, int(self.current_image.width  * s))
            height = max(1, int(self.current_image.height * s))
            img = self.current_image.resize((width, height), Image.Resampling.LANCZOS)
            self.current_photo = ImageTk.PhotoImage(img)

            self.map_canvas.delete("all")
            self.map_image_id = self.map_canvas.create_image(0, 0, anchor="nw", image=self.current_photo)
            self.map_canvas.configure(scrollregion=(0, 0, width, height))
    
    def on_zoom(self, event):
        """マウスホイールでズーム。端(上限/下限)では位置を動かさない。"""
        if not self.current_image:
            return "break"

        # 方向判定
        zoom_in = False
        if getattr(event, "delta", 0) != 0:       # Win/macOS
            zoom_in = event.delta > 0
        elif getattr(event, "num", None) in (4, 5):  # Linux
            zoom_in = (event.num == 4)
        else:
            return "break"

        # 現在倍率と希望倍率
        old_zoom = float(self.zoom)
        step = 1.1 if zoom_in else (1/1.1)
        desired = old_zoom * step

        # クランプ（ここを好みで変更）
        MIN_ZOOM, MAX_ZOOM = 0.35, 1.0
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, desired))

        # 端に到達して倍率が変わらないなら、何もしない（位置も動かさない）
        if new_zoom == old_zoom:
            return "break"

        # “実際に変化した倍率”で補正（端での過補正を防ぐ）
        effective = new_zoom / old_zoom
        self.zoom = new_zoom

        # キャンバス座標でのマウス位置（この近辺を保つ）
        cx = self.map_canvas.canvasx(event.x)
        cy = self.map_canvas.canvasy(event.y)

        # 再描画
        self.scale_image()

        # 新しい画像サイズ
        new_w = max(1, int(self.current_image.width  * self.zoom))
        new_h = max(1, int(self.current_image.height * self.zoom))

        # 可視領域
        view_w = self.map_canvas.winfo_width()
        view_h = self.map_canvas.winfo_height()

        # 左上位置: マウス位置基準で補正（effective を使用）
        new_left = cx * effective - event.x
        new_top  = cy * effective - event.y

        # 0..1 に正規化してスクロール
        def moveto_norm(pos_px, total, view):
            if total <= view:
                return 0.0
            # 範囲内クランプ
            pos_px = max(0, min(total - view, pos_px))
            return pos_px / total

        self.map_canvas.xview_moveto(moveto_norm(new_left, new_w, view_w))
        self.map_canvas.yview_moveto(moveto_norm(new_top,  new_h, view_h))

        return "break"

    def reset_scale(self):
        self.zoom = 0.4
        self.scale_image()

def main():
    root = tk.Tk()
    app = MapFilterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
