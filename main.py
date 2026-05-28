import os
import json
import random
import shutil
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.scrollview import ScrollView
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.resources import resource_find
from kivy.core.window import Window

# 设置输入法模式为平移（避免遮挡）
Window.softinput_mode = 'pan'

# ---------- 注册自定义字体 ----------
def register_chinese_font():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(base_dir, 'assets', 'fonts', 'DroidSansFallback.ttf')
    if os.path.exists(font_path):
        LabelBase.register(name='MyChineseFont', fn_regular=font_path)
        return 'MyChineseFont'
    if os.path.exists('assets/fonts/DroidSansFallback.ttf'):
        LabelBase.register(name='MyChineseFont', fn_regular='assets/fonts/DroidSansFallback.ttf')
        return 'MyChineseFont'
    return None

CHINESE_FONT = register_chinese_font()
def font_or_default():
    return CHINESE_FONT

# ---------- 数据管理 ----------
class VocabData:
    def __init__(self):
        self.groups = {}
        self.mistakes = {
            "dictation": [], "listening": [],
            "stubborn_dictation": [], "stubborn_listening": []
        }
        # 外部可访问目录
        self.external_data_dir = os.path.join('/sdcard', 'Android', 'data', 'org.kileykam.vocabtool', 'files')
        self.json_file_path = os.path.join(self.external_data_dir, "grouped_vocab.json")
        self.mistakes_file_path = os.path.join(self.external_data_dir, "mistakes.json")
        self.audio_dir = os.path.join(self.external_data_dir, "audio_cache")
        self._prepare_external_data()
        self.load_data()
        self.load_mistakes()

    def _prepare_external_data(self):
        try:
            os.makedirs(self.external_data_dir, exist_ok=True)
            os.makedirs(self.audio_dir, exist_ok=True)
            if not os.path.exists(self.json_file_path):
                default_json = resource_find('assets/default_vocab.json')
                if default_json and os.path.exists(default_json):
                    shutil.copy2(default_json, self.json_file_path)
                else:
                    demo = {"1": [{"en": "hello", "ch": "你好"}], "2": [{"en": "world", "ch": "世界"}]}
                    with open(self.json_file_path, 'w', encoding='utf-8') as f:
                        json.dump(demo, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"准备外部数据失败: {e}")

    def load_data(self):
        if os.path.exists(self.json_file_path):
            try:
                with open(self.json_file_path, 'r', encoding='utf-8') as f:
                    self.groups = json.load(f)
            except:
                self.groups = {"1": []}
        else:
            self.groups = {"1": [{"en": "hello", "ch": "你好"}]}

    def load_mistakes(self):
        if os.path.exists(self.mistakes_file_path):
            try:
                with open(self.mistakes_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        for k in self.mistakes:
                            self.mistakes[k] = data.get(k, [])
            except:
                pass

    def save_mistakes(self):
        try:
            with open(self.mistakes_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.mistakes, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"保存错题本失败: {e}")

    def get_local_related_words(self, target_word):
        if '99' not in self.groups or not self.groups['99']:
            return []
        target_en = target_word['en'].strip().lower()
        stem = target_en[:4] if len(target_en) >= 4 else target_en
        related = []
        for w in self.groups['99']:
            w_en = w['en'].strip().lower()
            if (len(w_en) >= 4 and len(target_en) >= 4 and (stem in w_en or w_en.startswith(stem))) or \
                    (len(w_en) > 3 and w_en in target_en):
                related.append(w)
        return related[:3]

# ---------- UI 界面 ----------
class MainMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=40, spacing=30)
        layout.add_widget(Label(text="🌟 英语竞赛专属助记工具 🌟", font_size='40sp',
                                size_hint_y=0.25, font_name=font_or_default()))
        grid = GridLayout(cols=2, spacing=25, size_hint_y=0.6)
        btn1 = Button(text="📖 单词背记", font_size='26sp', font_name=font_or_default())
        btn1.bind(on_release=lambda x: self.go_to_mode('memory'))
        btn2 = Button(text="✍️ 看中默英", font_size='26sp', font_name=font_or_default())
        btn2.bind(on_release=lambda x: self.go_to_mode('dictation'))
        btn3 = Button(text="🎧 听音拼写", font_size='26sp', font_name=font_or_default())
        btn3.bind(on_release=lambda x: self.go_to_mode('listening'))
        btn4 = Button(text="📓 错题/顽固练习中心", font_size='26sp', font_name=font_or_default(),
                      background_color=(0.2, 0.5, 0.8, 1))
        btn4.bind(on_release=lambda x: self.go_to_mode('mistake'))
        grid.add_widget(btn1)
        grid.add_widget(btn2)
        grid.add_widget(btn3)
        grid.add_widget(btn4)
        layout.add_widget(grid)
        exit_btn = Button(text="🚪 退出程序", font_size='20sp', size_hint_y=0.15,
                          background_color=(0.7, 0.7, 0.7, 1), font_name=font_or_default())
        exit_btn.bind(on_release=lambda x: App.get_running_app().stop())
        layout.add_widget(exit_btn)
        self.add_widget(layout)

    def go_to_mode(self, mode):
        if mode == 'mistake':
            self.manager.current = 'mistake_menu'
        else:
            self.manager.get_screen('group_select').next_mode = mode
            self.manager.current = 'group_select'

class GroupSelectScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.next_mode = 'memory'
        self.main_layout = BoxLayout(orientation='vertical', padding=20, spacing=15)
        self.add_widget(self.main_layout)

    def on_enter(self):
        self.main_layout.clear_widgets()
        self.main_layout.add_widget(
            Label(text="👉 请选择要练习的组别", font_size='28sp', size_hint_y=0.1,
                  font_name=font_or_default()))
        valid_keys = [k for k in db.groups.keys() if k.isdigit() and k != '99']
        valid_keys.sort(key=int)
        cols_count = 4 if len(valid_keys) <= 20 else 5
        grid = GridLayout(cols=cols_count, spacing=12, size_hint_y=None,
                          row_default_height=100, row_force_default=True)
        grid.bind(minimum_height=grid.setter('height'))
        theme_names = {"21": "食物", "22": "身体", "23": "动物", "24": "运动", "25": "职业", "26": "服装"}
        for g_str in valid_keys:
            count = len(db.groups.get(g_str, []))
            suffix = f" ({theme_names[g_str]})" if g_str in theme_names else ""
            btn_text = f"第 {g_str} 组{suffix}\n[{count} 词]"
            btn = Button(text=btn_text, font_size='15sp', halign='center', font_name=font_or_default())
            btn.bind(on_release=lambda x, g=g_str: self.start_practice(g, False))
            grid.add_widget(btn)
        all_words_list = []
        for k in valid_keys:
            all_words_list.extend(db.groups.get(k, []))
        if all_words_list:
            btn_all = Button(text=f"🎯 全部单词\n[{len(all_words_list)} 词]", font_size='15sp',
                             halign='center', background_color=(0.1, 0.6, 0.6, 1),
                             font_name=font_or_default())
            btn_all.bind(on_release=lambda x: self.start_practice('0', True))
            grid.add_widget(btn_all)
        if '99' in db.groups and db.groups['99']:
            g99_count = len(db.groups.get('99', []))
            btn_99 = Button(text=f"🌟 99 拓展联想组\n[{g99_count} 词]", font_size='15sp',
                            halign='center', background_color=(0.8, 0.5, 0.2, 1),
                            font_name=font_or_default())
            btn_99.bind(on_release=lambda x: self.start_practice('99', False))
            grid.add_widget(btn_99)
        scroll_container = ScrollView(size_hint_y=0.75)
        scroll_container.add_widget(grid)
        self.main_layout.add_widget(scroll_container)
        back_btn = Button(text="↩️ 返回主菜单", font_size='20sp', size_hint_y=0.15,
                          font_name=font_or_default())
        back_btn.bind(on_release=self.back)
        self.main_layout.add_widget(back_btn)

    def start_practice(self, group_id, is_all=False):
        if is_all:
            words = []
            for k in db.groups.keys():
                if k.isdigit() and k != '99':
                    words.extend(db.groups.get(k, []))
            title = "全部生成单词"
        else:
            words = db.groups.get(group_id, [])
            title = f"第 {group_id} 组" if group_id != '99' else "第 99 组拓展"
        if not words:
            return
        p_screen = self.manager.get_screen('practice')
        p_screen.setup_session(words, self.next_mode, title)
        self.manager.current = 'practice'

    def back(self, instance):
        self.manager.current = 'main_menu'

class PracticeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.words = []
        self.mode = 'memory'
        self.current_index = 0
        self.is_mistake_session = False
        self.is_stubborn_session = False
        self.has_errored = False

        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.status_label = Label(text="", font_size='18sp', size_hint_y=0.06,
                                  color=(0.7, 0.7, 0.7, 1), font_name=font_or_default())
        self.layout.add_widget(self.status_label)

        self.scroll_view = ScrollView(size_hint_y=0.62, bar_width=10)

        self.terminal_label = Label(
            text="",
            font_size='26sp',
            size_hint_y=None,
            size_hint_x=1,
            halign='left',
            valign='bottom',
            markup=True,
            font_name=font_or_default()
        )
        self.terminal_label.bind(width=self.update_text_size)
        self.terminal_label.bind(texture_size=self.update_label_height)

        self.scroll_view.add_widget(self.terminal_label)
        self.layout.add_widget(self.scroll_view)

        # 修改 TextInput：增加英文过滤和输入法优化
        self.text_input = TextInput(
            font_size='48sp',
            multiline=False,
            size_hint_y=0.16,
            halign='center',
            padding=[10, 15, 10, 10],
            auto_correction=False,
            input_filter=self._english_filter
        )
        self.text_input.bind(on_text_validate=self.handle_enter_action)
        self.layout.add_widget(self.text_input)

        btn_control_layout = BoxLayout(orientation='horizontal', size_hint_y=0.16, spacing=15)

        self.voice_btn = Button(text="🔊 播放读音 (或输入 R)", font_size='22sp',
                                size_hint_x=0.5, background_color=(0.2, 0.6, 0.4, 1),
                                font_name=font_or_default())
        self.voice_btn.bind(on_release=lambda x: self.trigger_voice_play())

        self.exit_control_btn = Button(text="🚪 退出练习 (或输入 Q)", font_size='22sp',
                                       size_hint_x=0.5, background_color=(0.7, 0.3, 0.3, 1),
                                       font_name=font_or_default())
        self.exit_control_btn.bind(on_release=self.exit_practice)

        btn_control_layout.add_widget(self.voice_btn)
        btn_control_layout.add_widget(self.exit_control_btn)

        self.layout.add_widget(btn_control_layout)
        self.add_widget(self.layout)

    def _english_filter(self, text, from_undo=False):
        """只允许英文字母、数字、空格、短横线、下划线"""
        allowed = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_')
        return ''.join(ch for ch in text if ch in allowed)

    def update_text_size(self, instance, val):
        self.terminal_label.text_size = (val - 20, None)

    def update_label_height(self, instance, size):
        self.terminal_label.height = max(size[1], self.scroll_view.height)

    def print_to_terminal(self, text):
        self.terminal_label.text += text + "\n"
        Clock.schedule_once(lambda dt: setattr(self.scroll_view, 'scroll_y', 0), 0.01)

    def setup_session(self, words, mode, title, is_mistake=False, is_stubborn=False):
        self.words = list(words)
        random.shuffle(self.words)
        self.mode = mode
        self.current_index = 0
        self.is_mistake_session = is_mistake
        self.is_stubborn_session = is_stubborn
        self.has_errored = False

        self.text_input.text = ""
        self.terminal_label.text = ""
        self.terminal_label.height = self.scroll_view.height

        self.print_to_terminal(f"[color=00ffcc]============ 🚀 练习开始：{title} ({mode}模式) ============[/color]")

        if self.mode == 'memory':
            self.text_input.opacity = 0
            self.text_input.disabled = True
            self.voice_btn.text = "➡️ 下一个"
        else:
            self.text_input.opacity = 1
            self.text_input.disabled = False
            self.voice_btn.text = "🔊 播放读音 (或输入 R)"

        self.update_ui()

    def update_ui(self):
        if self.current_index >= len(self.words):
            self.print_to_terminal("\n[color=ffcc00]🎉 恭喜！本组单词练习全部顺利结束！点击下方退出。[/color]")
            self.text_input.opacity = 0
            self.text_input.disabled = True
            self.voice_btn.text = "返回主页"
            return

        word = self.words[self.current_index]
        self.status_label.text = f"题组进度: {self.current_index + 1} / {len(self.words)}"
        self.has_errored = False

        prefix = f"\n[color=ffffff][{self.current_index + 1}/{len(self.words)}][/color] "
        if self.mode == 'memory':
            self.print_to_terminal(f"{prefix}单词: [color=00ffff][b]{word['en']}[/b][/color]")
        elif self.mode == 'dictation':
            self.print_to_terminal(f"{prefix}提示(中译英): [color=ffbb00]{word['ch']}[/color]")
            self.focus_input()
        elif self.mode == 'listening':
            self.print_to_terminal(f"{prefix}提示(听音拼写): [color=ffbb00]🎧 [请听发音][/color] 含义: {word['ch']}")
            self.play_voice(word['en'])
            self.focus_input()

    def focus_input(self, *args):
        if self.text_input.opacity == 1 and self.text_input.disabled is False:
            Clock.schedule_once(lambda dt: setattr(self.text_input, 'focus', True), 0.02)

    def trigger_voice_play(self):
        if self.voice_btn.text == "返回主页":
            self.text_input.text = ""
            self.manager.current = 'main_menu'
            return

        if self.mode == 'memory':
            word = self.words[self.current_index]
            if "下一个" not in self.voice_btn.text:
                self.print_to_terminal(f"   💡 中文释义: [color=ffcc00]{word['ch']}[/color]")
                self.voice_btn.text = "➡️ 下一个"
            else:
                self.current_index += 1
                self.voice_btn.text = "👀 看答案"
                self.update_ui()
        else:
            if self.current_index < len(self.words):
                self.play_voice(self.words[self.current_index]['en'])
                self.focus_input()

    def handle_enter_action(self, instance):
        val = self.text_input.text.strip().lower()

        if val == 'q':
            self.exit_practice(None)
            return
        if val == 'r':
            self.trigger_voice_play()
            self.text_input.text = ""
            self.focus_input()
            return

        if self.current_index >= len(self.words):
            return
        word = self.words[self.current_index]

        if val == word['en'].strip().lower():
            related_text = ""
            related = db.get_local_related_words(word)
            if related:
                related_text = " \n      [color=888888]扩展词汇：" + " ｜ ".join(
                    [f"{r['en']} -> {r['ch']}" for r in related]) + "[/color]"

            self.print_to_terminal(f"   [color=00ff00]✅ 正确![/color] 输入: {val}{related_text}")
            self.text_input.text = ""
            self.current_index += 1
            self.update_ui()
        else:
            self.print_to_terminal(
                f"   [color=ff3333]❌ 错误![/color] 输入: '{val}' -> [color=33ff33]正确答案: 【 {word['en']} 】[/color]")
            self.text_input.text = ""
            self.focus_input()

            if not self.has_errored:
                self.has_errored = True
                cat = "dictation" if self.mode == 'dictation' else "listening"
                if not self.is_mistake_session and not self.is_stubborn_session:
                    if word not in db.mistakes[cat]:
                        db.mistakes[cat].append(word)
                elif self.is_mistake_session and not self.is_stubborn_session:
                    stubborn_cat = f"stubborn_{cat}"
                    if word not in db.mistakes[stubborn_cat]:
                        db.mistakes[stubborn_cat].append(word)
                db.save_mistakes()

    def play_voice(self, text):
        safe_name = "".join(c for c in text.strip().lower() if c.isalnum() or c in " -_")
        audio_path = os.path.join(db.audio_dir, f"{safe_name}.mp3")
        if os.path.exists(audio_path):
            sound = SoundLoader.load(audio_path)
            if sound:
                sound.play()

    def exit_practice(self, instance):
        self.text_input.text = ""
        self.manager.current = 'main_menu'

class MistakeMenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=30, spacing=15)
        layout.add_widget(
            Label(text="📓 错题集与顽固复习中心", font_size='32sp', size_hint_y=0.12,
                  font_name=font_or_default()))
        self.info_label = Label(text="", font_size='18sp', size_hint_y=0.15,
                                halign='center', font_name=font_or_default())
        layout.add_widget(self.info_label)
        grid = GridLayout(cols=2, spacing=15, size_hint_y=0.45)
        btn_d = Button(text="✍️ 默写普通错题", font_size='20sp', font_name=font_or_default())
        btn_d.bind(on_release=lambda x: self.start_mistake('dictation', is_stubborn=False))
        btn_l = Button(text="🎧 听写普通错题", font_size='20sp', font_name=font_or_default())
        btn_l.bind(on_release=lambda x: self.start_mistake('listening', is_stubborn=False))
        btn_sd = Button(text="🔴 默写顽固错题", font_size='20sp', font_name=font_or_default(),
                        background_color=(0.9, 0.4, 0.4, 1))
        btn_sd.bind(on_release=lambda x: self.start_mistake('stubborn_dictation', is_stubborn=True))
        btn_sl = Button(text="🔴 听写顽固错题", font_size='20sp', font_name=font_or_default(),
                        background_color=(0.9, 0.4, 0.4, 1))
        btn_sl.bind(on_release=lambda x: self.start_mistake('stubborn_listening', is_stubborn=True))
        grid.add_widget(btn_d)
        grid.add_widget(btn_l)
        grid.add_widget(btn_sd)
        grid.add_widget(btn_sl)
        layout.add_widget(grid)
        clear_box = BoxLayout(orientation='horizontal', spacing=20, size_hint_y=0.14)
        clear_normal = Button(text="🗑️ 清空普通错题", font_size='16sp', font_name=font_or_default(),
                              background_color=(0.7, 0.2, 0.2, 1))
        clear_normal.bind(on_release=lambda x: self.clear_action(target='normal'))
        clear_stubborn = Button(text="🗑️ 清空顽固错题", font_size='16sp', font_name=font_or_default(),
                                background_color=(0.9, 0.1, 0.1, 1))
        clear_stubborn.bind(on_release=lambda x: self.clear_action(target='stubborn'))
        clear_box.add_widget(clear_normal)
        clear_box.add_widget(clear_stubborn)
        layout.add_widget(clear_box)
        back_btn = Button(text="↩️ 返回主菜单", font_size='20sp', size_hint_y=0.14,
                          font_name=font_or_default())
        back_btn.bind(on_release=self.back)
        layout.add_widget(back_btn)
        self.add_widget(layout)

    def on_enter(self):
        d = len(db.mistakes.get('dictation', []))
        l = len(db.mistakes.get('listening', []))
        sd = len(db.mistakes.get('stubborn_dictation', []))
        sl = len(db.mistakes.get('stubborn_listening', []))
        self.info_label.text = f"【普通错题】 默写: {d} | 听写: {l}\n【顽固错题】 默写: {sd} | 听写: {sl}"

    def start_mistake(self, mode_key, is_stubborn):
        words = db.mistakes.get(mode_key, [])
        if not words:
            return
        practice_mode = 'dictation' if 'dictation' in mode_key else 'listening'
        title = "顽固错题本" if is_stubborn else "标准错题本"
        p_screen = self.manager.get_screen('practice')
        p_screen.setup_session(words, practice_mode, title, is_mistake=True, is_stubborn=is_stubborn)
        self.manager.current = 'practice'

    def clear_action(self, target):
        if target == 'normal':
            db.mistakes['dictation'] = []
            db.mistakes['listening'] = []
        elif target == 'stubborn':
            db.mistakes['stubborn_dictation'] = []
            db.mistakes['stubborn_listening'] = []
        db.save_mistakes()
        self.on_enter()

    def back(self, instance):
        self.manager.current = 'main_menu'

class VocabApp(App):
    def build(self):
        global db
        db = VocabData()
        sm = ScreenManager()
        sm.add_widget(MainMenuScreen(name='main_menu'))
        sm.add_widget(GroupSelectScreen(name='group_select'))
        sm.add_widget(PracticeScreen(name='practice'))
        sm.add_widget(MistakeMenuScreen(name='mistake_menu'))
        return sm

if __name__ == '__main__':
    VocabApp().run()