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
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

        for label, target in [("Room A", "room_a"), ("Room B", "room_b"), ("Tenant Info", "tenant_info")]:
            btn = Button(text=label, size_hint_y=None, height=50)
            btn.bind(on_press=self.make_switch(target))
            layout.add_widget(btn)

        self.add_widget(layout)

    def make_switch(self, target_screen):
        def switch(instance):
            self.manager.current = target_screen
        return switch

# 🛏️ Room Screen
class RoomScreen(Screen):
    def __init__(self, room_name, bunk_count, **kwargs):
        super().__init__(**kwargs)
        scroll = ScrollView()
        self.layout = BoxLayout(orientation='vertical', size_hint_y=None, padding=10, spacing=10)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        scroll.add_widget(self.layout)
        self.add_widget(scroll)

        self.room_name = room_name
        self.bunk_count = bunk_count
        self.layout.add_widget(Label(text=f"{room_name} - Select a bunk", size_hint_y=None, height=40))

        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT bunk FROM tenants
            WHERE room = ? AND (leave_date IS NULL OR leave_date = '' OR leave_date > ?)
        """, (self.room_name, today))
        assigned_bunks = set(row[0] for row in cursor.fetchall())

        for i in range(1, bunk_count + 1):
            for bunk_type in ["upper", "lower"]:
                bunk_id = f"{bunk_type}-{i}"
                btn = Button(text=f"{bunk_type.capitalize()} Bunk {i}", size_hint_y=None, height=40)
                btn.bind(on_press=self.make_form(self.room_name, bunk_type, i))
                self.layout.add_widget(btn)

        back_btn = Button(text="Back", size_hint_y=None, height=40)
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)

    def make_form(self, room, bunk_type, bunk_number):
        def callback(instance):
            bunk_id = f"{bunk_type}-{bunk_number}"
            form_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

            cursor.execute("SELECT name, date, number, leave_date FROM tenants WHERE room = ? AND bunk = ?", (room, bunk_id))
            existing = cursor.fetchone()

            name_input = TextInput(text=existing[0] if existing else "", hint_text="Name", size_hint_y=None, height=40)
            date_input = TextInput(text=existing[1] if existing else "", hint_text="Date (YYYY-MM-DD)", size_hint_y=None, height=40)
            number_input = TextInput(text=existing[2] if existing else "", hint_text="Contact Number", size_hint_y=None, height=40)
            leave_input = TextInput(text=existing[3] if existing and existing[3] else "", hint_text="Leave Date (YYYY-MM-DD)", size_hint_y=None, height=40)

            submit_btn = Button(text="Submit", size_hint_y=None, height=40)
            close_btn = Button(text="Cancel", size_hint_y=None, height=40)

            popup = Popup(title=f"{room} - {bunk_type.capitalize()} Bunk {bunk_number}",
                          content=form_layout,
                          size_hint=(0.9, 0.8))

            submit_btn.bind(on_press=lambda x: self.save_tenant_and_close(
                room,
                bunk_id,
                name_input.text,
                date_input.text,
                number_input.text,
                leave_input.text,
                popup
            ))
            close_btn.bind(on_press=popup.dismiss)

            for widget in [name_input, date_input, number_input, leave_input, submit_btn, close_btn]:
                form_layout.add_widget(widget)

            popup.open()
        return callback

    def save_tenant_and_close(self, room, bunk, name, date, number, leave_date, popup):
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
            SELECT bunk FROM tenants
            WHERE room = ? AND bunk = ? AND (leave_date IS NULL OR leave_date = '' OR leave_date > ?)
        """, (room, bunk, today))
        occupied = cursor.fetchone()

        if occupied:
            warning = Popup(title="Bunk Occupied",
                            content=Label(text="This bunk is currently occupied."),
                            size_hint=(0.8, 0.3))
            warning.open()
            return

        cursor.execute("""
            INSERT INTO tenants (room, bunk, name, date, number, leave_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (room, bunk, name, date, number, leave_date))
        conn.commit()
        popup.dismiss()
        self.manager.current = "menu"

    def go_back(self, instance):
        self.manager.current = "menu"
# 📋 Tenant Info Screen
class TenantInfoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Main vertical layout
        root = BoxLayout(orientation='vertical')

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
        root.add_widget(top_section)

        # 📜 Middle section: Scrollable tenant list
        scroll = ScrollView()
        self.layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10, padding=10)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        scroll.add_widget(self.layout)
        root.add_widget(scroll)

        # 🔙 Bottom section: Fixed Back button
        bottom_section = BoxLayout(size_hint_y=None, height=60, padding=10)
        back_btn = Button(text="Back", size_hint_x=1)
        back_btn.bind(on_press=self.go_back)
        bottom_section.add_widget(back_btn)
        root.add_widget(bottom_section)

        self.add_widget(root)


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
        back_btn = Button(text="Back", size_hint_y=None, height=40)
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)

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
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(RoomScreen("RM A", 6, name="room_a"))
        sm.add_widget(RoomScreen("RM B", 5, name="room_b"))
        sm.add_widget(TenantInfoScreen(name="tenant_info"))
        return sm

BedSpaceApp().run()
