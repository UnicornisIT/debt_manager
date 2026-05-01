from datetime import date, datetime
from extensions import db
from app.models import Payment


def add_payment(debt, amount, payment_date=None, comment=None):
    if not payment_date:
        payment_date = date.today()

    new_remaining = max(debt.remaining_amount - amount, 0)
    payment = Payment(
        debt_id=debt.id,
        amount=amount,
        payment_date=payment_date,
        comment=comment,
        remaining_after_payment=new_remaining,
    )

    debt.remaining_amount = new_remaining
    debt.updated_at = datetime.utcnow()
    db.session.add(payment)
    db.session.commit()

    return payment
