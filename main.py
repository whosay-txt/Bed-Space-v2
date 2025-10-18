from kivy.config import Config
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.popup import Popup
import sqlite3
from datetime import datetime
from kivy.uix.image import Image
from kivy.uix.floatlayout import FloatLayout
from kivy.graphics import Rectangle
from kivy.uix.video import video
from kivy.graphics import Color
from kivy.graphics import Line
from functools import partial


# ✅ SQLite Setup
conn = sqlite3.connect("tenants.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT,
    bunk TEXT,
    name TEXT,
    date TEXT,
    number TEXT,
    payment TEXT DEFAULT '',
    leave_date TEXT DEFAULT ''
)
""")

# 🏠 Menu Screen
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = FloatLayout()

        # Add background video
        background = video(
            source='Mainmenu.mp4',
            state='play',
            options={'eos':'loop'},
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        )
        layout.add_widget(background)

        # Create button panel
        button_panel = BoxLayout(
            orientation='vertical',
            spacing=10,
            padding=10,
            size_hint=(0.5, None),
            height=200,
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )

        for label, target in [("Room A", "room_a"), ("Room B", "room_b"), ("Tenant Info", "tenant_info")]:
            nav_button = Button(
                text=label,
                size_hint_y=None,
                height=50,
                background_normal='',
                background_color=(1, 1, 1, 0),
                color=(1, 1, 1, 1)
            )

            # Create outline per button
            def add_outline(btn):
                with btn.canvas.before:
                    Color(1, 1, 1, 1)
                    outline = Line(rectangle=(btn.x, btn.y, btn.width, btn.height), width=1.5)

                def update_outline(instance, value):
                    outline.rectangle = (btn.x, btn.y, btn.width, btn.height)

                btn.bind(pos=update_outline, size=update_outline)

            add_outline(nav_button)

            nav_button.bind(on_press=self.make_switch(target))
            button_panel.add_widget(nav_button)

        layout.add_widget(button_panel)
        self.add_widget(layout)

    def make_switch(self, target_screen):
        def switch(instance):
            self.manager.current = target_screen
        return switch


# 🛏️ Room A screen
class RoomAScreen(Screen):
    def __init__(self, **kwargs):
        super(RoomAScreen, self).__init__(**kwargs)
        layout = FloatLayout()
        self.bunk_buttons = {}
        # Background image
        layout.add_widget(Image(
            source='room_a.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        ))

        # Bed buttons
        from functools import partial

        for bed_name, x, y in [
            ('Up1', 0.05, 0.75), ('Low1', 0.05, 0.65), 
            ('Up2', 0.27, 0.75), ('Low2', 0.27, 0.65), 
            ('Up3', 0.56, 0.75), ('Low3', 0.56, 0.65),
            ('Up4', 0.55, 0.50), ('Low4', 0.55, 0.40),
            ('Up5', 0.12, 0.1), ('Low5', 0.30, 0.1),
            ('Up6', 0.60, 0.1), ('Low6', 0.79, 0.1)
        ]:
            color = self.get_bunk_color(bed_name)
            btn = Button(
                text=bed_name,
                size_hint=(0.15, 0.1),
                pos_hint={'x': x, 'y': y},
                background_color=color
            )
            btn.bind(on_release=partial(self.show_tenant_popup, bunk_name=bed_name))
            layout.add_widget(btn)
            self.bunk_buttons[bed_name] = btn

        back_btn = Button(text="Back", size_hint=(1, None), height=50, pos_hint={'x': 0, 'y': 0})
        back_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def get_bunk_color(self, bunk_name):
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("SELECT leave_date FROM tenants WHERE bunk = ?", (bunk_name,))
        tenants = cursor.fetchall()
        for t in tenants:
            leave = t[0]
            if not leave or leave.strip() == '' or leave.strip().upper() == 'N/A' or leave > today:
                return (1, 0, 0, 0.5)  # Red
        return (0, 1, 0, 0.5)  # Green

    def refresh_bunk_color(self, bunk_name):
        if bunk_name in self.bunk_buttons:
            self.bunk_buttons[bunk_name].background_color = self.get_bunk_color(bunk_name)

    def show_tenant_popup(self, instance, bunk_name):
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT id, room, bunk, name, date, number, payment, leave_date
            FROM tenants
            WHERE bunk = ?
        """, (bunk_name,))
        all_tenants = cursor.fetchall()

        active_tenants = []
        for t in all_tenants:
            leave = t[7]
            if not leave or leave.strip() == '' or leave.strip().upper() == 'N/A' or leave > today:
                active_tenants.append(t)

        scroll = ScrollView()
        content_layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=10, spacing=10)
        content_layout.bind(minimum_height=content_layout.setter('height'))

        popup = Popup(title=f"Tenant Info - {bunk_name}", size_hint=(0.9, 0.8))

        if not active_tenants:
            content_layout.add_widget(Label(
                text=f"No active tenant in bunk {bunk_name}.",
                size_hint_y=None, height=40
            ))

            content_layout.add_widget(Label(text="Add New Tenant", size_hint_y=None, height=30))

            name_input = TextInput(hint_text="Full Name", size_hint_y=None, height=40)
            contact_input = TextInput(hint_text="Contact Number", size_hint_y=None, height=40)
            date_input = TextInput(hint_text="Start Date (YYYY-MM-DD)", size_hint_y=None, height=40)
            payment_input = TextInput(hint_text="Initial Payment", size_hint_y=None, height=40)

            content_layout.add_widget(name_input)
            content_layout.add_widget(contact_input)
            content_layout.add_widget(date_input)
            content_layout.add_widget(payment_input)

            def submit_tenant(instance):
                self.add_tenant(
                    room='A', bunk=bunk_name,
                    name=name_input.text,
                    number=contact_input.text,
                    date=date_input.text,
                    payment=payment_input.text
                )
                self.refresh_bunk_color(bunk_name)
                popup.dismiss()

            add_btn = Button(text="Add Tenant", size_hint_y=None, height=40)
            add_btn.bind(on_press=submit_tenant)
            content_layout.add_widget(add_btn)

        else:
            for t in active_tenants:
                info = (
                    f"Room: {t[1]}\n"
                    f"Bunk: {t[2]}\n"
                    f"Name: {t[3]}\n"
                    f"Date: {t[4]}\n"
                    f"Contact: {t[5]}\n"
                    f"Payment: ₱{t[6] if t[6] else '0.00'}\n"
                    f"Leave: {t[7] or 'N/A'}"
                )
                label = Label(text=info, halign='left', valign='top', size_hint_y=None, height=160)
                label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
                content_layout.add_widget(label)

                payment_input = TextInput(hint_text="Enter Payment")
                update_btn = Button(text="Update", size_hint_x=0.3)
                update_btn.bind(on_press=lambda x, tid=t[0], inp=payment_input: self.update_payment(tid, inp.text))
                payment_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
                payment_row.add_widget(payment_input)
                payment_row.add_widget(update_btn)
                content_layout.add_widget(payment_row)

                leave_input = TextInput(hint_text="Leave Date (YYYY-MM-DD)")
                leave_btn = Button(text="Set Leave", size_hint_x=0.3)
                leave_btn.bind(on_press=lambda x, tid=t[0], inp=leave_input: self.update_leave_date(tid, inp.text))
                leave_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
                leave_row.add_widget(leave_input)
                leave_row.add_widget(leave_btn)
                content_layout.add_widget(leave_row)

                delete_btn = Button(text="Delete Tenant", size_hint_y=None, height=40)
                delete_btn.bind(on_press=lambda x, tid=t[0]: self.delete_tenant(tid))
                content_layout.add_widget(delete_btn)

        close_btn = Button(text="Close", size_hint_y=None, height=40)
        close_btn.bind(on_press=lambda x: popup.dismiss())
        content_layout.add_widget(close_btn)

        scroll.add_widget(content_layout)
        popup.content = scroll
        popup.open()

    def add_tenant(self, room, bunk, name, number, date, payment):
        try:
            cursor.execute("""
                INSERT INTO tenants (room, bunk, name, number, date, payment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (room, bunk, name, number, date, float(payment) if payment else 0.0))
            conn.commit()
        except Exception as e:
            print(f"Error adding tenant: {e}")

    def update_payment(self, tenant_id, amount):
        try:
            cursor.execute("UPDATE tenants SET payment = ? WHERE id = ?", (float(amount), tenant_id))
            conn.commit()
        except Exception as e:
            print(f"Error updating payment: {e}")

    def update_leave_date(self, tenant_id, leave_date):
        try:
            cursor.execute("UPDATE tenants SET leave_date = ? WHERE id = ?", (leave_date, tenant_id))
            conn.commit()
        except Exception as e:
            print(f"Error updating leave date: {e}")

    def delete_tenant(self, tenant_id):
        try:
            cursor.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
            conn.commit()
        except Exception as e:
            print(f"Error deleting tenant: {e}")



class RoomBScreen(Screen):
    def __init__(self, **kwargs):
        super(RoomBScreen, self).__init__(**kwargs)
        layout = FloatLayout()
        self.bunk_buttons = {}
        # Background image
        
        layout.add_widget(Image(
            source='room_b.png',
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={'x': 0, 'y': 0}
        ))

        # Bed buttons
        from functools import partial

        for bed_name, x, y in [
            ('Up1', 0.47, 0.62),('Low1', 0.63, 0.62), 
            ('Up2', 0.47, 0.47), ('Low2', 0.63, 0.47), 
            ('Up3', 0.47, 0.34), ('Low3', 0.63, 0.34),
            ('Up4', 0.12, 0.46), ('Low4', 0.12, 0.36),
            ('Up5', 0.12, 0.24), ('Low5', 0.30, 0.24),
        ]:
            color = self.get_bunk_color(bed_name)
            btn = Button(
                text=bed_name,
                size_hint=(0.15, 0.1),
                pos_hint={'x': x, 'y': y},
                background_color=color
            )
            btn.bind(on_release=partial(self.show_tenant_popup, bunk_name=bed_name))
            layout.add_widget(btn)
            self.bunk_buttons[bed_name] = btn

        back_btn = Button(text="Back", size_hint=(1, None), height=50, pos_hint={'x': 0, 'y': 0})
        back_btn.bind(on_release=lambda x: setattr(self.manager, 'current', 'menu'))
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def get_bunk_color(self, bunk_name):
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("SELECT leave_date FROM tenants WHERE bunk = ?", (bunk_name,))
        tenants = cursor.fetchall()
        for t in tenants:
            leave = t[0]
            if not leave or leave.strip() == '' or leave.strip().upper() == 'N/A' or leave > today:
                return (1, 0, 0, 0.5)  # Red
        return (0, 1, 0, 0.5)  # Green

    def refresh_bunk_color(self, bunk_name):
        if bunk_name in self.bunk_buttons:
            self.bunk_buttons[bunk_name].background_color = self.get_bunk_color(bunk_name)

    def show_tenant_popup(self, instance, bunk_name):
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT id, room, bunk, name, date, number, payment, leave_date
            FROM tenants
            WHERE bunk = ?
        """, (bunk_name,))
        all_tenants = cursor.fetchall()

        active_tenants = []
        for t in all_tenants:
            leave = t[7]
            if not leave or leave.strip() == '' or leave.strip().upper() == 'N/A' or leave > today:
                active_tenants.append(t)

        scroll = ScrollView()
        content_layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=10, spacing=10)
        content_layout.bind(minimum_height=content_layout.setter('height'))

        popup = Popup(title=f"Tenant Info - {bunk_name}", size_hint=(0.9, 0.8))

        if not active_tenants:
            content_layout.add_widget(Label(
                text=f"No active tenant in bunk {bunk_name}.",
                size_hint_y=None, height=40
            ))

            content_layout.add_widget(Label(text="Add New Tenant", size_hint_y=None, height=30))

            name_input = TextInput(hint_text="Full Name", size_hint_y=None, height=40)
            contact_input = TextInput(hint_text="Contact Number", size_hint_y=None, height=40)
            date_input = TextInput(hint_text="Start Date (YYYY-MM-DD)", size_hint_y=None, height=40)
            payment_input = TextInput(hint_text="Initial Payment", size_hint_y=None, height=40)

            content_layout.add_widget(name_input)
            content_layout.add_widget(contact_input)
            content_layout.add_widget(date_input)
            content_layout.add_widget(payment_input)

            def submit_tenant(instance):
                self.add_tenant(
                    room='A', bunk=bunk_name,
                    name=name_input.text,
                    number=contact_input.text,
                    date=date_input.text,
                    payment=payment_input.text
                )
                self.refresh_bunk_color(bunk_name)
                popup.dismiss()

            add_btn = Button(text="Add Tenant", size_hint_y=None, height=40)
            add_btn.bind(on_press=submit_tenant)
            content_layout.add_widget(add_btn)

        else:
            for t in active_tenants:
                info = (
                    f"Room: {t[1]}\n"
                    f"Bunk: {t[2]}\n"
                    f"Name: {t[3]}\n"
                    f"Date: {t[4]}\n"
                    f"Contact: {t[5]}\n"
                    f"Payment: ₱{t[6] if t[6] else '0.00'}\n"
                    f"Leave: {t[7] or 'N/A'}"
                )
                label = Label(text=info, halign='left', valign='top', size_hint_y=None, height=160)
                label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
                content_layout.add_widget(label)

                payment_input = TextInput(hint_text="Enter Payment")
                update_btn = Button(text="Update", size_hint_x=0.3)
                update_btn.bind(on_press=lambda x, tid=t[0], inp=payment_input: self.update_payment(tid, inp.text))
                payment_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
                payment_row.add_widget(payment_input)
                payment_row.add_widget(update_btn)
                content_layout.add_widget(payment_row)

                leave_input = TextInput(hint_text="Leave Date (YYYY-MM-DD)")
                leave_btn = Button(text="Set Leave", size_hint_x=0.3)
                leave_btn.bind(on_press=lambda x, tid=t[0], inp=leave_input: self.update_leave_date(tid, inp.text))
                leave_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
                leave_row.add_widget(leave_input)
                leave_row.add_widget(leave_btn)
                content_layout.add_widget(leave_row)

                delete_btn = Button(text="Delete Tenant", size_hint_y=None, height=40)
                delete_btn.bind(on_press=lambda x, tid=t[0]: self.delete_tenant(tid))
                content_layout.add_widget(delete_btn)

        close_btn = Button(text="Close", size_hint_y=None, height=40)
        close_btn.bind(on_press=lambda x: popup.dismiss())
        content_layout.add_widget(close_btn)

        scroll.add_widget(content_layout)
        popup.content = scroll
        popup.open()

    def add_tenant(self, room, bunk, name, number, date, payment):
        try:
            cursor.execute("""
                INSERT INTO tenants (room, bunk, name, number, date, payment)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (room, bunk, name, number, date, float(payment) if payment else 0.0))
            conn.commit()
        except Exception as e:
            print(f"Error adding tenant: {e}")

    def update_payment(self, tenant_id, amount):
        try:
            cursor.execute("UPDATE tenants SET payment = ? WHERE id = ?", (float(amount), tenant_id))
            conn.commit()
        except Exception as e:
            print(f"Error updating payment: {e}")

    def update_leave_date(self, tenant_id, leave_date):
        try:
            cursor.execute("UPDATE tenants SET leave_date = ? WHERE id = ?", (leave_date, tenant_id))
            conn.commit()
        except Exception as e:
            print(f"Error updating leave date: {e}")

    def delete_tenant(self, tenant_id):
        try:
            cursor.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
            conn.commit()
        except Exception as e:
            print(f"Error deleting tenant: {e}")



# 📋 Tenant Info Screen
class TenantInfoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        root = FloatLayout()
        with root.canvas.before:
            Color(0, 0, 0, 1)
            self.bg_rect = Rectangle(size=root.size, pos=root.pos)

        bg = Image(source='tenantinfo.png', allow_stretch=True, keep_ratio=False)
        root.add_widget(bg)

        
        # Main vertical layout
        foreground = BoxLayout(orientation='vertical', size_hint=(1, 1))
        

        # 🔝 Top section: Title + Search
        top_section = BoxLayout(orientation='vertical', size_hint_y=None, height=100, padding=10, spacing=10)
        title = Label(text="Tenant Info", size_hint_y=None, height=40)
        search_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
        self.search_input = TextInput(hint_text="Search by name")
        search_btn = Button(text="Search", size_hint_x=0.3)
        search_btn.bind(on_press=self.search_tenant_popup)
        search_row.add_widget(self.search_input)
        search_row.add_widget(search_btn)
        top_section.add_widget(title)
        top_section.add_widget(search_row)
        foreground.add_widget(top_section)

        # 📜 Middle section: Scrollable tenant list
        scroll = ScrollView()
        self.layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=10)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        scroll.add_widget(self.layout)
        foreground.add_widget(scroll)

        # 🔙 Bottom section: Fixed Back button
        bottom_section = BoxLayout(size_hint_y=None, height=60, padding=10)
        back_btn = Button(text="Back", size_hint_x=1)
        back_btn.bind(on_press=self.go_back)
        bottom_section.add_widget(back_btn)
        foreground.add_widget(bottom_section)

        root.add_widget(foreground)
        self.add_widget(root)
    def _update_bg_rect(self, instance, value):
        self.bg_rect.size = instance.size
        self.bg_rect.pos = instance.po

    def on_pre_enter(self):
        self.refresh()

    def refresh(self):
        self.layout.clear_widgets()
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT id, room, bunk, name, date, number, payment, leave_date
            FROM tenants
            WHERE leave_date IS NULL OR leave_date = '' OR leave_date > ?
        """, (today,))
        tenants = cursor.fetchall()

        if not tenants:
            self.layout.add_widget(Label(text="No active tenants found.", size_hint_y=None, height=40))

        for tenant in tenants:
            box = BoxLayout(orientation='vertical', size_hint_y=None, padding=5, spacing=5)
            box.height = 300

            summary = (
                f"Room: {tenant[1]}\n"
                f"Bunk: {tenant[2]}\n"
                f"Name: {tenant[3]}\n"
                f"Date: {tenant[4]}\n"
                f"Contact: {tenant[5]}\n"
                f"Leave: {tenant[7] or 'N/A'}\n"
                f"Payment: ₱{tenant[6] if tenant[6] else '0.00'}"
            )

            label = Label(text=summary, halign='left', valign='top', size_hint_y=None, height=160)
            label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
            box.add_widget(label)

            # 💰 Payment row
            payment_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
            payment_input = TextInput(hint_text="Enter Payment")
            update_btn = Button(text="Update", size_hint_x=0.3)
            update_btn.bind(on_press=lambda x, tid=tenant[0], inp=payment_input: self.update_payment(tid, inp.text))
            payment_row.add_widget(payment_input)
            payment_row.add_widget(update_btn)
            box.add_widget(payment_row)

            # 🏃 Leave row
            leave_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
            leave_input = TextInput(hint_text="Leave Date")
            leave_btn = Button(text="Set Leave", size_hint_x=0.3)
            leave_btn.bind(on_press=lambda x, tid=tenant[0], inp=leave_input: self.update_leave_date(tid, inp.text))
            leave_row.add_widget(leave_input)
            leave_row.add_widget(leave_btn)
            box.add_widget(leave_row)

            # ❌ Delete row
            delete_row = BoxLayout(size_hint_y=None, height=40)
            delete_btn = Button(text="Delete", size_hint_x=1)
            delete_btn.bind(on_press=lambda x, tid=tenant[0]: self.delete_tenant(tid))
            delete_row.add_widget(delete_btn)
            box.add_widget(delete_row)

            self.layout.add_widget(box)
            spacer = Label(size_hint_y=None, height=20)
            self.layout.add_widget(spacer)

        # 🔙 Back button
        # back_btn = Button(text="Back", size_hint_y=None, height=40)
        # back_btn.bind(on_press=self.go_back)
        # self.layout.add_widget(back_btn)

    def search_tenant_popup(self, instance):
        name_query = self.search_input.text.strip().lower()
        if not name_query:
            return

        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT room, bunk, name, date, number, payment, leave_date
            FROM tenants
            WHERE (leave_date IS NULL OR leave_date = '' OR leave_date > ?)
        """, (today,))
        tenants = cursor.fetchall()

        matches = [t for t in tenants if name_query == t[2].strip().lower()]

        if not matches:
            popup = Popup(title="No Match Found",
                        content=Label(text="No tenant found with that name."),
                        size_hint=(0.8, 0.3))
            popup.open()
            return

        # 📜 Scrollable content
        scroll = ScrollView()
        content_layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=10, spacing=10)
        content_layout.bind(minimum_height=content_layout.setter('height'))

        for t in matches:
            info = (
                f"Room: {t[0]}\n"
                f"Bunk: {t[1]}\n"
                f"Name: {t[2]}\n"
                f"Date: {t[3]}\n"
                f"Contact: {t[4]}\n"
                f"Payment: ₱{t[5] if t[5] else '0.00'}\n"
                f"Leave: {t[6] or 'N/A'}"
            )
            label = Label(text=info, halign='left', valign='top', size_hint_y=None, height=160)
            label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
            content_layout.add_widget(label)

        close_btn = Button(text="Close", size_hint_y=None, height=40)
        close_btn.bind(on_press=lambda x: popup.dismiss())
        content_layout.add_widget(close_btn)

        scroll.add_widget(content_layout)

        popup = Popup(title="Tenant Info", content=scroll, size_hint=(0.9, 0.8))
        popup.open()
        
    def update_payment(self, tenant_id, payment):
        if not payment.strip().replace('.', '', 1).isdigit():
            return
        cursor.execute("UPDATE tenants SET payment = ? WHERE id = ?", (payment, tenant_id))
        conn.commit()
        self.refresh()

    def update_leave_date(self, tenant_id, leave_date):
        cursor.execute("UPDATE tenants SET leave_date = ? WHERE id = ?", (leave_date, tenant_id))
        conn.commit()
        self.refresh()

    def delete_tenant(self, tenant_id):
        cursor.execute("DELETE FROM tenants WHERE id = ?", (tenant_id,))
        conn.commit()
        self.refresh()

    def go_back(self, instance):
        self.manager.current = "menu"

# 🚀 App Entry Point

class BedSpaceApp(App):
    def build(self):
        sm = ScreenManager()

        # Add all screens to the same ScreenManager instance
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(TenantInfoScreen(name="tenant_info"))
        sm.add_widget(RoomAScreen(name="room_a"))  # New layout with image and buttons
        sm.add_widget(RoomBScreen(name="room_b"))  # New layout with image and buttons

        return sm

BedSpaceApp().run()

