from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, make_response
import sqlite3, hashlib, os, re, uuid, io
from datetime import datetime, timedelta, date
from functools import wraps
import qrcode, base64

app = Flask(__name__)
app.secret_key = "busbooking_secret_2024"

DB = "busbooking.db"

# ─── DB HELPERS ───────────────────────────────────────────────────────────────
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        password TEXT NOT NULL,
        role TEXT DEFAULT 'user',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS buses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_number TEXT UNIQUE NOT NULL,
        bus_name TEXT NOT NULL,
        bus_type TEXT NOT NULL,
        source TEXT NOT NULL,
        destination TEXT NOT NULL,
        departure_time TEXT NOT NULL,
        arrival_time TEXT NOT NULL,
        duration TEXT NOT NULL,
        price REAL NOT NULL,
        total_seats INTEGER NOT NULL DEFAULT 40,
        amenities TEXT,
        is_active INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_ref TEXT UNIQUE NOT NULL,
        user_id INTEGER NOT NULL,
        bus_id INTEGER NOT NULL,
        travel_date TEXT NOT NULL,
        seats TEXT NOT NULL,
        seat_count INTEGER NOT NULL,
        total_price REAL NOT NULL,
        payment_method TEXT,
        payment_status TEXT DEFAULT 'pending',
        booking_status TEXT DEFAULT 'booked',
        passenger_name TEXT,
        passenger_phone TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(bus_id) REFERENCES buses(id)
    );

    CREATE TABLE IF NOT EXISTS seat_locks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bus_id INTEGER NOT NULL,
        travel_date TEXT NOT NULL,
        seat_number INTEGER NOT NULL,
        session_id TEXT NOT NULL,
        locked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        bus_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        comment TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Seed admin
    pw = hashlib.sha256("admin123".encode()).hexdigest()
    c.execute("INSERT OR IGNORE INTO users (name,email,phone,password,role) VALUES (?,?,?,?,?)",
              ("Admin","admin@busbook.com","9999999999",pw,"admin"))

    # Seed sample buses
    buses = [
        ("TN-01","KPN Travels","AC Sleeper","Chennai","Coimbatore","22:00","06:00","8h","650",40,"WiFi,Charging,Water"),
        ("TN-02","SRS Travels","Non-AC Seater","Chennai","Madurai","21:00","04:30","7.5h","380",40,"Charging"),
        ("TN-03","Parveen Travels","AC Seater","Chennai","Salem","20:00","01:00","5h","420",40,"WiFi,Charging"),
        ("TN-04","VRL Travels","Sleeper","Chennai","Trichy","22:30","05:00","6.5h","480",40,"Charging,Water"),
        ("TN-05","Orange Travels","AC Sleeper","Coimbatore","Chennai","21:30","06:00","8.5h","680",40,"WiFi,Charging,Water"),
        ("TN-06","KPN Travels","Non-AC Seater","Madurai","Chennai","20:00","04:00","8h","360",40,"Charging"),
        ("TN-07","SRS Travels","AC Seater","Salem","Chennai","22:00","03:00","5h","400",40,"WiFi"),
        ("TN-08","Parveen Travels","AC Sleeper","Trichy","Coimbatore","20:30","04:00","7.5h","550",40,"WiFi,Charging"),
        ("TN-09","VRL Travels","Non-AC Seater","Coimbatore","Madurai","08:00","12:30","4.5h","280",40,"Charging"),
        ("TN-10","KPN Travels","AC Seater","Madurai","Coimbatore","09:00","14:00","5h","350",40,"WiFi,Charging"),
        ("TN-11","Orange Travels","AC Sleeper","Chennai","Tirunelveli","22:00","07:00","9h","720",40,"WiFi,Charging,Water"),
        ("TN-12","SRS Travels","Non-AC Seater","Chennai","Vellore","06:00","10:00","4h","220",40,"Charging"),
        ("TN-13","Parveen Travels","AC Seater","Coimbatore","Salem","07:00","10:00","3h","280",40,"WiFi"),
        ("TN-14","KPN Travels","AC Sleeper","Madurai","Trichy","18:00","21:00","3h","320",40,"WiFi,Charging"),
        ("TN-15","VRL Travels","Non-AC Seater","Trichy","Madurai","07:00","10:00","3h","200",40,"Charging"),
    ]
    for b in buses:
        c.execute("INSERT OR IGNORE INTO buses (bus_number,bus_name,bus_type,source,destination,departure_time,arrival_time,duration,price,total_seats,amenities) VALUES (?,?,?,?,?,?,?,?,?,?,?)", b)

    conn.commit()
    conn.close()

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login first.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get('role') != 'admin':
            flash("Admin access required.", "danger")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

def get_booked_seats(bus_id, travel_date):
    conn = get_db()
    rows = conn.execute(
        "SELECT seats FROM bookings WHERE bus_id=? AND travel_date=? AND booking_status='booked'",
        (bus_id, travel_date)).fetchall()
    conn.close()
    booked = []
    for r in rows:
        booked.extend([int(s) for s in r['seats'].split(',')])
    return booked

def get_locked_seats(bus_id, travel_date):
    conn = get_db()
    cutoff = datetime.now() - timedelta(minutes=5)
    rows = conn.execute(
        "SELECT seat_number FROM seat_locks WHERE bus_id=? AND travel_date=? AND locked_at>?",
        (bus_id, travel_date, cutoff)).fetchall()
    conn.close()
    return [r['seat_number'] for r in rows]

def make_qr(text):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode()

DISTRICTS = sorted([
    "Chennai","Coimbatore","Madurai","Trichy","Salem","Tirunelveli","Vellore",
    "Erode","Tiruppur","Thanjavur","Dindigul","Cuddalore","Nagercoil","Kanchipuram",
    "Puducherry","Hosur","Ooty","Karur","Sivakasi","Kumbakonam","Ramanathapuram",
    "Tiruvannamalai","Namakkal","Krishnagiri","Villupuram","Tiruvarur","Nagapattinam",
    "Ariyalur","Perambalur","Pudukkottai","Virudhunagar","Thoothukudi","Sivaganga"
])

# ─── ROUTES ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html', districts=DISTRICTS,
                           today=date.today().isoformat(),
                           max_date=(date.today()+timedelta(days=14)).isoformat())

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        phone = request.form['phone'].strip()
        pw = request.form['password']
        pw2 = request.form['confirm_password']
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            flash("Invalid email address.", "danger")
            return redirect(url_for('register'))
        if pw != pw2:
            flash("Passwords do not match.", "danger")
            return redirect(url_for('register'))
        if len(pw) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for('register'))
        try:
            conn = get_db()
            conn.execute("INSERT INTO users (name,email,phone,password) VALUES (?,?,?,?)",
                         (name, email, phone, hash_pw(pw)))
            conn.commit()
            conn.close()
            flash("Registration successful! Please login.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Email already registered.", "danger")
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        pw = request.form['password']
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=? AND password=?",
                            (email, hash_pw(pw))).fetchone()
        conn.close()
        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            session['session_id'] = str(uuid.uuid4())
            flash(f"Welcome back, {user['name']}!", "success")
            return redirect(url_for('admin_dashboard') if user['role']=='admin' else url_for('index'))
        flash("Invalid email or password.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "info")
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET','POST'])
@login_required
def profile():
    conn = get_db()
    if request.method == 'POST':
        name = request.form['name'].strip()
        phone = request.form['phone'].strip()
        conn.execute("UPDATE users SET name=?, phone=? WHERE id=?",
                     (name, phone, session['user_id']))
        conn.commit()
        session['user_name'] = name
        flash("Profile updated.", "success")
    user = conn.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/search')
def search():
    src = request.args.get('source','')
    dst = request.args.get('destination','')
    tdate = request.args.get('travel_date','')
    buses = []
    if src and dst and tdate:
        conn = get_db()
        buses_raw = conn.execute(
            "SELECT * FROM buses WHERE source=? AND destination=? AND is_active=1",
            (src, dst)).fetchall()
        conn.close()
        for b in buses_raw:
            booked = get_booked_seats(b['id'], tdate)
            avail = b['total_seats'] - len(booked)
            buses.append({**dict(b), 'available_seats': avail})
    return render_template('search.html', buses=buses, source=src,
                           destination=dst, travel_date=tdate, districts=DISTRICTS,
                           today=date.today().isoformat(),
                           max_date=(date.today()+timedelta(days=14)).isoformat())

@app.route('/bus/<int:bus_id>/seats')
@login_required
def seat_selection(bus_id):
    tdate = request.args.get('travel_date','')
    if not tdate:
        flash("Please select a travel date.", "warning")
        return redirect(url_for('index'))
    conn = get_db()
    bus = conn.execute("SELECT * FROM buses WHERE id=?", (bus_id,)).fetchone()
    conn.close()
    if not bus:
        flash("Bus not found.", "danger")
        return redirect(url_for('index'))
    booked = get_booked_seats(bus_id, tdate)
    locked = get_locked_seats(bus_id, tdate)
    my_locked = []
    conn2 = get_db()
    cutoff = datetime.now() - timedelta(minutes=5)
    rows = conn2.execute(
        "SELECT seat_number FROM seat_locks WHERE bus_id=? AND travel_date=? AND session_id=? AND locked_at>?",
        (bus_id, tdate, session.get('session_id',''), cutoff)).fetchall()
    conn2.close()
    my_locked = [r['seat_number'] for r in rows]
    return render_template('seats.html', bus=bus, travel_date=tdate,
                           booked=booked, locked=locked, my_locked=my_locked,
                           total=bus['total_seats'])

@app.route('/lock_seat', methods=['POST'])
@login_required
def lock_seat():
    data = request.get_json()
    bus_id = data.get('bus_id')
    seat = data.get('seat')
    tdate = data.get('travel_date')
    sid = session.get('session_id','')
    booked = get_booked_seats(bus_id, tdate)
    locked = get_locked_seats(bus_id, tdate)
    if seat in booked or seat in locked:
        return jsonify({'ok': False, 'msg': 'Seat not available'})
    conn = get_db()
    conn.execute("INSERT INTO seat_locks (bus_id,travel_date,seat_number,session_id) VALUES (?,?,?,?)",
                 (bus_id, tdate, seat, sid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/unlock_seat', methods=['POST'])
@login_required
def unlock_seat():
    data = request.get_json()
    bus_id = data.get('bus_id')
    seat = data.get('seat')
    tdate = data.get('travel_date')
    sid = session.get('session_id','')
    conn = get_db()
    conn.execute("DELETE FROM seat_locks WHERE bus_id=? AND travel_date=? AND seat_number=? AND session_id=?",
                 (bus_id, tdate, seat, sid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@app.route('/book/<int:bus_id>', methods=['GET','POST'])
@login_required
def book(bus_id):
    tdate = request.args.get('travel_date') or request.form.get('travel_date','')
    seats_str = request.args.get('seats') or request.form.get('seats','')
    conn = get_db()
    bus = conn.execute("SELECT * FROM buses WHERE id=?", (bus_id,)).fetchone()
    conn.close()
    if not bus:
        flash("Bus not found.", "danger")
        return redirect(url_for('index'))
    if request.method == 'POST':
        seats_str = request.form.get('seats','')
        tdate = request.form.get('travel_date','')
        pname = request.form.get('passenger_name','').strip()
        pphone = request.form.get('passenger_phone','').strip()
        payment = request.form.get('payment_method','')
        if not seats_str:
            flash("Please select at least one seat.", "warning")
            return redirect(url_for('seat_selection', bus_id=bus_id, travel_date=tdate))
        seat_list = [int(s) for s in seats_str.split(',') if s]
        # Final check
        booked = get_booked_seats(bus_id, tdate)
        for s in seat_list:
            if s in booked:
                flash(f"Seat {s} was just booked by someone else. Please reselect.", "danger")
                return redirect(url_for('seat_selection', bus_id=bus_id, travel_date=tdate))
        total = bus['price'] * len(seat_list)
        ref = "BB" + str(uuid.uuid4().hex[:8]).upper()
        conn2 = get_db()
        conn2.execute("""INSERT INTO bookings
            (booking_ref,user_id,bus_id,travel_date,seats,seat_count,total_price,
             payment_method,payment_status,booking_status,passenger_name,passenger_phone)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (ref, session['user_id'], bus_id, tdate, seats_str, len(seat_list),
             total, payment, 'paid', 'booked', pname, pphone))
        # Remove locks
        sid = session.get('session_id','')
        for s in seat_list:
            conn2.execute("DELETE FROM seat_locks WHERE bus_id=? AND travel_date=? AND seat_number=? AND session_id=?",
                         (bus_id, tdate, s, sid))
        conn2.commit()
        conn2.close()
        flash("Booking confirmed! 🎉", "success")
        return redirect(url_for('ticket', ref=ref))
    seats = [int(s) for s in seats_str.split(',') if s]
    total = bus['price'] * len(seats)
    return render_template('book.html', bus=bus, travel_date=tdate,
                           seats=seats, total=total)

@app.route('/ticket/<ref>')
@login_required
def ticket(ref):
    conn = get_db()
    bk = conn.execute("""
        SELECT b.*,u.name as uname,u.email,u.phone as uphon,
               bs.bus_name,bs.bus_number,bs.bus_type,bs.source,bs.destination,
               bs.departure_time,bs.arrival_time,bs.duration,bs.amenities
        FROM bookings b
        JOIN users u ON b.user_id=u.id
        JOIN buses bs ON b.bus_id=bs.id
        WHERE b.booking_ref=? AND b.user_id=?
    """, (ref, session['user_id'])).fetchone()
    conn.close()
    if not bk:
        flash("Ticket not found.", "danger")
        return redirect(url_for('my_bookings'))
    qr_data = f"BookingRef:{ref}|Bus:{bk['bus_number']}|Date:{bk['travel_date']}|Seats:{bk['seats']}"
    qr_img = make_qr(qr_data)
    return render_template('ticket.html', bk=bk, qr_img=qr_img)

@app.route('/my-bookings')
@login_required
def my_bookings():
    conn = get_db()
    bookings = conn.execute("""
        SELECT b.*,bs.bus_name,bs.bus_number,bs.source,bs.destination,
               bs.departure_time,bs.arrival_time,bs.bus_type
        FROM bookings b JOIN buses bs ON b.bus_id=bs.id
        WHERE b.user_id=? ORDER BY b.created_at DESC
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('my_bookings.html', bookings=bookings)

@app.route('/cancel/<ref>', methods=['POST'])
@login_required
def cancel(ref):
    conn = get_db()
    bk = conn.execute("SELECT * FROM bookings WHERE booking_ref=? AND user_id=?",
                      (ref, session['user_id'])).fetchone()
    if bk and bk['booking_status'] == 'booked':
        tdate = datetime.strptime(bk['travel_date'], '%Y-%m-%d').date()
        if tdate > date.today():
            conn.execute("UPDATE bookings SET booking_status='cancelled' WHERE booking_ref=?", (ref,))
            conn.commit()
            flash("Booking cancelled. Refund will be processed in 5-7 days.", "success")
        else:
            flash("Cannot cancel past bookings.", "danger")
    conn.close()
    return redirect(url_for('my_bookings'))

# ─── ADMIN ────────────────────────────────────────────────────────────────────

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    conn = get_db()
    stats = {
        'users': conn.execute("SELECT COUNT(*) FROM users WHERE role='user'").fetchone()[0],
        'buses': conn.execute("SELECT COUNT(*) FROM buses WHERE is_active=1").fetchone()[0],
        'bookings': conn.execute("SELECT COUNT(*) FROM bookings WHERE booking_status='booked'").fetchone()[0],
        'revenue': conn.execute("SELECT COALESCE(SUM(total_price),0) FROM bookings WHERE booking_status='booked' AND payment_status='paid'").fetchone()[0],
    }
    recent = conn.execute("""
        SELECT bk.*,u.name as uname,bs.bus_name,bs.source,bs.destination
        FROM bookings bk JOIN users u ON bk.user_id=u.id
        JOIN buses bs ON bk.bus_id=bs.id
        ORDER BY bk.created_at DESC LIMIT 10
    """).fetchall()
    conn.close()
    return render_template('admin/dashboard.html', stats=stats, recent=recent)

@app.route('/admin/buses')
@login_required
@admin_required
def admin_buses():
    conn = get_db()
    buses = conn.execute("SELECT * FROM buses ORDER BY id").fetchall()
    conn.close()
    return render_template('admin/buses.html', buses=buses, districts=DISTRICTS)

@app.route('/admin/buses/add', methods=['POST'])
@login_required
@admin_required
def admin_add_bus():
    f = request.form
    conn = get_db()
    try:
        conn.execute("""INSERT INTO buses
            (bus_number,bus_name,bus_type,source,destination,departure_time,
             arrival_time,duration,price,total_seats,amenities)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (f['bus_number'],f['bus_name'],f['bus_type'],f['source'],f['destination'],
             f['departure_time'],f['arrival_time'],f['duration'],
             float(f['price']),int(f['total_seats']),f.get('amenities','')))
        conn.commit()
        flash("Bus added successfully.", "success")
    except sqlite3.IntegrityError:
        flash("Bus number already exists.", "danger")
    finally:
        conn.close()
    return redirect(url_for('admin_buses'))

@app.route('/admin/buses/edit/<int:bid>', methods=['POST'])
@login_required
@admin_required
def admin_edit_bus(bid):
    f = request.form
    conn = get_db()
    conn.execute("""UPDATE buses SET bus_name=?,bus_type=?,source=?,destination=?,
        departure_time=?,arrival_time=?,duration=?,price=?,total_seats=?,
        amenities=?,is_active=? WHERE id=?""",
        (f['bus_name'],f['bus_type'],f['source'],f['destination'],
         f['departure_time'],f['arrival_time'],f['duration'],
         float(f['price']),int(f['total_seats']),f.get('amenities',''),
         int(f.get('is_active',1)), bid))
    conn.commit()
    conn.close()
    flash("Bus updated.", "success")
    return redirect(url_for('admin_buses'))

@app.route('/admin/buses/delete/<int:bid>', methods=['POST'])
@login_required
@admin_required
def admin_delete_bus(bid):
    conn = get_db()
    conn.execute("UPDATE buses SET is_active=0 WHERE id=?", (bid,))
    conn.commit()
    conn.close()
    flash("Bus deactivated.", "info")
    return redirect(url_for('admin_buses'))

@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    conn = get_db()
    users = conn.execute("""
        SELECT u.*, COUNT(b.id) as booking_count
        FROM users u LEFT JOIN bookings b ON u.id=b.user_id
        GROUP BY u.id ORDER BY u.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin/users.html', users=users)

@app.route('/admin/bookings')
@login_required
@admin_required
def admin_bookings():
    conn = get_db()
    bookings = conn.execute("""
        SELECT bk.*,u.name as uname,u.email,bs.bus_name,bs.bus_number,
               bs.source,bs.destination
        FROM bookings bk JOIN users u ON bk.user_id=u.id
        JOIN buses bs ON bk.bus_id=bs.id
        ORDER BY bk.created_at DESC
    """).fetchall()
    conn.close()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/rate/<int:bus_id>', methods=['POST'])
@login_required
def rate_bus(bus_id):
    rating = int(request.form.get('rating', 0))
    comment = request.form.get('comment','').strip()
    if 1 <= rating <= 5:
        conn = get_db()
        existing = conn.execute("SELECT id FROM ratings WHERE user_id=? AND bus_id=?",
                                (session['user_id'], bus_id)).fetchone()
        if existing:
            conn.execute("UPDATE ratings SET rating=?,comment=? WHERE id=?",
                         (rating, comment, existing['id']))
        else:
            conn.execute("INSERT INTO ratings (user_id,bus_id,rating,comment) VALUES (?,?,?,?)",
                         (session['user_id'], bus_id, rating, comment))
        conn.commit()
        conn.close()
        flash("Rating submitted. Thank you!", "success")
    return redirect(url_for('my_bookings'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
