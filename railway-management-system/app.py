from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'railway_management_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///railway.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Database Models
class Train(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    train_number = db.Column(db.String(10), unique=True, nullable=False)
    train_name = db.Column(db.String(100), nullable=False)
    source = db.Column(db.String(100), nullable=False)
    destination = db.Column(db.String(100), nullable=False)
    departure_time = db.Column(db.DateTime, nullable=False)
    arrival_time = db.Column(db.DateTime, nullable=False)
    seats_available = db.Column(db.Integer, nullable=False)
    bookings = db.relationship('Booking', backref='train', lazy=True, cascade="all, delete")

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    passenger_name = db.Column(db.String(100), nullable=False)
    passenger_age = db.Column(db.Integer, nullable=False)
    passenger_gender = db.Column(db.String(10), nullable=False)
    passenger_contact = db.Column(db.String(20), nullable=False)
    train_id = db.Column(db.Integer, db.ForeignKey('train.id'), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    seat_number = db.Column(db.Integer, nullable=False)

def reset_database():
    # Delete existing database file
    db_file = 'instance/railway.db'
    if os.path.exists(db_file):
        os.remove(db_file)
    
    # Create all tables
    with app.app_context():
        db.create_all()
    
    print("Database reset complete with new schema")

@app.route('/')
def index():
    trains = Train.query.all()
    return render_template('index.html', trains=trains)

@app.route('/book/<int:train_id>', methods=['GET', 'POST'])
def book_ticket(train_id):
    train = Train.query.get_or_404(train_id)
    booked_seats = [booking.seat_number for booking in train.bookings]
    total_seats = train.seats_available + len(booked_seats)
    
    if request.method == 'POST':
        selected_seats = request.form.get('selected_seats', '').split(',')
        if not selected_seats:
            flash('Please select at least one seat.', 'error')
            return redirect(url_for('view_seats', train_id=train_id))

        try:
            selected_seats = [int(seat.strip()) for seat in selected_seats if seat.strip()]
        except ValueError:
            flash('Invalid seat selection.', 'error')
            return redirect(url_for('view_seats', train_id=train_id))

        available_seats = [seat for seat in range(1, total_seats + 1) if seat not in booked_seats]
        if any(seat not in available_seats for seat in selected_seats):
            flash('One or more selected seats are no longer available!', 'error')
            return redirect(url_for('view_seats', train_id=train_id))

        # Create bookings for each selected seat
        for seat_number in selected_seats:
            passenger_name = request.form.get(f'passenger_name_{seat_number}', '').strip()
            passenger_age = request.form.get(f'passenger_age_{seat_number}')
            passenger_gender = request.form.get(f'passenger_gender_{seat_number}')
            passenger_contact = request.form.get(f'passenger_contact_{seat_number}')

            # Validation
            if not passenger_name or not passenger_age or not passenger_gender or not passenger_contact:
                flash(f'Missing details for seat {seat_number}.', 'error')
                return redirect(url_for('view_seats', train_id=train_id))

            try:
                passenger_age = int(passenger_age)
            except ValueError:
                flash(f'Invalid age for seat {seat_number}.', 'error')
                return redirect(url_for('view_seats', train_id=train_id))

            booking = Booking(
                passenger_name=passenger_name,
                passenger_age=passenger_age,
                passenger_gender=passenger_gender,
                passenger_contact=passenger_contact,
                train_id=train_id,
                seat_number=seat_number
            )
            db.session.add(booking)
        
        train.seats_available -= len(selected_seats)
        db.session.commit()
        
        flash(f'{len(selected_seats)} ticket(s) booked successfully!', 'success')
        return redirect(url_for('index'))

    return redirect(url_for('view_seats', train_id=train_id))
    
@app.route('/seats/<int:train_id>')
def view_seats(train_id):
    train = Train.query.get_or_404(train_id)
    booked_seats = [booking.seat_number for booking in train.bookings]
    total_seats = train.seats_available + len(booked_seats)
    available_seats = [seat for seat in range(1, total_seats + 1) if seat not in booked_seats]
    
    return render_template(
        'seats.html',
        train=train,
        booked_seats=booked_seats,
        total_seats=total_seats,
        available_seats=available_seats
    )


@app.route('/bookings')
def view_bookings():
    bookings = Booking.query.all()
    return render_template('bookings.html', bookings=bookings)

@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    train = Train.query.get(booking.train_id)
    train.seats_available += 1
    db.session.delete(booking)
    db.session.commit()
    flash('Booking canceled successfully!', 'success')
    return redirect(url_for('view_bookings'))

@app.route('/add_train', methods=['GET', 'POST'])
def add_train():
    # Admin check
    if not request.args.get('admin') == 'true':
        flash('Access denied! Admins only.', 'error')
        return redirect(url_for('index'))

    if request.method == 'POST':
        train = Train(
            train_number=request.form['train_number'],
            train_name=request.form['train_name'],
            source=request.form['source'],
            destination=request.form['destination'],
            departure_time=datetime.strptime(request.form['departure_time'], '%Y-%m-%dT%H:%M'),
            arrival_time=datetime.strptime(request.form['arrival_time'], '%Y-%m-%dT%H:%M'),
            seats_available=int(request.form['seats_available']),
        )
        db.session.add(train)
        db.session.commit()
        flash('Train added successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('add_train.html')

@app.route('/delete_train/<int:train_id>', methods=['POST'])
def delete_train(train_id):
    train = Train.query.get_or_404(train_id)
    db.session.delete(train)
    db.session.commit()
    flash('Train deleted successfully!', 'success')
    return redirect(url_for('index'))



@app.route('/payment/<int:train_id>/<passenger_name>', methods=['GET', 'POST'])
def payment(train_id, passenger_name):
    train = Train.query.get_or_404(train_id)
    booked_seats = request.args.getlist('selected_seats')  # Retrieve selected seats from query params

    if request.method == 'POST':
        for seat_number in booked_seats:
            booking = Booking(
                passenger_name=passenger_name,
                train_id=train_id,
                seat_number=int(seat_number)
            )
            db.session.add(booking)
        train.seats_available -= len(booked_seats)
        db.session.commit()

        flash(f'{len(booked_seats)} ticket(s) booked successfully!', 'success')
        return redirect(url_for('index'))
    return render_template('payment.html', train=train, passenger_name=passenger_name, selected_seats=booked_seats)

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    trains = Train.query.all()
    bookings = Booking.query.all()
    return render_template('admin_dashboard.html', trains=trains, bookings=bookings)

@app.route('/update_train/<int:train_id>', methods=['GET', 'POST'])
def update_train(train_id):
    train = Train.query.get_or_404(train_id)
    if request.method == 'POST':
        train.train_number = request.form['train_number']
        train.train_name = request.form['train_name']
        train.source = request.form['source']
        train.destination = request.form['destination']
        train.departure_time = datetime.strptime(request.form['departure_time'], '%Y-%m-%dT%H:%M')
        train.arrival_time = datetime.strptime(request.form['arrival_time'], '%Y-%m-%dT%H:%M')
        train.seats_available = int(request.form['seats_available'])
        db.session.commit()
        flash('Train details updated successfully!', 'success')
        return redirect(url_for('admin_dashboard'))
    return render_template('update_train.html', train=train)

# Ensure database tables are created
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)