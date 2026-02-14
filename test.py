import tkinter as tk
from tkinter import messagebox, ttk
import mysql.connector
from datetime import datetime, timedelta

# ---------------- MySQL Connection ----------------
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="9060748494",
    database="marenaa"
)
cursor = db.cursor()

# ---------------- Globals ----------------
user_id = None
user_name = None

# ---------------- Helper Functions ----------------
def run_query(query, values=(), fetchone=False, fetchall=False):
    cursor.execute(query, values)
    if fetchone:
        return cursor.fetchone()
    elif fetchall:
        return cursor.fetchall()
    else:
        db.commit()

# ---------------- Main App ----------------
class MarenaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Marena Slot Booking System")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6, font=("Arial", 10))
        self.style.configure("TLabel", font=("Arial", 11))
        self.login_screen()

    def clear_screen(self):
        for widget in self.root.winfo_children():
            widget.destroy()

    def login_screen(self):
        self.clear_screen()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        ttk.Label(frame, text="Login to Marena", font=("Arial", 16)).grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Label(frame, text="User ID:").grid(row=1, column=0, sticky='e', padx=5, pady=5)
        self.entry_user_id = ttk.Entry(frame)
        self.entry_user_id.grid(row=1, column=1, pady=5)
        self.entry_user_id.focus()

        ttk.Label(frame, text="Password:").grid(row=2, column=0, sticky='e', padx=5, pady=5)
        self.entry_password = ttk.Entry(frame, show="*")
        self.entry_password.grid(row=2, column=1, pady=5)
        self.entry_password.bind("<Return>", lambda e: self.login())

        ttk.Button(frame, text="Login", command=self.login).grid(row=3, column=0, columnspan=2, pady=15)

    def login(self):
        global user_id, user_name
        uid = self.entry_user_id.get()
        pwd = self.entry_password.get()

        result = run_query("SELECT name, password, subscription_status FROM users WHERE id = %s", (uid,), fetchone=True)
        if result:
            name, db_password, sub_status = result
            if pwd == db_password:
                if sub_status == 'a':
                    user_id = uid
                    user_name = name
                    self.dashboard()
                else:
                    messagebox.showwarning("Inactive", "Your subscription has expired.")
            else:
                messagebox.showerror("Login Failed", "Invalid password.")
        else:
            messagebox.showerror("Login Failed", "Invalid user ID.")

    def dashboard(self):
        self.clear_screen()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        ttk.Label(frame, text=f"Welcome, {user_name}", font=("Arial", 14)).grid(row=0, column=0, columnspan=2, pady=10)

        ttk.Button(frame, text="Book Slot", command=self.book_slot, width=30).grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(frame, text="Cancel Slot", command=self.cancel_slot, width=30).grid(row=2, column=0, columnspan=2, pady=5)
        ttk.Button(frame, text="Modify Slot", command=self.modify_slot, width=30).grid(row=3, column=0, columnspan=2, pady=5)
        ttk.Button(frame, text="Logout", command=self.login_screen, width=30).grid(row=4, column=0, columnspan=2, pady=15)

    # Slot Booking
    def book_slot(self):
        self.clear_screen()
        next_day = (datetime.today() + timedelta(days=1)).date()
        facilities = run_query("""
            SELECT f.id, f.name 
            FROM facilities f JOIN subscriptions s ON f.id = s.facility_id
            WHERE s.user_id = %s
        """, (user_id,), fetchall=True)

        if not facilities:
            messagebox.showinfo("No Access", "You have no active subscriptions.")
            self.dashboard()
            return

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        ttk.Label(frame, text="Select Facility", font=("Arial", 12)).grid(row=0, column=0, columnspan=2, pady=10)
        self.facility_cb = ttk.Combobox(frame, values=[f[1] for f in facilities], width=35)
        self.facility_cb.grid(row=1, column=0, columnspan=2, pady=5)

        def load_slots():
            idx = self.facility_cb.current()
            if idx == -1:
                return

            facility_id, _ = facilities[idx]

            # Check for existing booking
            if run_query("""
                SELECT b.id FROM bookings b 
                JOIN slots s ON b.slot_id = s.id 
                WHERE b.user_id = %s AND s.facility_id = %s AND s.date = %s
            """, (user_id, facility_id, next_day), fetchone=True):
                messagebox.showinfo("Duplicate", "You already booked a slot for this facility.")
                return

            # Get available slots
            slots = run_query("""
                SELECT s.id, s.time_start, s.time_end, f.capacity,
                (SELECT COUNT(*) FROM bookings WHERE slot_id = s.id) 
                FROM slots s JOIN facilities f ON s.facility_id = f.id
                WHERE s.facility_id = %s AND s.date = %s
            """, (facility_id, next_day), fetchall=True)

            available = [(sid, s, e, cap - booked) for sid, s, e, cap, booked in slots if booked < cap]
            if not available:
                messagebox.showinfo("Full", "No available slots.")
                return

            self.slot_cb = ttk.Combobox(frame, values=[
                f"{s}-{e} ({left} left)" for _, s, e, left in available
            ], width=35)
            self.slot_cb.grid(row=4, column=0, columnspan=2, pady=5)

            def confirm_booking():
                idx2 = self.slot_cb.current()
                if idx2 == -1: return
                slot_id = available[idx2][0]
                if messagebox.askyesno("Confirm", "Confirm this booking?"):
                    run_query("INSERT INTO bookings (user_id, slot_id) VALUES (%s, %s)", (user_id, slot_id))
                    messagebox.showinfo("Booked", "Slot successfully booked.")
                    self.dashboard()

            ttk.Button(frame, text="Confirm Booking", command=confirm_booking).grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(frame, text="Load Slots", command=load_slots).grid(row=2, column=0, columnspan=2, pady=5)
        ttk.Button(frame, text="Back", command=self.dashboard).grid(row=6, column=0, columnspan=2, pady=10)

    # Cancel Slot
    def cancel_slot(self):
        self.clear_screen()
        next_day = (datetime.today() + timedelta(days=1)).date()
        bookings = run_query("""
            SELECT b.id, s.time_start, s.time_end, f.name 
            FROM bookings b JOIN slots s ON b.slot_id = s.id 
            JOIN facilities f ON s.facility_id = f.id 
            WHERE b.user_id = %s AND s.date = %s
        """, (user_id, next_day), fetchall=True)

        if not bookings:
            messagebox.showinfo("None", "No bookings to cancel.")
            self.dashboard()
            return

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        self.cancel_cb = ttk.Combobox(frame, values=[
            f"{f} - {start}-{end}" for (_, start, end, f) in bookings
        ], width=40)
        self.cancel_cb.grid(row=0, column=0, columnspan=2, pady=10)

        def cancel():
            idx = self.cancel_cb.current()
            if idx == -1: return
            bid = bookings[idx][0]
            if messagebox.askyesno("Confirm", "Cancel this booking?"):
                run_query("DELETE FROM bookings WHERE id = %s", (bid,))
                messagebox.showinfo("Cancelled", "Booking successfully cancelled.")
                self.dashboard()

        ttk.Button(frame, text="Cancel Booking", command=cancel).grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(frame, text="Back", command=self.dashboard).grid(row=2, column=0, columnspan=2, pady=10)

    # Modify Slot
    def modify_slot(self):
        self.clear_screen()
        next_day = (datetime.today() + timedelta(days=1)).date()
        bookings = run_query("""
            SELECT b.id, s.id, s.time_start, s.time_end, f.name, s.facility_id 
            FROM bookings b JOIN slots s ON b.slot_id = s.id 
            JOIN facilities f ON s.facility_id = f.id 
            WHERE b.user_id = %s AND s.date = %s
        """, (user_id, next_day), fetchall=True)

        if not bookings:
            messagebox.showinfo("None", "No bookings to modify.")
            self.dashboard()
            return

        frame = ttk.Frame(self.root, padding=20)
        frame.pack(expand=True)

        self.modify_cb = ttk.Combobox(frame, values=[
            f"{f} - {start}-{end}" for (_, _, start, end, f, _) in bookings
        ], width=40)
        self.modify_cb.grid(row=0, column=0, columnspan=2, pady=10)

        def load_new_slots():
            idx = self.modify_cb.current()
            if idx == -1: return

            booking_id, current_slot_id, _, _, _, facility_id = bookings[idx]
            slots = run_query("""
                SELECT s.id, s.time_start, s.time_end, f.capacity,
                (SELECT COUNT(*) FROM bookings WHERE slot_id = s.id)
                FROM slots s JOIN facilities f ON s.facility_id = f.id
                WHERE s.facility_id = %s AND s.date = %s AND s.id != %s
            """, (facility_id, next_day, current_slot_id), fetchall=True)

            new_slots = []
            for sid, s, e, cap, booked in slots:
                exists = run_query("""
                    SELECT b.id FROM bookings b JOIN slots s ON b.slot_id = s.id
                    WHERE b.user_id = %s AND s.date = %s AND s.time_start = %s
                """, (user_id, next_day, s), fetchone=True)
                if not exists and booked < cap:
                    new_slots.append((sid, s, e, cap - booked))

            if not new_slots:
                messagebox.showinfo("No Slots", "No other vacant slots.")
                return

            self.new_cb = ttk.Combobox(frame, values=[
                f"{s}-{e} ({left} left)" for (_, s, e, left) in new_slots
            ], width=40)
            self.new_cb.grid(row=2, column=0, columnspan=2, pady=5)

            def update_booking():
                idx2 = self.new_cb.current()
                if idx2 == -1: return
                new_sid = new_slots[idx2][0]
                run_query("UPDATE bookings SET slot_id = %s WHERE id = %s", (new_sid, booking_id))
                messagebox.showinfo("Success", "Booking modified successfully.")
                self.dashboard()

            ttk.Button(frame, text="Confirm Change", command=update_booking).grid(row=3, column=0, columnspan=2, pady=5)

        ttk.Button(frame, text="Load Available Slots", command=load_new_slots).grid(row=1, column=0, columnspan=2, pady=5)
        ttk.Button(frame, text="Back", command=self.dashboard).grid(row=4, column=0, columnspan=2, pady=10)

# ---------------- Launch App ----------------
root = tk.Tk()
app = MarenaApp(root)
root.mainloop()
