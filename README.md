# Trailhead TrekManagement

A Flask web application for running a trekking company: an admin publishes treks and manages
people, guides run the treks they are assigned, and trekkers browse and book seats.

## How it works

The app is a server-rendered Flask app (Jinja2 templates + a single stylesheet) backed by a
SQLite database through Flask-SQLAlchemy. `app.py` builds the app with `create_app()`, registers
one blueprint per role, and calls `setup_database()` on startup, which creates the tables and
seeds a default admin account if none exists. Sessions are handled by Flask-Login, and passwords
are stored as Werkzeug hashes.

### Roles

Every account is a `User` with a `role` (`admin`, `staff`, `trekker`) and an `account_status`
(`active`, `pending`, `blacklisted`). Login is refused for pending and blacklisted accounts, and
each blueprint is guarded by a `role_required` decorator, so a signed-in user can only reach their
own section (`/admin`, `/staff`, `/trekker`) — anything else returns 403.

- **Admin** — creates and edits treks, assigns a guide to each one, approves or blacklists guide
  applications, adds guides directly, blacklists or reactivates trekkers, and browses all bookings
  plus a global search across treks and people.
- **Staff (guide)** — signs up via a separate form and waits for admin approval. Once approved and
  assigned a trek, they manage its seat count and status, view the participant list, toggle payment
  status, remove participants, and move the trek through *Ongoing* → *Completed*. They can only
  touch treks assigned to them.
- **Trekker** — registers freely, browses open treks with search/difficulty/region filters, books a
  seat, cancels a booking, and views a history of completed and cancelled trips.

### Trek and booking lifecycle

A trek is created as **Pending**. Assigning a guide moves it to **Approved**; removing the guide
sends it back to Pending. The guide then opens it (**Open**) so trekkers can book, and later marks
it **Ongoing** and **Completed**. Only Open treks with free slots accept bookings.

A `Booking` links a trekker to a trek and is **Booked**, **Cancelled**, or **Completed**. Booking
decrements the trek's available slots; cancelling (by the trekker or the guide) returns the seat,
capped at the trek's total. Completing a trek marks every active booking as Completed and zeroes
the remaining slots, so those trips show up in the trekker's history.

## Project layout

| Path | Purpose |
| --- | --- |
| `app.py` | App factory, blueprint registration, home page, error handlers |
| `config.py` | Secret key and SQLite path (`instance/trailhead.db`) |
| `models.py` | `User`, `StaffProfile`, `Trek`, `Booking` and the status constants |
| `seed.py` | Creates tables and the default admin account |
| `routes/` | `auth`, `admin`, `staff`, `trekker` blueprints + the `role_required` decorator |
| `templates/` | Jinja2 templates, one folder per role, sharing `base.html` and `macros.html` |
| `static/css/` | Stylesheet |

## Running it

```bash
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000. The seeded admin login is `admin@gmail.com` / `Admin@000`.
