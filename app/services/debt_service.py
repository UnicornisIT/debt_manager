from datetime import datetime
from flask_login import current_user
from app.models import Debt
from app.utils import is_local_test_user

_demo_debts = None


def _load_demo_debts():
    global _demo_debts
    if _demo_debts is None:
        from app.services.finance_summary_service import get_finance_summary
        summary = get_finance_summary(None)
        _demo_debts = [debt for debt in summary['active_debts']]
    return _demo_debts


def get_demo_debts():
    return _load_demo_debts()


def get_demo_debt(debt_id):
    return next((debt for debt in _load_demo_debts() if debt.id == debt_id), None)


def create_demo_debt(**kwargs):
    debts = _load_demo_debts()
    next_id = max((debt.id for debt in debts), default=100) + 1
    debt = Debt(id=next_id, **kwargs)
    debts.append(debt)
    return debt


def delete_demo_debt(debt_id):
    debts = _load_demo_debts()
    for debt in debts:
        if debt.id == debt_id:
            debts.remove(debt)
            return True
    return False


def get_user_debt(debt_id):
    if is_local_test_user():
        return get_demo_debt(debt_id)
    return Debt.query.filter_by(id=debt_id, user_id=current_user.id).first()
