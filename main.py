from flask import *
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import config
import datetime

correct = True

app = Flask(__name__)
app.config['SECRET_KEY'] = config.secret_key

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


class Users(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250))
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    api_key = db.Column(db.String(18), unique=True)
    plan = db.Column(db.String(100))


class Business(db.Model):
    __tablename__ = 'business'
    id = db.Column(db.Integer, primary_key=True)
    business_name = db.Column(db.String(250), nullable=False)
    business_email = db.Column(db.String(100), nullable=False)
    business_phone_no = db.Column(db.String(14), nullable=False)
    business_website = db.Column(db.String(250))
    api_key = db.Column(db.String(18), nullable=False)

    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary


class Orders(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    api_key = db.Column(db.String(18), nullable=False)
    customer_name = db.Column(db.String(250), nullable=False)
    customer_address = db.Column(db.String(200), nullable=False)
    product_name = db.Column(db.String(250), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    time = db.Column(db.String(250), nullable=False)
    business_name = db.Column(db.String(250), nullable=False)

    def to_dict(self):
        dictionary = {}
        for column in self.__table__.columns:
            dictionary[column.name] = getattr(self, column.name)
        return dictionary


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = request.args.get('error')
    all_users = db.session.query(Users).all()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('pass')
        verified_user = Users.query.filter_by(email=email).first()
        if verified_user in all_users:
            checked_password = check_password_hash(verified_user.password, password)
            if checked_password:
                login_user(verified_user)
                user_name = verified_user.name
                api_key = verified_user.api_key
                return redirect(url_for('dashboard', logged_in=current_user.is_authenticated,
                                        name=user_name, api_key=api_key))
            else:
                error = 'Incorrect password. Please try again'
                return redirect(url_for('login', error=error))
        else:
            error = 'That email address does not exist. Please try again'
            return redirect(url_for('login', error=error))
    return render_template('login.html', error=error)


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    error = request.args.get('error')
    all_users = db.session.query(Users).all()
    if request.method == 'POST':
        name = request.form.get('name').title()
        email = request.form.get('email')
        plan = request.form.get('plan').title()
        password = request.form.get('pass')
        verify_new_user = Users.query.filter_by(email=email).first()
        if verify_new_user in all_users:
            error = 'That email address is already used. Log in instead?'
            return redirect(url_for('login', error=error))
        api_key = config.api_key_generator()
        for user in all_users:
            if user.api_key == api_key:
                api_key = config.api_key_generator()
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=8)
        new_user = Users(name=name, email=email, password=hashed_password, api_key=api_key, plan=plan)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login', error=error))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    name = request.args.get('name')
    api_key = request.args.get('api_key')
    verified_businesses = Business.query.filter_by(api_key=api_key).all()
    business_names = [business.business_name for business in verified_businesses]
    return render_template('dashboard.html', logged_in=current_user.is_authenticated,
                           current_user=current_user, name=name, api_key=api_key, businesses=verified_businesses, )


@app.route('/docs')
def docs():
    return render_template('docs.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    return render_template('contact.html')


@app.route('/listings')
@login_required
def listings():
    api_key = request.args.get('api_key')
    user = Users.query.filter_by(api_key=api_key).first()
    business_name = request.args.get('business_name')
    verify_api_key = Orders.query.filter_by(api_key=api_key).all()
    orders = [order.to_dict() for order in verify_api_key if order.business_name == business_name]
    return render_template('order_listings.html', orders=orders, logged_in=current_user.is_authenticated,
                           name=user.name, api_key=user.api_key)


@app.route('/del_order')
@login_required
def del_order():
    business_name = request.args.get('business_name')
    api_key = request.args.get('api_key')
    order_id = request.args.get('id')
    order_to_delete = Orders.query.get(int(order_id))
    db.session.delete(order_to_delete)
    db.session.commit()
    return redirect(url_for('listings', api_key=api_key, business_name=business_name, logged_in=current_user.is_authenticated))


@app.route('/del_business')
@login_required
def del_business():
    business_id = request.args.get('id')
    api_key = request.args.get('api_key')
    business_name = request.args.get('business_name').title()
    business_to_delete = Business.query.get(int(business_id))
    db.session.delete(business_to_delete)
    db.session.commit()
    user = Users.query.filter_by(api_key=api_key).first()
    verify_order_id = Orders.query.filter_by(api_key=api_key).all()

    orders_to_delete = []
    for order in verify_order_id:
        if order.business_name == business_name:
            orders_to_delete.append(order.id)

    for orders in orders_to_delete:
        o_t_d = Orders.query.get(orders)
        db.session.delete(o_t_d)
        db.session.commit()

    return redirect(url_for('dashboard', api_key=api_key, name=user.name))


@app.route('/business_setup', methods=['GET', 'POST'])
@login_required
def business_reg():
    error = request.args.get('error')
    if request.method == 'POST':
        busines_name = request.form.get('biz_name').title()
        business_email = request.form.get('biz_email')
        business_website = request.form.get('biz_website')
        business_phone_no = request.form.get('biz_phone_no')
        api_key = request.args.get('api_key')
        verify_business_name = Business.query.filter_by(api_key=api_key).all()

        if not verify_business_name:
            new_business = Business(business_name=busines_name, business_email=business_email,
                                    business_phone_no=business_phone_no, business_website=business_website,
                                    api_key=api_key)
            db.session.add(new_business)
            db.session.commit()
            return redirect(url_for('order', api_key=api_key, business_name=busines_name, logged_in=current_user.is_authenticated))
        else:
            all_business_names = []
            for business in verify_business_name:
                all_business_names.append(business.business_name)

            if request.form.get('biz_name').title() in all_business_names:
                return jsonify(error="You already have a business with this name")
            else:
                new_business = Business(business_name=busines_name, business_email=business_email,
                                        business_phone_no=business_phone_no,
                                        business_website=business_website,
                                        api_key=api_key)
                db.session.add(new_business)
                db.session.commit()
                return redirect(url_for('order', api_key=api_key, business_name=busines_name, logged_in=current_user.is_authenticated))

    return render_template('business_signup.html', error=error)


@app.route('/order', methods=['GET', 'POST'])
def order():
    message = request.args.get('message')
    if request.method == 'POST':
        api_key = request.args.get('api_key')
        business_name = request.args.get('business_name').title()
        customer_name = request.form.get('cus_name')
        customer_address = request.form.get('address')
        product = request.form.get('product_name')
        qty = request.form.get('qty')
        time = datetime.datetime.now()
        verify_api_key = Users.query.filter_by(api_key=api_key).first()
        verify_business = Business.query.filter_by(api_key=api_key).all()

        business_names = []

        for business in verify_business:
            business_names.append(business.business_name)

        if api_key == verify_api_key.api_key:
            if business_name in business_names:
                new_order = Orders(api_key=api_key,
                                   customer_name=customer_name,
                                   customer_address=customer_address,
                                   product_name=product,
                                   quantity=qty,
                                   time=time,
                                   business_name=business_name)
                db.session.add(new_order)
                db.session.commit()
                message = 'Your order has been successfully received.'
                return redirect(url_for('order', message=message, logged_in=current_user.is_authenticated))

    return render_template('order.html', message=message, logged_in=current_user.is_authenticated)


@app.route('/all_orders')
def get_all_orders():
    api_key = request.args.get('api-key')
    business_name = request.args.get('business_name').title()
    verify_api_key = Orders.query.filter_by(api_key=api_key).all()

    if not verify_api_key:
        return jsonify(error='Invalid API key')
    else:
        return jsonify(orders=[order.to_dict() for order in verify_api_key if order.business_name == business_name])


@app.route('/all_businesses')
def get_all_businesses():
    global correct
    api_key = request.args.get('api-key')
    verified_businesses = Business.query.filter_by(api_key=api_key).all()
    verify_api = Users.query.filter_by(api_key=api_key).first()
    all_businesses = []

    for business in verified_businesses:
        all_businesses.append(business.business_name)

    try:
        if api_key == verify_api.api_key:
            correct = True

    except AttributeError:
        correct = False

    if all_businesses == [] and correct == True:
        return jsonify(businesses=[business.to_dict() for business in verified_businesses])

    if all_businesses != [] and correct == True:
        return jsonify(businesses=[business.to_dict() for business in verified_businesses])

    if all_businesses != [] and correct == False:
        return jsonify(error='Invalid API key')

    if all_businesses == [] and correct == False:
        return jsonify(error='Invalid API key')


@app.route('/add_business', methods=['GET', 'POST'])
def add_business():
    busines_name = request.args.get('business_name').title()
    business_email = request.args.get('business_email')
    business_phone_no = request.args.get('business_phone_number')
    business_website = request.args.get('business_website')
    api_key = request.args.get('api-key')

    verify_api_key = Users.query.filter_by(api_key=api_key).all()
    verify_business_name = Business.query.filter_by(api_key=api_key).all()

    if not verify_api_key:
        return jsonify(error={'Invalid API key': 'Your API key is incorrect. Please check again'})
    else:
        if not verify_business_name:
            new_business = Business(business_name=busines_name, business_email=business_email,
                                    business_phone_no=business_phone_no, business_website=business_website,
                                    api_key=api_key)
            db.session.add(new_business)
            db.session.commit()
            return jsonify(response={'Success': 'Successfully added new business'})
        else:
            all_business_names = []
            for business in verify_business_name:
                all_business_names.append(business.business_name)

            if request.args.get('business_name').title() in all_business_names:
                return jsonify(error="You already have a business with this name")
            else:
                new_business = Business(business_name=busines_name, business_email=business_email,
                                        business_phone_no=business_phone_no,
                                        business_website=business_website,
                                        api_key=api_key)
                db.session.add(new_business)
                db.session.commit()
                return jsonify(response={'Success': 'Successfully added new business'})


@app.route('/add_order', methods=['GET', 'POST'])
def add_order():
    busines_name = request.args.get('business_name').title()
    api_key = request.args.get('api-key')
    customer_name = request.args.get('customer_name')
    customer_address = request.args.get('customer_address')
    product = request.args.get('product_name')
    qty = request.args.get('quantity')
    time = datetime.datetime.now()
    verify_api = Business.query.filter_by(api_key=api_key).all()
    verify_user = Users.query.filter_by(api_key=api_key).first()

    business_api = []
    business_names = []

    for business in verify_api:
        business_api.append(business.api_key)
        business_names.append(business.business_name)

    if api_key == verify_user.api_key:
        if busines_name in business_names:
            new_order = Orders(api_key=api_key,
                               customer_name=customer_name,
                               customer_address=customer_address,
                               product_name=product,
                               quantity=qty,
                               time=time,
                               business_name=busines_name)
            db.session.add(new_order)
            db.session.commit()
            return jsonify(Success='New order has been successfully added.')
        else:
            return jsonify(error="You don't have any business with that name")
    else:
        return jsonify(error='Invalid API key')


@app.route('/delete_order', methods=['GET', 'DELETE'])
def delete_order():
    order_id = request.args.get('id')
    busines_name = request.args.get('business_name').title()
    api_key = request.args.get('api-key')
    verified_businesses = Orders.query.filter_by(business_name=busines_name).all()
    verify_api = Users.query.filter_by(api_key=api_key).first()

    all_order_ids = []
    all_business_names = []
    apis = []

    for business in verified_businesses:
        all_order_ids.append(business.id)
        all_business_names.append(business.business_name)
        apis.append(business.api_key)

    try:
        if api_key in apis and api_key == verify_api.api_key:
            if busines_name in all_business_names:
                order_id = int(order_id)
                if order_id in all_order_ids:
                    order_to_delete = Orders.query.get(order_id)
                    db.session.delete(order_to_delete)
                    db.session.commit()
                    return jsonify(Success="The order has been successfully deleted")
                else:
                    return jsonify(error="Your business does'nt have an order with that id")
            else:
                return jsonify(error='Incorrect business name')
        else:
            return jsonify(error='Invalid API key or non-existing order ID')
    except AttributeError:
        return jsonify(error='Invalid API key')


@app.route('/delete_business', methods=['GET', 'DELETE'])
def delete_business():
    busines_name = request.args.get('business_name').title()
    api_key = request.args.get('api-key')

    verified_businesses = Business.query.filter_by(api_key=api_key).all()
    verify_api = Users.query.filter_by(api_key=api_key).first()
    verify_order_id = Orders.query.filter_by(api_key=api_key).all()

    business_names = {}
    orders_to_delete = []

    for business in verified_businesses:
        business_names[business.business_name] = business.id

    for order in verify_order_id:
        if order.business_name == busines_name:
            orders_to_delete.append(order.id)

    if not verified_businesses:
        return jsonify(error="Invalid API key")
    else:
        if verify_api.api_key == api_key:
            if busines_name in business_names.keys():
                business_to_delete = Business.query.get(business_names[busines_name])
                db.session.delete(business_to_delete)
                db.session.commit()
                for orders in orders_to_delete:
                    o_t_d = Orders.query.get(orders)
                    db.session.delete(o_t_d)
                    db.session.commit()
                return jsonify(Deleted='Business has been successfully deleted')
            else:
                return jsonify(error="You don't have any business with the given business name in our database")
        else:
            return jsonify(error='Invalid API key')


if __name__ == '__main__':
    app.run(debug=True)
