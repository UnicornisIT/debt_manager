import csv
from io import StringIO
from datetime import datetime
from flask import redirect, render_template, request, url_for, Response
from flask_login import current_user, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError
from app.models import ActivityLog, Debt, DictionaryEntry, Payment, User, AppSetting
from app.routes.auth import LocalTestUser
from app.utils import admin_required, DICTIONARY_TYPES, DEFAULT_SETTINGS, get_setting, record_activity, set_setting
from extensions import db


def init_app(app):
    @app.route('/admin')
    @admin_required
    def admin_dashboard():
        error_message = None
        stats = {
            'users': '—',
            'debts': '—',
            'payments': '—',
            'logs': '—',
            'dictionary_entries': '—',
        }
        try:
            stats = {
                'users': User.query.count(),
                'debts': Debt.query.count(),
                'payments': Payment.query.count(),
                'logs': ActivityLog.query.count(),
                'dictionary_entries': DictionaryEntry.query.count(),
            }
        except SQLAlchemyError as e:
            error_message = 'Ошибка подключения к базе данных. Админ-табло недоступно.'

        return render_template('admin_dashboard.html', stats=stats, error_message=error_message)

    @app.route('/admin/settings', methods=['GET', 'POST'])
    @admin_required
    def admin_settings():
        success_message = None

        if request.method == 'POST':
            for key in DEFAULT_SETTINGS.keys():
                value = request.form.get(key, '').strip()
                if key in ('registration_enabled', 'telegram_login_enabled', 'archive_enabled', 'export_enabled', 'overdue_after_date'):
                    value = 'true' if value == 'on' or value.lower() in ('1', 'true', 'yes', 'on') else 'false'
                if not value:
                    value = DEFAULT_SETTINGS.get(key, '')
                set_setting(key, value)
            record_activity('Изменил настройки приложения', current_user, description='Обновлены системные настройки')
            return redirect(url_for('admin_settings', success='Настройки сохранены'))

        settings = {key: get_setting(key, DEFAULT_SETTINGS[key]) for key in DEFAULT_SETTINGS}
        return render_template('admin_settings.html', settings=settings, success_message=request.args.get('success'))

    @app.route('/admin/dictionaries', methods=['GET', 'POST'])
    @admin_required
    def admin_dictionaries():
        error_message = None
        success_message = request.args.get('success')

        if request.method == 'POST':
            dictionary_type = request.form.get('dictionary_type')
            value = str(request.form.get('value', '')).strip()
            if not dictionary_type or dictionary_type not in [item[0] for item in DICTIONARY_TYPES]:
                error_message = 'Выберите тип справочника'
            elif not value:
                error_message = 'Значение не может быть пустым'
            else:
                try:
                    entry = DictionaryEntry(dictionary_type=dictionary_type, value=value)
                    db.session.add(entry)
                    db.session.commit()
                    record_activity('Добавил элемент справочника', current_user, entity_type=dictionary_type, description=value)
                    return redirect(url_for('admin_dictionaries', success='Элемент добавлен'))
                except Exception as e:
                    db.session.rollback()
                    error_message = f'Не удалось сохранить элемент: {str(e)}'

        entries = DictionaryEntry.query.order_by(DictionaryEntry.dictionary_type.asc(), DictionaryEntry.value.asc()).all()
        type_labels = {key: label for key, label in DICTIONARY_TYPES}
        return render_template('admin_dictionaries.html', entries=entries, types=DICTIONARY_TYPES, type_labels=type_labels, error_message=error_message, success_message=success_message)

    @app.route('/admin/dictionaries/<int:entry_id>/delete', methods=['POST'])
    @admin_required
    def admin_delete_dictionary_entry(entry_id):
        entry = DictionaryEntry.query.get(entry_id)
        if entry:
            db.session.delete(entry)
            db.session.commit()
            record_activity('Удалил элемент справочника', current_user, entity_type=entry.dictionary_type, entity_id=entry.id, description=entry.value)
            return redirect(url_for('admin_dictionaries', success='Элемент удалён'))
        return redirect(url_for('admin_dictionaries', success='Элемент не найден'))

    @app.route('/admin/users')
    @admin_required
    def admin_users():
        users = User.query.order_by(User.role.desc(), User.created_at.desc()).all()
        return render_template('admin_users.html', users=users)

    @app.route('/admin/impersonate/test', methods=['POST'])
    @admin_required
    def admin_impersonate_test():
        try:
            test_user = User.query.filter_by(username='test').first()
            if not test_user:
                test_user = User(
                    telegram_id=-999999999,
                    username='test',
                    first_name='test',
                    last_name=None,
                    auth_date=datetime.utcnow(),
                    role='user',
                    is_blocked=False,
                    login_count=0,
                )
                db.session.add(test_user)
                db.session.commit()

            if test_user.is_blocked:
                test_user.is_blocked = False
                db.session.commit()

            logout_user()
            login_user(test_user)
        except SQLAlchemyError:
            db.session.rollback()
            logout_user()
            login_user(LocalTestUser())

        return redirect(url_for('index'))

    @app.route('/admin/impersonate/<int:user_id>', methods=['POST'])
    @admin_required
    def admin_impersonate_user(user_id):
        user = User.query.get_or_404(user_id)
        if user.is_blocked:
            return redirect(url_for('admin_users'))

        logout_user()
        login_user(user)
        return redirect(url_for('index'))

    @app.route('/admin/users/<int:user_id>', methods=['GET', 'POST'])
    @admin_required
    def admin_user_detail(user_id):
        user = User.query.get_or_404(user_id)
        if request.method == 'POST':
            action = request.form.get('action')
            if action == 'block':
                user.is_blocked = True
                record_activity('Заблокировал пользователя', current_user, entity_type='user', entity_id=user.id, description=f'Пользователь {user.telegram_id}')
            elif action == 'unblock':
                user.is_blocked = False
                record_activity('Разблокировал пользователя', current_user, entity_type='user', entity_id=user.id, description=f'Пользователь {user.telegram_id}')
            elif action in ('make_admin', 'make_superadmin', 'make_user'):
                if not current_user.is_superadmin:
                    return redirect(url_for('admin_user_detail', user_id=user.id))
                if action == 'make_admin':
                    user.role = 'admin'
                    record_activity('Назначил администратора', current_user, entity_type='user', entity_id=user.id)
                elif action == 'make_superadmin':
                    user.role = 'superadmin'
                    record_activity('Назначил супер-администратора', current_user, entity_type='user', entity_id=user.id)
                else:
                    user.role = 'user'
                    record_activity('Снял административные права', current_user, entity_type='user', entity_id=user.id)
            elif action == 'delete':
                if not current_user.is_superadmin:
                    return redirect(url_for('admin_user_detail', user_id=user.id))
                record_activity('Удалил пользователя', current_user, entity_type='user', entity_id=user.id)
                db.session.delete(user)
                db.session.commit()
                return redirect(url_for('admin_users'))
            db.session.commit()
            return redirect(url_for('admin_user_detail', user_id=user.id, success='Действие выполнено'))

        active_debts = Debt.query.filter_by(user_id=user.id, status='active').count()
        archived_debts = Debt.query.filter_by(user_id=user.id, status='archived').count()
        payments = Payment.query.join(Debt).filter(Debt.user_id == user.id).count()
        recent_actions = ActivityLog.query.filter_by(user_id=user.id).order_by(ActivityLog.created_at.desc()).limit(20).all()
        return render_template('admin_user_detail.html', user=user, active_debts=active_debts, archived_debts=archived_debts, payments=payments, recent_actions=recent_actions, success_message=request.args.get('success'))

    @app.route('/admin/logs')
    @admin_required
    def admin_logs():
        logs = ActivityLog.query.order_by(ActivityLog.created_at.desc()).limit(100).all()
        return render_template('admin_logs.html', logs=logs)

    @app.route('/admin/export')
    @admin_required
    def admin_export():
        debts = Debt.query.order_by(Debt.created_at.desc()).limit(100).all()
        payments = Payment.query.order_by(Payment.payment_date.desc()).limit(100).all()
        return render_template('admin_export.html', debts=debts, payments=payments)

    @app.route('/admin/export/<string:export_type>.csv')
    @admin_required
    def admin_export_csv(export_type):
        output = StringIO()
        writer = csv.writer(output)

        if export_type == 'users':
            writer.writerow(['id', 'telegram_id', 'username', 'first_name', 'last_name', 'role', 'is_blocked', 'login_count', 'last_login_ip', 'last_user_agent', 'created_at'])
            for user in User.query.order_by(User.id.asc()).all():
                writer.writerow([
                    user.id,
                    user.telegram_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    user.role,
                    'yes' if user.is_blocked else 'no',
                    user.login_count,
                    user.last_login_ip,
                    user.last_user_agent,
                    user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else '',
                ])
            filename = 'users.csv'
        elif export_type == 'debts':
            writer.writerow(['id', 'user_id', 'bank_name', 'debt_type', 'product_name', 'total_amount', 'remaining_amount', 'status', 'next_payment_date', 'created_at', 'updated_at'])
            for debt in Debt.query.order_by(Debt.id.asc()).all():
                writer.writerow([
                    debt.id,
                    debt.user_id,
                    debt.bank_name,
                    debt.debt_type,
                    debt.product_name,
                    float(debt.total_amount),
                    float(debt.remaining_amount),
                    debt.status,
                    debt.next_payment_date.strftime('%Y-%m-%d') if debt.next_payment_date else '',
                    debt.created_at.strftime('%Y-%m-%d %H:%M:%S') if debt.created_at else '',
                    debt.updated_at.strftime('%Y-%m-%d %H:%M:%S') if debt.updated_at else '',
                ])
            filename = 'debts.csv'
        elif export_type == 'payments':
            writer.writerow(['id', 'debt_id', 'amount', 'payment_date', 'remaining_after_payment', 'comment', 'created_at'])
            for payment in Payment.query.order_by(Payment.id.asc()).all():
                writer.writerow([
                    payment.id,
                    payment.debt_id,
                    float(payment.amount),
                    payment.payment_date.strftime('%Y-%m-%d') if payment.payment_date else '',
                    float(payment.remaining_after_payment),
                    payment.comment,
                    payment.created_at.strftime('%Y-%m-%d %H:%M:%S') if payment.created_at else '',
                ])
            filename = 'payments.csv'
        else:
            return redirect(url_for('admin_export'))

        response = Response(output.getvalue(), mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename={filename}'
        return response
