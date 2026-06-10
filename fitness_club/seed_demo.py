"""Namuna (demo) ma'lumotlarni bazaga qo'shish.

Ishlatish:  python seed_demo.py
"""
import random
from datetime import date, datetime, timedelta

from app import app
from models import Attendance, Member, Membership, Payment, Plan, Trainer, db

FIRST = ["Ali", "Vali", "Hasan", "Husan", "Sardor", "Jasur", "Dilnoza",
         "Madina", "Kamola", "Bekzod", "Aziza", "Shaxzod", "Nodira", "Rustam"]
LAST = ["Aliyev", "Karimov", "Yusupov", "Rahimov", "Tошева", "Saidova",
        "Ergashev", "Tursunov", "Qodirov", "Ismoilov"]


def run():
    with app.app_context():
        if Member.query.count() > 0:
            print("Bazada allaqachon a'zolar bor. Demo qo'shilmadi.")
            return

        trainers = [
            Trainer(full_name="Akmal Trenerov", speciality="Bodybuilding", phone="+998901112233"),
            Trainer(full_name="Gulnoza Yoga", speciality="Yoga & Pilates", phone="+998907778899"),
            Trainer(full_name="Boburjon Boks", speciality="Boks", phone="+998935554433"),
        ]
        db.session.add_all(trainers)
        db.session.commit()

        plans = Plan.query.all()

        for i in range(18):
            name = f"{random.choice(FIRST)} {random.choice(LAST)}"
            m = Member(
                full_name=name,
                phone=f"+9989{random.randint(10000000, 99999999)}",
                gender=random.choice(["Erkak", "Ayol"]),
                trainer=random.choice(trainers),
                created_at=datetime.utcnow() - timedelta(days=random.randint(1, 120)),
            )
            db.session.add(m)
            db.session.flush()

            plan = random.choice(plans)
            start = date.today() - timedelta(days=random.randint(0, 40))
            ms = Membership(member=m, plan=plan, start_date=start,
                            end_date=start + timedelta(days=plan.duration_days))
            db.session.add(ms)
            db.session.add(Payment(member_id=m.id, amount=plan.price,
                                   method=random.choice(["naqd", "karta"]),
                                   note=f"Abonement: {plan.name}"))

            for _ in range(random.randint(0, 12)):
                db.session.add(Attendance(
                    member_id=m.id,
                    checked_in_at=datetime.utcnow() - timedelta(
                        days=random.randint(0, 20), hours=random.randint(0, 12)),
                ))

        db.session.commit()
        print(f"✅ Demo ma'lumotlar qo'shildi: {Member.query.count()} a'zo, "
              f"{Payment.query.count()} to'lov, {Attendance.query.count()} tashrif.")


if __name__ == "__main__":
    run()
