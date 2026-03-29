"""
Scale Display - Android App (Kivy)
"""
import os
import json
import socket
import threading
import time

import kivy
kivy.require('2.3.0')

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex as hex_c
from kivy.graphics import Color, Rectangle, RoundedRectangle

Window.clearcolor = hex_c('#f0f4f8')

# ─── Palette ──────────────────────────────────────────────────────────────────
NAV_BG    = hex_c('#1a2332')
C_BLUE    = hex_c('#3b82f6')
C_ORANGE  = hex_c('#f97316')
C_RED     = hex_c('#ef4444')
C_GREEN   = hex_c('#22c55e')
C_DARK    = hex_c('#0f172a')
C_CYAN    = hex_c('#38bdf8')
C_TEXT    = hex_c('#1e293b')
C_MUTED   = hex_c('#64748b')
C_WHITE   = hex_c('#ffffff')
C_CARD    = hex_c('#ffffff')

DEFAULT_CFG = {
    "ip": "192.168.1.100",
    "port": 8000,
    "mode": "manual",
    "interval": 2.0
}

# ─── Config ───────────────────────────────────────────────────────────────────
def cfg_path():
    return os.path.join(App.get_running_app().user_data_dir, 'config.json')

def load_cfg():
    try:
        with open(cfg_path(), 'r') as f:
            d = json.load(f)
        for k, v in DEFAULT_CFG.items():
            d.setdefault(k, v)
        return d
    except Exception:
        return DEFAULT_CFG.copy()

def save_cfg(cfg):
    with open(cfg_path(), 'w') as f:
        json.dump(cfg, f)

# ─── Scale TCP ────────────────────────────────────────────────────────────────
def scale_cmd(ip, port, cmd, timeout=5):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((ip, int(port)))
        s.sendall(cmd.encode('ascii'))
        if cmd == 'W':
            buf = b''
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    chunk = s.recv(16)
                except socket.timeout:
                    break
                if not chunk:
                    break
                buf += chunk
                if len(buf.rstrip(b'\r\n')) >= 7:
                    break
            return buf.decode('ascii', errors='replace').strip()
        else:
            try:
                s.settimeout(1)
                s.recv(16)
            except Exception:
                pass
            return 'ok'

# ─── Helpers ──────────────────────────────────────────────────────────────────
def make_btn(text, bg, on_press, size_hint=(1, None), height=dp(54)):
    btn = Button(
        text=text,
        size_hint=size_hint,
        height=height,
        background_normal='',
        background_color=bg,
        color=C_WHITE,
        font_size=sp(16),
        bold=True,
    )
    btn.bind(on_press=on_press)
    return btn

def make_label(text, size=sp(14), color=C_TEXT, bold=False, halign='right'):
    lbl = Label(
        text=text,
        font_size=size,
        color=color,
        bold=bold,
        halign=halign,
        size_hint_y=None,
        height=dp(30),
    )
    lbl.bind(size=lambda *a: setattr(lbl, 'text_size', (lbl.width, None)))
    return lbl

def make_input(hint, text='', input_filter=None):
    ti = TextInput(
        hint_text=hint,
        text=str(text),
        size_hint=(1, None),
        height=dp(48),
        font_size=sp(16),
        multiline=False,
        input_filter=input_filter,
        background_color=C_WHITE,
        foreground_color=C_TEXT,
        padding=[dp(12), dp(10)],
        write_tab=False,
    )
    return ti

# ─── Nav Bar ──────────────────────────────────────────────────────────────────
class NavBar(BoxLayout):
    def __init__(self, sm, **kwargs):
        super().__init__(orientation='horizontal', size_hint=(1, None),
                         height=dp(52), **kwargs)
        self.sm = sm
        with self.canvas.before:
            Color(*NAV_BG)
            self.rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._upd, size=self._upd)

        spacer = Widget()
        self.add_widget(spacer)

        self.btn_weight = Button(
            text='⚖  משקל', size_hint=(None, 1), width=dp(130),
            background_normal='', background_color=C_BLUE,
            color=C_WHITE, font_size=sp(15), bold=True,
        )
        self.btn_settings = Button(
            text='⚙  הגדרות', size_hint=(None, 1), width=dp(130),
            background_normal='', background_color=NAV_BG,
            color=hex_c('#94a3b8'), font_size=sp(15),
        )
        self.btn_weight.bind(on_press=lambda *a: self._go('weight'))
        self.btn_settings.bind(on_press=lambda *a: self._go('settings'))
        self.add_widget(self.btn_settings)
        self.add_widget(self.btn_weight)

    def _upd(self, *a):
        self.rect.pos = self.pos
        self.rect.size = self.size

    def _go(self, name):
        self.sm.current = name
        if name == 'weight':
            self.btn_weight.background_color = C_BLUE
            self.btn_weight.color = C_WHITE
            self.btn_settings.background_color = NAV_BG
            self.btn_settings.color = hex_c('#94a3b8')
        else:
            self.btn_settings.background_color = C_BLUE
            self.btn_settings.color = C_WHITE
            self.btn_weight.background_color = NAV_BG
            self.btn_weight.color = hex_c('#94a3b8')

# ─── Weight Screen ────────────────────────────────────────────────────────────
class WeightScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auto_event = None
        self._busy = False
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))

        # Weight card
        card = BoxLayout(orientation='vertical', size_hint=(1, None),
                         height=dp(200), padding=dp(20), spacing=dp(6))
        with card.canvas.before:
            Color(*C_DARK)
            self._card_rect = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(16)])
        card.bind(pos=lambda *a: setattr(self, '_', self._upd_card(card)),
                  size=lambda *a: self._upd_card(card))

        lbl_title = Label(text='משקל נוכחי', font_size=sp(12),
                          color=hex_c('#94a3b8'), size_hint_y=None, height=dp(20),
                          halign='center')
        lbl_title.bind(size=lambda *a: setattr(lbl_title, 'text_size', (lbl_title.width, None)))

        self.lbl_weight = Label(
            text='---',
            font_size=sp(72),
            bold=True,
            color=C_CYAN,
            size_hint_y=None,
            height=dp(100),
            halign='center',
            base_direction='ltr',
        )
        self.lbl_weight.bind(size=lambda *a: setattr(self.lbl_weight, 'text_size',
                                                      (self.lbl_weight.width, None)))

        lbl_unit = Label(text="ק\"ג", font_size=sp(14), color=hex_c('#475569'),
                         size_hint_y=None, height=dp(20), halign='center')
        lbl_unit.bind(size=lambda *a: setattr(lbl_unit, 'text_size', (lbl_unit.width, None)))

        self.lbl_status = Label(text='ממתין', font_size=sp(12), color=hex_c('#64748b'),
                                size_hint_y=None, height=dp(22), halign='center')
        self.lbl_status.bind(size=lambda *a: setattr(self.lbl_status, 'text_size',
                                                      (self.lbl_status.width, None)))

        card.add_widget(lbl_title)
        card.add_widget(self.lbl_weight)
        card.add_widget(lbl_unit)
        card.add_widget(self.lbl_status)
        root.add_widget(card)

        # Buttons
        btn_grid = GridLayout(cols=1, spacing=dp(10), size_hint=(1, None))
        btn_grid.bind(minimum_height=btn_grid.setter('height'))

        self.btn_get = make_btn('משקל', C_BLUE, self._on_get)
        btn_grid.add_widget(self.btn_get)

        row2 = BoxLayout(orientation='horizontal', spacing=dp(10),
                         size_hint=(1, None), height=dp(54))
        row2.add_widget(make_btn('טרה  (T)', C_ORANGE, self._on_tare))
        row2.add_widget(make_btn('איפוס  (Z)', C_RED, self._on_zero))
        btn_grid.add_widget(row2)

        root.add_widget(btn_grid)
        root.add_widget(Widget())  # spacer
        self.add_widget(root)

    def _upd_card(self, card):
        self._card_rect.pos = card.pos
        self._card_rect.size = card.size

    def on_enter(self):
        cfg = load_cfg()
        if cfg.get('mode') == 'auto':
            self._start_auto(cfg)
        else:
            self._stop_auto()
            self._set_btn_normal()

    def on_leave(self):
        self._stop_auto()

    def _on_get(self, *a):
        if self._busy:
            return
        threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        if self._busy:
            return
        self._busy = True
        Clock.schedule_once(lambda *a: self._set_status('מתחבר...', hex_c('#60a5fa')))
        try:
            cfg = load_cfg()
            val = scale_cmd(cfg['ip'], cfg['port'], 'W')
            Clock.schedule_once(lambda *a: self._set_weight(val))
            Clock.schedule_once(lambda *a: self._set_status('עודכן ✓', hex_c('#86efac')))
        except Exception as e:
            Clock.schedule_once(lambda *a: self._set_weight_err(str(e)))
            Clock.schedule_once(lambda *a: self._set_status('שגיאה', hex_c('#fca5a5')))
        finally:
            self._busy = False

    def _on_tare(self, *a):
        threading.Thread(target=self._send_cmd, args=('T', 'טרה בוצע'), daemon=True).start()

    def _on_zero(self, *a):
        threading.Thread(target=self._send_cmd, args=('Z', 'איפוס בוצע'), daemon=True).start()

    def _send_cmd(self, cmd, msg):
        try:
            cfg = load_cfg()
            scale_cmd(cfg['ip'], cfg['port'], cmd)
            Clock.schedule_once(lambda *a: self._set_status(msg, hex_c('#86efac')))
        except Exception as e:
            Clock.schedule_once(lambda *a: self._set_status(str(e), hex_c('#fca5a5')))

    def _start_auto(self, cfg):
        self._stop_auto()
        self.btn_get.text = 'אוטו פעיל'
        self.btn_get.background_color = hex_c('#475569')
        self.btn_get.disabled = True
        interval = max(0.5, float(cfg.get('interval', 2.0)))
        self._on_get()
        self._auto_event = Clock.schedule_interval(lambda *a: self._on_get(), interval)

    def _stop_auto(self):
        if self._auto_event:
            self._auto_event.cancel()
            self._auto_event = None

    def _set_btn_normal(self):
        self.btn_get.text = 'משקל'
        self.btn_get.background_color = C_BLUE
        self.btn_get.disabled = False

    def _set_weight(self, val):
        self.lbl_weight.text = val
        self.lbl_weight.color = C_CYAN
        self.lbl_weight.font_size = sp(62)

    def _set_weight_err(self, msg):
        self.lbl_weight.text = 'שגיאה'
        self.lbl_weight.color = hex_c('#f87171')
        self.lbl_weight.font_size = sp(36)

    def _set_status(self, msg, color=None):
        self.lbl_status.text = msg
        if color:
            self.lbl_status.color = color

# ─── Settings Screen ──────────────────────────────────────────────────────────
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build()

    def _build(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(14))

        title = make_label('הגדרות חיבור', size=sp(18), bold=True)
        root.add_widget(title)

        root.add_widget(make_label('כתובת IP'))
        self.inp_ip = make_input('192.168.1.100')
        root.add_widget(self.inp_ip)

        root.add_widget(make_label('פורט'))
        self.inp_port = make_input('8000', input_filter='int')
        root.add_widget(self.inp_port)

        root.add_widget(make_label('מצב קריאה'))
        mode_row = BoxLayout(orientation='horizontal', size_hint=(1, None),
                             height=dp(48), spacing=dp(8))
        self.btn_manual = ToggleButton(
            text='ידני', group='mode', state='down',
            background_normal='', background_down='',
            background_color=C_BLUE, color=C_WHITE,
            font_size=sp(15), bold=True,
        )
        self.btn_auto = ToggleButton(
            text='אוטומטי', group='mode',
            background_normal='', background_down='',
            background_color=hex_c('#e2e8f0'), color=C_TEXT,
            font_size=sp(15),
        )
        self.btn_manual.bind(on_press=lambda *a: self._mode_changed('manual'))
        self.btn_auto.bind(on_press=lambda *a: self._mode_changed('auto'))
        mode_row.add_widget(self.btn_auto)
        mode_row.add_widget(self.btn_manual)
        root.add_widget(mode_row)

        self.lbl_interval = make_label('מרווח עדכון (שניות)')
        root.add_widget(self.lbl_interval)
        self.inp_interval = make_input('2', input_filter='float')
        root.add_widget(self.inp_interval)

        root.add_widget(Widget(size_hint_y=None, height=dp(8)))

        btn_row = BoxLayout(orientation='horizontal', size_hint=(1, None),
                            height=dp(54), spacing=dp(10))
        btn_row.add_widget(make_btn('שמור', C_GREEN, self._save, size_hint=(1, 1)))
        btn_row.add_widget(make_btn('בדוק חיבור', C_BLUE, self._test, size_hint=(1, 1)))
        root.add_widget(btn_row)

        self.lbl_result = make_label('', size=sp(13), color=C_MUTED)
        root.add_widget(self.lbl_result)

        root.add_widget(Widget())  # spacer
        self.add_widget(root)

    def on_enter(self):
        cfg = load_cfg()
        self.inp_ip.text = str(cfg.get('ip', ''))
        self.inp_port.text = str(cfg.get('port', ''))
        self.inp_interval.text = str(cfg.get('interval', 2.0))
        if cfg.get('mode') == 'auto':
            self.btn_auto.state = 'down'
            self.btn_manual.state = 'normal'
            self._mode_changed('auto')
        else:
            self.btn_manual.state = 'down'
            self.btn_auto.state = 'normal'
            self._mode_changed('manual')

    def _mode_changed(self, mode):
        if mode == 'auto':
            self.btn_auto.background_color = C_BLUE
            self.btn_auto.color = C_WHITE
            self.btn_manual.background_color = hex_c('#e2e8f0')
            self.btn_manual.color = C_TEXT
            self.inp_interval.disabled = False
            self.lbl_interval.color = C_TEXT
        else:
            self.btn_manual.background_color = C_BLUE
            self.btn_manual.color = C_WHITE
            self.btn_auto.background_color = hex_c('#e2e8f0')
            self.btn_auto.color = C_TEXT
            self.inp_interval.disabled = True
            self.lbl_interval.color = C_MUTED

    def _save(self, *a):
        ip = self.inp_ip.text.strip()
        try:
            port = int(self.inp_port.text.strip())
            assert 1 <= port <= 65535
        except Exception:
            self.lbl_result.text = 'פורט לא תקין'
            self.lbl_result.color = hex_c('#ef4444')
            return
        try:
            interval = float(self.inp_interval.text.strip())
            assert interval > 0
        except Exception:
            self.lbl_result.text = 'מרווח לא תקין'
            self.lbl_result.color = hex_c('#ef4444')
            return
        if not ip:
            self.lbl_result.text = 'יש להזין IP'
            self.lbl_result.color = hex_c('#ef4444')
            return

        mode = 'auto' if self.btn_auto.state == 'down' else 'manual'
        save_cfg({'ip': ip, 'port': port, 'mode': mode, 'interval': interval})
        self.lbl_result.text = '✔ ההגדרות נשמרו'
        self.lbl_result.color = hex_c('#22c55e')

    def _test(self, *a):
        self.lbl_result.text = 'בודק חיבור...'
        self.lbl_result.color = hex_c('#60a5fa')
        ip = self.inp_ip.text.strip()
        try:
            port = int(self.inp_port.text.strip())
        except Exception:
            self.lbl_result.text = 'פורט לא תקין'
            return

        def _do():
            try:
                val = scale_cmd(ip, port, 'W', timeout=4)
                Clock.schedule_once(lambda *a: self._set_result(f'✔ מחובר – משקל: {val}',
                                                                 hex_c('#22c55e')))
            except Exception as e:
                Clock.schedule_once(lambda *a: self._set_result(f'✘ {e}', hex_c('#ef4444')))

        threading.Thread(target=_do, daemon=True).start()

    def _set_result(self, msg, color):
        self.lbl_result.text = msg
        self.lbl_result.color = color

# ─── App ──────────────────────────────────────────────────────────────────────
class ScaleApp(App):
    def build(self):
        self.title = 'Shekel Weight Display'

        sm = ScreenManager(transition=NoTransition())
        sm.add_widget(WeightScreen(name='weight'))
        sm.add_widget(SettingsScreen(name='settings'))

        nav = NavBar(sm)

        root = BoxLayout(orientation='vertical')
        root.add_widget(nav)
        root.add_widget(sm)
        return root

if __name__ == '__main__':
    ScaleApp().run()
