from datetime import date, timedelta
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from extensions import db
from app.models import Debt, Income, Expense, Payment


def get_finance_summary(user_id, year=None, month=None):
    today = date.today()
    use_selected_month = year is not None and month is not None
    if use_selected_month:
        try:
            month_start = date(int(year), int(month), 1)
        except (TypeError, ValueError):
            month_start = date(today.year, today.month, 1)
    else:
        month_start = date(today.year, today.month, 1)
    month_end = date(month_start.year + (month_start.month // 12), ((month_start.month % 12) + 1), 1) if month_start.month != 12 else date(month_start.year + 1, 1, 1)

    if user_id is None:
        def safe_day(day):
            return min(day, 28)

        debts = [
            Debt(
                id=101,
                user_id=0,
                bank_name='Тинькофф',
                debt_type='credit_card',
                product_name='Tinkoff Platinum',
                total_amount=85000,
                remaining_amount=47500,
                minimum_payment=3200,
                interest_rate=28.9,
                next_payment_date=date(month_start.year, month_start.month, safe_day(25)),
                comment='Основная кредитная карта',
                status='active',
            ),
            Debt(
                id=102,
                user_id=0,
                bank_name='Сбербанк',
                debt_type='split',
                product_name='СберСплит — MacBook Pro',
                total_amount=180000,
                remaining_amount=120000,
                minimum_payment=15000,
                interest_rate=None,
                next_payment_date=date(month_start.year, month_start.month, safe_day(15)),
                comment='12 платежей, прошло 4',
                status='active',
            ),
            Debt(
                id=103,
                user_id=0,
                bank_name='Альфа-Банк',
                debt_type='credit_card',
                product_name='Альфа-Карта',
                total_amount=50000,
                remaining_amount=8200,
                minimum_payment=1500,
                interest_rate=24.5,
                next_payment_date=date(month_start.year, month_start.month, safe_day(5)),
                comment='Почти погашена',
                status='active',
            ),
            Debt(
                id=104,
                user_id=0,
                bank_name='Сбербанк',
                debt_type='mortgage',
                product_name='Ипотека на квартиру',
                total_amount=3600000,
                remaining_amount=3480000,
                minimum_payment=22000,
                interest_rate=3.6,
                next_payment_date=date(month_start.year, month_start.month, safe_day(10)),
                comment='Ипотека на 20 лет',
                status='active',
            ),
            Debt(
                id=105,
                user_id=0,
                bank_name='Совкомбанк',
                debt_type='mortgage',
                product_name='Ипотека с просрочкой',
                total_amount=3600000,
                remaining_amount=3500000,
                minimum_payment=25000,
                interest_rate=14.0,
                next_payment_date=today - timedelta(days=12),
                comment='Просроченный платеж по ипотеке 14% годовых',
                status='active',
            ),
        ]

        incomes_this_month = [
            Income(
                id=201,
                user_id=0,
                amount=85000,
                category='salary',
                source='Основная работа',
                income_date=date(month_start.year, month_start.month, safe_day(10)),
                comment='Зарплата за текущий месяц',
            ),
            Income(
                id=202,
                user_id=0,
                amount=15000,
                category='bonus',
                source='Премия',
                income_date=date(month_start.year, month_start.month, safe_day(5)),
                comment='Премия за выполнение плана',
            ),
        ]

        expenses_this_month = [
            Expense(
                id=301,
                user_id=0,
                amount=3500,
                category='products',
                title='Продукты',
                expense_date=date(month_start.year, month_start.month, safe_day(12)),
                payment_method='card',
                comment='Покупка в супермаркете',
            ),
            Expense(
                id=302,
                user_id=0,
                amount=6200,
                category='transport',
                title='Транспорт',
                expense_date=date(month_start.year, month_start.month, safe_day(7)),
                payment_method='card',
                comment='Такси и метро',
            ),
            Expense(
                id=303,
                user_id=0,
                amount=2200,
                category='subscriptions',
                title='Подписки',
                expense_date=date(month_start.year, month_start.month, safe_day(3)),
                payment_method='card',
                comment='Онлайн-сервисы',
            ),
        ]

        payments_this_month = [
            Payment(
                id=401,
                debt_id=101,
                amount=10000,
                payment_date=date(month_start.year, month_start.month, safe_day(25)),
                comment='Плановый платеж',
                remaining_after_payment=57500,
            ),
            Payment(
                id=402,
                debt_id=101,
                amount=20000,
                payment_date=date(month_start.year, month_start.month, safe_day(5)),
                comment='Досрочный платеж',
                remaining_after_payment=67500,
            ),
        ]

        total_incomes = sum(float(item.amount) for item in incomes_this_month)
        total_expenses = sum(float(item.amount) for item in expenses_this_month)
        total_payments = sum(float(item.amount) for item in payments_this_month)
        free_balance = total_incomes - total_expenses - total_payments
        overdue_count = len([d for d in debts if d.next_payment_date and d.next_payment_date < today])
        nearest_debt = next((d for d in debts if d.next_payment_date and d.next_payment_date >= today), None)

        mortgage_debts = [d for d in debts if d.debt_type == 'mortgage']
        total_mortgage_remaining = sum(float(d.remaining_amount) for d in mortgage_debts)
        total_mortgage_original = sum(float(d.total_amount) for d in mortgage_debts)
        total_mortgage_interest = sum(
            float(d.remaining_amount) * float(d.interest_rate) / 12 / 100
            for d in mortgage_debts
            if d.interest_rate is not None
        )

        return {
            'today': today,
            'month_start': month_start,
            'month_end': month_end,
            'active_debts': debts,
            'mortgage_debts': mortgage_debts,
            'mortgage_count': len(mortgage_debts),
            'total_mortgage_remaining': total_mortgage_remaining,
            'total_mortgage_original': total_mortgage_original,
            'total_mortgage_interest': total_mortgage_interest,
            'total_remaining': sum(float(d.remaining_amount) for d in debts),
            'total_original': sum(float(d.total_amount) for d in debts),
            'incomes_this_month': incomes_this_month,
            'expenses_this_month': expenses_this_month,
            'payments_this_month': payments_this_month,
            'total_incomes': total_incomes,
            'total_expenses': total_expenses,
            'total_payments': total_payments,
            'free_balance': free_balance,
            'days_left': (month_end - today).days if month_start.year == today.year and month_start.month == today.month else 0,
            'nearest_debt': nearest_debt,
            'overdue_count': overdue_count,
            'archived_count': 0,
            'total_debts': len(debts),
            'selected_year': month_start.year,
            'selected_month': month_start.month,
        }

    try:
        active_debts = Debt.query.filter_by(status='active', user_id=user_id).order_by(db.case((Debt.next_payment_date.is_(None), 1), else_=0), Debt.next_payment_date.asc()).all()
        total_remaining = sum(float(d.remaining_amount) for d in active_debts)
        total_original = sum(float(d.total_amount) for d in active_debts)

        incomes_this_month = Income.query.filter_by(user_id=user_id).filter(Income.income_date >= month_start, Income.income_date < month_end).all()
        expenses_this_month = Expense.query.filter_by(user_id=user_id).filter(Expense.expense_date >= month_start, Expense.expense_date < month_end).all()
        payments_this_month = Payment.query.join(Debt).filter(Debt.user_id == user_id, Payment.payment_date >= month_start, Payment.payment_date < month_end).all()

        if not use_selected_month and not (incomes_this_month or expenses_this_month or payments_this_month):
            latest_income = Income.query.with_entities(func.max(Income.income_date)).filter_by(user_id=user_id).scalar()
            latest_expense = Expense.query.with_entities(func.max(Expense.expense_date)).filter_by(user_id=user_id).scalar()
            latest_payment = Payment.query.join(Debt).with_entities(func.max(Payment.payment_date)).filter(Debt.user_id == user_id).scalar()
            latest_date = max(d for d in (latest_income, latest_expense, latest_payment) if d is not None) if any((latest_income, latest_expense, latest_payment)) else None
            if latest_date:
                month_start = date(latest_date.year, latest_date.month, 1)
                month_end = date(month_start.year + (month_start.month // 12), ((month_start.month % 12) + 1), 1) if month_start.month != 12 else date(month_start.year + 1, 1, 1)
                incomes_this_month = Income.query.filter_by(user_id=user_id).filter(Income.income_date >= month_start, Income.income_date < month_end).all()
                expenses_this_month = Expense.query.filter_by(user_id=user_id).filter(Expense.expense_date >= month_start, Expense.expense_date < month_end).all()
                payments_this_month = Payment.query.join(Debt).filter(Debt.user_id == user_id, Payment.payment_date >= month_start, Payment.payment_date < month_end).all()

        total_incomes = float(Income.query.with_entities(func.coalesce(func.sum(Income.amount), 0)).filter_by(user_id=user_id).filter(Income.income_date >= month_start, Income.income_date < month_end).scalar() or 0)
        total_expenses = float(Expense.query.with_entities(func.coalesce(func.sum(Expense.amount), 0)).filter_by(user_id=user_id).filter(Expense.expense_date >= month_start, Expense.expense_date < month_end).scalar() or 0)
        total_payments = float(Payment.query.with_entities(func.coalesce(func.sum(Payment.amount), 0)).join(Debt).filter(Debt.user_id == user_id, Payment.payment_date >= month_start, Payment.payment_date < month_end).scalar() or 0)
        archived_count = Debt.query.filter_by(status='archived', user_id=user_id).count()
        total_debts = Debt.query.filter_by(user_id=user_id).count()
    except SQLAlchemyError:
        return {
            'today': today,
            'month_start': month_start,
            'month_end': month_end,
            'active_debts': [],
            'total_remaining': 0.0,
            'total_original': 0.0,
            'incomes_this_month': [],
            'expenses_this_month': [],
            'payments_this_month': [],
            'total_incomes': 0.0,
            'total_expenses': 0.0,
            'total_payments': 0.0,
            'free_balance': 0.0,
            'days_left': 0,
            'nearest_debt': None,
            'overdue_count': 0,
            'archived_count': 0,
            'total_debts': 0,
            'selected_year': month_start.year,
            'selected_month': month_start.month,
        }

    incomes_this_month = Income.query.filter_by(user_id=user_id).filter(Income.income_date >= month_start, Income.income_date < month_end).all()
    expenses_this_month = Expense.query.filter_by(user_id=user_id).filter(Expense.expense_date >= month_start, Expense.expense_date < month_end).all()
    payments_this_month = Payment.query.join(Debt).filter(Debt.user_id == user_id, Payment.payment_date >= month_start, Payment.payment_date < month_end).all()

    if not use_selected_month and not (incomes_this_month or expenses_this_month or payments_this_month):
        latest_income = Income.query.with_entities(func.max(Income.income_date)).filter_by(user_id=user_id).scalar()
        latest_expense = Expense.query.with_entities(func.max(Expense.expense_date)).filter_by(user_id=user_id).scalar()
        latest_payment = Payment.query.join(Debt).with_entities(func.max(Payment.payment_date)).filter(Debt.user_id == user_id).scalar()
        latest_date = max(d for d in (latest_income, latest_expense, latest_payment) if d is not None) if any((latest_income, latest_expense, latest_payment)) else None
        if latest_date:
            month_start = date(latest_date.year, latest_date.month, 1)
            month_end = date(month_start.year + (month_start.month // 12), ((month_start.month % 12) + 1), 1) if month_start.month != 12 else date(month_start.year + 1, 1, 1)
            incomes_this_month = Income.query.filter_by(user_id=user_id).filter(Income.income_date >= month_start, Income.income_date < month_end).all()
            expenses_this_month = Expense.query.filter_by(user_id=user_id).filter(Expense.expense_date >= month_start, Expense.expense_date < month_end).all()
            payments_this_month = Payment.query.join(Debt).filter(Debt.user_id == user_id, Payment.payment_date >= month_start, Payment.payment_date < month_end).all()

    total_incomes = float(Income.query.with_entities(func.coalesce(func.sum(Income.amount), 0)).filter_by(user_id=user_id).filter(Income.income_date >= month_start, Income.income_date < month_end).scalar() or 0)
    total_expenses = float(Expense.query.with_entities(func.coalesce(func.sum(Expense.amount), 0)).filter_by(user_id=user_id).filter(Expense.expense_date >= month_start, Expense.expense_date < month_end).scalar() or 0)
    total_payments = float(Payment.query.with_entities(func.coalesce(func.sum(Payment.amount), 0)).join(Debt).filter(Debt.user_id == user_id, Payment.payment_date >= month_start, Payment.payment_date < month_end).scalar() or 0)
    free_balance = total_incomes - total_expenses - total_payments
    overdue_count = len([d for d in active_debts if d.next_payment_date and d.next_payment_date < today])
    archived_count = Debt.query.filter_by(status='archived', user_id=user_id).count()
    total_debts = Debt.query.filter_by(user_id=user_id).count()

    if month_start.year == today.year and month_start.month == today.month:
        days_left = (month_end - today).days
    else:
        days_left = 0

    nearest_debt = next((d for d in active_debts if d.next_payment_date and d.next_payment_date >= today), None)

    mortgage_debts = [d for d in active_debts if d.debt_type == 'mortgage']
    total_mortgage_remaining = sum(float(d.remaining_amount) for d in mortgage_debts)
    total_mortgage_original = sum(float(d.total_amount) for d in mortgage_debts)
    total_mortgage_interest = sum(
        float(d.remaining_amount) * float(d.interest_rate) / 12 / 100
        for d in mortgage_debts
        if d.interest_rate is not None
    )

    return {
        'today': today,
        'month_start': month_start,
        'month_end': month_end,
        'active_debts': active_debts,
        'mortgage_debts': mortgage_debts,
        'mortgage_count': len(mortgage_debts),
        'total_mortgage_remaining': total_mortgage_remaining,
        'total_mortgage_original': total_mortgage_original,
        'total_mortgage_interest': total_mortgage_interest,
        'total_remaining': total_remaining,
        'total_original': total_original,
        'incomes_this_month': incomes_this_month,
        'expenses_this_month': expenses_this_month,
        'payments_this_month': payments_this_month,
        'total_incomes': total_incomes,
        'total_expenses': total_expenses,
        'total_payments': total_payments,
        'free_balance': free_balance,
        'days_left': days_left,
        'nearest_debt': nearest_debt,
        'overdue_count': overdue_count,
        'archived_count': archived_count,
        'total_debts': total_debts,
        'selected_year': month_start.year,
        'selected_month': month_start.month,
    }
