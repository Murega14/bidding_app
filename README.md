# Bidding App

A Flask-based RESTful API for managing online product bidding.

## Features

- User and Admin authentication
- Product management
- Real-time bidding
- Bid tracking and history
- Secure password hashing
- JWT-based authorization

## Setup

1. Clone the repository
```bash
git clone <repository-url>
cd bidding_app
```

2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate  # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
SECRET_KEY=your_secret_key
JWT_KEY=your_jwt_key
```

5. Initialize database
```bash
flask db init
flask db migrate
flask db upgrade
```

## API Endpoints

### Admin Routes
- `POST /api/v1/signup` - Create admin account
- `POST /api/v1/admin/login` - Admin login
- `POST /api/v1/admin/product/add` - Add new product
- `PUT /api/v1/admin/id/end` - End bidding manually
- `GET /api/v1/products/sold` - View sold products

### User Routes
- `POST /api/v1/user/signup` - Create user account
- `POST /api/v1/user/login` - User login
- `GET /api/v1/products` - View available products
- `POST /api/v1/products/<id>/bid` - Place bid on product

## Technologies Used

- Flask
- SQLAlchemy
- Flask-JWT-Extended
- SQLite
- Python 3.x