# -*- coding: utf-8 -*-
import os
import sys
import json
import socket
import threading
import time
import traceback


# ── Crash logger – writes to app data dir ─────────────────────────────────────
def _on_crash(exc_type, exc_value, exc_tb):
    try:
        from kivy.app import App
        app = App.get_running_app()
        log_path = os.path.join(
            app.user_data_dir if app else '.', 'crash.txt')
        with open(log_path, 'w') as f:
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass
    sys.__excepthook__(exc_type, exc_value, exc_tb)

sys.excepthook = _on_crash

# ── Kivy imports ──────────────────────────────────────────────────────────────
from kivy.app import App
from kivy.clock import Clock
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
from kivy.graphics import Color, Rectangle

# ── Colors (pure tuples – safe at module level) ───────────────────────────────
NAV_BG   = hex_c('#1a2332')
C_BLUE   = hex_c('#3b82f6')
C_ORANGE = hex_c('#f97316')
C_RED    = hex_c('#ef4444')
C_GREEN  = hex_c('#22c55e')
C_DARK   = hex_c('#0f172a')
C_CYAN   = hex_c('#38bdf8')
C_TEXT   = hex_c('#1e293b')
C_MUTED  = hex_c('#64748b')
C_WHITE  = hex_c('#ffffff')
C_LIGHT  = hex_c('#f0f4f8')

# ── Config ────────────────────────────────────────────────────────────────────
DEFAULT_CFG = {
    "ip": "192.168.1.100",
    "port": 8000,
    "mode": "manual",
    "interval": 2.0
}

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
        return dict(DEFAULT_CFG)

def save_cfg(cfg):
    try:
        with open(cfg_path(), 'w') as f:
            json.dump(cfg, f)
    except Exception:
        pass

# ── TCP ───────────────────────────────────────────────────────────────────────
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
        try:
            s.settimeout(1)
            s.recv(16)
        except Exception:
            pass
        return 'ok'

# ── UI helpers ────────────────────────────────────────────────────────────────
class BgWidget(Widget):
    """Widget with solid background color."""
    def __init__(self, color, **kwargs):
        super().__init__(**kwargs)
        self._bg_color = color
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg_color)
            Rectangle(pos=self.pos, size=self.size)


class BgBox(BoxLayout):
    """BoxLayout with solid background color."""
    def __init__(self, color, **kwargs):
        super().__init__(**kwargs)
        self._bg_color = color
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg_color)
            Rectangle(pos=self.pos, size=self.size)


def make_btn(text, bg, cb, **kwargs):
    kwargs.setdefault('size_hint', (1, None))
    kwargs.setdefault('height', dp(54))
    btn = Button(
        text=text,
        background_normal='',
        background_color=bg,
        color=C_WHITE,
        font_size=sp(16),
        bold=True,
        **kwargs
    )
    btn.bind(on_press=cb)
    return btn


def make_lbl(text, size=None, color=None, bold=False, halign='right', height=None):
    lbl = Label(
        text=text,
        font_size=size if size is not None else sp(14),
        color=color if color is not None else C_TEXT,
        bold=bold,
        halign=halign,
        size_hint_y=None,
        height=height if height is not None else dp(30),
    )
    lbl.bind(size=lambda inst, val: setattr(inst, 'text_size', (val[0], None)))
    return lbl


def make_inp(hint, text='', input_filter=None):
    return TextInput(
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

# ── Navigation bar ────────────────────────────────────────────────────────────
class NavBar(BgBox):
    def __init__(self, sm, **kwargs):
        super().__init__(NAV_BG, orientation='horizontal',
                         size_hint=(1, None), height=dp(56), **kwargs)
        self.sm = sm
        self.add_widget(Widget())  # spacer

        self.btn_settings = Button(
            text='Settings', size_hint=(None, 1), width=dp(120),
            background_normal='', background_color=NAV_BG,
            color=hex_c('#94a3b8'), font_size=sp(14),
        )
        self.btn_weight = Button(
            text='Weight', size_hint=(None, 1), width=dp(120),
            background_normal='', background_color=C_BLUE,
            color=C_WHITE, font_size=sp(14), bold=True,
        )
        self.btn_weight.bind(on_press=lambda *_: self._go('weight'))
        self.btn_settings.bind(on_press=lambda *_: self._go('settings'))
        self.add_widget(self.btn_settings)
        self.add_widget(self.btn_weight)

    def _go(self, name):
        self.sm.current = name
        active   = C_BLUE
        inactive = NAV_BG
        if name == 'weight':
            self.btn_weight.background_color = active
            self.btn_weight.color = C_WHITE
            self.btn_settings.background_color = inactive
            self.btn_settings.color = hex_c('#94a3b8')
        else:
            self.btn_settings.background_color = active
            self.btn_settings.color = C_WHITE
            self.btn_weight.background_color = inactive
            self.btn_weight.color = hex_c('#94a3b8')

# ── Weight screen ─────────────────────────────────────────────────────────────
class WeightScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._auto_event = None
        self._busy = False
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(12))

        # Dark card background
        card = BgBox(C_DARK, orientation='vertical',
                     size_hint=(1, None), height=dp(190),
                     padding=dp(20), spacing=dp(4))

        card.add_widget(make_lbl('Current Weight', size=sp(12),
                                  color=hex_c('#94a3b8'), halign='center',
                                  height=dp(20)))

        self.lbl_weight = Label(
            text='---', font_size=sp(68), bold=True,
            color=C_CYAN, size_hint_y=None, height=dp(90),
            halign='center',
        )
        self.lbl_weight.bind(
            size=lambda inst, val: setattr(inst, 'text_size', (val[0], None))
        )
        card.add_widget(self.lbl_weight)

        card.add_widget(make_lbl('kg', size=sp(14),
                                  color=hex_c('#475569'), halign='center',
                                  height=dp(18)))

        self.lbl_status = make_lbl('Ready', size=sp(12),
                                    color=hex_c('#64748b'), halign='center',
                                    height=dp(20))
        card.add_widget(self.lbl_status)
        root.add_widget(card)

        # Buttons
        btn_grid = GridLayout(cols=1, spacing=dp(10),
                               size_hint=(1, None))
        btn_grid.bind(minimum_height=btn_grid.setter('height'))

        self.btn_get = make_btn('Weight', C_BLUE, self._on_get)
        btn_grid.add_widget(self.btn_get)

        row2 = BoxLayout(orientation='horizontal', spacing=dp(10),
                          size_hint=(1, None), height=dp(54))
        row2.add_widget(make_btn('Tare', C_ORANGE, self._on_tare))
        row2.add_widget(make_btn('Zero', C_RED, self._on_zero))
        btn_grid.add_widget(row2)

        root.add_widget(btn_grid)
        root.add_widget(Widget())
        self.add_widget(root)

    def on_enter(self):
        cfg = load_cfg()
        if cfg.get('mode') == 'auto':
            self._start_auto(cfg)
        else:
            self._stop_auto()
            self._set_btn_normal()

    def on_leave(self):
        self._stop_auto()

    def _on_get(self, *_):
        if not self._busy:
            threading.Thread(target=self._fetch, daemon=True).start()

    def _fetch(self):
        if self._busy:
            return
        self._busy = True
        Clock.schedule_once(lambda *_: self._set_status('Connecting...', hex_c('#60a5fa')))
        try:
            cfg = load_cfg()
            val = scale_cmd(cfg['ip'], cfg['port'], 'W')
            Clock.schedule_once(lambda *_: self._set_weight(val))
            Clock.schedule_once(lambda *_: self._set_status('Updated', hex_c('#86efac')))
        except Exception as e:
            msg = str(e)[:40]
            Clock.schedule_once(lambda *_: self._set_weight_err())
            Clock.schedule_once(lambda *_: self._set_status(msg, hex_c('#fca5a5')))
        finally:
            self._busy = False

    def _on_tare(self, *_):
        threading.Thread(
            target=self._send_cmd, args=('T', 'Tare done'), daemon=True).start()

    def _on_zero(self, *_):
        threading.Thread(
            target=self._send_cmd, args=('Z', 'Zero done'), daemon=True).start()

    def _send_cmd(self, cmd, msg):
        try:
            cfg = load_cfg()
            scale_cmd(cfg['ip'], cfg['port'], cmd)
            Clock.schedule_once(lambda *_: self._set_status(msg, hex_c('#86efac')))
        except Exception as e:
            m = str(e)[:40]
            Clock.schedule_once(lambda *_: self._set_status(m, hex_c('#fca5a5')))

    def _start_auto(self, cfg):
        self._stop_auto()
        self.btn_get.text = 'Auto ON'
        self.btn_get.background_color = hex_c('#475569')
        self.btn_get.disabled = True
        interval = max(0.5, float(cfg.get('interval', 2.0)))
        self._on_get()
        self._auto_event = Clock.schedule_interval(
            lambda *_: self._on_get(), interval)

    def _stop_auto(self):
        if self._auto_event:
            self._auto_event.cancel()
            self._auto_event = None

    def _set_btn_normal(self):
        self.btn_get.text = 'Weight'
        self.btn_get.background_color = C_BLUE
        self.btn_get.disabled = False

    def _set_weight(self, val):
        self.lbl_weight.text = val
        self.lbl_weight.color = C_CYAN
        self.lbl_weight.font_size = sp(62)

    def _set_weight_err(self):
        self.lbl_weight.text = 'Error'
        self.lbl_weight.color = hex_c('#f87171')
        self.lbl_weight.font_size = sp(36)

    def _set_status(self, msg, color=None):
        self.lbl_status.text = msg
        if color is not None:
            self.lbl_status.color = color

# ── Settings screen ───────────────────────────────────────────────────────────
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._build_ui()

    def _build_ui(self):
        root = BoxLayout(orientation='vertical', padding=dp(16), spacing=dp(10))

        root.add_widget(make_lbl('Connection Settings', size=sp(18), bold=True))

        root.add_widget(make_lbl('IP Address'))
        self.inp_ip = make_inp('192.168.1.100')
        root.add_widget(self.inp_ip)

        root.add_widget(make_lbl('Port'))
        self.inp_port = make_inp('8000', input_filter='int')
        root.add_widget(self.inp_port)

        root.add_widget(make_lbl('Mode'))
        mode_row = BoxLayout(orientation='horizontal', size_hint=(1, None),
                              height=dp(48), spacing=dp(8))
        self.btn_manual = ToggleButton(
            text='Manual', group='mode', state='down',
            background_normal='', background_down='',
            background_color=C_BLUE, color=C_WHITE,
            font_size=sp(15), bold=True,
        )
        self.btn_auto = ToggleButton(
            text='Auto', group='mode',
            background_normal='', background_down='',
            background_color=hex_c('#e2e8f0'), color=C_TEXT,
            font_size=sp(15),
        )
        self.btn_manual.bind(on_press=lambda *_: self._mode('manual'))
        self.btn_auto.bind(on_press=lambda *_: self._mode('auto'))
        mode_row.add_widget(self.btn_auto)
        mode_row.add_widget(self.btn_manual)
        root.add_widget(mode_row)

        self.lbl_interval = make_lbl('Interval (seconds)')
        root.add_widget(self.lbl_interval)
        self.inp_interval = make_inp('2', input_filter='float')
        root.add_widget(self.inp_interval)

        root.add_widget(Widget(size_hint_y=None, height=dp(8)))

        btn_row = BoxLayout(orientation='horizontal', size_hint=(1, None),
                             height=dp(54), spacing=dp(10))
        btn_row.add_widget(make_btn('Save', C_GREEN, self._save, size_hint=(1, 1)))
        btn_row.add_widget(make_btn('Test', C_BLUE, self._test, size_hint=(1, 1)))
        root.add_widget(btn_row)

        self.lbl_result = make_lbl('', size=sp(13), color=C_MUTED)
        root.add_widget(self.lbl_result)

        root.add_widget(Widget())
        self.add_widget(root)

    def on_enter(self):
        cfg = load_cfg()
        self.inp_ip.text = str(cfg.get('ip', ''))
        self.inp_port.text = str(cfg.get('port', ''))
        self.inp_interval.text = str(cfg.get('interval', 2.0))
        if cfg.get('mode') == 'auto':
            self.btn_auto.state = 'down'
            self.btn_manual.state = 'normal'
            self._mode('auto')
        else:
            self.btn_manual.state = 'down'
            self.btn_auto.state = 'normal'
            self._mode('manual')

    def _mode(self, mode):
        if mode == 'auto':
            self.btn_auto.background_color = C_BLUE
            self.btn_auto.color = C_WHITE
            self.btn_manual.background_color = hex_c('#e2e8f0')
            self.btn_manual.color = C_TEXT
            self.inp_interval.disabled = False
        else:
            self.btn_manual.background_color = C_BLUE
            self.btn_manual.color = C_WHITE
            self.btn_auto.background_color = hex_c('#e2e8f0')
            self.btn_auto.color = C_TEXT
            self.inp_interval.disabled = True

    def _save(self, *_):
        ip = self.inp_ip.text.strip()
        if not ip:
            self._result('Enter IP address', hex_c('#ef4444'))
            return
        try:
            port = int(self.inp_port.text.strip())
            assert 1 <= port <= 65535
        except Exception:
            self._result('Invalid port', hex_c('#ef4444'))
            return
        try:
            interval = float(self.inp_interval.text.strip())
            assert interval > 0
        except Exception:
            self._result('Invalid interval', hex_c('#ef4444'))
            return
        mode = 'auto' if self.btn_auto.state == 'down' else 'manual'
        save_cfg({'ip': ip, 'port': port, 'mode': mode, 'interval': interval})
        self._result('Saved!', hex_c('#22c55e'))

    def _test(self, *_):
        self._result('Testing...', hex_c('#60a5fa'))
        ip = self.inp_ip.text.strip()
        try:
            port = int(self.inp_port.text.strip())
        except Exception:
            self._result('Invalid port', hex_c('#ef4444'))
            return

        def _do():
            try:
                val = scale_cmd(ip, port, 'W', timeout=4)
                Clock.schedule_once(
                    lambda *_: self._result('Connected: ' + val, hex_c('#22c55e')))
            except Exception as e:
                Clock.schedule_once(
                    lambda *_: self._result(str(e)[:40], hex_c('#ef4444')))

        threading.Thread(target=_do, daemon=True).start()

    def _result(self, msg, color=None):
        self.lbl_result.text = msg
        if color is not None:
            self.lbl_result.color = color

# ── Application ───────────────────────────────────────────────────────────────
class ScaleApp(App):
    def build(self):
        from kivy.core.window import Window
        Window.clearcolor = C_LIGHT

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
