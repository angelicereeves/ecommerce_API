# E-Commerce API (Flask + MySQL)

A fully functional RESTful API for managing users, products, and orders.  
Built with Flask, SQLAlchemy, and Marshmallow, and connected to a MySQL database.  
Functional CRUD operations, many-to-many relationships between orders and products, and input validation.



#Features

- Users
  - Create, read, update, and delete users
  - Unique email constraint
- Products
  - Create, read, update, and delete products
  - Price validation
- Orders
  - Create orders for users
  - Add or remove products from orders
  - List all orders for a user
  - List all products in a specific order
- Data validation with Marshmallow schemas
- Association table (order_product) to handle many-to-many relationship between orders and products
- Duplicate prevention in association table
- Error handling for invalid IDs and bad requests
- Database initialization route for quick setup

---

#Techs used

- **Python** 3.11+
- **Flask** (web framework)
- **Flask-SQLAlchemy** (ORM)
- **Flask-Marshmallow** (serialization & validation)
- **MySQL** (database)
- **MySQL Connector/Python** (driver)

---

#Setup Instructions

1. Clone the repository - https://github.com/angelicereeves/ecommerce_API
git clone https://github.com/angelicereeves/ecommerce_API
cd ecommerce_API

2. set up a venv: 
python -m venv venv
source venv/bin/activate      # Mac/Linux
venv\Scripts\activate         # Windows

3. install dependencies:
pip install Flask Flask-SQLAlchemy Flask-Marshmallow marshmallow mysql-connector-python

4. configure DB connection:
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv(
    'DATABASE_URL',
    'mysql+mysqlconnector://root:0829AmDAjD23%3C3%21@localhost/ecommerce_api'
)

5. create DB in MySQL
CREATE DATABASE ecommerce_api;

6. initialize tables:
flask - POST http://127.0.0.1:5000/initdb






