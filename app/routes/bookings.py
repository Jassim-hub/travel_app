"""
Booking routes for the Travel App.
Handles tour bookings, booking management, and booking-related operations.
"""

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    abort,
    current_app,
)
from flask_login import current_user, login_required
from app import db
from app.models import Tour, Booking, BookingStatus, User
from app.forms import BookingForm, BookingUpdateForm, BookingCancelForm
from app.decorators import active_user_required, check_booking_ownership, admin_required
from datetime import datetime, date
import secrets
from app.utils import send_booking_confirmation_email

# Create bookings blueprint
bookings_bp = Blueprint("bookings", __name__, url_prefix="/bookings")


@bookings_bp.route("/book/<int:tour_id>", methods=["GET", "POST"])
@login_required
@active_user_required
def book_tour(tour_id):
    """
    Book a specific tour.

    Features:
    - Form validation for booking details
    - Availability checking
    - Booking creation
    - Email confirmation (TODO)

    Access: Authenticated users only
    """

    # Get the tour or return 404
    tour = Tour.query.get_or_404(tour_id)

    # Check if tour is available
    if not tour.is_active:
        flash(
            "Sorry, this tour is currently unavailable for booking. Please contact support if you have questions.",
            "error",
        )
        return redirect(url_for("tours.detail", id=tour_id))

    form = BookingForm()

    if form.validate_on_submit():
        try:
            # Check availability for the requested date and participants
            existing_bookings = Booking.query.filter(
                Booking.tour_id == tour_id,
                Booking.travel_date == form.booking_date.data,
                Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.PENDING]),
            ).all()

            # Calculate total participants for this date
            total_participants = sum(
                booking.participants for booking in existing_bookings
            )

            # Check if adding new participants would exceed limit
            if total_participants + form.participants.data > tour.max_participants:
                available_spots = tour.max_participants - total_participants
                flash(
                    f"Sorry, only {available_spots} spots available for {form.booking_date.data}. "
                    f"Please choose fewer participants or a different date.",
                    "danger",
                )
                return render_template("bookings/book.html", tour=tour, form=form)

            # Calculate total price
            total_price = tour.price * form.participants.data

            # Create booking
            booking = Booking(
                user_id=current_user.id,
                tour_id=tour_id,
                participants=form.participants.data,
                travel_date=form.booking_date.data,
                total_amount=total_price,
                contact_phone=form.contact_phone.data,
                emergency_contact=form.emergency_contact.data,
                special_requests=form.special_requests.data,
                status=BookingStatus.PENDING,  # Pending until payment
                booking_reference=generate_booking_reference(),
            )

            db.session.add(booking)
            db.session.commit()

            # Send booking confirmation email
            try:
                send_booking_confirmation_email(booking)
                flash(
                    f"Booking successful! Your booking reference is {booking.booking_reference}. "
                    f"A confirmation email has been sent to {current_user.email}.",
                    "success",
                )
            except Exception as e:
                current_app.logger.error(
                    f"Failed to send booking confirmation email: {str(e)}"
                )
                flash(
                    f"Booking successful! Your booking reference is {booking.booking_reference}. "
                    f"Please proceed to payment to confirm your booking.",
                    "success",
                )

            # TODO: Redirect to payment page
            return redirect(url_for("bookings.my_bookings"))

        except Exception as e:
            db.session.rollback()
            flash(
                "An error occurred while creating your booking. Please try again.",
                "danger",
            )
            current_app.logger.error(f"Booking creation error: {str(e)}")

    return render_template("bookings/book.html", tour=tour, form=form)


@bookings_bp.route("/my-bookings")
@login_required
@active_user_required
def my_bookings():
    """
    Display user's bookings.

    Features:
    - List all user bookings
    - Filter by status
    - Show booking details
    - Action buttons (view, update, cancel)

    Access: Authenticated users only
    """

    # Get filter parameters
    status_filter = request.args.get("status", "")

    # Build query
    query = Booking.query.filter_by(user_id=current_user.id)

    if status_filter:
        try:
            status_enum = BookingStatus[status_filter.upper()]
            query = query.filter_by(status=status_enum)
        except KeyError:
            # Invalid status filter, ignore
            pass

    # Order by creation date (newest first)
    bookings = query.order_by(Booking.created_at.desc()).all()

    return render_template(
        "bookings/my_bookings.html", bookings=bookings, status_filter=status_filter
    )


@bookings_bp.route("/view/<int:booking_id>")
@login_required
@check_booking_ownership
def view_booking(booking_id):
    """
    View detailed booking information.

    Features:
    - Complete booking details
    - Tour information
    - Payment status
    - Action buttons

    Access: Booking owner or admin
    """

    booking = Booking.query.get_or_404(booking_id)
    return render_template("bookings/view.html", booking=booking)


@bookings_bp.route("/update/<int:booking_id>", methods=["GET", "POST"])
@login_required
@check_booking_ownership
def update_booking(booking_id):
    """
    Update booking details.

    Features:
    - Modify participants, date, contact info
    - Availability checking
    - Price recalculation

    Restrictions:
    - Only pending/confirmed bookings can be updated
    - Cannot update within 48 hours of tour date

    Access: Booking owner or admin
    """

    booking = Booking.query.get_or_404(booking_id)

    # Check if booking can be updated
    if booking.status in [BookingStatus.CANCELLED, BookingStatus.COMPLETED]:
        flash("This booking cannot be updated.", "warning")
        return redirect(url_for("bookings.view_booking", booking_id=booking_id))

    # Check if within update deadline (48 hours before tour)
    from datetime import timedelta

    update_deadline = booking.travel_date - timedelta(days=2)
    if date.today() > update_deadline:
        flash("Bookings cannot be updated within 48 hours of the tour date.", "warning")
        return redirect(url_for("bookings.view_booking", booking_id=booking_id))

    form = BookingUpdateForm(obj=booking)

    if form.validate_on_submit():
        try:
            # Check availability if participants or date changed
            if (
                form.participants.data != booking.participants
                or form.booking_date.data != booking.travel_date
            ):

                # Get existing bookings for new date (excluding current booking)
                existing_bookings = Booking.query.filter(
                    Booking.tour_id == booking.tour_id,
                    Booking.travel_date == form.booking_date.data,
                    Booking.id != booking_id,
                    Booking.status.in_(
                        [BookingStatus.CONFIRMED, BookingStatus.PENDING]
                    ),
                ).all()

                total_participants = sum(b.participants for b in existing_bookings)

                if (
                    total_participants + form.participants.data
                    > booking.tour.max_participants
                ):
                    available_spots = booking.tour.max_participants - total_participants
                    flash(
                        f"Sorry, only {available_spots} spots available for {form.booking_date.data}. "
                        f"Please choose fewer participants or a different date.",
                        "danger",
                    )
                    return render_template(
                        "bookings/update.html", booking=booking, form=form
                    )

            # Update booking
            booking.participants = form.participants.data
            booking.travel_date = form.booking_date.data
            booking.contact_phone = form.contact_phone.data
            booking.emergency_contact = form.emergency_contact.data
            booking.special_requests = form.special_requests.data

            # Recalculate total price
            booking.total_amount = booking.tour.price * booking.participants
            booking.updated_at = datetime.utcnow()

            db.session.commit()

            flash("Booking updated successfully!", "success")
            return redirect(url_for("bookings.view_booking", booking_id=booking_id))

        except Exception as e:
            db.session.rollback()
            flash(
                "An error occurred while updating your booking. Please try again.",
                "danger",
            )
            current_app.logger.error(f"Booking update error: {str(e)}")

    return render_template("bookings/update.html", booking=booking, form=form)


@bookings_bp.route("/cancel/<int:booking_id>", methods=["GET", "POST"])
@login_required
@check_booking_ownership
def cancel_booking(booking_id):
    """
    Cancel a booking.

    Features:
    - Cancellation confirmation
    - Refund processing (TODO)
    - Email notification (TODO)

    Restrictions:
    - Cannot cancel completed bookings
    - Refund policy applies

    Access: Booking owner or admin
    """

    booking = Booking.query.get_or_404(booking_id)

    # Check if booking can be cancelled
    if booking.status == BookingStatus.CANCELLED:
        flash("This booking is already cancelled.", "info")
        return redirect(url_for("bookings.view_booking", booking_id=booking_id))

    if booking.status == BookingStatus.COMPLETED:
        flash("Completed bookings cannot be cancelled.", "warning")
        return redirect(url_for("bookings.view_booking", booking_id=booking_id))

    form = BookingCancelForm()

    if form.validate_on_submit():
        try:
            # Update booking status
            booking.status = BookingStatus.CANCELLED
            booking.cancellation_reason = form.cancel_reason.data
            booking.cancelled_at = datetime.utcnow()
            booking.updated_at = datetime.utcnow()

            # Process refund if booking was paid
            if (
                booking.payment_status
                and str(booking.payment_status) == "PaymentStatus.COMPLETED"
            ):
                try:
                    # TODO: Implement refund logic here
                    # For now, just flash a warning
                    flash(
                        "Booking cancelled successfully. Refund processing failed - please contact support.",
                        "warning",
                    )
                except Exception as e:
                    current_app.logger.error(f"Refund processing error: {str(e)}")
                    flash(
                        "Booking cancelled successfully. Refund will be processed manually - please contact support.",
                        "warning",
                    )
            else:
                flash(
                    "Booking cancelled successfully.",
                    "success",
                )

            db.session.commit()

            # TODO: Send cancellation email
            return redirect(url_for("bookings.my_bookings"))

        except Exception as e:
            db.session.rollback()
            flash(
                "An error occurred while cancelling your booking. Please try again.",
                "danger",
            )
            current_app.logger.error(f"Booking cancellation error: {str(e)}")

    return render_template("bookings/cancel.html", booking=booking, form=form)


@bookings_bp.route("/admin/bookings")
@admin_required
def admin_bookings():
    """
    Admin page to view all bookings and mark confirmed ones as completed.
    """
    bookings = Booking.query.order_by(Booking.created_at.desc()).all()
    return render_template("admin/bookings.html", bookings=bookings)


@bookings_bp.route("/admin/mark-completed/<int:booking_id>", methods=["POST"])
@admin_required
def mark_booking_completed(booking_id):
    """
    Admin action to mark a confirmed booking as completed.
    """
    booking = Booking.query.get_or_404(booking_id)
    if booking.status == BookingStatus.CONFIRMED:
        # Only add revenue if payment is completed
        if str(booking.payment_status) == "PaymentStatus.COMPLETED":
            tour = booking.tour
            tour.total_revenue += booking.total_amount
            db.session.add(tour)
        booking.status = BookingStatus.COMPLETED
        booking.updated_at = datetime.utcnow()
        db.session.commit()
        flash(
            "Booking marked as completed. Revenue updated. User can now review this tour.",
            "success",
        )
    else:
        flash("Only confirmed bookings can be marked as completed.", "warning")
    return redirect(url_for("bookings.admin_bookings"))


def generate_booking_reference():
    """
    Generate a unique booking reference.
    Format: BK-YYYYMMDD-XXXX (BK-20241206-A1B2)
    """
    from datetime import datetime

    date_str = datetime.now().strftime("%Y%m%d")
    random_str = secrets.token_hex(2).upper()
    return f"BK-{date_str}-{random_str}"


# Error handlers for bookings
@bookings_bp.errorhandler(404)
def booking_not_found(error):
    """Handle booking not found errors"""
    flash("Booking not found.", "danger")
    return redirect(url_for("bookings.my_bookings"))


@bookings_bp.errorhandler(403)
def booking_access_denied(error):
    """Handle booking access denied errors"""
    flash("You don't have permission to access this booking.", "danger")
    return redirect(url_for("bookings.my_bookings"))
