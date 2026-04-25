from datetime import datetime
from extensions import db


class Debt(db.Model):
    """Модель долга (кредитная карта или банковский сплит)"""
    __tablename__ = 'debts'

    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(100), nullable=False)
    debt_type = db.Column(db.Enum('credit_card', 'split'), nullable=False)
    product_name = db.Column(db.String(150), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    remaining_amount = db.Column(db.Numeric(12, 2), nullable=False)
    minimum_payment = db.Column(db.Numeric(12, 2), nullable=True)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=True)
    next_payment_date = db.Column(db.Date, nullable=True)
    comment = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum('active', 'archived'), nullable=False, default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связь с платежами
    payments = db.relationship('Payment', backref='debt', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        """Сериализация объекта в словарь для JSON-ответов"""
        from datetime import date
        today = date.today()
        days_until_payment = None
        if self.next_payment_date:
            days_until_payment = (self.next_payment_date - today).days

        return {
            'id': self.id,
            'bank_name': self.bank_name,
            'debt_type': self.debt_type,
            'debt_type_label': 'Кредитная карта' if self.debt_type == 'credit_card' else 'Сплит',
            'product_name': self.product_name,
            'total_amount': float(self.total_amount),
            'remaining_amount': float(self.remaining_amount),
            'minimum_payment': float(self.minimum_payment) if self.minimum_payment else None,
            'interest_rate': float(self.interest_rate) if self.interest_rate else None,
            'next_payment_date': self.next_payment_date.strftime('%Y-%m-%d') if self.next_payment_date else None,
            'next_payment_date_display': self.next_payment_date.strftime('%d.%m.%Y') if self.next_payment_date else None,
            'comment': self.comment,
            'status': self.status,
            'days_until_payment': days_until_payment,
            'paid_percent': round((1 - float(self.remaining_amount) / float(self.total_amount)) * 100, 1) if float(self.total_amount) > 0 else 100,
            'created_at': self.created_at.strftime('%d.%m.%Y') if self.created_at else None,
        }

    def __repr__(self):
        return f'<Debt {self.bank_name} - {self.product_name}>'


class Payment(db.Model):
    """Модель платежа"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    debt_id = db.Column(db.Integer, db.ForeignKey('debts.id'), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    payment_date = db.Column(db.Date, nullable=False, default=datetime.utcnow)
    comment = db.Column(db.Text, nullable=True)
    remaining_after_payment = db.Column(db.Numeric(12, 2), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'debt_id': self.debt_id,
            'amount': float(self.amount),
            'payment_date': self.payment_date.strftime('%d.%m.%Y') if self.payment_date else None,
            'comment': self.comment,
            'remaining_after_payment': float(self.remaining_after_payment),
            'created_at': self.created_at.strftime('%d.%m.%Y %H:%M') if self.created_at else None,
        }

    def __repr__(self):
        return f'<Payment {self.amount} for debt {self.debt_id}>'
