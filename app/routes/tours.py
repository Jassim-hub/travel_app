"""
Tours blueprint for the Travel App.
This module handles all tour-related routes including listing, details, and management.
"""

from flask import Blueprint, render_template, request, flash, redirect, url_for, abort
from flask_login import login_required, current_user
from app.models import Tour, Category, db, TourStatus
from app.decorators import admin_required
from app.utils import save_tour_image, delete_tour_image
from sqlalchemy import or_
from app.forms import ReviewForm
from app.models import Review, BookingStatus

# Create tours blueprint
tours_bp = Blueprint("tours", __name__, url_prefix="/tours")


@tours_bp.route("/")
def index():
    """
    Display all tours with search and filtering.
    """
    # Get query parameters
    search = request.args.get("search", "")
    category_id = request.args.get("category", "")
    min_price = request.args.get("min_price", "")
    max_price = request.args.get("max_price", "")
    page = request.args.get("page", 1, type=int)

    # Start with base query
    query = Tour.query

    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Tour.title.contains(search),
                Tour.destination.contains(search),
                Tour.description.contains(search),
            )
        )

    # Apply category filter
    if category_id:
        query = query.filter(Tour.category_id == category_id)

    # Apply price filters
    if min_price:
        try:
            query = query.filter(Tour.price >= float(min_price))
        except ValueError:
            pass

    if max_price:
        try:
            query = query.filter(Tour.price <= float(max_price))
        except ValueError:
            pass

    # Order by created date (newest first)
    query = query.order_by(Tour.created_at.desc())

    # Paginate results
    tours = query.paginate(
        page=page, per_page=9, error_out=False  # 9 tours per page (3x3 grid)
    )

    # Get all categories for filter dropdown
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "tours/index.html", tours=tours, categories=categories, title="Tours"
    )


@tours_bp.route("/<int:id>", methods=["GET", "POST"])
def detail(id):
    """
    Display detailed information about a specific tour and handle review submission.
    """
    tour = Tour.query.get_or_404(id)
    related_tours = []
    if tour.category:
        related_tours = (
            Tour.query.filter(Tour.category_id == tour.category.id, Tour.id != tour.id)
            .limit(3)
            .all()
        )

    review_form = None
    review_submitted = False
    can_review = False
    user_review = None

    if current_user.is_authenticated:
        # Check if user can review this tour
        can_review = current_user.can_review_tour(tour.id)
        # Check if user already has a review
        user_review = Review.query.filter_by(
            user_id=current_user.id, tour_id=tour.id
        ).first()
        review_form = ReviewForm()
        if review_form.validate_on_submit() and can_review:
            # Create and save review
            review = Review(
                user_id=current_user.id,
                tour_id=tour.id,
                rating=review_form.rating.data,
                comment=review_form.comment.data,
                is_approved=False,  # Admin must approve
            )
            db.session.add(review)
            db.session.commit()
            flash(
                "Thank you for your feedback! Your review will be published after admin approval.",
                "success",
            )
            review_submitted = True
            can_review = False
            user_review = review

    return render_template(
        "tours/detail.html",
        tour=tour,
        related_tours=related_tours,
        review_form=review_form,
        can_review=can_review,
        review_submitted=review_submitted,
        user_review=user_review,
        title=tour.title,
    )


@tours_bp.route("/create", methods=["GET", "POST"])
@login_required
@admin_required
def create():
    """
    Create a new tour (admin only).
    """
    if request.method == "POST":
        try:
            # Get form data
            name = request.form.get("name")
            destination = request.form.get("destination")
            description = request.form.get("description")
            price = request.form.get("price")
            duration = request.form.get("duration")
            max_participants = request.form.get("max_participants")
            category_id = request.form.get("category_id")
            image_url = request.form.get("image_url")

            # Handle file upload
            image_file = request.files.get("image")
            if image_file and image_file.filename:
                # Save uploaded image
                uploaded_image_url = save_tour_image(image_file)
                if uploaded_image_url:
                    image_url = uploaded_image_url
                else:
                    flash("Error uploading image. Please try again.", "warning")

            # Basic validation
            if not all(
                [name, destination, description, price, duration, max_participants]
            ):
                flash("All required fields must be filled.", "danger")
                return redirect(url_for("tours.create"))

            # Create new tour
            from datetime import datetime

            available_from_str = request.form.get("available_from")
            available_to_str = request.form.get("available_to")
            available_from = (
                datetime.strptime(available_from_str, "%Y-%m-%d").date()
                if available_from_str
                else None
            )
            available_to = (
                datetime.strptime(available_to_str, "%Y-%m-%d").date()
                if available_to_str
                else None
            )

            tour = Tour(
                title=name,
                destination=destination,
                description=description,
                price=float(price),
                duration_days=int(duration),
                max_participants=int(max_participants),
                category_id=int(category_id) if category_id else None,
                image_url=image_url if image_url else None,
                is_active=True,
                available_from=available_from,
                available_to=available_to,
            )

            db.session.add(tour)
            db.session.commit()

            flash(f'Tour "{name}" created successfully!', "success")
            return redirect(url_for("tours.detail", id=tour.id))

        except ValueError as e:
            flash("Invalid data provided. Please check your input.", "danger")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while creating the tour.", "danger")

    # Get categories for dropdown
    categories = Category.query.order_by(Category.name).all()

    return render_template(
        "tours/create.html", categories=categories, title="Create Tour"
    )


@tours_bp.route("/<int:id>/edit", methods=["GET", "POST"])
@login_required
@admin_required
def edit(id):
    """
    Edit an existing tour (admin only).
    """
    tour = Tour.query.get_or_404(id)

    if request.method == "POST":
        try:
            from datetime import date, timedelta

            # Store old image URL for potential deletion
            old_image_url = tour.image_url

            # Update tour data
            tour.title = request.form.get("name")
            tour.destination = request.form.get("destination")
            tour.description = request.form.get("description")
            tour.price = float(request.form.get("price"))
            tour.duration_days = int(request.form.get("duration"))
            tour.max_participants = int(request.form.get("max_participants"))
            tour.category_id = (
                int(request.form.get("category_id"))
                if request.form.get("category_id")
                else None
            )
            # Update available_from and available_to
            from datetime import datetime

            available_from_str = request.form.get("available_from")
            available_to_str = request.form.get("available_to")
            if available_from_str:
                tour.available_from = datetime.strptime(
                    available_from_str, "%Y-%m-%d"
                ).date()
            if available_to_str:
                tour.available_to = datetime.strptime(
                    available_to_str, "%Y-%m-%d"
                ).date()

            # Handle image upload
            image_file = request.files.get("image")
            if image_file and image_file.filename:
                # Save new uploaded image
                uploaded_image_url = save_tour_image(image_file)
                if uploaded_image_url:
                    tour.image_url = uploaded_image_url
                    # Delete old image if it was uploaded (not external URL)
                    if old_image_url and old_image_url.startswith(
                        "/static/images/tours/"
                    ):
                        delete_tour_image(old_image_url)
                else:
                    flash("Error uploading image. Please try again.", "warning")
            else:
                # Use provided URL if no file uploaded
                tour.image_url = (
                    request.form.get("image_url")
                    if request.form.get("image_url")
                    else tour.image_url
                )

            # Fix: Ensure all conditions for availability are met
            is_available = bool(request.form.get("is_available"))
            tour.is_active = is_available
            if is_available:
                today = date.today()
                # Fix available_from and available_to if needed
                if tour.available_from > today:
                    tour.available_from = today
                if tour.available_to < today:
                    tour.available_to = today + timedelta(days=30)
                # Check max_participants vs confirmed bookings
                confirmed = 0
                if hasattr(tour, "bookings"):
                    confirmed = sum(
                        b.participants
                        for b in tour.bookings
                        if getattr(b, "status", None)
                        and str(getattr(b, "status")) == "BookingStatus.CONFIRMED"
                    )
                if tour.max_participants <= confirmed:
                    tour.max_participants = confirmed + 1
                    flash(
                        "Max participants was increased to allow new bookings.",
                        "warning",
                    )

            db.session.commit()

            flash(f'Tour "{tour.title}" updated successfully!', "success")
            return redirect(url_for("tours.detail", id=tour.id))

        except ValueError as e:
            flash("Invalid data provided. Please check your input.", "danger")
        except Exception as e:
            db.session.rollback()
            flash("An error occurred while updating the tour.", "danger")

    # Get categories for dropdown
    categories = Category.query.order_by(Category.name).all()

    # Format available_from and available_to for input fields (YYYY-MM-DD or empty)
    available_from_str = (
        tour.available_from.strftime("%Y-%m-%d") if tour.available_from else ""
    )
    available_to_str = (
        tour.available_to.strftime("%Y-%m-%d") if tour.available_to else ""
    )

    return render_template(
        "tours/edit.html",
        tour=tour,
        categories=categories,
        title=f"Edit {tour.title}",
        available_from_str=available_from_str,
        available_to_str=available_to_str,
    )


@tours_bp.route("/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete(id):
    """
    Delete a tour (admin only).
    """
    tour = Tour.query.get_or_404(id)

    try:
        tour_name = tour.title

        # Delete associated image file if it was uploaded
        if tour.image_url and tour.image_url.startswith("/static/images/tours/"):
            delete_tour_image(tour.image_url)

        db.session.delete(tour)
        db.session.commit()

        flash(f'Tour "{tour_name}" deleted successfully!', "success")
        return redirect(url_for("tours.index"))

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting the tour.", "danger")
        return redirect(url_for("tours.detail", id=id))


@tours_bp.route("/<int:id>/toggle-availability", methods=["POST"])
@login_required
@admin_required
def toggle_availability(id):
    """
    Toggle tour availability (admin only).
    """
    tour = Tour.query.get_or_404(id)

    try:
        tour.is_active = not tour.is_active
        db.session.commit()

        status = "available" if tour.is_active else "unavailable"
        flash(f'Tour "{tour.title}" is now {status}.', "success")

    except Exception as e:
        db.session.rollback()
        flash("An error occurred while updating the tour.", "danger")

    return redirect(url_for("tours.manage"))


@tours_bp.route("/mark_completed/<int:tour_id>", methods=["POST"])
@login_required
@admin_required
def mark_tour_completed(tour_id):
    """
    Mark a tour as completed (admin only).
    Also sets all related confirmed bookings to completed and sends thank you emails.
    """
    from app.utils import send_email
    from app.models import BookingStatus

    tour = Tour.query.get_or_404(tour_id)
    tour.status = TourStatus.COMPLETED

    # Find all confirmed bookings for this tour
    confirmed_bookings = [
        b for b in tour.bookings if b.status == BookingStatus.CONFIRMED
    ]
    for booking in confirmed_bookings:
        booking.status = BookingStatus.COMPLETED
        # Send thank you email to user
        user = booking.user
        subject = "Thank You for Traveling with Travel Escapes!"
        body = f"Dear {user.full_name},\n\nThank you for completing your tour '{tour.title}' with Travel Escapes! We hope you had a wonderful experience. You can now leave a review for your tour from your account.\n\nBest regards,\nTravel Escapes Team"
        send_email(subject, [user.email], body)

    try:
        db.session.commit()
        flash(
            f"Tour '{tour.title}' and all related bookings have been marked as completed. Users have been notified.",
            "success",
        )
    except Exception as e:
        db.session.rollback()
        flash(
            "Error marking tour and bookings as completed. Please try again.", "error"
        )

    return redirect(url_for("bookings.admin_bookings"))


# Category management routes


# Admin category management page (new template)
@tours_bp.route("/admin/categories", methods=["GET"])
@login_required
@admin_required
def admin_manage_categories():
    """
    Render the admin category management page.
    """
    categories = Category.query.order_by(Category.name).all()
    return render_template(
        "admin/manage_categories.html", categories=categories, title="Manage Categories"
    )


# Create category from admin page
@tours_bp.route("/admin/categories/create", methods=["POST"])
@login_required
@admin_required
def create_category():
    """
    Create a new category (admin only).
    """
    name = request.form.get("name")
    description = request.form.get("description")

    # Optional fields from Category model
    image_url = request.form.get("image_url")
    is_active = True  # Default to active

    if not name:
        flash("Category name is required.", "danger")
        return redirect(url_for("tours.admin_manage_categories"))

    try:
        category = Category(
            name=name, description=description, image_url=image_url, is_active=is_active
        )
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{name}" created successfully!', "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while creating the category.", "danger")

    return redirect(url_for("tours.admin_manage_categories"))


# Delete category from admin page
@tours_bp.route("/admin/categories/<int:id>/delete", methods=["POST"])
@login_required
@admin_required
def delete_category(id):
    """
    Delete a category (admin only).
    """
    category = Category.query.get_or_404(id)
    # Check if category has tours
    if category.tours:
        flash(
            f'Cannot delete category "{category.name}" because it has tours assigned.',
            "danger",
        )
        return redirect(url_for("tours.admin_manage_categories"))
    try:
        category_name = category.name
        db.session.delete(category)
        db.session.commit()
        flash(f'Category "{category_name}" deleted successfully!', "success")
    except Exception as e:
        db.session.rollback()
        flash("An error occurred while deleting the category.", "danger")
    return redirect(url_for("tours.admin_manage_categories"))


@tours_bp.route("/manage")
@login_required
@admin_required
def manage():
    """
    Admin dashboard for managing tours.
    """
    # Get query parameters
    search = request.args.get("search", "")
    category_id = request.args.get("category", "")
    status = request.args.get("status", "")
    page = request.args.get("page", 1, type=int)

    # Start with base query
    query = Tour.query

    # Apply search filter
    if search:
        query = query.filter(
            or_(
                Tour.title.contains(search),
                Tour.destination.contains(search),
                Tour.description.contains(search),
            )
        )

    # Apply category filter
    if category_id:
        query = query.filter(Tour.category_id == category_id)

    # Apply status filter
    if status == "available":
        query = query.filter(Tour.is_active == True)
    elif status == "unavailable":
        query = query.filter(Tour.is_active == False)

    # Order by created date (newest first)
    query = query.order_by(Tour.created_at.desc())

    # Paginate results
    tours = query.paginate(
        page=page, per_page=10, error_out=False  # 10 tours per page for admin view
    )

    # Get all categories for filter dropdown
    categories = Category.query.order_by(Category.name).all()

    # Get counts for statistics
    available_count = Tour.query.filter(Tour.is_active == True).count()
    unavailable_count = Tour.query.filter(Tour.is_active == False).count()

    return render_template(
        "tours/manage.html",
        tours=tours,
        categories=categories,
        available_count=available_count,
        unavailable_count=unavailable_count,
        title="Manage Tours",
    )
