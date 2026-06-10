"""Fitnes klubni boshqarish tizimi — Flask veb-ilovasi."""
import os
from datetime import date, datetime, timedelta

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from sqlalchemy import func

from models import (
    Attendance,
    Member,
    Membership,
    Payment,
    Plan,
    Trainer,
    db,
)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "fitnes-klub-maxfiy-kalit")

    # Railway PostgreSQL: DATABASE_URL avtomatik beriladi.
    # Lokal ishlatishda SQLite ishlatiladi.
    db_url = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "fitness.db"),
    )
    # Railway postgres:// prefiksini postgresql:// ga o'zgartirish (SQLAlchemy talab qiladi)
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    with app.app_context():
        db.create_all()
        seed_defaults()

    register_routes(app)
    register_filters(app)
    return app


def seed_defaults():
    """Birinchi ishga tushishda standart tariflarni qo'shadi."""
    if Plan.query.count() == 0:
        db.session.add_all(
            [
                Plan(name="1 oylik", duration_days=30, price=300000,
                     description="Bir oylik to'liq abonement"),
                Plan(name="3 oylik", duration_days=90, price=750000,
                     description="Uch oylik (chegirmali)"),
                Plan(name="1 yillik", duration_days=365, price=2400000,
                     description="Yillik abonement (eng foydali)"),
                Plan(name="Kunlik", duration_days=1, price=20000,
                     description="Bir martalik tashrif"),
            ]
        )
        db.session.commit()


def register_filters(app):
    @app.template_filter("money")
    def money(value):
        try:
            return f"{int(value):,}".replace(",", " ") + " so'm"
        except (TypeError, ValueError):
            return value

    @app.template_filter("dt")
    def dt(value):
        if not value:
            return "—"
        if isinstance(value, datetime):
            return value.strftime("%d.%m.%Y %H:%M")
        return value.strftime("%d.%m.%Y")


def register_routes(app):
    # ---------------- Bosh sahifa / Dashboard ----------------
    @app.route("/")
    def dashboard():
        today = date.today()
        members = Member.query.all()
        total_members = len(members)
        active = sum(1 for m in members if m.status == "active")
        expiring = sum(1 for m in members if m.status == "expiring")
        expired = sum(1 for m in members if m.status == "expired")

        today_attendance = Attendance.query.filter(
            func.date(Attendance.checked_in_at) == today
        ).count()

        month_start = today.replace(day=1)
        month_income = (
            db.session.query(func.coalesce(func.sum(Payment.amount), 0))
            .filter(Payment.paid_at >= month_start)
            .scalar()
        )
        total_income = (
            db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
        )

        expiring_soon = sorted(
            [m for m in members if m.status in ("expiring", "expired")],
            key=lambda m: m.end_date or date.max,
        )[:8]

        recent_payments = (
            Payment.query.order_by(Payment.paid_at.desc()).limit(6).all()
        )

        return render_template(
            "dashboard.html",
            total_members=total_members,
            active=active,
            expiring=expiring,
            expired=expired,
            today_attendance=today_attendance,
            month_income=month_income,
            total_income=total_income,
            expiring_soon=expiring_soon,
            recent_payments=recent_payments,
        )

    # ---------------- A'zolar ----------------
    @app.route("/members")
    def members():
        q = request.args.get("q", "").strip()
        status = request.args.get("status", "")
        query = Member.query.order_by(Member.created_at.desc())
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(Member.full_name.ilike(like), Member.phone.ilike(like))
            )
        items = query.all()
        if status:
            items = [m for m in items if m.status == status]
        return render_template("members.html", members=items, q=q, status=status)

    @app.route("/members/new", methods=["GET", "POST"])
    def member_new():
        if request.method == "POST":
            member = Member(
                full_name=request.form["full_name"].strip(),
                phone=request.form.get("phone", "").strip(),
                email=request.form.get("email", "").strip(),
                gender=request.form.get("gender"),
                notes=request.form.get("notes", "").strip(),
            )
            bd = request.form.get("birth_date")
            if bd:
                member.birth_date = datetime.strptime(bd, "%Y-%m-%d").date()
            trainer_id = request.form.get("trainer_id")
            if trainer_id:
                member.trainer_id = int(trainer_id)
            db.session.add(member)
            db.session.commit()
            flash(f"A'zo qo'shildi: {member.full_name}", "success")
            return redirect(url_for("member_detail", member_id=member.id))
        return render_template(
            "member_form.html", member=None, trainers=Trainer.query.all()
        )

    @app.route("/members/<int:member_id>")
    def member_detail(member_id):
        member = db.get_or_404(Member, member_id)
        plans = Plan.query.filter_by(is_active=True).all()
        return render_template(
            "member_detail.html", member=member, plans=plans
        )

    @app.route("/members/<int:member_id>/edit", methods=["GET", "POST"])
    def member_edit(member_id):
        member = db.get_or_404(Member, member_id)
        if request.method == "POST":
            member.full_name = request.form["full_name"].strip()
            member.phone = request.form.get("phone", "").strip()
            member.email = request.form.get("email", "").strip()
            member.gender = request.form.get("gender")
            member.notes = request.form.get("notes", "").strip()
            bd = request.form.get("birth_date")
            member.birth_date = (
                datetime.strptime(bd, "%Y-%m-%d").date() if bd else None
            )
            trainer_id = request.form.get("trainer_id")
            member.trainer_id = int(trainer_id) if trainer_id else None
            db.session.commit()
            flash("Ma'lumotlar yangilandi", "success")
            return redirect(url_for("member_detail", member_id=member.id))
        return render_template(
            "member_form.html", member=member, trainers=Trainer.query.all()
        )

    @app.route("/members/<int:member_id>/delete", methods=["POST"])
    def member_delete(member_id):
        member = db.get_or_404(Member, member_id)
        db.session.delete(member)
        db.session.commit()
        flash("A'zo o'chirildi", "info")
        return redirect(url_for("members"))

    @app.route("/members/<int:member_id>/checkin", methods=["POST"])
    def member_checkin(member_id):
        member = db.get_or_404(Member, member_id)
        db.session.add(Attendance(member_id=member.id))
        db.session.commit()
        flash(f"{member.full_name} — kirish belgilandi ✅", "success")
        return redirect(request.referrer or url_for("member_detail", member_id=member_id))

    # ---------------- Abonement biriktirish + To'lov ----------------
    @app.route("/members/<int:member_id>/subscribe", methods=["POST"])
    def member_subscribe(member_id):
        member = db.get_or_404(Member, member_id)
        plan = db.get_or_404(Plan, int(request.form["plan_id"]))

        # Faol abonement bo'lsa, uning tugash sanasidan davom ettiramiz
        existing = member.active_membership
        start = (
            existing.end_date + timedelta(days=1)
            if existing and existing.end_date >= date.today()
            else date.today()
        )
        membership = Membership.make(member, plan, start_date=start)
        db.session.add(membership)

        if request.form.get("with_payment"):
            db.session.add(
                Payment(
                    member_id=member.id,
                    amount=plan.price,
                    method=request.form.get("method", "naqd"),
                    note=f"Abonement: {plan.name}",
                )
            )
        db.session.commit()
        flash(f"Abonement biriktirildi: {plan.name}", "success")
        return redirect(url_for("member_detail", member_id=member.id))

    @app.route("/members/<int:member_id>/pay", methods=["POST"])
    def member_pay(member_id):
        member = db.get_or_404(Member, member_id)
        amount = float(request.form.get("amount") or 0)
        db.session.add(
            Payment(
                member_id=member.id,
                amount=amount,
                method=request.form.get("method", "naqd"),
                note=request.form.get("note", "").strip(),
            )
        )
        db.session.commit()
        flash(f"To'lov qabul qilindi: {int(amount):,} so'm".replace(",", " "), "success")
        return redirect(url_for("member_detail", member_id=member.id))

    # ---------------- Tariflar ----------------
    @app.route("/plans", methods=["GET", "POST"])
    def plans():
        if request.method == "POST":
            db.session.add(
                Plan(
                    name=request.form["name"].strip(),
                    duration_days=int(request.form.get("duration_days") or 30),
                    price=float(request.form.get("price") or 0),
                    description=request.form.get("description", "").strip(),
                )
            )
            db.session.commit()
            flash("Tarif qo'shildi", "success")
            return redirect(url_for("plans"))
        return render_template("plans.html", plans=Plan.query.all())

    @app.route("/plans/<int:plan_id>/toggle", methods=["POST"])
    def plan_toggle(plan_id):
        plan = db.get_or_404(Plan, plan_id)
        plan.is_active = not plan.is_active
        db.session.commit()
        return redirect(url_for("plans"))

    @app.route("/plans/<int:plan_id>/delete", methods=["POST"])
    def plan_delete(plan_id):
        plan = db.get_or_404(Plan, plan_id)
        if plan.memberships:
            flash("Bu tarif a'zolarda ishlatilgan, o'chirib bo'lmaydi (faqat yashirish mumkin)", "danger")
        else:
            db.session.delete(plan)
            db.session.commit()
            flash("Tarif o'chirildi", "info")
        return redirect(url_for("plans"))

    # ---------------- Murabbiylar ----------------
    @app.route("/trainers", methods=["GET", "POST"])
    def trainers():
        if request.method == "POST":
            db.session.add(
                Trainer(
                    full_name=request.form["full_name"].strip(),
                    phone=request.form.get("phone", "").strip(),
                    speciality=request.form.get("speciality", "").strip(),
                )
            )
            db.session.commit()
            flash("Murabbiy qo'shildi", "success")
            return redirect(url_for("trainers"))
        return render_template("trainers.html", trainers=Trainer.query.all())

    @app.route("/trainers/<int:trainer_id>/delete", methods=["POST"])
    def trainer_delete(trainer_id):
        trainer = db.get_or_404(Trainer, trainer_id)
        db.session.delete(trainer)
        db.session.commit()
        flash("Murabbiy o'chirildi", "info")
        return redirect(url_for("trainers"))

    # ---------------- To'lovlar ----------------
    @app.route("/payments")
    def payments():
        items = Payment.query.order_by(Payment.paid_at.desc()).limit(200).all()
        total = db.session.query(func.coalesce(func.sum(Payment.amount), 0)).scalar()
        return render_template("payments.html", payments=items, total=total)

    # ---------------- Davomat ----------------
    @app.route("/attendance")
    def attendance():
        day_str = request.args.get("day")
        day = (
            datetime.strptime(day_str, "%Y-%m-%d").date()
            if day_str
            else date.today()
        )
        items = (
            Attendance.query.filter(func.date(Attendance.checked_in_at) == day)
            .order_by(Attendance.checked_in_at.desc())
            .all()
        )
        return render_template("attendance.html", attendances=items, day=day)


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
