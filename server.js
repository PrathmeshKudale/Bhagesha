const express = require('express');
const cors = require('cors');
const app = express();
const PORT = 5000;

app.use(cors()); // Allows frontend to talk to backend
app.use(express.json());

// Mock Database (In real life, this comes from MongoDB)
const products = [
    {
        id: 1,
        name: "iPhone 15 Pro",
        price: 999,
        image: "https://via.placeholder.com/150",
        rating: 4.5
    },
    {
        id: 2,
        name: "Sony WH-1000XM5",
        price: 348,
        image: "https://via.placeholder.com/150",
        rating: 4.8
    },
    {
        id: 3,
        name: "MacBook Air M2",
        price: 1199,
        image: "https://via.placeholder.com/150",
        rating: 4.9
    },
    {
        id: 4,
        name: "Nike Air Jordan",
        price: 150,
        image: "https://via.placeholder.com/150",
        rating: 4.2
    }
];

// API Endpoint to get products
app.get('/api/products', (req, res) => {
    res.json(products);
});

// API Endpoint to place order
app.post('/api/order', (req, res) => {
    const { cart } = req.body;
    console.log("Order received for:", cart);
    res.json({ message: "Order Placed Successfully!" });
});

app.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
