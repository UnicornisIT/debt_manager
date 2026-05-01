from datetime import datetime
from flask import jsonify, request
from flask_login import current_user
from app.models import Debt
from app.services.debt_service import get_user_debt
from app.utils import is_local_test_user, parse_date, parse_decimal
from extensions import db


def init_app(app):
    @app.route('/api/debts', methods=['GET'])
    def api_get_debts():
        if is_local_test_user():
            debts = get_demo_debts()
            status = request.args.get('status', 'active')
            type_filter = request.args.get('type', '').strip()
            filtered = [d for d in debts if d.status == status]
            if type_filter:
                filtered = [d for d in filtered if d.debt_type == type_filter]
            return jsonify({'success': True, 'debts': [d.to_dict() for d in filtered]})

        status = request.args.get('status', 'active')
        bank_filter = request.args.get('bank', '').strip()
        type_filter = request.args.get('type', '').strip()

        query = Debt.query.filter_by(status=status, user_id=current_user.id)
        if bank_filter:
            query = query.filter(Debt.bank_name.ilike(f'%{bank_filter}%'))
        if type_filter:
            query = query.filter_by(debt_type=type_filter)

        debts = query.order_by(db.case((Debt.next_payment_date.is_(None), 1), else_=0), Debt.next_payment_date.asc()).all()
        return jsonify({'success': True, 'debts': [d.to_dict() for d in debts]})

    @app.route('/api/debts', methods=['POST'])
    def api_create_debt():
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        try:
            bank_name = str(data.get('bank_name', '')).strip()
            if not bank_name:
                raise ValueError("Название банка обязательно")

            debt_type = str(data.get('debt_type', '')).strip()
            if debt_type not in ('credit_card', 'split', 'mortgage'):
                raise ValueError("Тип долга: выберите 'credit_card', 'split' или 'mortgage'")

            product_name = str(data.get('product_name', '')).strip()
            if not product_name:
                raise ValueError("Название продукта/карты обязательно")

            total_amount = parse_decimal(data.get('total_amount'), 'Сумма долга', required=True)
            remaining_amount = parse_decimal(data.get('remaining_amount'), 'Остаток долга', required=True)
            minimum_payment = parse_decimal(data.get('minimum_payment'), 'Минимальный платеж', required=False)
            interest_rate = parse_decimal(data.get('interest_rate'), 'Процентная ставка', required=False)
            next_payment_date = parse_date(data.get('next_payment_date'), 'Дата следующего платежа')

            if remaining_amount > total_amount:
                raise ValueError("Остаток долга не может превышать общую сумму")

            debt = Debt(
                user_id=current_user.id,
                bank_name=bank_name,
                debt_type=debt_type,
                product_name=product_name,
                total_amount=total_amount,
                remaining_amount=remaining_amount,
                minimum_payment=minimum_payment,
                interest_rate=interest_rate,
                next_payment_date=next_payment_date,
                comment=str(data.get('comment', '')).strip() or None,
                status='active',
            )
            db.session.add(debt)
            db.session.commit()
            return jsonify({'success': True, 'debt': debt.to_dict()}), 201

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 422
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Ошибка сервера: {str(e)}'}), 500

    @app.route('/api/debts/<int:debt_id>', methods=['GET'])
    def api_get_debt(debt_id):
        debt = get_user_debt(debt_id)
        if not debt:
            return jsonify({'success': False, 'error': 'Долг не найден'}), 404
        return jsonify({'success': True, 'debt': debt.to_dict()})

    @app.route('/api/debts/<int:debt_id>', methods=['PUT'])
    def api_update_debt(debt_id):
        debt = get_user_debt(debt_id)
        if not debt:
            return jsonify({'success': False, 'error': 'Долг не найден'}), 404

        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Нет данных'}), 400

        try:
            if 'bank_name' in data:
                bank_name = str(data['bank_name']).strip()
                if not bank_name:
                    raise ValueError("Название банка обязательно")
                debt.bank_name = bank_name

            if 'debt_type' in data:
                if data['debt_type'] not in ('credit_card', 'split', 'mortgage'):
                    raise ValueError("Некорректный тип долга")
                debt.debt_type = data['debt_type']

            if 'product_name' in data:
                product_name = str(data['product_name']).strip()
                if not product_name:
                    raise ValueError("Название продукта обязательно")
                debt.product_name = product_name

            if 'total_amount' in data:
                debt.total_amount = parse_decimal(data['total_amount'], 'Сумма долга', required=True)
            if 'remaining_amount' in data:
                debt.remaining_amount = parse_decimal(data['remaining_amount'], 'Остаток долга', required=True)
            if 'minimum_payment' in data:
                debt.minimum_payment = parse_decimal(data['minimum_payment'], 'Минимальный платеж', required=False)
            if 'interest_rate' in data:
                debt.interest_rate = parse_decimal(data['interest_rate'], 'Процентная ставка', required=False)
            if 'next_payment_date' in data:
                debt.next_payment_date = parse_date(data['next_payment_date'], 'Дата следующего платежа')
            if 'comment' in data:
                debt.comment = str(data['comment']).strip() or None

            if float(debt.remaining_amount) > float(debt.total_amount):
                raise ValueError("Остаток долга не может превышать общую сумму")

            debt.updated_at = datetime.utcnow()
            if not is_local_test_user():
                db.session.commit()
            return jsonify({'success': True, 'debt': debt.to_dict()})

        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 422
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'error': f'Ошибка сервера: {str(e)}'}), 500

    @app.route('/api/debts/<int:debt_id>/archive', methods=['POST'])
    def api_archive_debt(debt_id):
        debt = get_user_debt(debt_id)
        if not debt:
            return jsonify({'success': False, 'error': 'Долг не найден'}), 404

        debt.status = 'archived'
        debt.updated_at = datetime.utcnow()
        if not is_local_test_user():
            db.session.commit()
        return jsonify({'success': True, 'message': 'Карточка перемещена в архив'})

    @app.route('/api/debts/<int:debt_id>/restore', methods=['POST'])
    def api_restore_debt(debt_id):
        debt = get_user_debt(debt_id)
        if not debt:
            return jsonify({'success': False, 'error': 'Долг не найден'}), 404

        debt.status = 'active'
        debt.updated_at = datetime.utcnow()
        if not is_local_test_user():
            db.session.commit()
        return jsonify({'success': True, 'message': 'Карточка восстановлена', 'debt': debt.to_dict()})

    @app.route('/api/debts/<int:debt_id>/delete', methods=['DELETE'])
    def api_delete_debt(debt_id):
        debt = get_user_debt(debt_id)
        if not debt:
            return jsonify({'success': False, 'error': 'Долг не найден'}), 404

        if not is_local_test_user():
            db.session.delete(debt)
            db.session.commit()
        else:
            from app.services.debt_service import delete_demo_debt
            delete_demo_debt(debt_id)
        return jsonify({'success': True, 'message': 'Карточка удалена'})
