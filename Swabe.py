from kivy.config import Config
Config.set('graphics', 'width', '360')
Config.set('graphics', 'height', '640')
from kivy.uix.popup import Popup

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
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
try:
    cursor.execute("ALTER TABLE tenants ADD COLUMN leave_date TEXT")
    conn.commit()
except sqlite3.OperationalError:
    pass

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

        # ✅ Bunk availability tracking
        cursor.execute("SELECT bunk FROM tenants WHERE room = ?", (self.room_name,))
        assigned_bunks = set(row[0] for row in cursor.fetchall())

        for i in range(1, bunk_count + 1):
            for bunk_type in ["upper", "lower"]:
                bunk_id = f"{bunk_type}-{i}"
                btn = Button(text=f"{bunk_type.capitalize()} Bunk {i}", size_hint_y=None, height=40)

                if bunk_id in assigned_bunks:
                    btn.disabled = True
                    btn.text += " (Taken)"
                else:
                    btn.bind(on_press=self.make_form(self.room_name, bunk_type, i))

                self.layout.add_widget(btn)

        back_btn = Button(text="Back", size_hint_y=None, height=40)
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)
    def save_tenant_and_close(self, room, bunk, name, date, number, leave_date, popup):
        cursor.execute("INSERT INTO tenants (room, bunk, name, date, number, leave_date) VALUES (?, ?, ?, ?, ?, ?)",
                   (room, bunk, name, date, number, leave_date))
        conn.commit()
        popup.dismiss()
        self.manager.current = "menu"


    def make_form(self, room, bunk_type, bunk_number):
        def callback(instance):
            form_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)

            name_input = TextInput(hint_text="Name", size_hint_y=None, height=40)
            date_input = TextInput(hint_text="Date (YYYY-MM-DD)", size_hint_y=None, height=40)
            number_input = TextInput(hint_text="Contact Number", size_hint_y=None, height=40)
            leave_input = TextInput(hint_text="Leave Date (YYYY-MM-DD)", size_hint_y=None, height=40)

            submit_btn = Button(text="Submit", size_hint_y=None, height=40)
            close_btn = Button(text="Cancel", size_hint_y=None, height=40)

            popup = Popup(title=f"{room} - {bunk_type.capitalize()} Bunk {bunk_number}",
                        content=form_layout,
                        size_hint=(0.9, 0.8))

            submit_btn.bind(on_press=lambda x: self.save_tenant_and_close(
                room,
                f"{bunk_type}-{bunk_number}",
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


    def save_tenant(self, room, bunk, name, date, number, leave_date):
        cursor.execute("INSERT INTO tenants (room, bunk, name, date, number, leave_date) VALUES (?, ?, ?, ?, ?, ?)",
                       (room, bunk, name, date, number, leave_date))
        conn.commit()
        self.manager.current = "menu"

    def go_back(self, instance):
        self.manager.current = "menu"

# 📋 Tenant Info Screen
class TenantInfoScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Main vertical layout
        root = BoxLayout(orientation='vertical', padding=10, spacing=10)

        # Title stays fixed at the top
        title = Label(text="Tenant Info", size_hint_y=None, height=40)
        root.add_widget(title)

        # Scrollable tenant layout
        scroll = ScrollView()
        self.layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=10)
        self.layout.bind(minimum_height=self.layout.setter('height'))
        scroll.add_widget(self.layout)

        root.add_widget(scroll)
        self.add_widget(root)

    def on_pre_enter(self):
        self.refresh()

    def refresh(self):
        self.layout.clear_widgets()
        self.layout.add_widget(Label(text="Tenant Info", size_hint_y=20, height=40))

        # ✅ Filter tenants by leave date
        today = datetime.today().strftime("%Y-%m-%d")
        cursor.execute("""
        SELECT id, room, bunk, name, date, number, payment, leave_date
        FROM tenants
        WHERE leave_date IS NULL OR leave_date = '' OR leave_date > ?
        """, (today,))

        for tenant in cursor.fetchall():
            box = BoxLayout(orientation='vertical', size_hint_y=None, padding=5, spacing=5)

            summary = (
                f"{tenant[1]}\n"
                f"{tenant[2]}\n"
                f"{tenant[3]}\n"
                f"{tenant[4]}\n"
                f"{tenant[5]}\n"
                f"Leave: {tenant[7] or 'N/A'}\n"
                f"Payment: ₱{tenant[6] if tenant[6] else '0.00'}"
            )

            label = Label(text=summary, halign='left', valign='top', size_hint_y=None, height=160)
            label.bind(size=lambda instance, value: setattr(instance, 'text_size', (instance.width, None)))
            box.add_widget(label)

            button_row = BoxLayout(size_hint_y=None, height=40, spacing=5)

            payment_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
            payment_input = TextInput(hint_text="Enter Payment")
            update_btn = Button(text="Update", size_hint_x=0.3)
            update_btn.bind(on_press=lambda x, tid=tenant[0], inp=payment_input: self.update_payment(tid, inp.text))
            payment_row.add_widget(payment_input)
            payment_row.add_widget(update_btn)
            box.add_widget(payment_row)


            leave_row = BoxLayout(size_hint_y=None, height=40, spacing=5)
            leave_input = TextInput(hint_text="Leave Date")
            leave_btn = Button(text="Set Leave", size_hint_x=0.3)
            leave_btn.bind(on_press=lambda x, tid=tenant[0], inp=leave_input: self.update_leave_date(tid, inp.text))
            leave_row.add_widget(leave_input)
            leave_row.add_widget(leave_btn)
            box.add_widget(leave_row)

            delete_row = BoxLayout(size_hint_y=None, height=40)
            delete_btn = Button(text="Delete", size_hint_x=1)
            delete_btn.bind(on_press=lambda x, tid=tenant[0]: self.delete_tenant(tid))
            delete_row.add_widget(delete_btn)
            box.add_widget(delete_row)


            box.add_widget(button_row)
            self.layout.add_widget(box)

            # ✅ Add spacer between tenants
            spacer = Label(text="", size_hint_y=None, height=160)
            self.layout.add_widget(spacer)

        back_btn = Button(text="Back", size_hint_y=None, height=40)
        back_btn.bind(on_press=self.go_back)
        self.layout.add_widget(back_btn)

    def update_payment(self, tenant_id, payment):
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