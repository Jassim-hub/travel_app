"""
Database models for the Travel App.
This module contains all database table definitions.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from enum import Enum

# Create database instance
db = SQLAlchemy()


class UserRole(Enum):
    """User roles enumeration"""

    USER = "user"
    ADMIN = "admin"


class BookingStatus(Enum):
    """Booking status enumeration"""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class PaymentStatus(Enum):
    """Payment status enumeration"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class TourStatus(Enum):
    """Tour status enumeration"""

    ACTIVE = "active"
    INACTIVE = "inactive"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(UserMixin, db.Model):
    """
    User model for authentication and user management.
    Inherits from UserMixin for Flask-Login integration.
    """

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    bio = db.Column(db.Text)
    role = db.Column(db.Enum(UserRole), default=UserRole.USER)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    is_active = db.Column(db.Boolean, default=True)

    # Relationships
    bookings = db.relationship("Booking", backref="user", lazy=True)
    reviews = db.relationship("Review", backref="user", lazy=True)
    # inquiries relationship is defined in Inquiry model

    # Relationships will be added later

    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        """Check if user has admin role"""
        return self.role == UserRole.ADMIN

    @property
    def full_name(self):
        """Get user's full name"""
        return f"{self.first_name} {self.last_name}"

    @property
    def total_bookings(self):
        """Get total number of bookings made by user"""
        return len(self.bookings)

    @property
    def completed_bookings(self):
        """Get number of completed bookings"""
        return len([b for b in self.bookings if b.status == BookingStatus.COMPLETED])

    def can_review_tour(self, tour_id):
        """Check if user can review a specific tour"""
        # User must have completed booking for the tour
        completed_bookings = [
            b
            for b in self.bookings
            if b.tour_id == tour_id and b.status == BookingStatus.COMPLETED
        ]
        if not completed_bookings:
            return False

        # Check if user already reviewed this tour
        existing_review = [r for r in self.reviews if r.tour_id == tour_id]
        return len(existing_review) == 0

    def __repr__(self):
        return f"<User {self.username}>"


class Category(db.Model):
    """
    Category model for organizing tours into different types.
    Examples: Adventure, Beach, Cultural, Wildlife, etc.
    """

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    tours = db.relationship(
        "Tour", backref="category", lazy=True, cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Category {self.name}>"


class Tour(db.Model):
    """
    Tour model - The core of the application.
    Contains all tour package information and complex business logic.
    """

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    destination = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    duration_days = db.Column(db.Integer, nullable=False)
    max_participants = db.Column(db.Integer, nullable=False)

    # Date availability
    available_from = db.Column(db.Date, nullable=False)
    available_to = db.Column(db.Date, nullable=False)

    # Tour details
    difficulty_level = db.Column(db.String(20), default="Easy")  # Easy, Medium, Hard
    includes = db.Column(db.Text)  # What's included in the tour
    excludes = db.Column(db.Text)  # What's not included

    # Media
    image_url = db.Column(db.String(500))
    gallery_images = db.Column(db.Text)  # JSON string of image URLs

    # Status and features
    featured = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    status = db.Column(db.Enum(TourStatus), default=TourStatus.ACTIVE)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Foreign Keys
    category_id = db.Column(db.Integer, db.ForeignKey("category.id"), nullable=False)

    # Relationships
    bookings = db.relationship("Booking", backref="tour", lazy=True)
    reviews = db.relationship("Review", backref="tour", lazy=True)
    itinerary = db.relationship(
        "TourItinerary", backref="tour", lazy=True, cascade="all, delete-orphan"
    )

    total_revenue = db.Column(db.Float, default=0.0)

    @property
    def average_rating(self):
        """Calculate average rating from all approved reviews"""
        approved_reviews = [review for review in self.reviews if review.is_approved]
        if approved_reviews:
            return sum(review.rating for review in approved_reviews) / len(
                approved_reviews
            )
        return 0.0

    @property
    def review_count(self):
        """Count of approved reviews"""
        return len([review for review in self.reviews if review.is_approved])

    @property
    def available_spots(self):
        """Calculate available spots for booking"""
        confirmed_bookings = sum(
            booking.participants
            for booking in self.bookings
            if booking.status == BookingStatus.CONFIRMED
        )
        return max(0, self.max_participants - confirmed_bookings)

    @property
    def is_available(self):
        """Check if tour is available for booking"""
        today = date.today()
        return (
            self.is_active
            and self.available_from <= today <= self.available_to
            and self.available_spots > 0
        )

    def can_be_booked_on(self, booking_date):
        """Check if tour can be booked on specific date"""
        return (
            self.is_active
            and self.available_from <= booking_date <= self.available_to
            and self.available_spots > 0
        )

    def __repr__(self):
        return f"<Tour {self.title}>"


class TourItinerary(db.Model):
    """
    Tour itinerary model for day-by-day tour details.
    Allows detailed planning of tour activities.
    """

    id = db.Column(db.Integer, primary_key=True)
    tour_id = db.Column(db.Integer, db.ForeignKey("tour.id"), nullable=False)
    day_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    activities = db.Column(db.Text)  # JSON string of activities
    accommodation = db.Column(db.String(200))
    meals = db.Column(db.String(100))  # e.g., "Breakfast, Lunch, Dinner"

    # Ensure unique day numbers per tour
    __table_args__ = (db.UniqueConstraint("tour_id", "day_number"),)

    def __repr__(self):
        return f"<TourItinerary Day {self.day_number} - {self.title}>"


class Booking(db.Model):
    """
    Booking model - Contains complex business logic for tour bookings.
    This is the heart of the reservation system.
    """

    id = db.Column(db.Integer, primary_key=True)

    # Unique booking reference (e.g., TRV-2024-001234)
    booking_reference = db.Column(db.String(20), unique=True, nullable=False)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tour_id = db.Column(db.Integer, db.ForeignKey("tour.id"), nullable=False)

    # Booking details

    participants = db.Column(db.Integer, nullable=False, default=1)
    total_amount = db.Column(db.Float, nullable=False)
    booking_date = db.Column(db.Date, nullable=False, default=date.today)
    travel_date = db.Column(db.Date, nullable=False)

    # Status tracking
    status = db.Column(db.Enum(BookingStatus), default=BookingStatus.PENDING)
    payment_status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)

    # Additional information
    special_requests = db.Column(db.Text)
    notes = db.Column(db.Text)  # Admin notes

    # Contact information
    contact_phone = db.Column(db.String(20))
    emergency_contact = db.Column(db.String(100))

    # Emergency contact information
    emergency_contact_name = db.Column(db.String(100))
    emergency_contact_phone = db.Column(db.String(20))
    emergency_contact_relation = db.Column(db.String(50))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    cancelled_at = db.Column(db.DateTime)

    # Cancellation information
    cancellation_reason = db.Column(db.Text)

    # Relationships
    payments = db.relationship("Payment", backref="booking", lazy=True)

    def __init__(self, **kwargs):
        """Initialize booking with auto-generated reference"""
        super().__init__(**kwargs)
        if not self.booking_reference:
            self.booking_reference = self.generate_booking_reference()

    @staticmethod
    def generate_booking_reference():
        """Generate unique booking reference number"""
        import random
        import string

        year = datetime.now().year
        random_part = "".join(random.choices(string.digits, k=6))
        return f"TRV-{year}-{random_part}"

    @property
    def is_cancellable(self):
        """Check if booking can be cancelled (e.g., 7 days before travel)"""
        from datetime import timedelta

        cancellation_deadline = self.travel_date - timedelta(days=7)
        return date.today() <= cancellation_deadline and self.status in [
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
        ]

    @property
    def is_modifiable(self):
        """Check if booking can be modified"""
        from datetime import timedelta

        modification_deadline = self.travel_date - timedelta(days=3)
        return date.today() <= modification_deadline and self.status in [
            BookingStatus.PENDING,
            BookingStatus.CONFIRMED,
        ]

    @property
    def days_until_travel(self):
        """Calculate days until travel date"""
        return (self.travel_date - date.today()).days

    @property
    def total_paid(self):
        """Calculate total amount paid"""
        return sum(
            payment.amount
            for payment in self.payments
            if payment.status == PaymentStatus.COMPLETED
        )

    @property
    def outstanding_amount(self):
        """Calculate outstanding payment amount"""
        return max(0, self.total_amount - self.total_paid)

    def can_be_reviewed(self):
        """Check if booking can be reviewed (after travel date)"""
        return (
            self.status == BookingStatus.COMPLETED and date.today() > self.travel_date
        )

    def __repr__(self):
        return f"<Booking {self.booking_reference}"


class Payment(db.Model):
    """
    Payment model for tracking all payment transactions.
    Supports multiple payments per booking (deposits, installments, etc.)
    """

    id = db.Column(db.Integer, primary_key=True)

    # Foreign Key
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=False)

    # Payment details
    amount = db.Column(db.Float, nullable=False)
    currency = db.Column(db.String(3), default="USD")
    payment_method = db.Column(db.String(50))  # 'stripe', 'paypal', 'bank_transfer'

    # External payment system references
    transaction_id = db.Column(db.String(100), unique=True)
    stripe_payment_intent_id = db.Column(db.String(100))

    # Status and metadata
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)
    failure_reason = db.Column(db.String(200))

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Payment {self.transaction_id}: {self.amount} {self.currency}>"


class Review(db.Model):
    """
    Review model for tour ratings and feedback.
    Includes approval system and spam protection.
    """

    id = db.Column(db.Integer, primary_key=True)

    # Foreign Keys
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    tour_id = db.Column(db.Integer, db.ForeignKey("tour.id"), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=True)

    # Review content
    rating = db.Column(db.Integer, nullable=False)  # 1-5 stars
    title = db.Column(db.String(200))
    comment = db.Column(db.Text)

    # Review metadata
    is_approved = db.Column(db.Boolean, default=False)
    is_verified_purchase = db.Column(db.Boolean, default=False)
    helpful_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)

    # Ensure one review per user per tour
    __table_args__ = (db.UniqueConstraint("user_id", "tour_id"),)

    def __init__(self, **kwargs):
        """Initialize review with verified purchase check"""
        super().__init__(**kwargs)
        if self.booking_id:
            self.is_verified_purchase = True

    @property
    def is_recent(self):
        """Check if review is recent (within last 30 days)"""
        from datetime import timedelta

        return (datetime.utcnow() - self.created_at).days <= 30

    def __repr__(self):
        return f"<Review {self.rating} stars for Tour {self.tour_id}>"


class Inquiry(db.Model):
    """
    Inquiry model for contact form submissions and customer support.
    """

    id = db.Column(db.Integer, primary_key=True)

    # Contact details (user can be logged in or anonymous)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20))

    # Inquiry content
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    inquiry_type = db.Column(
        db.String(50), default="general"
    )  # 'general', 'booking', 'complaint', 'suggestion'

    # Tour reference (if inquiry is about specific tour)
    tour_id = db.Column(db.Integer, db.ForeignKey("tour.id"), nullable=True)
    booking_id = db.Column(db.Integer, db.ForeignKey("booking.id"), nullable=True)

    # Status and response
    status = db.Column(db.String(20), default="new")  # 'new', 'in_progress', 'resolved', 'closed'
    is_resolved = db.Column(db.Boolean, default=False)
    
    # Bot processing fields
    bot_processed = db.Column(db.Boolean, default=False)
    bot_confidence = db.Column(db.Float, nullable=True)
    bot_response_sent = db.Column(db.Boolean, default=False)
    requires_human_review = db.Column(db.Boolean, default=False)
    admin_response = db.Column(db.Text)
    internal_notes = db.Column(db.Text)  # Internal admin notes
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)  # Assigned admin
    priority = db.Column(
        db.String(20), default="medium"
    )  # 'low', 'medium', 'high', 'urgent'
    response_count = db.Column(db.Integer, default=0)  # Number of responses sent

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)
    last_response_at = db.Column(db.DateTime)  # Last time admin responded

    # Relationships - specify foreign_keys to avoid ambiguity
    user = db.relationship("User", foreign_keys=[user_id], 
                          backref=db.backref("submitted_inquiries", lazy="dynamic"))
    tour = db.relationship("Tour", backref="inquiries")
    booking = db.relationship("Booking", backref="inquiries")
    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id], 
                                 backref=db.backref("assigned_inquiries", lazy="dynamic"))

    @property
    def is_urgent(self):
        """Check if inquiry is urgent (high priority or old unresolved)"""
        from datetime import timedelta
        
        return (
            self.priority == "urgent"
            or (not self.is_resolved and (datetime.utcnow() - self.created_at).days > 3)
        )

    def __repr__(self):
        return f"<Inquiry {self.id}: {self.subject}>"


class InquiryResponse(db.Model):
    """
    Individual responses to inquiries from admin staff.
    """
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    response_text = db.Column(db.Text, nullable=False)
    responder_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Admin who responded
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    inquiry = db.relationship('Inquiry', backref='responses')
    responder = db.relationship('User', backref='inquiry_responses')

    def __repr__(self):
        return f"<Response {self.id} for Inquiry {self.inquiry_id}>"
