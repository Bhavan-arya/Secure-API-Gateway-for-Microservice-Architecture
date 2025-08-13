from flask import Flask, request, jsonify
import bcrypt

app = Flask(__name__)

# In-memory storage for users
users = []

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"})


@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400

    # Check if user already exists
    if any(u['username'] == data['username'] for u in users):
        return jsonify({'error': 'Username already exists'}), 409

    # Hash password
    hashed = bcrypt.hashpw(data['password'].encode('utf-8'), bcrypt.gensalt())

    user = {
        'id': len(users) + 1,
        'username': data['username'],
        'password': hashed,
        'email': data.get('email', '')
    }
    users.append(user)
    return jsonify({'message': 'User created successfully', 'user_id': user['id']}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data or 'username' not in data or 'password' not in data:
        return jsonify({'error': 'Username and password required'}), 400

    user = next((u for u in users if u['username'] == data['username']), None)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if bcrypt.checkpw(data['password'].encode('utf-8'), user['password']):
        return jsonify({'message': 'Login successful', 'user_id': user['id']}), 200

    return jsonify({'error': 'Invalid password'}), 401


@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user['id'],
        'username': user['username'],
        'email': user['email']
    }), 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
