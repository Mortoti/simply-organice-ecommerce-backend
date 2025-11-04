# 🛍️ Simply Organice – E-Commerce Backend

## Overview
**Simply Organice** is a Django REST Framework backend for a multi-branch e-commerce platform.
It powers product management, collections, orders, and branch-specific operations for **Accra** and **Kumasi** branches.
Now enhanced with **JWT Authentication**, the system ensures secure access for users and administrators.
Users **must log in before placing orders**.

---

## 🧰 Tech Stack
- **Python 3.x**
- **Django**
- **Django REST Framework (DRF)**
- **Simple JWT** (for authentication)
- **SQLite / PostgreSQL**
- **Pillow** (for image handling)
- **Django CORS Headers** (for frontend integration)

---

## 🚀 Core Features
- 🔐 **JWT Authentication** for secure login and API access
- 🏬 **Multi-branch management** (Accra & Kumasi)
- 🗂️ **Collections & categories** for products
- 🛒 **Product CRUD** with image upload and availability control
- 📦 **Order creation** (only for authenticated users)
- 🔗 **Order items** linking multiple products to a single order
- 📍 **Branch-specific order visibility** for admins
- 👑 **Superuser control** across all branches and operations

---

## ⚙️ Setup Instructions

1.  **Clone the repository**
    ```bash
    git clone <your-repo-url>
    cd ecommerce-backend
    ```

2.  **Create and activate a virtual environment**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

3.  **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Apply migrations and create superuser**
    ```bash
    python manage.py migrate
    python manage.py createsuperuser
    ```

5.  **Run the development server**
    ```bash
    python manage.py runserver
    ```

6.  **Access the admin panel**
    URL: `http://127.0.0.1:8000/admin/`

---

## 🧩 Models Overview

**Branch**
* Represents a physical branch location (e.g., Accra, Kumasi).
* Fields: `name`

**Collection**
* Represents product categories (e.g., Cakes, Watches, etc.).
* Fields: `name`

**Product**
* Individual products under a collection.
* Fields: `collection` (FK), `name`, `description`, `price`, `image`, `availability`

**Order**
* Captures order details tied to authenticated users, including customer and recipient info.
* Fields: `user` (FK), `branch` (FK), `customer_name`, `customer_phone`, `recipient_name`, `recipient_phone`, `delivery_address`, `status`, `created_at`

**OrderItem**
* Links products to specific orders.
* Fields: `order` (FK), `product` (FK), `quantity`, `price_at_purchase`

---

## 🔑 Authentication (JWT)
All authenticated routes require a valid JWT token.

**Endpoints**
* `POST /api/token/` → Obtain access and refresh tokens
* `POST /api/token/refresh/` → Refresh access token

**Header Format:**
```makefile
Authorization: Bearer <access_token>
