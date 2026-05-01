from datetime import date
from flask import jsonify, request
from app.models import Payment
from app.services.debt_service import get_user_debt
from app.services.payment_service import add_payment
from app.utils import parse_date, parse_decimal


def init_app(app):
    @app.route('/api/debts/<int:debt_id>/payments', methods=['GET'])
    def api_get_payments(debt_id):
        debt = get_user_debt(debt_id)
        if not debt:
            return jsonify({'success': False, 'error': 'Долг не найден'}), 404

        payments = Payment.query.filter_by(debt_id=debt_id).order_by(Payment.payment_date.desc()).all()
        return jsonify({
            'success': True,
            'debt': debt.to_dict(),
            'payments': [p.to_dict() for p in payments]
        })

    @app.route('/api/debts/<int:debt_id>/payments', methods=['POST'])
    def api_add_payment(debt_id):
        debt = get_user_debt(debt_id)
        if not debt:
            return jsonify({'success': False, 'error': 'Долг не найден'}), 404
        if debt.status != 'active':
            return jsonify({'success': False, 'error': 'Нельзя вносить платеж в архивный долг'}), 422

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        try:
            amount = parse_decimal(data.get('amount'), 'Сумма платежа', required=True)
            if amount <= 0:
                raise ValueError("Сумма платежа должна быть больше нуля")

            payment_date_str = data.get('payment_date')
            if payment_date_str:
                payment_date = parse_date(payment_date_str, 'Дата платежа')
            else:
                payment_date = date.today()

            payment = add_payment(debt, amount, payment_date=payment_date, comment=str(data.get('comment', '')).strip() or None)
            debt_cleared = float(debt.remaining_amount) <= 0.01

            return jsonify({
                'success': True,
                'payment': payment.to_dict(),
                'debt': debt.to_dict(),
                'debt_cleared': debt_cleared,
            })

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 422
        except Exception as e:
            return jsonify({'success': False, 'error': f'Ошибка сервера: {str(e)}'}), 500
