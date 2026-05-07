# 🚌 BusBook TN — Tamil Nadu Bus Booking System

A complete bus booking web application built with:
- **Backend**: Python (Flask)
- **Frontend**: HTML, CSS
- **Database**: SQLite

---

## 🚀 How to Run

### Windows (Easy Way)
1. Make sure Python 3.8+ is installed → https://python.org
2. Double-click `start.bat`
3. Browser opens automatically at http://127.0.0.1:5000

### Manual (Any OS)
```bash
pip install -r requirements.txt
python app.py
```
Then open http://127.0.0.1:5000

---

## 🔑 Default Login Credentials

| Role  | Email                | Password  |
|-------|----------------------|-----------|
| Admin | admin@busbook.com    | admin123  |
| User  | Register yourself    | —         |

---

## 📦 Modules Included

### 👤 User Module
- Register / Login / Logout
- Profile management
- Session-based authentication
- Password hashing (SHA-256)

### 🔍 Bus Search
- Source & Destination (34 Tamil Nadu districts)
- Travel date selection (next 14 days only)
- Available seats count per bus

### 💺 Seat Booking
- Visual seat layout (up to 40 seats)
- Color-coded: Green (available), Red (booked), Yellow (locked), Blue (selected)
- 5-minute seat locking to prevent conflicts
- Max 6 seats per booking

### 💳 Payment
- UPI / Debit/Credit Card / Net Banking
- Simulated payment (no real transaction)
- Payment stored in DB

### 🎟 Ticket
- Auto-generated booking reference (e.g., BB3F7A2C1D)
- QR code for verification
- Print-ready layout

### ❌ Cancellation
- Cancel active bookings
- Only future-date bookings cancellable
- Seat availability auto-updates

### 📜 Booking History
- View all past & current bookings
- Cancel or view ticket from history
- Rate your bus (1–5 stars)

### 🧑‍💼 Admin Panel
- Dashboard with stats (users, buses, bookings, revenue)
- Add / Edit / Deactivate buses
- View all users with booking counts
- View all bookings with full details

---

## 🗂 Project Structure

```
busbooking/
├── app.py                  ← Main Flask application
├── requirements.txt        ← Python dependencies
├── start.bat               ← Windows launcher
├── busbooking.db           ← SQLite database (auto-created)
├── static/
│   └── css/
│       └── style.css       ← All styles
└── templates/
    ├── base.html           ← Base layout + navbar
    ├── index.html          ← Homepage
    ├── login.html          ← Login page
    ├── register.html       ← Register page
    ├── profile.html        ← Profile management
    ├── search.html         ← Bus search & results
    ├── seats.html          ← Seat selection
    ← book.html             ← Booking + payment form
    ├── ticket.html         ← Ticket with QR code
    ├── my_bookings.html    ← Booking history
    └── admin/
        ├── base.html       ← Admin layout
        ├── dashboard.html  ← Admin dashboard
        ├── buses.html      ← Manage buses
        ├── bookings.html   ← All bookings
        └── users.html      ← All users
```

---

## 🛡 Security Features
- Password encryption with SHA-256
- SQL injection prevention (parameterized queries)
- Session-based authentication
- Admin route protection
- Email format validation

## 🧠 Smart Features
- Seat locking system (5-minute hold)
- Automatic seat availability update on booking/cancellation
- Dynamic price calculation based on seat count
- QR code ticket generation
- Date range restriction (today + 14 days)

---

*Built for Tamil Nadu college project — BusBook TN © 2024*
