# Simply Organice - E-Commerce Backend

## Description
Simply Organice is a Django REST Framework backend for a multi-branch e-commerce platform. It handles products, collections, orders, and branch-specific sales for Accra and Kumasi branches. This backend serves as the core system for managing products, orders, and branch-specific operations.

## Technologies Used
- Python 3.x
- Django
- Django REST Framework
- SQLite (default) or PostgreSQL
- Pillow (for handling product images)
- Django CORS Headers (for frontend integration)

## Features
- Multi-branch management (Accra & Kumasi)
- Product collections and categories
- Product CRUD with images and availability
- Order creation capturing both customer and recipient details
- Order items linking multiple products to a single order
- Branch-specific order filtering for admins
- Superuser control over the entire system

## Setup Instructions
1. Clone the repository:
   git clone <your-repo-url>
   cd ecommerce-backend

2. Create and activate virtual environment:
   python -m venv venv
   # Windows
   venv\Scripts\activate
   # Mac/Linux
   source venv/bin/activate

3. Install dependencies:
   pip install -r requirements.txt

4. Apply migrations and create superuser:
   python manage.py migrate
   python manage.py createsuperuser

5. Run development server:
   python manage.py runserver

6. Access admin panel:
   http://127.0.0.1:8000/admin/

## Models Overview
### Branch
Represents a physical branch (e.g., Accra, Kumasi). Fields: name

### Collection
Represents product categories (Cakes, Watches, etc.). Fields: name

### Product
Individual products under a collection. Fields: collection (FK), name, description, price, image, availability

### Order
Captures customer and recipient details along with branch and status. Fields: branch (FK), customer_name, customer_phone, recipient_name, recipient_phone, delivery_address, status, created_at

### OrderItem
Links products to orders. Fields: order (FK), product (FK), quantity, price_at_purchase

## Usage Notes
- No customer login is required; checkout captures customer and recipient info directly.
- Superuser has full control over branches, products, collections, and orders.
- Branch admins can only see their own branch’s orders.

## Future Improvements
- Payment gateway integration
- Advanced order status tracking and notifications
- Frontend dashboard for branch admins
- Analytics for sales per branch and product
