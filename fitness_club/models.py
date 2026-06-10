"""Ma'lumotlar bazasi modellari (Fitnes klub boshqaruv tizimi)."""
from datetime import date, datetime, timedelta

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Trainer(db.Model):
    """Murabbiy."""

    __tablename__ = "trainers"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    speciality = db.Column(db.String(120))  # Mutaxassisligi
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    members = db.relationship("Member", back_populates="trainer")

    def __repr__(self):
        return f"<Trainer {self.full_name}>"


class Plan(db.Model):
    """Abonement (tarif) rejasi."""

    __tablename__ = "plans"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    duration_days = db.Column(db.Integer, nullable=False, default=30)  # Muddati (kun)
    price = db.Column(db.Float, nullable=False, default=0.0)  # Narxi
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)

    memberships = db.relationship("Membership", back_populates="plan")

    def __repr__(self):
        return f"<Plan {self.name}>"


class Member(db.Model):
    """Klub a'zosi."""

    __tablename__ = "members"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(120))
    gender = db.Column(db.String(10))  # Jinsi
    birth_date = db.Column(db.Date)
    notes = db.Column(db.String(255))
    trainer_id = db.Column(db.Integer, db.ForeignKey("trainers.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    trainer = db.relationship("Trainer", back_populates="members")
    memberships = db.relationship(
        "Membership", back_populates="member", cascade="all, delete-orphan"
    )
    payments = db.relationship(
        "Payment", back_populates="member", cascade="all, delete-orphan"
    )
    attendances = db.relationship(
        "Attendance", back_populates="member", cascade="all, delete-orphan"
    )

    @property
    def active_membership(self):
        """Hozir amal qilayotgan abonement (eng kech tugaydigani)."""
        today = date.today()
        active = [m for m in self.memberships if m.end_date >= today]
        if not active:
            return None
        return max(active, key=lambda m: m.end_date)

    @property
    def status(self):
        m = self.active_membership
        if not m:
            return "expired"  # Muddati tugagan / abonement yo'q
        if (m.end_date - date.today()).days <= 3:
            return "expiring"  # Tugashiga oz qoldi
        return "active"  # Faol

    @property
    def end_date(self):
        m = self.active_membership
        return m.end_date if m else None

    def __repr__(self):
        return f"<Member {self.full_name}>"


class Membership(db.Model):
    """A'zoga biriktirilgan abonement (sotib olingan reja)."""

    __tablename__ = "memberships"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    plan_id = db.Column(db.Integer, db.ForeignKey("plans.id"), nullable=False)
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    end_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    member = db.relationship("Member", back_populates="memberships")
    plan = db.relationship("Plan", back_populates="memberships")

    @staticmethod
    def make(member, plan, start_date=None):
        start = start_date or date.today()
        end = start + timedelta(days=plan.duration_days)
        return Membership(
            member=member, plan=plan, start_date=start, end_date=end
        )


class Payment(db.Model):
    """To'lov."""

    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    amount = db.Column(db.Float, nullable=False, default=0.0)
    method = db.Column(db.String(20), default="naqd")  # naqd / karta / o'tkazma
    note = db.Column(db.String(255))
    paid_at = db.Column(db.DateTime, default=datetime.utcnow)

    member = db.relationship("Member", back_populates="payments")


class Attendance(db.Model):
    """Davomat (kirish belgisi)."""

    __tablename__ = "attendances"

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey("members.id"), nullable=False)
    checked_in_at = db.Column(db.DateTime, default=datetime.utcnow)

    member = db.relationship("Member", back_populates="attendances")
