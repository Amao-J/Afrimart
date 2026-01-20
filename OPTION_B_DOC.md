#  Integrating Afrimart Django Backend with React Frontend

Complete step-by-step guide for building a modern React frontend that conne

---

##  Table of Contents

1. [Overview](#overview)
2. [Backend API Setup](#backend-api-setup)
3. [React Frontend Setup](#react-frontend-setup)
4. [Authentication Implementation](#authentication-implementation)
5. [Product Display](#product-display)
6. [Currency Conversion](#currency-conversion)
7. [Cart Management](#cart-management)
8. [Complete Code Examples](#complete-code-examples)
9. [Deployment](#deployment)

---

## 🎯 Overview

This integration allows you to:
- Use Django as a REST API backend
- Build a modern React SPA (Single Page Application)
- Handle authentication with JWT tokens
- Display products with real-time currency conversion
- Manage shopping cart state
- Process payments with Flutterwave

**Architecture:**
```
React Frontend (localhost:3000)
        ↕ REST API (JSON)
Django Backend (localhost:8000)
        ↕
    Database
```


## ⚛️ React Frontend Setup

### Step 1: Create React App

```bash
npx create-react-app afrimart-frontend
cd afrimart-frontend
npm install axios react-router-dom
```

### Step 2: Create API Service

Create `src/services/api.js`:

```javascript
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Add token to requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  }
);

export const productsAPI = {
  getAll: (params) => api.get('/products/', { params }),
  getOne: (id) => api.get(`/products/${id}/`),
};

export const authAPI = {
  register: (data) => api.post('/auth/register/', data),
  login: (data) => api.post('/auth/login/', data),
};

export const categoriesAPI = {
  getAll: () => api.get('/categories/'),
};

export default api;
```

### Step 3: Create Product Card Component

Create `src/components/ProductCard.jsx`:

```jsx
import React from 'react';
import './ProductCard.css';

function ProductCard({ product }) {
  const getDiscountedPrice = () => {
    if (product.has_discount) {
      const discount = product.price * (product.discount_percentage / 100);
      return product.price - discount;
    }
    return product.price;
  };

  const getSavings = () => {
    return product.price - getDiscountedPrice();
  };

  return (
    <div className="product-card">
      {product.has_discount && (
        <div className="discount-badge">
          {Math.round(product.discount_percentage)}% OFF
        </div>
      )}

      <div className="product-image">
        {product.cloudinary_url ? (
          <img src={product.cloudinary_url} alt={product.name} />
        ) : (
          <div className="placeholder">No Image</div>
        )}
      </div>

      <div className="product-info">
        <h3>{product.name}</h3>
        
        <div className="price-section">
          {product.has_discount ? (
            <>
              <p className="original-price">₦{product.price.toLocaleString()}</p>
              <p className="discounted-price">₦{getDiscountedPrice().toLocaleString()}</p>
              <p className="savings">Save ₦{getSavings().toLocaleString()}</p>
            </>
          ) : (
            <p className="price">₦{product.price.toLocaleString()}</p>
          )}
        </div>

        <p className="stock">{product.stock} in stock</p>

        <button className="add-to-cart-btn">
          Add to Cart
        </button>
      </div>
    </div>
  );
}

export default ProductCard;
```

### Step 4: Create Product List Page

Create `src/pages/ProductList.jsx`:

```jsx
import React, { useState, useEffect } from 'react';
import { productsAPI } from '../services/api';
import ProductCard from '../components/ProductCard';
import './ProductList.css';

function ProductList() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await productsAPI.getAll({ featured: true });
      setProducts(response.data.results || response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="product-list-page">
      <h1>Featured Products</h1>
      <div className="product-grid">
        {products.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  );
}

export default ProductList;
```

### Step 5: Create Login Page

Create `src/pages/Login.jsx`:

```jsx
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import './Login.css';

function Login() {
  const [credentials, setCredentials] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const response = await authAPI.login(credentials);
      localStorage.setItem('access_token', response.data.access);
      localStorage.setItem('refresh_token', response.data.refresh);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      navigate('/');
    } catch (err) {
      setError('Invalid credentials');
    }
  };

  return (
    <div className="login-page">
      <form onSubmit={handleSubmit} className="login-form">
        <h2>Login</h2>
        {error && <p className="error">{error}</p>}
        
        <input
          type="text"
          placeholder="Username"
          value={credentials.username}
          onChange={(e) => setCredentials({...credentials, username: e.target.value})}
          required
        />
        
        <input
          type="password"
          placeholder="Password"
          value={credentials.password}
          onChange={(e) => setCredentials({...credentials, password: e.target.value})}
          required
        />
        
        <button type="submit">Login</button>
      </form>
    </div>
  );
}

export default Login;
```

### Step 6: Create App Component

Update `src/App.js`:

```jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import ProductList from './pages/ProductList';
import Login from './pages/Login';
import './App.css';

function App() {
  return (
    <Router>
      <div className="App">
        <header>
          <h1>Afrimart</h1>
        </header>
        
        <main>
          <Routes>
            <Route path="/" element={<ProductList />} />
            <Route path="/login" element={<Login />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}

export default App;
```

---

## 🎨 CSS Styling

### ProductCard.css

Create `src/components/ProductCard.css`:

```css
.product-card {
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: transform 0.3s;
  position: relative;
}

.product-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.15);
}

.discount-badge {
  position: absolute;
  top: 10px;
  right: 10px;
  background: linear-gradient(135deg, #ff416c, #ff4b2b);
  color: white;
  padding: 6px 12px;
  border-radius: 20px;
  font-size: 12px;
  font-weight: bold;
  z-index: 10;
}

.product-image {
  height: 250px;
  overflow: hidden;
}

.product-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.placeholder {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  color: #999;
}

.product-info {
  padding: 15px;
}

.product-info h3 {
  font-size: 16px;
  margin-bottom: 10px;
  color: #333;
}

.original-price {
  text-decoration: line-through;
  color: #999;
  font-size: 14px;
  margin: 0;
}

.discounted-price {
  color: #ff4b2b;
  font-size: 24px;
  font-weight: bold;
  margin: 5px 0;
}

.savings {
  color: #28a745;
  font-size: 12px;
  font-weight: 600;
  margin: 0;
}

.price {
  font-size: 20px;
  font-weight: bold;
  color: #667eea;
}

.stock {
  font-size: 12px;
  color: #666;
  margin: 10px 0;
}

.add-to-cart-btn {
  width: 100%;
  padding: 12px;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: transform 0.2s;
}

.add-to-cart-btn:hover {
  transform: translateY(-2px);
}
```

### ProductList.css

Create `src/pages/ProductList.css`:

```css
.product-list-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 20px;
}

.product-list-page h1 {
  text-align: center;
  margin-bottom: 40px;
  font-size: 32px;
  color: #333;
}

.product-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
  gap: 30px;
}

@media (max-width: 768px) {
  .product-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 15px;
  }
}
```

---

## 🚀 Running the Application

### Start Django Backend

```bash
# Terminal 1
cd backend
python manage.py runserver
# Runs on http://localhost:8000
```

### Start React Frontend

```bash
# Terminal 2
cd afrimart-frontend
npm start
# Runs on http://localhost:3000
```

---

## 📦 API Endpoints Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/products/` | List all products |
| GET | `/api/products/?featured=true` | Get featured products |
| GET | `/api/products/?category=1` | Filter by category |
| GET | `/api/products/{id}/` | Get single product |
| GET | `/api/categories/` | List categories |
| POST | `/api/auth/register/` | Register user |
| POST | `/api/auth/login/` | Login user |

---

## 🎉 Summary

You now have:
- ✅ Django REST API backend
- ✅ React frontend with routing
- ✅ Product display with discounts
- ✅ Authentication system
- ✅ Responsive design

**Next Steps:**
1. Add cart management
2. Implement checkout
3. Add payment integration
4. Create user dashboard
5. Deploy to production

Happy coding! 🚀
