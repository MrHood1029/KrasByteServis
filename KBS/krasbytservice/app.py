from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from models import db, User, Client, Order, SparePart, Employee, OrderStatus
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from flask import request, jsonify


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///krasbytservice.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))



def calculate_total_profit():
    """Расчет общей прибыли по всем заказам"""
    total_profit = 0
    for order in Order.query.all():
        profit = (order.sale_price or 0) - (order.repair_costs or 0) - (order.purchase_price or 0)
        total_profit += profit
    return total_profit


def get_status_badge_class(status_id):
    """Получение класса CSS для статуса"""
    classes = {
        1: 'primary',  # Новая
        2: 'info',  # В обработке
        3: 'warning',  # В ремонте
        4: 'success',  # Выполнена
        5: 'danger'  # Отменена
    }
    return classes.get(status_id, 'secondary')


# Добавляем функции в контекст шаблонов
@app.context_processor
def utility_processor():
    return {
        'calculate_total_profit': calculate_total_profit,
        'get_status_badge_class': get_status_badge_class
    }


@app.route('/orders')
@login_required
def orders():
    orders_list = Order.query.order_by(Order.created_at.desc()).all()
    statuses = OrderStatus.query.all()
    employees = Employee.query.all()
    clients = Client.query.all()

    return render_template('orders.html',
                           orders=orders_list,
                           statuses=statuses,
                           employees=employees,
                           clients=clients)


@app.route('/add_order', methods=['POST'])
@login_required
def add_order():
    if request.method == 'POST':
        try:
            new_order = Order(
                client_id=request.form['client_id'],
                washing_machine_model=request.form['model'],
                description=request.form.get('description', ''),
                status_id=request.form['status_id'],
                employee_id=request.form.get('employee_id') or None,
                purchase_price=float(request.form.get('purchase_price', 0)) or None,
                repair_costs=float(request.form.get('repair_costs', 0)) or None,
                sale_price=float(request.form.get('sale_price', 0)) or None,
                created_at=datetime.now()
            )
            db.session.add(new_order)
            db.session.commit()
            flash('Заказ успешно создан')
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при создании заказа')

    return redirect(url_for('orders'))


@app.route('/delete_order/<int:order_id>', methods=['DELETE'])
@login_required
def delete_order(order_id):
    try:
        order = Order.query.get(order_id)
        if order:
            db.session.delete(order)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Заказ не найден'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/order_details/<int:order_id>')
@login_required
def order_details(order_id):
    try:
        order = Order.query.get(order_id)
        if order:
            profit = (order.sale_price or 0) - (order.repair_costs or 0) - (order.purchase_price or 0)

            return jsonify({
                'success': True,
                'order': {
                    'id': order.id,
                    'client_name': order.client.name,
                    'client_phone': order.client.phone,
                    'client_email': order.client.email,
                    'client_address': order.client.address,
                    'model': order.washing_machine_model,
                    'description': order.description,
                    'status': order.status.name,
                    'status_class': get_status_badge_class(order.status_id),
                    'master': order.employee.name if order.employee else None,
                    'created_date': order.created_at.strftime('%d.%m.%Y'),
                    'purchase_price': order.purchase_price,
                    'repair_costs': order.repair_costs,
                    'sale_price': order.sale_price,
                    'profit': profit
                }
            })
        return jsonify({'success': False, 'error': 'Заказ не найден'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/dashboard')
@login_required
def dashboard():
    total_orders = Order.query.count()
    active_orders = Order.query.filter(Order.status_id != 4).count()  # 4 - Выполнена
    total_clients = Client.query.count()
    low_stock_parts = SparePart.query.filter(SparePart.quantity <= SparePart.min_stock).count()

    # Последние 5 заказов
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    return render_template('dashboard.html',
                           total_orders=total_orders,
                           active_orders=active_orders,
                           total_clients=total_clients,
                           low_stock_parts=low_stock_parts,
                           recent_orders=recent_orders)


@app.route('/clients')
@login_required
def clients():
    clients_list = Client.query.all()
    return render_template('clients.html', clients=clients_list)
def calculate_client_total(client):
    """Вспомогательная функция для расчета общей суммы заказов клиента"""
    total = 0
    for order in client.orders:
        if order.sale_price:
            total += order.sale_price
        elif order.repair_costs:
            total += order.repair_costs
    return total

@app.template_filter('strftime')
def strftime_filter(date, format_string='%Y-%m-%d'):
    if isinstance(date, str):
        date = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
    return date.strftime(format_string)

# Добавляем функцию в контекст шаблонов
@app.context_processor
def utility_processor():
    return dict(calculate_client_total=calculate_client_total)


@app.route('/add_client', methods=['POST'])
@login_required
def add_client():
    if request.method == 'POST':
        try:
            new_client = Client(
                name=request.form['name'],
                phone=request.form['phone'],
                email=request.form.get('email', ''),
                address=request.form.get('address', '')
            )
            db.session.add(new_client)
            db.session.commit()
            flash('Клиент успешно добавлен')
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при добавлении клиента')

    return redirect(url_for('clients'))


@app.route('/edit_client', methods=['POST'])
@login_required
def edit_client():
    if request.method == 'POST':
        try:
            client_id = request.form['client_id']
            client = Client.query.get(client_id)

            if client:
                client.name = request.form['name']
                client.phone = request.form['phone']
                client.email = request.form.get('email', '')
                client.address = request.form.get('address', '')

                db.session.commit()
                flash('Данные клиента успешно обновлены')
            else:
                flash('Клиент не найден')
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при обновлении данных клиента')

    return redirect(url_for('clients'))


@app.route('/delete_client/<int:client_id>', methods=['DELETE'])
@login_required
def delete_client(client_id):
    try:
        client = Client.query.get(client_id)
        if client:
            # Удаляем связанные заказы
            for order in client.orders:
                db.session.delete(order)
            db.session.delete(client)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Клиент не найден'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/client_details/<int:client_id>')
@login_required
def client_details(client_id):
    try:
        client = Client.query.get(client_id)
        if client:
            orders_data = []
            for order in client.orders:
                orders_data.append({
                    'id': order.id,
                    'date': order.created_at.strftime('%d.%m.%Y'),
                    'service': order.washing_machine_model,
                    'amount': order.sale_price or order.repair_costs or 0,
                    'status': order.status.name,
                    'status_class': 'success' if order.status_id == 4 else 'warning'
                })

            total_orders = len(client.orders)
            total_amount = calculate_client_total(client)
            avg_order = total_amount / total_orders if total_orders > 0 else 0

            return jsonify({
                'success': True,
                'client': {
                    'name': client.name,
                    'phone': client.phone,
                    'email': client.email,
                    'address': client.address,
                    'created_at': client.created_at.strftime('%d.%m.%Y'),
                    'orders_count': total_orders,
                    'total_amount': total_amount,
                    'avg_order': avg_order,
                    'last_order': client.orders[-1].created_at.strftime('%d.%m.%Y') if client.orders else None
                },
                'orders': orders_data
            })
        return jsonify({'success': False, 'error': 'Клиент не найден'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/warehouse')
@login_required
def warehouse():
    spare_parts = SparePart.query.all()
    return render_template('warehouse.html', spare_parts=spare_parts)


@app.route('/add_spare_part', methods=['POST'])
@login_required
def add_spare_part():
    if request.method == 'POST':
        try:
            new_part = SparePart(
                name=request.form['name'],
                article=request.form['article'],
                quantity=int(request.form['quantity']),
                min_stock=int(request.form['min_stock']),
                cost_price=float(request.form['cost_price']),
                retail_price=float(request.form['retail_price'])
            )
            db.session.add(new_part)
            db.session.commit()
            flash('Запчасть успешно добавлена')
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при добавлении запчасти')

    return redirect(url_for('warehouse'))


@app.route('/edit_spare_part', methods=['POST'])
@login_required
def edit_spare_part():
    if request.method == 'POST':
        try:
            part_id = request.form['part_id']
            part = SparePart.query.get(part_id)

            if part:
                part.name = request.form['name']
                part.article = request.form['article']
                part.quantity = int(request.form['quantity'])
                part.min_stock = int(request.form['min_stock'])
                part.cost_price = float(request.form['cost_price'])
                part.retail_price = float(request.form['retail_price'])

                db.session.commit()
                flash('Запчасть успешно обновлена')
            else:
                flash('Запчасть не найдена')
        except Exception as e:
            db.session.rollback()
            flash('Ошибка при обновлении запчасти')

    return redirect(url_for('warehouse'))


@app.route('/delete_spare_part/<int:part_id>', methods=['DELETE'])
@login_required
def delete_spare_part(part_id):
    try:
        part = SparePart.query.get(part_id)
        if part:
            db.session.delete(part)
            db.session.commit()
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Запчасть не найдена'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})



@app.route('/reports')
@login_required
def reports():
    # Получаем сотрудников для фильтров
    employees = Employee.query.all()

    # Устанавливаем даты по умолчанию (текущий месяц)
    today = datetime.now()
    first_day = today.replace(day=1)
    last_day = (first_day + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    return render_template('reports.html',
                           employees=employees,
                           default_date_from=first_day.strftime('%Y-%m-%d'),
                           default_date_to=last_day.strftime('%Y-%m-%d'))


@app.route('/api/generate_report', methods=['POST'])
@login_required
def generate_report():
    try:
        data = request.get_json()
        report_type = data.get('type')
        date_from = datetime.strptime(data.get('date_from'), '%Y-%m-%d')
        date_to = datetime.strptime(data.get('date_to'), '%Y-%m-%d')

        # Здесь будет логика генерации реальных отчетов из базы данных
        # Пока возвращаем тестовые данные

        if report_type == 'financial':
            report_data = {
                'total_revenue': 288900,
                'total_profit': 86670,
                'total_orders': 144,
                'categories': [
                    {'name': 'Продажи техники', 'count': 15, 'amount': 187500, 'percentage': 65},
                    {'name': 'Ремонтные услуги', 'count': 42, 'amount': 84000, 'percentage': 29},
                    {'name': 'Запчасти', 'count': 87, 'amount': 17400, 'percentage': 6}
                ]
            }
        else:
            report_data = {'message': 'Отчет в разработке'}

        return jsonify({'success': True, 'data': report_data})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/buy_request', methods=['GET', 'POST'])
def buy_request():
    if request.method == 'POST':
        # Обработка заявки на скупку
        name = request.form['name']
        phone = request.form['phone']
        model = request.form['model']
        condition = request.form['condition']
        description = request.form['description']

        # Сохранение заявки в базу
        new_client = Client(
            name=name,
            phone=phone,
            email='',
            address=''
        )
        db.session.add(new_client)
        db.session.flush()

        new_order = Order(
            client_id=new_client.id,
            washing_machine_model=model,
            condition=condition,
            description=description,
            status_id=1,  # Новая заявка
            created_at=datetime.now()
        )
        db.session.add(new_order)
        db.session.commit()

        flash('Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.')
        return redirect(url_for('index'))

    return render_template('buy_request.html')


@app.route('/repair_status')
def repair_status():
    return render_template('repair_status.html')


@app.route('/api/check_status', methods=['POST'])
def check_status():
    order_id = request.form.get('order_id')
    phone = request.form.get('phone')

    order = Order.query.filter_by(id=order_id).first()
    if order and order.client.phone == phone:
        return jsonify({
            'status': order.status.name,
            'model': order.washing_machine_model,
            'description': order.description
        })
    else:
        return jsonify({'error': 'Заказ не найден'})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # Создание тестовых данных
        if not User.query.first():
            admin = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)

            # Статусы заказов
            statuses = [
                OrderStatus(name='Новая', description='Новая заявка'),
                OrderStatus(name='В обработке', description='Заявка в обработке'),
                OrderStatus(name='В ремонте', description='Стиральная машина в ремонте'),
                OrderStatus(name='Выполнена', description='Заказ завершен'),
                OrderStatus(name='Отменена', description='Заказ отменен')
            ]
            db.session.add_all(statuses)
            db.session.commit()

    app.run(debug=True)