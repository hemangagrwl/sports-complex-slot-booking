from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import mysql.connector
from datetime import datetime, timedelta
import traceback

import os
from dotenv import load_dotenv

load_dotenv()
# ---------------- MySQL Connection ----------------
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

import os

db = mysql.connector.connect(
    host=os.getenv("MYSQLHOST"),
    user=os.getenv("MYSQLUSER"),
    password=os.getenv("MYSQLPASSWORD"),
    database=os.getenv("MYSQLDATABASE"),
    port=int(os.getenv("MYSQLPORT"))
)

cursor = db.cursor()

# ---------------- Helper Functions ----------------
def run_query(query, values=(), fetchone=False, fetchall=False):
    try:
        cursor.execute(query, values)
        if fetchone:
            return cursor.fetchone()
        elif fetchall:
            return cursor.fetchall()
        else:
            db.commit()
            return True
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        if not fetchone and not fetchall:
            db.rollback()
        return None if (fetchone or fetchall) else False

# ---------------- Routes ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uid = request.form.get('user_id')
        pwd = request.form.get('password')
        result = run_query("SELECT name, password, subscription_status FROM users WHERE id = %s", (uid,), fetchone=True)
        if result:
            name, db_password, sub_status = result
            if pwd == db_password:
                if sub_status == 'a':
                    session['user_id'] = uid
                    session['user_name'] = name
                    return redirect(url_for('dashboard'))
                else:
                    flash("Your subscription has expired.")
            else:
                flash("Invalid password.")
        else:
            flash("Invalid user ID.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect(url_for('login'))
    return render_template('dashboard.html', user_name=session['user_name'])

@app.route('/book_slots', methods=['GET', 'POST'])
def book_slots():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect(url_for('login'))
    next_day = (datetime.today() + timedelta(days=1)).date()
    
    # Get facilities user has subscription for
    subscribed_facilities = run_query("""
        SELECT f.id
        FROM facilities f
        JOIN subscriptions s ON f.id = s.facility_id
        WHERE s.user_id = %s
    """, (session['user_id'],), fetchall=True)
    
    if not subscribed_facilities:
        flash("You have no active subscriptions.")
        return redirect(url_for('dashboard'))
    
    # Get facilities user has booked for next day
    booked_facilities = run_query("""
        SELECT DISTINCT s.facility_id
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        WHERE b.user_id = %s AND s.date = %s
    """, (session['user_id'], next_day), fetchall=True)
    
    subscribed_ids = [f[0] for f in subscribed_facilities]
    booked_ids = [f[0] for f in booked_facilities]
    
    if len(subscribed_ids) == len(booked_ids) and all(fid in booked_ids for fid in subscribed_ids):
        flash("Cannot book any more slots. You have already booked slots for all available facilities.")
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        facility_id = request.form.get('facility')
        slot_id = request.form.get('slot')
        
        # Check if user already booked slot for this facility on next day
        facility_booking = run_query("""
            SELECT b.id FROM bookings b
            JOIN slots s ON b.slot_id = s.id
            WHERE b.user_id = %s AND s.facility_id = %s AND s.date = %s
        """, (session['user_id'], facility_id, next_day), fetchone=True)
        
        if facility_booking:
            flash("You have already booked a slot for this facility. Maximum one slot per facility is allowed.")
            return redirect(url_for('book_slots'))
        
        # Get time details of selected slot
        slot_time = run_query("""
            SELECT time_start, time_end
            FROM slots
            WHERE id = %s
        """, (slot_id,), fetchone=True)
        
        if not slot_time:
            flash("Invalid slot selected.")
            return redirect(url_for('book_slots'))
        slot_start, slot_end = slot_time
        
        # Check if user has a conflicting booking across all facilities
        time_conflict = run_query("""
            SELECT b.id FROM bookings b
            JOIN slots s ON b.slot_id = s.id
            WHERE b.user_id = %s AND s.date = %s
            AND ((s.time_start <= %s AND s.time_end > %s)
                 OR (s.time_start < %s AND s.time_end >= %s)
                 OR (s.time_start >= %s AND s.time_end <= %s))
        """, (session['user_id'], next_day, slot_start, slot_start, slot_end, slot_end, slot_start, slot_end), fetchone=True)
        
        if time_conflict:
            flash("You already have a booking at this time slot. Please select a different time.")
            return redirect(url_for('book_slots'))
        
        # Check if the slot is still available
        slot_check = run_query("""
            SELECT f.capacity, (SELECT COUNT(*) FROM bookings WHERE slot_id = %s)
            FROM slots s
            JOIN facilities f ON s.facility_id = f.id
            WHERE s.id = %s
        """, (slot_id, slot_id), fetchone=True)
        
        if slot_check:
            capacity, booked = slot_check
            if booked >= capacity:
                flash("Sorry, this slot is no longer available.")
                return redirect(url_for('book_slots'))
        
        result = run_query("INSERT INTO bookings (user_id, slot_id) VALUES (%s, %s)", (session['user_id'], slot_id))
        if result:
            flash("Slot successfully booked.")
        else:
            flash("Error booking slot. Please try again.")
        return redirect(url_for('dashboard'))
    
    # For GET, fetch user's subscribed facilities
    facilities = run_query("""
        SELECT f.id, f.name
        FROM facilities f
        JOIN subscriptions s ON f.id = s.facility_id
        WHERE s.user_id = %s
    """, (session['user_id'],), fetchall=True)
    print("Facilities from DB:", facilities)
    print("Current DB:", run_query("SELECT DATABASE()", fetchone=True))
    print("All subscriptions:", run_query("SELECT * FROM subscriptions WHERE user_id = %s", (session['user_id'],), fetchall=True))
    print("All DBs:", run_query("SHOW DATABASES", fetchall=True))
    print("All subscriptions table:", run_query("SELECT * FROM subscriptions", fetchall=True))

    facility_id = request.args.get('facility_id')
    slots = []
    if facility_id:
        facility_booking = run_query("""
            SELECT b.id FROM bookings b
            JOIN slots s ON b.slot_id = s.id
            WHERE b.user_id = %s AND s.facility_id = %s AND s.date = %s
        """, (session['user_id'], facility_id, next_day), fetchone=True)

        if facility_booking:
            flash("You have already booked a slot for this facility. Maximum one slot per facility is allowed.")
            return redirect(url_for('book_slots'))
        
        user_bookings = run_query("""
            SELECT s.time_start, s.time_end
            FROM bookings b
            JOIN slots s ON b.slot_id = s.id
            WHERE b.user_id = %s AND s.date = %s
        """, (session['user_id'], next_day), fetchall=True)
        
        slots_data = run_query("""
            SELECT s.id, s.time_start, s.time_end, f.capacity,
                   (SELECT COUNT(*) FROM bookings WHERE slot_id = s.id)
            FROM slots s
            JOIN facilities f ON s.facility_id = f.id
            WHERE s.facility_id = %s AND s.date = %s
        """, (facility_id, next_day), fetchall=True)
        
        if slots_data:
            for sid, start, end, cap, booked in slots_data:
                if booked >= cap:
                    continue
                conflict = False
                if user_bookings:
                    for booked_start, booked_end in user_bookings:
                        if ((start <= booked_start and end > booked_start) or
                            (start < booked_end and end >= booked_end) or
                            (start >= booked_start and end <= booked_end)):
                            conflict = True
                            break
                if not conflict:
                    slots.append((sid, start, end, cap - booked))
    
    return render_template('book_slots.html', facilities=facilities, slots=slots)

@app.route('/cancel_booking', methods=['GET', 'POST'])
def cancel_booking():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect(url_for('login'))
    next_day = (datetime.today() + timedelta(days=1)).date()
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        run_query("DELETE FROM bookings WHERE id = %s", (booking_id,))
        flash("Booking successfully cancelled.")
        return redirect(url_for('dashboard'))
    bookings = run_query("""
        SELECT b.id, s.time_start, s.time_end, f.name
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN facilities f ON s.facility_id = f.id
        WHERE b.user_id = %s AND s.date = %s
    """, (session['user_id'], next_day), fetchall=True)
    if not bookings:
        flash("No bookings to cancel.")
        return redirect(url_for('dashboard'))
    return render_template('cancel_booking.html', bookings=bookings)

@app.route('/modify_booking', methods=['GET', 'POST'])
def modify_booking():
    if 'user_id' not in session:
        flash("Please login first")
        return redirect(url_for('login'))
    next_day = (datetime.today() + timedelta(days=1)).date()
    if request.method == 'POST':
        booking_id = request.form.get('booking_id')
        new_slot_id = request.form.get('new_slot_id')
        new_slot_time = run_query("""
            SELECT time_start, time_end, facility_id
            FROM slots
            WHERE id = %s
        """, (new_slot_id,), fetchone=True)
        if not new_slot_time:
            flash("Invalid slot selected.")
            return redirect(url_for('modify_booking'))
        new_start, new_end, new_facility_id = new_slot_time
        current_booking = run_query("""
            SELECT s.facility_id, s.id
            FROM bookings b
            JOIN slots s ON b.slot_id = s.id
            WHERE b.id = %s
        """, (booking_id,), fetchone=True)
        if not current_booking:
            flash("Booking not found.")
            return redirect(url_for('modify_booking'))
        current_facility_id, current_slot_id = current_booking
        if current_facility_id != new_facility_id:
            facility_booking = run_query("""
                SELECT b.id FROM bookings b
                JOIN slots s ON b.slot_id = s.id
                WHERE b.user_id = %s AND s.facility_id = %s AND s.date = %s
                AND b.id != %s
            """, (session['user_id'], new_facility_id, next_day, booking_id), fetchone=True)
            if facility_booking:
                flash("You already have a booking for this facility. Maximum one slot per facility is allowed.")
                return redirect(url_for('modify_booking'))
        time_conflict = run_query("""
            SELECT b.id FROM bookings b
            JOIN slots s ON b.slot_id = s.id
            WHERE b.user_id = %s AND s.date = %s AND b.id != %s
            AND ((s.time_start <= %s AND s.time_end > %s) OR
                 (s.time_start < %s AND s.time_end >= %s) OR
                 (s.time_start >= %s AND s.time_end <= %s))
        """, (session['user_id'], next_day, booking_id, new_start, new_start, new_end, new_end, new_start, new_end), fetchone=True)
        if time_conflict:
            flash("You already have another booking at this time slot. Please select a different time.")
            return redirect(url_for('modify_booking'))
        run_query("UPDATE bookings SET slot_id = %s WHERE id = %s", (new_slot_id, booking_id))
        flash("Booking modified successfully.")
        return redirect(url_for('dashboard'))
    bookings = run_query("""
        SELECT b.id, s.id, s.time_start, s.time_end, f.name, s.facility_id
        FROM bookings b
        JOIN slots s ON b.slot_id = s.id
        JOIN facilities f ON s.facility_id = f.id
        WHERE b.user_id = %s AND s.date = %s
    """, (session['user_id'], next_day), fetchall=True)
    if not bookings:
        flash("No bookings to modify.")
        return redirect(url_for('dashboard'))
    booking_id = request.args.get('booking_id')
    current_slot_id = request.args.get('current_slot_id')
    facility_id = request.args.get('facility_id')
    new_slots = []
    if booking_id and current_slot_id and facility_id:
        user_bookings = run_query("""
            SELECT s.time_start, s.time_end
            FROM bookings b
            JOIN slots s ON b.slot_id = s.id
            WHERE b.user_id = %s AND s.date = %s AND b.id != %s
        """, (session['user_id'], next_day, booking_id), fetchall=True)
        slots_data = run_query("""
            SELECT s.id, s.time_start, s.time_end, f.capacity,
                   (SELECT COUNT(*) FROM bookings WHERE slot_id = s.id)
            FROM slots s
            JOIN facilities f ON s.facility_id = f.id
            WHERE s.facility_id = %s AND s.date = %s AND s.id != %s
        """, (facility_id, next_day, current_slot_id), fetchall=True)
        if slots_data:
            for sid, start, end, cap, booked in slots_data:
                if booked >= cap:
                    continue
                conflict = False
                if user_bookings:
                    for booked_start, booked_end in user_bookings:
                        if ((start <= booked_start and end > booked_start) or
                            (start < booked_end and end >= booked_end) or
                            (start >= booked_start and end <= booked_end)):
                            conflict = True
                            break
                if not conflict:
                    new_slots.append((sid, start, end, cap - booked))
    return render_template('modify_booking.html', bookings=bookings, new_slots=new_slots,
                           selected_booking_id=booking_id)

@app.route('/api/slots')
def api_slots():
    try:
        if 'user_id' not in session:
            return jsonify({"error": "Not authenticated"}), 401
        
        facility_id = request.args.get('facility_id')
        booking_id = request.args.get('booking_id')
        current_slot_id = request.args.get('current_slot_id')
        
        if not facility_id:
            return jsonify({"error": "No facility selected"}), 400
        
        try:
            facility_id = int(facility_id)
            if booking_id:
                booking_id = int(booking_id)
            if current_slot_id:
                current_slot_id = int(current_slot_id)
        except ValueError:
            return jsonify({"error": "Invalid parameter format"}), 400
            
        next_day = (datetime.today() + timedelta(days=1)).date()
        
        # If we're modifying a booking, don't check if already booked
        if not booking_id:
            # Check if user already has a booking for this facility
            facility_booking = run_query("""
                SELECT b.id FROM bookings b
                JOIN slots s ON b.slot_id = s.id
                WHERE b.user_id = %s AND s.facility_id = %s AND s.date = %s
            """, (session['user_id'], facility_id, next_day), fetchone=True)
            
            if facility_booking:
                return jsonify({"error": "You already have a booking for this facility. Maximum one slot per facility allowed."})
        
        # Get user's existing bookings to check for time conflicts
        # If modifying, exclude the booking being modified
        if booking_id:
            user_bookings = run_query("""
                SELECT s.time_start, s.time_end
                FROM bookings b
                JOIN slots s ON b.slot_id = s.id
                WHERE b.user_id = %s AND s.date = %s AND b.id != %s
            """, (session['user_id'], next_day, booking_id), fetchall=True)
        else:
            user_bookings = run_query("""
                SELECT s.time_start, s.time_end
                FROM bookings b
                JOIN slots s ON b.slot_id = s.id
                WHERE b.user_id = %s AND s.date = %s
            """, (session['user_id'], next_day), fetchall=True)
        
        if user_bookings is None:
            user_bookings = []
        
        # Get available slots - if modifying, exclude current slot
        if current_slot_id:
            slots_data = run_query("""
                SELECT s.id, s.time_start, s.time_end, f.capacity,
                       (SELECT COUNT(*) FROM bookings WHERE slot_id = s.id)
                FROM slots s
                JOIN facilities f ON s.facility_id = f.id
                WHERE s.facility_id = %s AND s.date = %s AND s.id != %s
            """, (facility_id, next_day, current_slot_id), fetchall=True)
        else:
            slots_data = run_query("""
                SELECT s.id, s.time_start, s.time_end, f.capacity,
                       (SELECT COUNT(*) FROM bookings WHERE slot_id = s.id)
                FROM slots s
                JOIN facilities f ON s.facility_id = f.id
                WHERE s.facility_id = %s AND s.date = %s
            """, (facility_id, next_day), fetchall=True)
        
        if slots_data is None:
            return jsonify({"error": "Error retrieving slots data"}), 500
        
        available_slots = []
        for sid, start, end, cap, booked in slots_data:
            if booked >= cap:
                continue
            
            conflict = False
            for booked_start, booked_end in user_bookings:
                if ((start <= booked_start and end > booked_start) or
                    (start < booked_end and end >= booked_end) or
                    (start >= booked_start and end <= booked_end)):
                    conflict = True
                    break
            
            if not conflict:
                available_slots.append({
                    "id": sid,
                    "start": str(start),
                    "end": str(end),
                    "capacity": cap - booked
                })
        
        return jsonify(available_slots)
        
    except Exception as e:
        print(f"Error in api_slots: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
